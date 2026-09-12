from __future__ import annotations
import re
from collections import Counter
import pandas as pd

# 한국어 일반 불용어(Stopwords) 목록
KOREAN_STOPWORDS = {
    "있다", "하다", "되다", "이다", "같다", "대해", "위해", "통해", "관련",
    "대한", "통한", "이", "그", "저", "것", "수", "등", "및", "더", "때",
    "내", "중", "제", "개", "점", "전", "후", "이번", "지난", "모든",
    "그리고", "하지만", "그러나", "또한", "또는", "경우", "모두", "어떤",
    "네이버", "검색", "결과", "정보", "확인", "보기", "바로가기", "더보기",
}


def tokenize_weighted_text(
    titles: list[str],
    descriptions: list[str],
    title_weight: int = 2,
    exclude_words: set[str] | None = None,
) -> list[str]:
    """제목(기본 가중치 2배)과 설명을 합쳐 불용어를 제외한 토큰(2글자 이상)을 추출합니다.

    제목과 채널 심층 EDA의 연관어 분석이 동일한 토큰화 규칙을 공유하도록 단일화한 진입점입니다.
    """
    full_text = " ".join(titles * title_weight + descriptions)
    tokens = re.findall(r"[가-힣a-zA-Z0-9]{2,}", full_text.lower())
    excluded = {word.lower() for word in (exclude_words or set())}
    return [
        token
        for token in tokens
        if token not in KOREAN_STOPWORDS and token not in excluded and not token.isdigit()
    ]


def extract_top_words(
    df_items: pd.DataFrame,
    keyword_filter: str | None = None,
    channel_filter: str | None = None,
    top_n: int = 25,
    exclude_words: list[str] | None = None,
    ngram_size: int = 1,
) -> pd.DataFrame:
    """수집된 문서들의 제목과 설명에서 빈출 주요 단어를 추출합니다."""
    if df_items.empty:
        return pd.DataFrame(columns=["단어", "빈도수"])

    target_df = df_items.copy()
    if keyword_filter and keyword_filter != "전체":
        target_df = target_df[target_df["keyword"] == keyword_filter]
    if channel_filter and channel_filter != "전체":
        target_df = target_df[target_df["channel_id"] == channel_filter]

    titles = target_df["title"].dropna().astype(str).tolist()
    descriptions = target_df["description"].dropna().astype(str).tolist()
    cleaned_tokens = tokenize_weighted_text(
        titles, descriptions, exclude_words=set(exclude_words or [])
    )

    if ngram_size == 2:
        cleaned_tokens = [
            f"{cleaned_tokens[index]} {cleaned_tokens[index + 1]}"
            for index in range(len(cleaned_tokens) - 1)
        ]

    counter: Counter[str] = Counter()
    counter.update(cleaned_tokens)

    most_common = counter.most_common(top_n)
    if not most_common:
        return pd.DataFrame(columns=["단어", "빈도수"])

    res_df = pd.DataFrame(most_common, columns=["단어", "빈도수"])
    return res_df
