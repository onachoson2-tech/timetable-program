# ────────────────────────────────
# filters.py  —  시간표 조건 필터링
# ────────────────────────────────
# 각 함수는 수업 행(dict) 또는 행 목록(list)을 받아
# 조건 충족 여부를 bool로 반환한다.
# ────────────────────────────────

from data_loader import time_to_min


# ── 수강 자격 검사 ─────────────────────────────────────

# 비고 컬럼에서 수강 불가로 처리할 키워드 목록
# AI소프트웨어융합학부 26학번 1학년 기준
_INVALID_REMARKS = [
    "23-25학번전용",
    "14-22학번전용",
    "트리니티전용",
    "의과대학전용",
    "사범대학전용",
    "헬스케어융합대전용",
    "휴먼서비스대전용",
    "외국인유학생전용",
    "학과사전신청만가능",
    "사이버강좌",
    "토요일휴먼서비스대전용",
]

# 비고 조건과 무관하게 수강 가능한 과목 (학교 측 예외 처리)
_REMARK_EXCEPTIONS = [
    "VERUM인성:그리스도교문화",
]


def is_valid_grade(row: dict) -> bool:
    """
    학년 컬럼이 1인 행만 True 반환.
    학년 정보가 없는 행은 False 반환.
    """
    try:
        return int(row.get("학년", 0)) == 1
    except Exception:
        return False


def is_valid_remark(row: dict) -> bool:
    """
    비고 컬럼에 수강 불가 키워드가 포함되면 False 반환.
    VERUM인성:그리스도교문화 과목은 예외적으로 True 반환.
    비고가 비어있거나 P/NP 등 수강 가능한 경우 True 반환.
    """
    # 예외 과목은 비고와 무관하게 통과
    nm = str(row.get("과목명", ""))
    if nm in _REMARK_EXCEPTIONS:
        return True

    remark = str(row.get("비고", ""))
    if remark in ("", "nan"):
        return True

    for keyword in _INVALID_REMARKS:
        if keyword in remark:
            return False

    return True


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
      학년 == 1          : 항상 검사 (1학년 과목만 허용)
      비고 수강 자격     : 항상 검사 (AI소프트웨어융합학부 26학번 기준)
      avoid_morning      : True 이면 오전(~12시) 수업이 있으면 False
      no_friday          : True 이면 금요일 수업이 있으면 False
      keep_lunch         : True 이면 점심(12~13시)과 겹치는 수업이 있으면 False
    """
    avoid_morning = prefs.get("avoid_morning", False)
    no_friday     = prefs.get("no_friday",     False)
    keep_lunch    = prefs.get("keep_lunch",    False)

    for row in rows:
        # 학년 검사 (항상 적용)
        if not is_valid_grade(row):
            return False
        # 비고 수강 자격 검사 (항상 적용)
        if not is_valid_remark(row):
            return False
        # 사용자 선택 조건 검사
        if avoid_morning and is_morning(row):
            return False
        if no_friday and is_friday(row):
            return False
        if keep_lunch and conflicts_lunch(row):
            return False

    return True
