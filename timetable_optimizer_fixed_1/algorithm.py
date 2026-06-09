# ────────────────────────────────
# algorithm.py  —  충돌 검사 및 시간표 탐색
# ────────────────────────────────

from itertools import combinations
from data_loader import load_data, time_to_min, get_subject_branches, get_courses_by_category
from config import MAX_CREDITS, MAX_CREDITS_HONOR


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


# ── 분반 선택 ──────────────────────────────────────────

def pick_best_branch(df, name: str, existing: list, prefs: dict) -> list | None:
    """
    과목의 여러 분반 중 기존 수업과 충돌 없는 첫 번째 분반을 반환.
    모두 충돌이면 None 반환.
    """
    branches = get_subject_branches(df, name)
    if not branches:
        return None

    for prof, rows in branches.items():
        if not has_any_conflict(existing + rows):
            return rows

    return None


# ── 시간표 통계 계산 ───────────────────────────────────

def calc_timetable_stats(rows: list) -> tuple:
    """
    시간표의 공강 일수, 총 학점 반환.
    반환: (free_days, total_credits)
    """
    days, seen = set(), set()
    total_cr = 0.0

    for r in rows:
        nm  = r.get("과목명", "")
        day = str(r.get("요일", ""))

        if nm not in seen:
            total_cr += float(r.get("학점", 0))
            seen.add(nm)

        if day and day != "nan":
            days.add(day)

    free = len({"월", "화", "수", "목", "금"} - days)
    return free, round(total_cr, 1)


def _sum_credits(rows: list, names: set) -> float:
    """fixed_rows 에서 중복 없이 학점 합산"""
    seen, total = set(), 0.0
    for r in rows:
        nm = r.get("과목명", "")
        if nm in names and nm not in seen:
            total += float(r.get("학점", 0))
            seen.add(nm)
    return total


# ── 메인 탐색 함수 ─────────────────────────────────────

def generate_timetables(preferences: dict, honor_student: bool = False) -> list:
    """
    preferences 에 따라 유효한 시간표 3개를 탐색해 반환.
    반환: [(subject_profs, free_days, total_credits), ...]
      subject_profs: [(과목명, 교수), ...] — 알고리즘이 선택한 분반 정보 포함
    """
    df = load_data()
    max_cr = MAX_CREDITS_HONOR if honor_student else MAX_CREDITS
    prefs  = preferences

    fixed_rows: list  = []
    fixed_names: set  = set()
    fixed_profs: dict = {}   # {과목명: 교수} — 알고리즘이 선택한 분반 기록

    # 1. 선택한 전공 과목 추가
    for nm in preferences.get("selected_major", []):
        _add_subject(df, nm, fixed_rows, fixed_names, fixed_profs, prefs)

    # 2. 선택한 교양필수 추가
    for nm in preferences.get("selected_liberal", []):
        _add_subject(df, nm, fixed_rows, fixed_names, fixed_profs, prefs)

    # 3. 남은 학점 계산
    fixed_cr  = _sum_credits(fixed_rows, fixed_names)
    remaining = max_cr - fixed_cr

    # 4. 교양선택 후보 목록
    opt_df   = get_courses_by_category(df, "교양선택")
    opt_df   = opt_df[~opt_df["과목명"].isin(fixed_names)]
    opt_list = opt_df.to_dict("records")

    # 5. 조합 탐색
    # r(교양선택 과목 수)별로 최대 PER_R개씩 수집해 다양한 크기의 조합을 골고루 탐색한다.
    PER_R   = 200
    MAX_ALL = 1400

    results = []
    for r in range(0, 7):
        count_r = 0
        for combo in combinations(opt_list, r):
            combo_cr = sum(float(c["학점"]) for c in combo)
            if combo_cr > remaining:
                continue

            all_rows = fixed_rows + list(combo)
            if has_any_conflict(all_rows):
                continue

            free, total = calc_timetable_stats(all_rows)

            combo_profs = {c["과목명"]: str(c["교수"]) for c in combo}
            subject_profs = (
                [(nm, fixed_profs[nm]) for nm in fixed_names]
                + [(nm, combo_profs[nm]) for nm in combo_profs]
            )
            results.append((subject_profs, free, total))
            count_r += 1

            if count_r >= PER_R:
                break

        if len(results) >= MAX_ALL:
            break

    return results[:3]


def _add_subject(df, name: str, fixed_rows: list, fixed_names: set,
                 fixed_profs: dict, prefs: dict):
    """과목을 fixed 목록에 추가. 이미 있거나 분반 없으면 무시."""
    if name in fixed_names:
        return
    branch = pick_best_branch(df, name, fixed_rows, prefs)
    if branch:
        fixed_rows.extend(branch)
        fixed_names.add(name)
        fixed_profs[name] = str(branch[0].get("교수", ""))


# ── 추천 이유 텍스트 ──────────────────────────────────

def get_reason(subject_profs: list, free_days: int,
               total_credits: float, prefs: dict) -> str:
    """
    subject_profs: [(과목명, 교수), ...]
    """
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
