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

    # 제목(가중치 2) + 설명(가중치 1) 합산
    titles = target_df["title"].dropna().astype(str).tolist()
    descriptions = target_df["description"].dropna().astype(str).tolist()

    full_text = " ".join(titles * 2 + descriptions)

    # 한글 및 영문 단어 추출 (2글자 이상)
    tokens = re.findall(r"[가-힣a-zA-Z0-9]{2,}", full_text.lower())
    excluded = {word.lower() for word in (exclude_words or [])}
    cleaned_tokens = [
        token
        for token in tokens
        if token not in KOREAN_STOPWORDS and token not in excluded and not token.isdigit()
    ]

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
