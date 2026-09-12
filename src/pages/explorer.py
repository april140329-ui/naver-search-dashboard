from __future__ import annotations

import pandas as pd
import streamlit as st

from src.components.page_shell import (
    prepare_analysis_page,
    render_data_status,
    render_empty_state,
    render_page_header,
)
from src.config.settings import SEARCH_CHANNELS
from src.utils.exporter import dataframe_to_csv_bytes, dataframe_to_excel_bytes


@st.cache_data(show_spinner=False)
def _make_excel(df: pd.DataFrame) -> bytes:
    return dataframe_to_excel_bytes(df, sheet_name="검색결과")


def render_explorer_page() -> None:
    render_page_header(
        "데이터 탐색",
        "수집 표본을 검색하고 필터링하며 원문 근거와 내보내기 데이터를 검증합니다.",
        eyebrow="DATA EXPLORER",
    )
    controls, data = prepare_analysis_page()
    if not data:
        render_empty_state(controls)
        return

    render_data_status(data)
    source_df: pd.DataFrame = data["df_items"].copy()
    if source_df.empty:
        st.warning("수집된 검색 결과 표본이 없습니다. 수집 오류를 확인해 주세요.")
        return

    st.markdown("### 표본 필터")
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])
    with filter_col1:
        keyword_options = sorted(source_df["keyword"].dropna().unique().tolist())
        selected_keywords = st.multiselect("검색어", keyword_options, default=keyword_options)
    with filter_col2:
        channel_options = sorted(source_df["channel_id"].dropna().unique().tolist())
        selected_channels = st.multiselect(
            "채널",
            channel_options,
            default=channel_options,
            format_func=lambda cid: SEARCH_CHANNELS[cid].name if cid in SEARCH_CHANNELS else cid,
        )
    with filter_col3:
        search_text = st.text_input("제목·설명·출처 검색", placeholder="예: 출시, 후기, 언론사명")

    filtered = source_df[
        source_df["keyword"].isin(selected_keywords)
        & source_df["channel_id"].isin(selected_channels)
    ].copy()
    if search_text.strip():
        needle = search_text.strip()
        searchable = (
            filtered["title"].fillna("")
            + " "
            + filtered["description"].fillna("")
            + " "
            + filtered["author_or_source"].fillna("")
        )
        filtered = filtered[searchable.str.contains(needle, case=False, regex=False)]

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("필터 결과", f"{len(filtered):,}건")
    metric2.metric("전체 수집 표본", f"{len(source_df):,}건")
    metric3.metric("포함 채널", f"{filtered['channel_id'].nunique():,}개")

    display_columns = [
        "keyword",
        "channel_name",
        "rank",
        "title",
        "description",
        "author_or_source",
        "pub_date",
        "link",
    ]
    display_columns = [column for column in display_columns if column in filtered.columns]
    st.dataframe(
        filtered[display_columns],
        column_config={
            "keyword": "검색어",
            "channel_name": "채널",
            "rank": st.column_config.NumberColumn("수집 순위", format="%d"),
            "title": st.column_config.TextColumn("제목", width="medium"),
            "description": st.column_config.TextColumn("설명", width="large"),
            "author_or_source": "작성자/출처",
            "pub_date": "발행일",
            "link": st.column_config.LinkColumn("원문", display_text="열기 ↗"),
        },
        hide_index=True,
        width="stretch",
        height=520,
    )

    download1, download2, _ = st.columns([1, 1, 3])
    export_df = filtered[display_columns]
    with download1:
        st.download_button(
            "CSV 다운로드",
            dataframe_to_csv_bytes(export_df),
            file_name="naver_search_filtered.csv",
            mime="text/csv",
            width="stretch",
        )
    with download2:
        st.download_button(
            "Excel 다운로드",
            _make_excel(export_df),
            file_name="naver_search_filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
