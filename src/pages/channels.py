from __future__ import annotations

from src.components.channel_views import render_channel_details_tab
from src.components.page_shell import (
    prepare_analysis_page,
    render_data_status,
    render_empty_state,
    render_page_header,
)


def render_channels_page() -> None:
    render_page_header(
        "채널 분석",
        "8대 검색 채널을 비교하고 선택한 채널의 콘텐츠 구조와 출처를 깊이 살펴봅니다.",
        eyebrow="CHANNEL DEEP DIVE",
    )
    controls, data = prepare_analysis_page()
    if not data:
        render_empty_state(controls)
        return

    render_data_status(data)
    render_channel_details_tab(
        data["df_items"],
        data["selected_channels"],
        data["df_channels"],
    )
