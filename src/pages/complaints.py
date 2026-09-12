from __future__ import annotations

from src.components.complaint_view import render_complaint_section
from src.components.page_shell import render_page_header
from src.components.sidebar import render_sidebar


def render_complaints_page() -> None:
    render_page_header(
        "민원 요구·감정 분석",
        "민원 본문에 문제·요구·감정·감정대상 라벨 초안을 붙여 이슈 구간과 평시의 차이를 비교합니다.",
        eyebrow="COMPLAINT INSIGHT",
    )
    # 이 화면은 업로드한 민원 표본만 사용하므로 검색 분석 실행 여부와 무관하게 동작합니다.
    render_sidebar()
    render_complaint_section()
