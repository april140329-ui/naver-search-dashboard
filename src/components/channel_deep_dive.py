from __future__ import annotations
import io
import pandas as pd
import plotly.express as px
import streamlit as st
from src.analysis.eda_engine import (
    enrich_channel_df,
    compute_channel_descriptive_stats,
    compute_channel_crosstab_source,
    compute_channel_crosstab_dow,
    compute_channel_pivot_table,
    compute_channel_word_freq_table,
)
from src.config.settings import SEARCH_CHANNELS


def render_channel_deep_dive_tab(channel_id: str, raw_df: pd.DataFrame) -> None:
    """
    단일 검색 채널(뉴스, 블로그, 카페, 웹문서, 백과사전 등)에 대해
    파이차트를 배제한 5대 인터랙티브 그래프와 5대 통계표를 렌더링하는 심층 EDA 뷰
    """
    spec = SEARCH_CHANNELS.get(channel_id)
    channel_name = spec.name if spec else channel_id
    icon = spec.icon if spec else "📄"

    if raw_df.empty:
        st.info(f"{icon} {channel_name} 채널에 대한 검색 결과가 없습니다.")
        return

    # 파생 변수(텍스트 길이, 요일, 일자) 추가
    df = enrich_channel_df(raw_df)

    # 상단 요약 바 & 다운로드
    col_t, col_c, col_x = st.columns([3, 1, 1])
    with col_t:
        st.markdown(f"#### {icon} **{channel_name}** 심층 EDA 리포트 (총 {len(df):,}건 분석)")
    with col_c:
        csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv_bytes,
            file_name=f"naver_{channel_id}_eda.csv",
            mime="text/csv",
            key=f"deep_csv_{channel_id}",
            width="stretch",
        )
    with col_x:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=channel_name)
            # 기술통계 및 교차표도 별도 시트에 함께 저장
            desc_st = compute_channel_descriptive_stats(df)
            if not desc_st.empty:
                desc_st.to_excel(writer, index=False, sheet_name="기술통계")
            ct_src = compute_channel_crosstab_source(df)
            if not ct_src.empty:
                ct_src.to_excel(writer, sheet_name="출처교차표")
        st.download_button(
            label="📥 Excel(다중시트)",
            data=buf.getvalue(),
            file_name=f"naver_{channel_id}_eda.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"deep_xlsx_{channel_id}",
            width="stretch",
        )

    st.markdown("---")

    # =========================================================================
    # PART 1. 파이차트를 제외한 5대 인터랙티브 그래프
    # =========================================================================
    st.markdown("### 📊 5대 인터랙티브 통계 시각화 (No Pie-Charts)")

    g_col1, g_col2 = st.columns([1, 1])

    # 1. 시계열 발행량 추이 막대 차트
    with g_col1:
        st.markdown("##### ① 시계열 게시물 등록 추이 (Time-Series Histogram)")
        valid_dates = df[df["발행일자"].notna() & (df["발행일자"] != "")]
        if not valid_dates.empty:
            fig_ts = px.histogram(
                valid_dates,
                x="발행일자",
                color="keyword",
                barmode="group",
                title=f"{channel_name} 일자별 게시물 등록 빈도",
                labels={"발행일자": "등록 일자", "count": "발행 건수", "keyword": "키워드"},
                template="plotly_white",
            )
            fig_ts.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_ts, width="stretch", key=f"{channel_id}_fig_ts")
        else:
            st.info("시계열 날짜 정보가 없습니다.")

    # 2. 키워드별 본문 글자 수 분포 박스플롯
    with g_col2:
        st.markdown("##### ② 키워드별 본문 글자수 박스플롯 (IQR & Outlier)")
        fig_box = px.box(
            df,
            x="keyword",
            y="본문글자수",
            color="keyword",
            points="outliers",
            title="키워드별 본문 설명 글자수 분포 및 이상치",
            labels={"keyword": "키워드", "본문글자수": "글자 수 (자)"},
            template="plotly_white",
        )
        fig_box.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
        st.plotly_chart(fig_box, width="stretch", key=f"{channel_id}_fig_box")

    g_col3, g_col4 = st.columns([1, 1])

    # 3. 주요 출처 / 언론사 / 작성자 Top 15 수평 막대 차트
    with g_col3:
        st.markdown("##### ③ 주요 출처/언론사 Top 15 분포 (Horizontal Bar)")
        top_src_df = (
            df[df["작성출처"] != "기타/미상"]
            .groupby(["작성출처", "keyword"])
            .size()
            .reset_index(name="건수")
        )
        if top_src_df.empty:
            top_src_df = df.groupby(["작성출처", "keyword"]).size().reset_index(name="건수")

        # 상위 15개 출처 필터링
        top_15_names = top_src_df.groupby("작성출처")["건수"].sum().nlargest(15).index
        sub_top = top_src_df[top_src_df["작성출처"].isin(top_15_names)].sort_values(by="건수", ascending=True)

        fig_src = px.bar(
            sub_top,
            x="건수",
            y="작성출처",
            color="keyword",
            orientation="h",
            title="상위 주요 작성 출처 및 미디어 집중도",
            labels={"건수": "문서 건수", "작성출처": "출처/매체명", "keyword": "키워드"},
            template="plotly_white",
        )
        fig_src.update_layout(height=370, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_src, width="stretch", key=f"{channel_id}_fig_src")

    # 4. 제목 글자 수 vs 본문 글자 수 상관 산점도
    with g_col4:
        st.markdown("##### ④ 제목 vs 본문 글자수 상관 산점도 (Scatter Plot)")
        fig_scatter = px.scatter(
            df,
            x="제목글자수",
            y="본문글자수",
            color="keyword",
            hover_data=["title", "작성출처"],
            title="제목 길이와 본문 길이 간의 상관 분포",
            labels={"제목글자수": "제목 길이 (자)", "본문글자수": "본문 길이 (자)", "keyword": "키워드"},
            template="plotly_white",
        )
        fig_scatter.update_layout(height=370, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_scatter, width="stretch", key=f"{channel_id}_fig_scatter")

    # 5. 요일별 발행 빈도 히트맵
    st.markdown("##### ⑤ 요일 x 키워드 콘텐츠 발행 빈도 히트맵 (Crosstab Heatmap)")
    ct_dow = compute_channel_crosstab_dow(df)
    if not ct_dow.empty:
        # 합계 열/행 제외 히트맵 구성
        plot_dow = ct_dow.drop(columns=["합계"], errors="ignore").drop(index=["합계"], errors="ignore")
        fig_hm = px.imshow(
            plot_dow,
            text_auto=True,
            color_continuous_scale="Viridis",
            title="요일별(월~일) 검색어 콘텐츠 발생 밀도",
            labels=dict(x="요일", y="키워드", color="발행 건수"),
            aspect="auto",
        )
        fig_hm.update_layout(height=260, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_hm, width="stretch", key=f"{channel_id}_fig_hm")

    st.markdown("---")

    # =========================================================================
    # PART 2. 5대 정량 통계 분석 표 (기술통계, 교차표, 피벗, 단어빈도)
    # =========================================================================
    st.markdown("### 📋 5대 정량 통계 분석 표 (Statistical Tables)")

    # 표 1. 기초 기술통계량 표
    st.markdown("##### 1️⃣ 키워드별 텍스트 글자 수 기술통계량 (Descriptive Statistics)")
    desc_df = compute_channel_descriptive_stats(df)
    if not desc_df.empty:
        st.dataframe(desc_df.set_index("키워드"), width="stretch")
    st.caption("※ 평균, 표준편차(Std), 중앙값(Median), 최솟값/최댓값을 포함한 통계 지표입니다.")

    t_col1, t_col2 = st.columns([1, 1])

    # 표 2. 키워드 x 주요 출처 교차표
    with t_col1:
        st.markdown("##### 2️⃣ 키워드 x 상위 출처/언론사 교차표 (Crosstab)")
        ct_source = compute_channel_crosstab_source(df, top_n=10)
        if not ct_source.empty:
            st.dataframe(ct_source, width="stretch")
        else:
            st.info("출처 교차표 데이터를 집계할 수 없습니다.")

    # 표 3. 키워드 x 발행 요일 교차표
    with t_col2:
        st.markdown("##### 3️⃣ 키워드 x 발행 요일 교차표 (Crosstab)")
        if not ct_dow.empty:
            st.dataframe(ct_dow, width="stretch")

    # 표 4. 키워드별 다차원 통계 집계 피벗테이블
    st.markdown("##### 4️⃣ 키워드별 다차원 피벗테이블 (Multi-Metric Pivot Table)")
    piv_df = compute_channel_pivot_table(df)
    if not piv_df.empty:
        st.dataframe(piv_df.set_index("keyword"), width="stretch")

    # 표 5. 상위 20개 연관어 빈도 및 누적 비중 순위표
    st.markdown("##### 5️⃣ 상위 20개 핵심 연관어 출현 빈도 및 누적 비중표 (Word Frequency Table)")
    word_freq_df = compute_channel_word_freq_table(df, top_n=20)
    if not word_freq_df.empty:
        st.dataframe(word_freq_df, width="stretch")

    # =========================================================================
    # PART 3. 원본 데이터 리스트 & 링크 바로가기
    # =========================================================================
    st.markdown("---")
    st.markdown("##### 🔍 수집 원본 데이터 미리보기")
    show_cols = [c for c in ["keyword", "title", "description", "pub_date", "작성출처", "link"] if c in df.columns]
    st.dataframe(
        df[show_cols],
        column_config={
            "link": st.column_config.LinkColumn("원문 링크", display_text="바로가기 ↗"),
            "title": st.column_config.TextColumn("제목", width="medium"),
            "description": st.column_config.TextColumn("본문 요약", width="large"),
        },
        width="stretch",
        height=300,
    )
