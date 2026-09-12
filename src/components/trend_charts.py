from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.eda_engine import compute_trend_pivot, compute_trend_summary_stats


def _trend_change_table(df_trend: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keyword, group in df_trend.sort_values("period").groupby("keyword"):
        values = group["ratio"].dropna()
        if values.empty:
            continue
        first = float(values.iloc[0])
        latest = float(values.iloc[-1])
        rows.append(
            {
                "검색어": keyword,
                "시작 지수": round(first, 2),
                "최근 지수": round(latest, 2),
                "기간 변화(pt)": round(latest - first, 2),
                "최고 지수": round(float(values.max()), 2),
            }
        )
    return pd.DataFrame(rows).sort_values("기간 변화(pt)", ascending=False) if rows else pd.DataFrame()


def render_trend_section(df_trend: pd.DataFrame, df_channels: pd.DataFrame | None = None) -> None:
    """트렌드 추이, 변화, 피크 및 상관관계를 목적별 탭으로 표시합니다."""
    if df_trend.empty or "ratio" not in df_trend.columns:
        st.warning("데이터랩 트렌드가 없습니다. 수집 오류 또는 분석 조건을 확인해 주세요.")
        return

    st.info("데이터랩 검색지수는 선택한 조건 안에서 최대값을 100으로 환산한 상대값이며 절대 검색량이 아닙니다.")
    tab_flow, tab_change, tab_peak, tab_relation = st.tabs(
        ["추이 비교", "증감 분석", "피크 분석", "관계 분석"]
    )

    with tab_flow:
        fig = px.line(
            df_trend,
            x="period",
            y="ratio",
            color="keyword",
            markers=df_trend["period"].nunique() <= 32,
            labels={"period": "일자", "ratio": "상대 검색지수", "keyword": "검색어"},
            template="plotly_white",
        )
        fig.update_layout(height=500, hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, width="stretch")

    with tab_change:
        changes = _trend_change_table(df_trend)
        if not changes.empty:
            chart = px.bar(
                changes.sort_values("기간 변화(pt)"),
                x="기간 변화(pt)",
                y="검색어",
                orientation="h",
                color="기간 변화(pt)",
                color_continuous_scale="RdYlGn",
                template="plotly_white",
            )
            chart.update_layout(height=360, coloraxis_showscale=False)
            st.plotly_chart(chart, width="stretch")
            st.dataframe(changes, hide_index=True, width="stretch")

    with tab_peak:
        peak_rows = (
            df_trend.loc[df_trend.groupby("keyword")["ratio"].idxmax()]
            .rename(columns={"keyword": "검색어", "period": "피크 일자", "ratio": "최고 지수"})
            [["검색어", "피크 일자", "최고 지수"]]
            .sort_values("최고 지수", ascending=False)
        )
        st.dataframe(peak_rows, hide_index=True, width="stretch")
        stats = compute_trend_summary_stats(df_trend).rename(columns={"keyword": "검색어"})
        if not stats.empty:
            st.markdown("#### 기간 통계")
            st.dataframe(stats, hide_index=True, width="stretch")

    with tab_relation:
        pivot_df = compute_trend_pivot(df_trend)
        if pivot_df.shape[1] > 1:
            corr = pivot_df.corr().round(3)
            chart = px.imshow(
                corr,
                text_auto=True,
                color_continuous_scale="RdBu",
                color_continuous_midpoint=0,
                labels={"color": "상관계수"},
                aspect="auto",
            )
            chart.update_layout(height=460, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(chart, width="stretch")
            st.caption("1에 가까울수록 같은 방향, -1에 가까울수록 반대 방향으로 움직인 구간이 많다는 뜻입니다.")
        else:
            st.info("관계 분석에는 2개 이상의 검색어가 필요합니다.")
