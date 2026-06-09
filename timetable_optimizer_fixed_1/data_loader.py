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
    과목명으로 행을 찾아 교수(분반) 기준으로 그룹화하여 반환.
    반환 형태: { "교수명": [row_dict, ...], ... }
    """
    rows = df[df["과목명"] == name]
    branches: dict = {}
    for _, r in rows.iterrows():
        prof = str(r["교수"])
        branches.setdefault(prof, []).append(r.to_dict())
    return branches


def get_courses_by_category(df: pd.DataFrame, category: str) -> pd.DataFrame:
    """카테고리로 과목 필터링 후 과목명 중복 제거한 DataFrame 반환"""
    filtered = df[df["카테고리"] == category].copy()
    return filtered.drop_duplicates(subset=["과목명"], keep="first")
