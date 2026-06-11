# ────────────────────────────────
# algorithm.py  —  충돌 검사 및 시간표 탐색
# ────────────────────────────────

import time
from itertools import combinations
from data_loader import (load_data, time_to_min,
                         get_subject_branches, get_courses_by_category,
                         get_courses_by_domain)
from config import (MAX_CREDITS, MAX_CREDITS_HONOR,
                    LIBERAL_AREA_DOMAINS, LIBERAL_AREA_COUNT)
from filters import passes_filters


# ── 충돌 검사 ──────────────────────────────────────────

def is_conflict(r1: dict, r2: dict) -> bool:
    """두 수업 행이 요일·시간 충돌하는지 확인"""
    d1, d2 = str(r1.get("요일", "")), str(r2.get("요일", ""))
    if d1 != d2 or d1 in ("", "nan"):
        return False
    s1, e1 = time_to_min(r1.get("시작", "")), time_to_min(r1.get("종료", ""))
    s2, e2 = time_to_min(r2.get("시작", "")), time_to_min(r2.get("종료", ""))
    if s1 < 0 or s2 < 0:
        return False
    return s1 < e2 and s2 < e1


def has_any_conflict(rows: list) -> bool:
    """행 목록 내 충돌이 하나라도 있으면 True"""
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if is_conflict(rows[i], rows[j]):
                return True
    return False


def conflicts_with_fixed(candidate_rows: list, fixed_rows: list) -> bool:
    """후보 과목 행들이 fixed 과목 행들과 충돌하는지 확인"""
    for cr in candidate_rows:
        for fr in fixed_rows:
            if is_conflict(cr, fr):
                return True
    return False


def has_internal_conflict(rows: list) -> bool:
    """행 목록 내부에서만 충돌 검사"""
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if is_conflict(rows[i], rows[j]):
                return True
    return False


# ── 분반 선택 ──────────────────────────────────────────

def pick_best_branch(df, name: str, existing: list, prefs: dict) -> tuple | None:
    """
    과목의 여러 분반 중 기존 수업과 충돌 없고 조건 필터를 통과하는
    첫 번째 분반을 반환.
    반환: (branch_key, rows) 또는 None
    branch_key: "교수명_분반번호" 형태의 문자열
    """
    branches = get_subject_branches(df, name)
    if not branches:
        return None

    for key, rows in branches.items():
        if has_any_conflict(existing + rows):
            continue
        if not passes_filters(rows, prefs):
            continue
        return key, rows

    return None


# ── 시간표 통계 계산 ───────────────────────────────────

def calc_timetable_stats(rows: list) -> tuple:
    """
    시간표의 공강 일수, 수업 있는 요일 수, 요일별 수업 수 편차, 총 학점 반환.
    반환: (free_days, active_days, day_variance, total_credits)
    """
    days, seen = set(), set()
    day_counts: dict = {"월": 0, "화": 0, "수": 0, "목": 0, "금": 0}
    total_cr = 0.0

    for r in rows:
        nm  = r.get("과목명", "")
        day = str(r.get("요일", ""))

        if nm not in seen:
            total_cr += float(r.get("학점", 0))
            seen.add(nm)

        if day in day_counts:
            days.add(day)
            day_counts[day] += 1

    free     = len({"월", "화", "수", "목", "금"} - days)
    active   = len(days)
    counts   = list(day_counts.values())
    avg      = sum(counts) / 5
    variance = sum((c - avg) ** 2 for c in counts) / 5

    return free, active, round(variance, 4), round(total_cr, 1)


def _sum_credits(rows: list, names: set) -> float:
    """fixed_rows 에서 중복 없이 학점 합산"""
    seen, total = set(), 0.0
    for r in rows:
        nm = r.get("과목명", "")
        if nm in names and nm not in seen:
            total += float(r.get("학점", 0))
            seen.add(nm)
    return total


# ── 교양선택 후보 사전 정리 ────────────────────────────

def _build_opt_candidates(df, fixed_rows: list, fixed_names: set,
                          prefs: dict) -> list:
    """
    교양선택 후보 목록을 탐색 전에 정리한다.

    적용하는 사전 필터 3가지:
      1. 이미 선택된 과목 제거 (fixed_names)
      2. 조건(오전회피·금공강·점심확보) 위반 과목 제거
      3. fixed 과목과 충돌하는 과목 제거

    반환: (과목명, 교수명_분반번호, [행...]) 튜플 목록
    """
    opt_df = get_courses_by_category(df, "교양선택")
    opt_df = opt_df[~opt_df["과목명"].isin(fixed_names)]

    candidates = []
    for _, row in opt_df.iterrows():
        nm = row["과목명"]

        branches = get_subject_branches(df, nm)
        for key, branch_rows in branches.items():
            if not passes_filters(branch_rows, prefs):
                continue
            if conflicts_with_fixed(branch_rows, fixed_rows):
                continue
            candidates.append((nm, key, branch_rows))
            break

    return candidates


# ── 메인 탐색 함수 ─────────────────────────────────────

