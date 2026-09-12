from __future__ import annotations

from src.components.page_shell import (
    prepare_analysis_page,
    render_data_status,
    render_empty_state,
    render_page_header,
)
from src.components.trend_charts import render_trend_section


def render_trends_page() -> None:
    render_page_header(
        "검색 트렌드",
        "키워드별 관심도 변화와 피크, 변동성, 동행 관계를 분석합니다.",
        eyebrow="TREND ANALYSIS",
    )
    controls, data = prepare_analysis_page()
    if not data:
        render_empty_state(controls)
        return

    render_data_status(data)
    render_trend_section(data["df_trend"], data["df_channels"])
