# ────────────────────────────────
# filters.py  —  시간표 조건 필터링
# ────────────────────────────────
# 각 함수는 수업 행(dict) 또는 행 목록(list)을 받아
# 조건 충족 여부를 bool로 반환한다.
# ────────────────────────────────

from data_loader import time_to_min


# ── 개별 행 검사 함수 ──────────────────────────────────

def is_morning(row: dict) -> bool:
    """
    수업 시작 시간이 12:00 이전이면 True.
    시간 정보가 없는 행(온라인 강좌 등)은 False 반환.
    """
    s = time_to_min(row.get("시작", ""))
    if s < 0:
        return False
    return s < 12 * 60


def is_friday(row: dict) -> bool:
    """
    수업 요일이 금요일이면 True.
    요일 정보가 없는 행은 False 반환.
    """
    day = str(row.get("요일", ""))
    return day == "금"


def conflicts_lunch(row: dict) -> bool:
    """
    수업 시간이 점심 시간(12:00~13:00)과 겹치면 True.
    시간 정보가 없는 행은 False 반환.
    겹침 조건: 수업 시작 < 13:00 AND 수업 종료 > 12:00
    """
    s = time_to_min(row.get("시작", ""))
    e = time_to_min(row.get("종료", ""))
    if s < 0 or e < 0:
        return False
    lunch_s = 12 * 60   # 720분
    lunch_e = 13 * 60   # 780분
    return s < lunch_e and e > lunch_s


# ── 시간표 전체 검사 함수 ──────────────────────────────

def passes_filters(rows: list, prefs: dict) -> bool:
    """
    행 목록 전체에 prefs 조건을 적용한다.
    모든 조건을 통과하면 True, 하나라도 위반하면 False.

    검사 조건:
      avoid_morning : True 이면 오전(~12시) 수업이 한 행이라도 있으면 False
      no_friday     : True 이면 금요일 수업이 한 행이라도 있으면 False
      keep_lunch    : True 이면 점심(12~13시)과 겹치는 수업이 있으면 False
    """
    avoid_morning = prefs.get("avoid_morning", False)
    no_friday     = prefs.get("no_friday",     False)
    keep_lunch    = prefs.get("keep_lunch",    False)

    for row in rows:
        if avoid_morning and is_morning(row):
            return False
        if no_friday and is_friday(row):
            return False
        if keep_lunch and conflicts_lunch(row):
            return False

    return True
