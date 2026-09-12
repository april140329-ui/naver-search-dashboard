"""민원(고충·불만) 텍스트에 특화된 유형 분류 및 심각도 분석."""
from __future__ import annotations

from collections import Counter

import pandas as pd

from src.analysis.text_mining import tokenize_weighted_text

# 민원 유형별 판별 키워드. 앞쪽 유형일수록 우선 매칭됩니다.
COMPLAINT_CATEGORIES: dict[str, set[str]] = {
    "소음": {"소음", "시끄", "층간소음", "공사소음", "확성기", "굉음", "울림", "고성방가", "진동"},
    "악취·환경오염": {"악취", "냄새", "매연", "미세먼지", "오염", "폐수", "하수구", "배출", "연기", "분진"},
    "쓰레기·청소": {"쓰레기", "무단투기", "폐기물", "청소", "분리수거", "방치", "적치", "불법투기", "오물"},
    "교통·주차": {"주차", "불법주정차", "교통", "신호등", "과속", "도로", "정체", "견인", "인도", "횡단보도"},
    "안전·위험": {"위험", "사고", "붕괴", "균열", "누수", "침수", "화재", "방범", "가로등", "추락", "감전"},
    "시설·보수": {"시설", "고장", "파손", "보수", "정비", "노후", "훼손", "수리", "설치", "철거"},
    "불친절·응대": {"불친절", "응대", "태도", "무시", "담당자", "안내", "말투", "고압적", "성의없"},
    "처리지연·미조치": {"지연", "무응답", "회신", "기다", "몇번째", "여러번", "감감무소식", "묵묵부답", "미조치"},
}

# 민원의 심각도를 끌어올리는 긴급/반복 표현
URGENCY_WORDS = {
    "긴급", "즉시", "당장", "심각", "매우", "너무", "계속", "반복", "여러번", "몇번째",
    "제발", "도저히", "참을수없", "못살겠", "죽겠", "최악", "고통",
}

# 민원 맥락의 부정 강도 표현 (일반 감성사전에 더해 가중치를 부여)
COMPLAINT_NEGATIVE_WORDS = {
    "불편", "불만", "피해", "고통", "호소", "항의", "신고", "단속", "위반", "방치",
    "손해", "짜증", "화가", "분노", "억울", "답답", "실망", "엉망", "형편없",
}


def classify_complaint_category(text: str) -> str:
    """민원 텍스트에서 가장 많이 매칭된 유형을 반환합니다. 매칭이 없으면 '기타'입니다."""
    scores = {
        category: sum(text.count(word) for word in words)
        for category, words in COMPLAINT_CATEGORIES.items()
    }
    top_category = max(scores, key=scores.get)
    return top_category if scores[top_category] > 0 else "기타"


def compute_severity(text: str, sentiment_score: int) -> tuple[int, str]:
    """감정 점수와 긴급 표현을 합쳐 민원 심각도 점수와 등급을 산출합니다.

    부정 감정이 강할수록, 긴급/반복 표현이 많을수록 점수가 높아집니다.
    """
    urgency_hits = sum(text.count(word) for word in URGENCY_WORDS)
    complaint_negatives = sum(text.count(word) for word in COMPLAINT_NEGATIVE_WORDS)
    # 감정 점수는 음수일수록 부정이므로 부호를 뒤집어 심각도에 반영합니다.
    score = max(0, -sentiment_score) + urgency_hits * 2 + complaint_negatives
    if score >= 5:
        return score, "심각"
    if score >= 2:
        return score, "보통"
    return score, "경미"


def analyze_complaints(df_scored: pd.DataFrame) -> pd.DataFrame:
    """감성 분류가 끝난 데이터에 민원 유형과 심각도 컬럼을 추가합니다.

    df_scored는 classify_sentiment()를 거쳐 '감성점수' 컬럼을 가진 DataFrame이어야 합니다.
    """
    if df_scored.empty:
        return df_scored.assign(
            민원유형=pd.Series(dtype=str),
            심각도점수=pd.Series(dtype=int),
            심각도=pd.Series(dtype=str),
        )

    res = df_scored.copy()
    combined = res["title"].fillna("").astype(str) + " " + res["description"].fillna("").astype(str)
    res["민원유형"] = combined.apply(classify_complaint_category)

    severity = [
        compute_severity(text, int(score))
        for text, score in zip(combined, res.get("감성점수", pd.Series([0] * len(res))))
    ]
    res["심각도점수"] = [item[0] for item in severity]
    res["심각도"] = [item[1] for item in severity]
    return res


def compute_category_summary(df_complaints: pd.DataFrame) -> pd.DataFrame:
    """민원 유형별 건수, 평균 심각도, 심각 건수를 집계합니다."""
    if df_complaints.empty or "민원유형" not in df_complaints.columns:
        return pd.DataFrame()

    summary = (
        df_complaints.groupby("민원유형")
        .agg(
            건수=("민원유형", "size"),
            평균심각도=("심각도점수", "mean"),
            심각건수=("심각도", lambda s: int((s == "심각").sum())),
        )
        .round(2)
        .reset_index()
        .sort_values("건수", ascending=False)
    )
    total = summary["건수"].sum()
    summary["비중(%)"] = (summary["건수"] / total * 100).round(1) if total else 0.0
    return summary


def compute_category_severity_crosstab(df_complaints: pd.DataFrame) -> pd.DataFrame:
    """민원 유형 x 심각도 교차표를 만듭니다."""
    if df_complaints.empty or "민원유형" not in df_complaints.columns:
        return pd.DataFrame()

    ct = pd.crosstab(df_complaints["민원유형"], df_complaints["심각도"])
    for level in ("심각", "보통", "경미"):
        if level not in ct.columns:
            ct[level] = 0
    return ct[["심각", "보통", "경미"]].sort_values("심각", ascending=False)


def top_words_by_category(
    df_complaints: pd.DataFrame,
    category: str,
    top_n: int = 10,
    exclude_words: list[str] | None = None,
) -> pd.DataFrame:
    """특정 민원 유형 문서에서 자주 등장하는 표현을 추출합니다."""
    if df_complaints.empty or "민원유형" not in df_complaints.columns:
        return pd.DataFrame(columns=["단어", "빈도수"])

    sub = df_complaints[df_complaints["민원유형"] == category]
    if sub.empty:
        return pd.DataFrame(columns=["단어", "빈도수"])

    titles = sub["title"].dropna().astype(str).tolist()
    descriptions = sub["description"].dropna().astype(str).tolist()
    tokens = tokenize_weighted_text(titles, descriptions, exclude_words=set(exclude_words or []))
    if not tokens:
        return pd.DataFrame(columns=["단어", "빈도수"])

    return pd.DataFrame(Counter(tokens).most_common(top_n), columns=["단어", "빈도수"])
