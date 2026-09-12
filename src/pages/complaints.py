from __future__ import annotations

from src.components.complaint_view import render_complaint_section
from src.components.page_shell import (
    prepare_analysis_page,
    render_data_status,
    render_empty_state,
    render_page_header,
)


def render_complaints_page() -> None:
    render_page_header(
        "민원 감정 분석",
        "수집한 글을 민원 유형과 심각도로 분류해 어떤 고충이 어디에 몰려 있는지 확인합니다.",
        eyebrow="COMPLAINT INSIGHT",
    )
    controls, data = prepare_analysis_page()
    if not data:
        render_empty_state(controls)
        return

    render_data_status(data)
    render_complaint_section(data["df_items"], data["keywords"])
