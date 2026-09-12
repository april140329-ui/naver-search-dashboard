from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.complaint import (
    analyze_complaints,
    compute_category_severity_crosstab,
    compute_category_summary,
    top_words_by_category,
)
from src.analysis.sentiment import classify_sentiment

SEVERITY_COLORS = {"심각": "#e5484d", "보통": "#f5a524", "경미": "#94a3b8"}
SEVERITY_ORDER = ["심각", "보통", "경미"]


def _render_headline_metrics(df_complaints: pd.DataFrame) -> None:
    total = len(df_complaints)
    severe = int((df_complaints["심각도"] == "심각").sum())
    negative = int((df_complaints["감성"] == "부정").sum())
    top_category = df_complaints["민원유형"].value_counts().idxmax() if total else "N/A"

    cols = st.columns(4)
    cols[0].metric("분석 대상 글", f"{total:,}건")
    cols[1].metric(
        "심각 민원",
        f"{severe:,}건",
        delta=f"{(severe / total * 100 if total else 0):.1f}%",
        help="부정 감정 강도와 긴급·반복 표현을 합산한 심각도 점수가 높은 글입니다.",
    )
    cols[2].metric(
        "부정 여론",
        f"{negative:,}건",
        delta=f"{(negative / total * 100 if total else 0):.1f}%",
    )
    cols[3].metric("최다 민원 유형", top_category)


def _render_category_section(df_complaints: pd.DataFrame) -> None:
    summary = compute_category_summary(df_complaints)
    if summary.empty:
        st.info("민원 유형을 집계할 데이터가 없습니다.")
        return

    chart_col, table_col = st.columns([3, 2], gap="large")
    with chart_col:
        chart = px.bar(
            summary.sort_values("건수"),
            x="건수",
            y="민원유형",
            orientation="h",
            color="평균심각도",
            color_continuous_scale=["#fde8e8", "#e5484d"],
            template="plotly_white",
            labels={"건수": "민원 글 수", "민원유형": "", "평균심각도": "평균 심각도"},
        )
        chart.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(chart, width="stretch")
    with table_col:
        st.dataframe(summary, hide_index=True, width="stretch", height=420)


def _render_severity_section(df_complaints: pd.DataFrame) -> None:
    crosstab = compute_category_severity_crosstab(df_complaints)
    if crosstab.empty:
        return

    melted = crosstab.reset_index().melt(
        id_vars="민원유형", value_vars=SEVERITY_ORDER, var_name="심각도", value_name="건수"
    )
    chart = px.bar(
        melted,
        x="민원유형",
        y="건수",
        color="심각도",
        barmode="stack",
        category_orders={"심각도": SEVERITY_ORDER},
        color_discrete_map=SEVERITY_COLORS,
        template="plotly_white",
        labels={"민원유형": ""},
    )
    chart.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(chart, width="stretch")


def _render_severe_documents(df_complaints: pd.DataFrame) -> None:
    severe_docs = (
        df_complaints.sort_values("심각도점수", ascending=False)
        .loc[:, ["심각도", "심각도점수", "민원유형", "keyword", "channel_name", "title", "link"]]
        .head(30)
    )
    if severe_docs.empty:
        st.caption("표시할 문서가 없습니다.")
        return

    st.dataframe(
        severe_docs.rename(
            columns={"keyword": "검색어", "channel_name": "채널", "title": "제목"}
        ),
        hide_index=True,
        width="stretch",
        height=420,
        column_config={
            "link": st.column_config.LinkColumn("원문", display_text="열기 ↗"),
            "제목": st.column_config.TextColumn("제목", width="large"),
        },
    )


def render_complaint_section(df_items: pd.DataFrame, keywords: list[str]) -> None:
    """수집한 글을 민원 유형과 심각도로 분류해 고충 중심으로 분석합니다."""
    if df_items.empty:
        st.info("민원 분석을 위한 수집 표본이 없습니다. 왼쪽에서 분석을 실행해 주세요.")
        return

    st.info(
        "민원 유형과 심각도는 키워드 사전 기반으로 자동 분류한 결과입니다. "
        "실제 민원 접수 데이터가 아닌 네이버 검색 글을 대상으로 하므로, "
        "정확한 판정보다 고충이 어디에 몰려 있는지 파악하는 용도로 활용하세요.",
        icon="ℹ️",
    )

    scored = classify_sentiment(df_items)
    complaints = analyze_complaints(scored)

    _render_headline_metrics(complaints)

    st.subheader("민원 유형 분포")
    st.caption("어떤 종류의 고충이 가장 많이 제기되는지 보여줍니다. 색이 진할수록 평균 심각도가 높습니다.")
    _render_category_section(complaints)

    st.subheader("유형별 심각도 구성")
    st.caption("같은 건수라도 심각 비중이 높은 유형이 우선 대응 대상입니다.")
    _render_severity_section(complaints)

    st.subheader("유형별 주요 표현")
    categories = complaints["민원유형"].value_counts().index.tolist()
    if categories:
        selected_category = st.selectbox("민원 유형 선택", categories)
        words = top_words_by_category(
            complaints, selected_category, top_n=12, exclude_words=keywords
        )
        if words.empty:
            st.caption("추출할 표현이 없습니다.")
        else:
            word_chart_col, word_table_col = st.columns([3, 2], gap="large")
            with word_chart_col:
                chart = px.bar(
                    words.iloc[::-1],
                    x="빈도수",
                    y="단어",
                    orientation="h",
                    color="빈도수",
                    color_continuous_scale=["#fde8e8", "#e5484d"],
                    template="plotly_white",
                    labels={"단어": ""},
                )
                chart.update_layout(height=380, coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(chart, width="stretch")
            with word_table_col:
                st.dataframe(words, hide_index=True, width="stretch", height=380)

    st.subheader("심각도 높은 민원 글")
    st.caption("심각도 점수가 높은 순으로 정렬했습니다. 원문 링크로 실제 내용을 확인하세요.")
    _render_severe_documents(complaints)
