# ────────────────────────────────
# algorithm.py  —  충돌 검사 및 시간표 탐색
# ────────────────────────────────

import time
import random
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

def pick_best_branch(df, name: str, existing: list, prefs: dict,
                     shuffle: bool = False) -> tuple | None:
    """
    과목의 여러 분반 중 기존 수업과 충돌 없고 조건 필터를 통과하는
    첫 번째 분반을 반환.
    shuffle=True 이면 분반 순서를 랜덤 셔플 후 탐색 (다양한 분반 배정).
    반환: (branch_key, rows) 또는 None
    branch_key: "교수명_분반번호" 형태의 문자열
    """
    branches = get_subject_branches(df, name)
    if not branches:
        return None

    items = list(branches.items())
    if shuffle:
        random.shuffle(items)

    for key, rows in items:
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
    버튼 클릭 시마다 교양필수·분반을 랜덤 배정하고
    교양선택 조합 중 조건에 맞는 1개를 즉시 반환.

    반환: (results, timed_out)
      results   : [(subject_profs, free_days, total_credits)] — 항상 1개
      timed_out : 15초 초과로 결과를 찾지 못한 경우 True
      subject_profs: [(과목명, 교수명_분반번호), ...]
    """
    TIMEOUT_SEC = 15

    df     = load_data()
    max_cr = MAX_CREDITS_HONOR if honor_student else MAX_CREDITS
    prefs  = preferences

    start_time = time.time()

    # 전공 과목을 단일분반/다분반으로 분리
    single_majors = []
    multi_majors  = []

    for nm in preferences.get("selected_major", []):
        branches = get_subject_branches(df, nm)
        valid = list(branches.items())
        if len(valid) <= 1:
            single_majors.append(nm)
        else:
            multi_majors.append((nm, valid))

    # 다분반 과목 분반 조합 — 랜덤 셔플
    from itertools import product as iproduct
    if multi_majors:
        multi_names   = [nm for nm, _ in multi_majors]
        multi_options = [options for _, options in multi_majors]
        branch_combos = list(iproduct(*multi_options))
        random.shuffle(branch_combos)
    else:
        multi_names   = []
        branch_combos = [()]

    for branch_combo in branch_combos:
        if time.time() - start_time > TIMEOUT_SEC:
            return [], True

        fixed_rows: list  = []
        fixed_names: set  = set()
        fixed_profs: dict = {}

        # 1. 단일분반 전공 과목 추가
        for nm in single_majors:
            _add_subject(df, nm, fixed_rows, fixed_names, fixed_profs, {})

        # 2. 다분반 전공 과목 — 이번 조합의 분반으로 고정
        skip_combo = False
        for nm, (key, rows) in zip(multi_names, branch_combo):
            if has_any_conflict(fixed_rows + rows):
                skip_combo = True
                break
            fixed_rows.extend(rows)
            fixed_names.add(nm)
            fixed_profs[nm] = key
        if skip_combo:
            continue

        # 3. 교양필수 영역에서 과목 랜덤 배정
        for area in preferences.get("selected_liberal", []):
            domain = LIBERAL_AREA_DOMAINS.get(area)
            if not domain:
                continue
            count     = LIBERAL_AREA_COUNT.get(area, 1)
            assigned  = 0
            domain_df = get_courses_by_domain(df, domain)

            for _, row in domain_df.sample(frac=1).iterrows():
                if assigned >= count:
                    break
                nm = row["과목명"]
                if nm in fixed_names:
                    continue
                current_cr = _sum_credits(fixed_rows, fixed_names)
                subject_cr = float(row.get("학점", 0))
                if current_cr + subject_cr > max_cr:
                    continue
                result = pick_best_branch(df, nm, fixed_rows, prefs)
                if result:
                    k, branch = result
                    fixed_rows.extend(branch)
                    fixed_names.add(nm)
                    fixed_profs[nm] = k
                    assigned += 1

        # 4. 남은 학점 계산
        fixed_cr  = _sum_credits(fixed_rows, fixed_names)
        remaining = max_cr - fixed_cr

        # 5. 교양선택 후보 사전 정리 후 랜덤 셔플
        candidates = _build_opt_candidates(df, fixed_rows, fixed_names, prefs)
        random.shuffle(candidates)

        # 6. 남은 학점으로 가능한 최대 r 동적 계산
        if candidates:
            min_cr = min(float(c[2][0].get("학점", 1)) for c in candidates)
            max_r  = min(6, int(remaining // min_cr))
        else:
            max_r = 0

        # 7. 셔플된 후보에서 조건에 맞는 첫 번째 조합 1개 반환
        for r in range(max_r, -1, -1):   # 학점 많은 조합부터 탐색
            for combo in combinations(candidates, r):
                if time.time() - start_time > TIMEOUT_SEC:
                    return [], True

                combo_cr = sum(float(c[2][0].get("학점", 0)) for c in combo)
                if combo_cr > remaining:
                    continue

                # 사이버강좌 2과목 초과 제외
                cyber_count = sum(
                    1 for _, _, rows in combo
                    if all(str(row.get("요일", "")) in ("", "nan") for row in rows)
                )
                if cyber_count > 2:
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
                # 조건에 맞는 첫 번째 조합 즉시 반환
                return [(subject_profs, free, total)], False

    return [], True


def _add_subject(df, name: str, fixed_rows: list, fixed_names: set,
                 fixed_profs: dict, prefs: dict):
    """과목을 fixed 목록에 추가. 이미 있거나 분반 없으면 무시.
    분반이 여러 개인 경우 랜덤 셔플 후 충돌 없는 분반 선택."""
    if name in fixed_names:
        return
    result = pick_best_branch(df, name, fixed_rows, prefs, shuffle=True)
    if result:
        key, branch = result
        fixed_rows.extend(branch)
        fixed_names.add(name)
        fixed_profs[name] = key


def _dedupe_and_shuffle(results: list) -> list:
    """
    탐색된 결과에서 과목 조합이 동일한 중복을 제거하고
    랜덤 순서로 섞어 반환.
    중복 기준: 과목명 + 교수명_분반번호 조합 (분반이 다르면 다른 결과로 처리)
    """
    if not results:
        return []

    seen, unique = set(), []
    for r in results:
        key = tuple(sorted((nm, prof) for nm, prof in r[0]))
        if key not in seen:
            seen.add(key)
            unique.append((r[0], r[1], r[4]))  # (subject_profs, free_days, total_credits)

    random.shuffle(unique)
    return unique


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
