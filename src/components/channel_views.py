from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.components.channel_deep_dive import render_channel_deep_dive_tab
from src.config.settings import SEARCH_CHANNELS


CHANNEL_GUIDES = {
    "news": "언론사 집중도와 보도 시점 중심으로 이슈 확산을 확인하세요.",
    "blog": "블로거·출처 집중도와 후기형 제목의 반복 패턴을 확인하세요.",
    "webkr": "도메인별 노출과 공식 문서·가이드 유형의 비중을 확인하세요.",
    "image": "썸네일과 원본 출처를 함께 검토해 시각 콘텐츠 방향을 파악하세요.",
    "kin": "반복 질문과 소비자의 정보 공백을 중심으로 살펴보세요.",
    "local": "API 표본이 검색어별 최대 5건이므로 주소와 카테고리를 정성적으로 확인하세요.",
    "cafearticle": "특정 커뮤니티 집중도와 실제 사용자 표현을 중심으로 살펴보세요.",
    "encyc": "표본이 적을 수 있으므로 용어 정의와 주제 커버리지 중심으로 확인하세요.",
}


def _render_channel_preview(channel_id: str, df: pd.DataFrame) -> None:
    if channel_id == "image" and not df.empty:
        image_rows = []
        for _, row in df.head(8).iterrows():
            extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
            if extra.get("thumbnail"):
                image_rows.append((extra["thumbnail"], row.get("title", "")))
        if image_rows:
            st.markdown("#### 이미지 표본")
            columns = st.columns(4)
            for index, (url, caption) in enumerate(image_rows):
                columns[index % 4].image(url, caption=caption, width="stretch")

    if channel_id == "local" and not df.empty:
        rows = []
        for _, row in df.iterrows():
            extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
            rows.append(
                {
                    "검색어": row.get("keyword", ""),
                    "장소": row.get("title", ""),
                    "주소": extra.get("roadAddress") or extra.get("address", ""),
                    "전화": extra.get("telephone", ""),
                    "원문": row.get("link", ""),
                }
            )
        st.markdown("#### 장소 표본")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def render_channel_details_tab(
    df_items: pd.DataFrame,
    selected_channels: list[str],
    df_channels: pd.DataFrame | None = None,
) -> None:
    """채널 비교 후 선택한 단일 채널만 계산·렌더링합니다."""
    active_channels = [channel for channel in selected_channels if channel in SEARCH_CHANNELS]
    if not active_channels:
        st.info("선택된 채널이 없습니다.")
        return

    st.markdown("### 채널 비교")
    if df_channels is not None and not df_channels.empty:
        chart_df = (
            df_channels.groupby(["channel_id", "channel_name"], as_index=False)["total_count"]
            .sum()
            .sort_values("total_count")
        )
        chart = px.bar(
            chart_df,
            x="total_count",
            y="channel_name",
            orientation="h",
            color="total_count",
            color_continuous_scale=["#d9f7e7", "#03C75A"],
            labels={"total_count": "검색 결과 추정량", "channel_name": "채널"},
            template="plotly_white",
        )
        chart.update_layout(height=360, coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(chart, width="stretch")

    selected = st.selectbox(
        "상세 분석 채널",
        active_channels,
        format_func=lambda channel: f"{SEARCH_CHANNELS[channel].icon} {SEARCH_CHANNELS[channel].name}",
    )
    channel_df = df_items[df_items["channel_id"] == selected].copy() if not df_items.empty else df_items
    estimated = 0
    if df_channels is not None and not df_channels.empty:
        estimated = int(df_channels.loc[df_channels["channel_id"] == selected, "total_count"].sum())

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("실제 수집 표본", f"{len(channel_df):,}건")
    metric2.metric("검색 결과 추정량", f"{estimated:,}건")
    metric3.metric("포함 검색어", f"{channel_df['keyword'].nunique() if not channel_df.empty else 0}개")
    st.info(CHANNEL_GUIDES.get(selected, "채널별 콘텐츠 특성을 확인하세요."))

    _render_channel_preview(selected, channel_df)
    render_channel_deep_dive_tab(selected, channel_df)
