from __future__ import annotations

from typing import Any

import streamlit as st


def render_metrics_view(kpi_data: dict[str, Any]) -> None:
    """검색 결과 추정량과 실제 수집 표본을 구분한 핵심 지표를 표시합니다."""
    first_row = st.columns(3)
    first_row[0].metric(
        "실제 수집 표본",
        f"{kpi_data.get('collected_items_count', 0):,}건",
        help="API 응답에서 실제로 내려받아 분석에 사용한 행 수입니다.",
    )
    first_row[1].metric(
        "검색 결과 추정량",
        f"{kpi_data.get('estimated_total', 0):,}건",
        help="검색 API의 total 응답 합계입니다. 검색어·채널 간 중복이 포함될 수 있으며 실제 수집 행 수와 다릅니다.",
    )
    first_row[2].metric(
        "추정량 1위 검색어",
        kpi_data.get("top_keyword", "N/A"),
        delta=f"{kpi_data.get('top_keyword_count', 0):,}건",
    )

    second_row = st.columns(3)
    second_row[0].metric("최대 집중 채널", kpi_data.get("top_channel_name", "N/A"))
    second_row[1].metric(
        "평균 관심도 1위",
        kpi_data.get("trend_leader", "N/A"),
        delta=f"평균 {kpi_data.get('trend_leader_avg', 0):.1f}pt",
        help="선택한 기간과 키워드 안에서 계산되는 데이터랩 상대지수입니다.",
    )
    peak = kpi_data.get("peak_info", {})
    second_row[2].metric(
        "최고 관심도 피크",
        peak.get("date", "N/A"),
        delta=f"{peak.get('keyword', 'N/A')} · {peak.get('ratio', 0):.1f}pt",
    )
