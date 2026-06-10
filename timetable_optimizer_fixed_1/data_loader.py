# ────────────────────────────────
# data_loader.py  —  데이터 로딩 및 시간 처리
# ────────────────────────────────

import os
import pandas as pd


def load_data() -> pd.DataFrame:
    """data.csv 를 읽어 DataFrame 반환"""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "data.csv")
    return pd.read_csv(path)


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

    기존 교수명 단독 키 방식은 동일 교수의 여러 분반이 하나로 합쳐지는
    문제가 있었으므로, 교수명+분반번호 조합을 키로 사용한다.
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
