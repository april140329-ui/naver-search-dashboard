from __future__ import annotations

from src.components.page_shell import (
    prepare_analysis_page,
    render_data_status,
    render_empty_state,
    render_page_header,
)
from src.components.text_insights import render_text_insights_section


def render_text_insights_page() -> None:
    render_page_header(
        "텍스트 인사이트",
        "제목과 설명문에 반복되는 주제어를 찾고, 검색어·채널별 메시지 차이와 여론 톤을 비교합니다.",
        eyebrow="CONTENT SIGNALS",
    )
    controls, data = prepare_analysis_page()
    if not data:
        render_empty_state(controls)
        return

    render_data_status(data)
    render_text_insights_section(data["df_items"], data["keywords"])
