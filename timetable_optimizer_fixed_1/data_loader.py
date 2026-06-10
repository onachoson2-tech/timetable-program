# ────────────────────────────────
# data_loader.py  —  데이터 로딩 및 시간 처리
# ────────────────────────────────

import os
import pandas as pd


# 비고 컬럼 수강 불가 키워드 (filters.py와 동일 기준)
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


def _is_valid_row(row: pd.Series) -> bool:
    """
    행이 AI소프트웨어융합학부 26학번 1학년 수강 가능 조건을 충족하는지 확인.
    학년 == 1 이고 비고에 수강 불가 키워드가 없으면 True.
    """
    # 학년 검사
    try:
        if int(row["학년"]) != 1:
            return False
    except Exception:
        return False

    # 예외 과목은 비고와 무관하게 통과
    if str(row.get("과목명", "")) in _REMARK_EXCEPTIONS:
        return True

    # 비고 검사
    remark = str(row.get("비고", ""))
    if remark in ("", "nan"):
        return True
    for keyword in _INVALID_REMARKS:
        if keyword in remark:
            return False

    return True


def load_data() -> pd.DataFrame:
    """
    data.csv를 읽어 AI소프트웨어융합학부 26학번 1학년 기준으로
    수강 불가 행을 사전 제거한 DataFrame 반환.
    """
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "data.csv")
    df   = pd.read_csv(path)

    # 수강 자격 사전 필터링
    mask = df.apply(_is_valid_row, axis=1)
    df   = df[mask].reset_index(drop=True)

    return df


def time_to_min(t) -> int:
    """
    "09:00" → 540 처럼 시간 문자열을 분 단위 정수로 변환.
    변환 불가이면 -1 반환.
    """
    try:
        h, m = map(int, str(t).strip().split(":"))
        return h * 60 + m
    except Exception:
        return -1


def get_subject_branches(df: pd.DataFrame, name: str) -> dict:
    """
    과목명으로 행을 찾아 교수명+분반번호 기준으로 그룹화하여 반환.
    반환 형태: { "교수명_분반번호": [row_dict, ...], ... }

    교수명+분반번호 조합을 키로 사용해 동일 교수의 여러 분반을 구분한다.
    예) 이기영_2, 이상식_3
    """
    rows = df[df["과목명"] == name]
    branches: dict = {}
    for _, r in rows.iterrows():
        key = f"{r['교수']}_{r['분반']}"
        branches.setdefault(key, []).append(r.to_dict())
    return branches


def get_courses_by_category(df: pd.DataFrame, category: str) -> pd.DataFrame:
    """카테고리로 과목 필터링 후 과목명 중복 제거한 DataFrame 반환"""
    filtered = df[df["카테고리"] == category].copy()
    return filtered.drop_duplicates(subset=["과목명"], keep="first")


def get_courses_by_domain(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    """
    영역(domain)으로 과목 필터링 후 과목명 중복 제거한 DataFrame 반환.
    교양필수 영역 자동 배정 시 사용한다.
    예) domain="VERUM인간" → VERUM인간 영역 과목 목록 반환
    """
    filtered = df[df["영역"] == domain].copy()
    return filtered.drop_duplicates(subset=["과목명"], keep="first")
