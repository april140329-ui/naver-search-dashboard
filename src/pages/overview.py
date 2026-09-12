from __future__ import annotations

import html

import pandas as pd
import plotly.express as px
import streamlit as st

from src.components.metrics_view import render_metrics_view
from src.components.page_shell import (
    prepare_analysis_page,
    render_data_status,
    render_empty_state,
    render_page_header,
)


def _render_insights(data: dict) -> None:
    kpi = data["kpi_data"]
    estimated_total = kpi.get("estimated_total", 0)
    top_keyword_share = (
        kpi.get("top_keyword_count", 0) / estimated_total * 100 if estimated_total else 0
    )

    df_channels = data["df_channels"]
    top_channel_share = 0.0
    if not df_channels.empty and estimated_total:
        channel_totals = df_channels.groupby("channel_name")["total_count"].sum()
        top_channel_share = float(channel_totals.max() / estimated_total * 100)

    peak = kpi.get("peak_info", {})
    cards = [
        (
            "시장 규모",
            f"{kpi.get('top_keyword', 'N/A')}가 검색 결과 추정량의 {top_keyword_share:.1f}%를 차지합니다.",
        ),
        (
            "채널 집중도",
            f"{kpi.get('top_channel_name', 'N/A')} 채널 비중이 가장 높으며 전체 추정량의 {top_channel_share:.1f}%입니다.",
        ),
        (
            "검색 피크",
            f"{peak.get('date', 'N/A')}에 {peak.get('keyword', 'N/A')} 관심도가 {peak.get('ratio', 0):.1f}pt로 가장 높았습니다.",
        ),
    ]
    columns = st.columns(3)
    for column, (label, text) in zip(columns, cards):
        with column:
            st.markdown(
                f"<div class='insight-card'><span>{html.escape(label)}</span><p>{html.escape(text)}</p></div>",
                unsafe_allow_html=True,
            )


def _render_overview_charts(data: dict) -> None:
    df_trend: pd.DataFrame = data["df_trend"]
    df_channels: pd.DataFrame = data["df_channels"]
    left, right = st.columns([3, 2])

    with left:
        st.markdown("### 검색 관심도 흐름")
        if df_trend.empty:
            st.info("표시할 데이터랩 트렌드가 없습니다.")
        else:
            fig = px.line(
                df_trend,
                x="period",
                y="ratio",
                color="keyword",
                labels={"period": "일자", "ratio": "상대 검색지수", "keyword": "검색어"},
                template="plotly_white",
            )
            fig.update_layout(height=380, hovermode="x unified", margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, width="stretch")
            st.caption("데이터랩 지수는 선택 조건 안에서 최대값을 100으로 환산한 상대값입니다.")

    with right:
        st.markdown("### 채널별 검색 결과 추정량")
        if df_channels.empty:
            st.info("표시할 검색 채널 데이터가 없습니다.")
        else:
            channel_totals = (
                df_channels.groupby("channel_name", as_index=False)["total_count"]
                .sum()
                .sort_values("total_count")
            )
            fig = px.bar(
                channel_totals,
                x="total_count",
                y="channel_name",
                orientation="h",
                labels={"total_count": "검색 결과 추정량", "channel_name": "채널"},
                color="total_count",
                color_continuous_scale=["#d9f7e7", "#03C75A"],
                template="plotly_white",
            )
            fig.update_layout(height=380, coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, width="stretch")


def render_overview_page() -> None:
    render_page_header(
        "마켓 인사이트 종합",
        "검색 시장의 규모, 관심도 변화, 채널 집중도를 한눈에 확인합니다.",
    )
    controls, data = prepare_analysis_page()
    if not data:
        render_empty_state(controls)
        return

    render_data_status(data)
    render_metrics_view(data["kpi_data"])
    st.markdown("### 지금 확인할 포인트")
    _render_insights(data)
    _render_overview_charts(data)