def generate_timetables(preferences: dict, honor_student: bool = False) -> tuple:
    """
    preferences 에 따라 유효한 시간표를 탐색해 균형형·공강형·몰아듣기형
    각 1개씩 최대 3개를 반환.

    반환: (results, timed_out)
      results   : [(subject_profs, free_days, total_credits), ...]
      timed_out : 15초 초과로 중단된 경우 True
      subject_profs: [(과목명, 교수명_분반번호), ...]
    """
    TIMEOUT_SEC = 15

    df     = load_data()
    max_cr = MAX_CREDITS_HONOR if honor_student else MAX_CREDITS
    prefs  = preferences

    fixed_rows: list  = []
    fixed_names: set  = set()
    fixed_profs: dict = {}

    # 1. 선택한 전공 과목 추가 — 조건 필터 제외 ({} 전달)
    for nm in preferences.get("selected_major", []):
        _add_subject(df, nm, fixed_rows, fixed_names, fixed_profs, {})

    # 2. 선택한 교양필수 영역에서 과목 자동 배정
    #    LIBERAL_AREA_COUNT 기준으로 영역당 지정된 수만큼 배정
    for area in preferences.get("selected_liberal", []):
        domain = LIBERAL_AREA_DOMAINS.get(area)
        if not domain:
            continue
        count     = LIBERAL_AREA_COUNT.get(area, 1)  # 배정할 과목 수
        assigned  = 0
        domain_df = get_courses_by_domain(df, domain)

        for _, row in domain_df.iterrows():
            if assigned >= count:
                break
            nm = row["과목명"]
            if nm in fixed_names:
                continue
            result = pick_best_branch(df, nm, fixed_rows, prefs)
            if result:
                key, branch = result
                fixed_rows.extend(branch)
                fixed_names.add(nm)
                fixed_profs[nm] = key
                assigned += 1

    # 3. 남은 학점 계산
    fixed_cr  = _sum_credits(fixed_rows, fixed_names)
    remaining = max_cr - fixed_cr

    # 4. 교양선택 후보 사전 정리
    candidates = _build_opt_candidates(df, fixed_rows, fixed_names, prefs)

    # 5. 남은 학점으로 가능한 최대 r 동적 계산
    if candidates:
        min_cr = min(float(c[2][0].get("학점", 1)) for c in candidates)
        max_r  = min(6, int(remaining // min_cr))
    else:
        max_r = 0

    # 6. 조합 탐색 (15초 타임아웃)
    PER_R   = 200
    MAX_ALL = 1400

    results    = []
    timed_out  = False
    start_time = time.time()

    for r in range(0, max_r + 1):
        count_r = 0
        for combo in combinations(candidates, r):
            # 타임아웃 검사
            if time.time() - start_time > TIMEOUT_SEC:
                timed_out = True
                break

            combo_cr = sum(float(c[2][0].get("학점", 0)) for c in combo)
            if combo_cr > remaining:
                continue

            combo_rows = [row for _, _, rows in combo for row in rows]
            if has_internal_conflict(combo_rows):
                continue

            all_rows = fixed_rows + combo_rows
            free, active, variance, total = calc_timetable_stats(all_rows)

            subject_profs = (
                [(nm, fixed_profs[nm]) for nm in fixed_names]
                + [(nm, key) for nm, key, _ in combo]
            )
            results.append((subject_profs, free, active, variance, total))
            count_r += 1

            if count_r >= PER_R:
                break

        if timed_out:
            break
        if len(results) >= MAX_ALL:
            break

    return _pick_three(results), timed_out


def _add_subject(df, name: str, fixed_rows: list, fixed_names: set,
                 fixed_profs: dict, prefs: dict):
    """과목을 fixed 목록에 추가. 이미 있거나 분반 없으면 무시."""
    if name in fixed_names:
        return
    result = pick_best_branch(df, name, fixed_rows, prefs)
    if result:
        key, branch = result
        fixed_rows.extend(branch)
        fixed_names.add(name)
        fixed_profs[name] = key


# ── 결과 정렬 및 3개 선택 ─────────────────────────────

def _pick_three(results: list) -> list:
    """
    탐색된 결과에서 균형형·공강형·몰아듣기형 각 1개를 선택해 반환.

    균형형      : 요일별 수업 수 편차(day_variance) 최소
    공강형      : 공강 일수(free_days) 최대
    몰아듣기형  : 수업 있는 요일 수(active_days) 최소
    """
    if not results:
        return []

    balanced = sorted(results, key=lambda x: x[3])[0]
    free_day = sorted(results, key=lambda x: -x[1])[0]
    packed   = sorted(results, key=lambda x: x[2])[0]

    def trim(r):
        return (r[0], r[1], r[4])

    seen, trimmed = set(), []
    for r in [balanced, free_day, packed]:
        key = tuple(sorted(nm for nm, _ in r[0]))
        if key not in seen:
            seen.add(key)
            trimmed.append(trim(r))

    return trimmed


# ── 추천 이유 텍스트 ──────────────────────────────────

def get_reason(subject_profs: list, free_days: int,
               total_credits: float, prefs: dict) -> str:
    parts = []
    if free_days >= 1:
        parts.append(f"공강 {free_days}일")
    if prefs.get("avoid_morning"):
        parts.append("오전회피")
    if prefs.get("no_friday"):
        parts.append("금공강")
    if prefs.get("keep_lunch"):
        parts.append("점심확보")
    parts.append(f"{total_credits}학점")
    return " · ".join(parts)
