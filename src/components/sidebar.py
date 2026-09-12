from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import streamlit as st

from src.config.settings import SEARCH_CHANNELS, get_api_credentials


def render_sidebar() -> dict[str, Any]:
    """모든 분석 페이지에서 공유하는 명시적 실행 폼을 렌더링합니다."""
    credentials = get_api_credentials()
    has_api_keys = credentials["is_configured"]

    st.sidebar.markdown("## NAVER Insight")
    st.sidebar.caption("분석 조건은 모든 페이지에 공통 적용됩니다.")
    if has_api_keys:
        st.sidebar.success("API 키 등록됨", icon="✅")
    else:
        st.sidebar.warning("API 키 미등록 · 데모 모드 사용 가능", icon="⚠️")

    today = datetime.now().date()
    with st.sidebar.form("analysis_controls"):
        raw_keywords = st.text_input(
            "검색어",
            value="아이폰, 갤럭시, 픽셀",
            placeholder="쉼표로 구분해 최대 5개",
            help="네이버 데이터랩 비교 제한에 맞춰 최대 5개까지 분석합니다.",
        )
        keywords = [keyword.strip() for keyword in raw_keywords.split(",") if keyword.strip()]

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("시작일", value=today - timedelta(days=90))
        with date_col2:
            end_date = st.date_input("종료일", value=today)

        time_unit = st.selectbox(
            "집계 단위",
            options=["date", "week", "month"],
            format_func=lambda value: {"date": "일간", "week": "주간", "month": "월간"}[value],
        )

        all_channel_ids = list(SEARCH_CHANNELS.keys())
        selected_channels = st.multiselect(
            "수집 채널",
            options=all_channel_ids,
            default=all_channel_ids,
            format_func=lambda channel_id: f"{SEARCH_CHANNELS[channel_id].icon} {SEARCH_CHANNELS[channel_id].name}",
        )

        with st.expander("수집 옵션"):
            display_count = st.slider("채널별 수집 표본", 10, 100, 30, 10)
            sort_order = st.radio(
                "정렬 기준",
                options=["sim", "date"],
                format_func=lambda value: "관련도순" if value == "sim" else "최신순",
                horizontal=True,
            )

        mock_mode = st.toggle(
            "데모 데이터 사용",
            value=not has_api_keys,
            help="켜면 외부 API를 호출하지 않고 시뮬레이션 데이터를 생성합니다.",
        )
        run_clicked = st.form_submit_button("분석 실행", type="primary", width="stretch")

    if len(keywords) > 5:
        st.sidebar.error(f"현재 {len(keywords)}개입니다. 검색어를 5개 이하로 줄여 주세요.")
    st.sidebar.caption("화면 이동만으로 API가 다시 호출되지는 않습니다.")

    return {
        "keywords": keywords,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "time_unit": time_unit,
        "selected_channels": selected_channels,
        "display_count": display_count,
        "sort_order": sort_order,
        "mock_mode": mock_mode,
        "run_clicked": run_clicked,
        "has_api_keys": has_api_keys,
    }
