from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.text_mining import extract_top_words
from src.config.settings import SEARCH_CHANNELS


def _word_bar_chart(words_df: pd.DataFrame, title: str) -> None:
    chart = px.bar(
        words_df.iloc[::-1],
        x="빈도수",
        y="단어",
        orientation="h",
        color="빈도수",
        color_continuous_scale=["#d9f7e7", "#03C75A"],
        title=title,
        template="plotly_white",
    )
    chart.update_layout(height=500, coloraxis_showscale=False, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(chart, width="stretch")


def _word_treemap(words_df: pd.DataFrame, title: str) -> None:
    """빈도에 비례한 타일 크기로 단어를 배치하는 워드클라우드 스타일 트리맵."""
    chart = px.treemap(
        words_df,
        path=[px.Constant("전체 연관어"), "단어"],
        values="빈도수",
        color="빈도수",
        color_continuous_scale=["#eaf7f0", "#03C75A", "#00693a"],
        title=title,
    )
    chart.update_traces(
        textinfo="label+value",
        textfont_size=16,
        marker=dict(cornerradius=6),
    )
    chart.update_layout(height=500, margin=dict(l=10, r=10, t=50, b=10), coloraxis_showscale=False)
    st.plotly_chart(chart, width="stretch")


def _render_word_visual(words_df: pd.DataFrame, title: str, view_key: str) -> None:
    view = st.radio(
        "시각화 방식",
        ["막대그래프", "트리맵(워드클라우드)"],
        horizontal=True,
        key=view_key,
        label_visibility="collapsed",
    )
    if view == "막대그래프":
        _word_bar_chart(words_df, title)
    else:
        _word_treemap(words_df, title)


def render_text_insights_section(df_items: pd.DataFrame, keywords: list[str]) -> None:
    """빈출어와 검색어별 특징 단어를 분리해 표시합니다."""
    if df_items.empty:
        st.info("텍스트 분석을 위한 수집 표본이 없습니다.")
        return

    tab_words, tab_compare = st.tabs(["연관어 분석", "검색어 비교"])
    with tab_words:
        filter1, filter2, filter3, filter4 = st.columns([1, 1, 1, 1])
        with filter1:
            keyword_options = ["전체"] + [keyword for keyword in keywords if keyword in df_items["keyword"].unique()]
            selected_keyword = st.selectbox("검색어", keyword_options)
        with filter2:
            channel_options = ["전체"] + sorted(df_items["channel_id"].dropna().unique().tolist())
            selected_channel = st.selectbox(
                "채널",
                channel_options,
                format_func=lambda channel: "전체 채널" if channel == "전체" else f"{SEARCH_CHANNELS[channel].icon} {SEARCH_CHANNELS[channel].name}",
            )
        with filter3:
            ngram_size = st.radio("단어 단위", [1, 2], format_func=lambda value: "단어" if value == 1 else "2어절", horizontal=True)
        with filter4:
            top_n = st.slider("표시 개수", 10, 40, 20, 5)

        exclude_queries = st.checkbox("입력 검색어 자체를 제외", value=True)
        words_df = extract_top_words(
            df_items,
            keyword_filter=selected_keyword,
            channel_filter=selected_channel,
            top_n=top_n,
            exclude_words=keywords if exclude_queries else None,
            ngram_size=ngram_size,
        )
        if words_df.empty:
            st.info("선택한 조건에서 추출할 연관어가 없습니다.")
        else:
            chart_col, table_col = st.columns([3, 2])
            with chart_col:
                _render_word_visual(words_df, f"상위 {len(words_df)}개 연관 표현", view_key="word_view_main")
            with table_col:
                ranking = words_df.copy()
                ranking.insert(0, "순위", range(1, len(ranking) + 1))
                st.dataframe(ranking, hide_index=True, width="stretch", height=500)

    with tab_compare:
        top_per_keyword = st.slider("검색어별 비교 단어 수", 3, 10, 5)
        records = []
        for keyword in keywords:
            word_df = extract_top_words(
                df_items,
                keyword_filter=keyword,
                top_n=top_per_keyword,
                exclude_words=keywords,
            )
            if not word_df.empty:
                word_df = word_df.copy()
                word_df["검색어"] = keyword
                records.append(word_df)
        if records:
            comparison = pd.concat(records, ignore_index=True)
            chart = px.bar(
                comparison,
                x="빈도수",
                y="단어",
                color="검색어",
                facet_col="검색어",
                facet_col_wrap=2,
                orientation="h",
                template="plotly_white",
            )
            chart.update_yaxes(matches=None, showticklabels=True)
            chart.update_layout(height=max(420, 250 * ((len(keywords) + 1) // 2)), margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(chart, width="stretch")
        else:
            st.info("비교할 단어가 없습니다.")
