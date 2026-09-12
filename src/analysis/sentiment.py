from __future__ import annotations
from collections import Counter
import pandas as pd
from src.analysis.text_mining import tokenize_weighted_text

# 사전 기반(lexicon-based) 감성 분석용 한국어 긍정/부정 단어 목록.
# 리뷰·뉴스·커뮤니티 글에서 흔히 쓰이는 표현 위주로 구성했습니다.
POSITIVE_WORDS = {
    "좋다", "좋아요", "최고", "훌륭", "만족", "추천", "강추", "대박", "우수", "인기",
    "성공", "호평", "기대", "편리", "안정", "합리적", "가성비", "친절", "깔끔", "빠르다",
    "튼튼", "신뢰", "상승", "급등", "돌파", "달성", "호실적", "완벽", "혁신", "사랑",
    "감동", "쾌적", "탁월", "무난", "굿", "짱",
}
NEGATIVE_WORDS = {
    "나쁘다", "별로", "불만", "실망", "고장", "불량", "환불", "비추", "최악", "단점",
    "우려", "논란", "하락", "급락", "폭락", "부족", "결함", "리콜", "사기", "느리다",
    "불편", "불안", "위험", "문제", "실패", "적자", "부진", "취소", "경고", "짜증",
    "먹통", "버벅", "하자", "피해", "손해",
}


def _score_text(text: str) -> int:
    """텍스트 내 긍정/부정 단어 등장 횟수 차이를 감성 점수로 환산합니다."""
    pos = sum(text.count(word) for word in POSITIVE_WORDS)
    neg = sum(text.count(word) for word in NEGATIVE_WORDS)
    return pos - neg


def classify_sentiment(df_items: pd.DataFrame) -> pd.DataFrame:
    """제목+설명 텍스트에 사전 기반 긍/부정 점수를 매겨 감성 라벨(긍정/중립/부정)을 추가합니다.

    단순 사전 매칭 방식이므로 반어법이나 '좋지 않다' 같은 부정어 결합은 정확히
    반영되지 않습니다. 정밀 분류가 아닌 대략적인 여론 톤 파악용 참고 지표입니다.
    """
    if df_items.empty:
        return df_items.assign(감성점수=pd.Series(dtype=int), 감성=pd.Series(dtype=str))

    res = df_items.copy()
    combined_text = res["title"].fillna("").astype(str) + " " + res["description"].fillna("").astype(str)
    scores = combined_text.apply(_score_text)
    res["감성점수"] = scores
    res["감성"] = scores.apply(lambda s: "긍정" if s > 0 else ("부정" if s < 0 else "중립"))
    return res


def compute_sentiment_summary(df_scored: pd.DataFrame, group_col: str = "keyword") -> pd.DataFrame:
    """그룹(검색어/채널)별 긍정·중립·부정 건수 및 비중을 집계합니다."""
    if df_scored.empty or "감성" not in df_scored.columns or group_col not in df_scored.columns:
        return pd.DataFrame()

    grouped = df_scored.groupby([group_col, "감성"]).size().unstack(fill_value=0)
    for col in ("긍정", "중립", "부정"):
        if col not in grouped.columns:
            grouped[col] = 0
    grouped = grouped[["긍정", "중립", "부정"]]
    grouped["합계"] = grouped.sum(axis=1)
    for col in ("긍정", "중립", "부정"):
        grouped[f"{col}비중(%)"] = (grouped[col] / grouped["합계"] * 100).round(1)
    return grouped.reset_index()


def compute_sentiment_trend(df_scored: pd.DataFrame) -> pd.DataFrame:
    """발행일자를 기준으로 일자별 긍정/중립/부정 건수 추이를 계산합니다 (파싱 가능한 날짜만 반영)."""
    if df_scored.empty or "pub_date" not in df_scored.columns or "감성" not in df_scored.columns:
        return pd.DataFrame()

    parsed = pd.to_datetime(df_scored["pub_date"], errors="coerce")
    valid = df_scored.assign(_dt=parsed).dropna(subset=["_dt"])
    if valid.empty:
        return pd.DataFrame()

    valid = valid.assign(일자=valid["_dt"].dt.date)
    return valid.groupby(["일자", "감성"]).size().reset_index(name="건수")


def top_words_by_sentiment(
    df_scored: pd.DataFrame,
    sentiment_label: str,
    top_n: int = 15,
    exclude_words: list[str] | None = None,
) -> pd.DataFrame:
    """특정 감성 라벨로 분류된 문서들에서 빈출 단어를 추출합니다."""
    if df_scored.empty or "감성" not in df_scored.columns:
        return pd.DataFrame(columns=["단어", "빈도수"])

    sub = df_scored[df_scored["감성"] == sentiment_label]
    if sub.empty:
        return pd.DataFrame(columns=["단어", "빈도수"])

    titles = sub["title"].dropna().astype(str).tolist()
    descriptions = sub["description"].dropna().astype(str).tolist()
    tokens = tokenize_weighted_text(titles, descriptions, exclude_words=set(exclude_words or []))
    if not tokens:
        return pd.DataFrame(columns=["단어", "빈도수"])

    most_common = Counter(tokens).most_common(top_n)
    return pd.DataFrame(most_common, columns=["단어", "빈도수"])
