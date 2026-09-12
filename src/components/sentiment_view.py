from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.sentiment import (
    classify_sentiment,
    compute_sentiment_summary,
    compute_sentiment_trend,
    top_words_by_sentiment,
)

SENTIMENT_COLORS = {"긍정": "#03C75A", "중립": "#94a3b8", "부정": "#e5484d"}
SENTIMENT_ORDER = ["긍정", "중립", "부정"]


def _stacked_sentiment_chart(summary: pd.DataFrame, group_col: str, x_label: str):
    chart_df = summary.melt(
        id_vars=group_col, value_vars=SENTIMENT_ORDER, var_name="감성", value_name="건수"
    )
    fig = px.bar(
        chart_df,
        x=group_col,
        y="건수",
        color="감성",
        barmode="stack",
        category_orders={"감성": SENTIMENT_ORDER},
        color_discrete_map=SENTIMENT_COLORS,
        template="plotly_white",
        labels={group_col: x_label, "건수": "문서 건수"},
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
    return fig


def render_sentiment_section(df_items: pd.DataFrame, keywords: list[str]) -> None:
    """사전 기반 감성 분석으로 검색어·채널별 여론 톤과 추이를 보여줍니다."""
    if df_items.empty:
        st.info("여론/감성 분석을 위한 수집 표본이 없습니다.")
        return

    st.info(
        "이 분석은 긍정/부정 단어 사전을 이용한 규칙 기반(rule-based) 근사치입니다. "
        "반어법이나 '좋지 않다'와 같은 부정어 결합은 정확히 반영되지 않을 수 있어 "
        "정밀 분류가 아닌 여론 톤 참고 지표로 활용하시기 바랍니다."
    )

    scored = classify_sentiment(df_items)
    total = len(scored)
    counts = scored["감성"].value_counts()
    pos_count, neu_count, neg_count = (int(counts.get(label, 0)) for label in SENTIMENT_ORDER)

    metric_cols = st.columns(3)
    metric_cols[0].metric("긍정 비중", f"{(pos_count / total * 100 if total else 0):.1f}%", delta=f"{pos_count:,}건")
    metric_cols[1].metric("중립 비중", f"{(neu_count / total * 100 if total else 0):.1f}%", delta=f"{neu_count:,}건")
    metric_cols[2].metric("부정 비중", f"{(neg_count / total * 100 if total else 0):.1f}%", delta=f"{neg_count:,}건")

    st.markdown("### 검색어별 여론 비교")
    kw_summary = compute_sentiment_summary(scored, group_col="keyword")
    if kw_summary.empty:
        st.caption("검색어별 여론을 집계할 데이터가 없습니다.")
    else:
        st.plotly_chart(
            _stacked_sentiment_chart(kw_summary, "keyword", "검색어"), width="stretch"
        )
        st.dataframe(kw_summary.rename(columns={"keyword": "검색어"}), hide_index=True, width="stretch")

    st.markdown("### 채널별 여론 분포")
    ch_summary = compute_sentiment_summary(scored, group_col="channel_name")
    if ch_summary.empty:
        st.caption("채널별 여론을 집계할 데이터가 없습니다.")
    else:
        st.plotly_chart(
            _stacked_sentiment_chart(ch_summary, "channel_name", "채널"), width="stretch"
        )

    trend = compute_sentiment_trend(scored)
    if not trend.empty:
        st.markdown("### 여론 추이 (일자별 비중)")
        fig_trend = px.area(
            trend,
            x="일자",
            y="건수",
            color="감성",
            category_orders={"감성": SENTIMENT_ORDER},
            color_discrete_map=SENTIMENT_COLORS,
            groupnorm="fraction",
            template="plotly_white",
            labels={"건수": "비중"},
        )
        fig_trend.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10), yaxis_tickformat=".0%")
        st.plotly_chart(fig_trend, width="stretch")
        st.caption("발행일자가 확인된 문서만 반영한 일자별 긍/중/부정 비중 추이입니다.")

    st.markdown("### 긍정·부정 연관어")
    word_col1, word_col2 = st.columns(2)
    with word_col1:
        st.markdown("**긍정 문서 주요 단어**")
        pos_words = top_words_by_sentiment(scored, "긍정", top_n=10, exclude_words=keywords)
        if pos_words.empty:
            st.caption("긍정으로 분류된 문서가 없습니다.")
        else:
            st.dataframe(pos_words, hide_index=True, width="stretch")
    with word_col2:
        st.markdown("**부정 문서 주요 단어**")
        neg_words = top_words_by_sentiment(scored, "부정", top_n=10, exclude_words=keywords)
        if neg_words.empty:
            st.caption("부정으로 분류된 문서가 없습니다.")
        else:
            st.dataframe(neg_words, hide_index=True, width="stretch")

    with st.expander("부정 여론 샘플 문서 보기"):
        neg_docs = scored.loc[scored["감성"] == "부정", ["keyword", "channel_name", "title", "link"]].head(20)
        if neg_docs.empty:
            st.caption("부정으로 분류된 문서가 없습니다.")
        else:
            st.dataframe(
                neg_docs.rename(columns={"keyword": "검색어", "channel_name": "채널", "title": "제목"}),
                hide_index=True,
                width="stretch",
                column_config={"link": st.column_config.LinkColumn("원문", display_text="열기 ↗")},
            )
