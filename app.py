from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.config.settings import BASE_DIR
from src.pages.channels import render_channels_page
from src.pages.complaints import render_complaints_page
from src.pages.explorer import render_explorer_page
from src.pages.overview import render_overview_page
from src.pages.settings_page import render_settings_page
from src.pages.text_insights_page import render_text_insights_page
from src.pages.trends import render_trends_page


def load_custom_css() -> None:
    """공통 대시보드 스타일을 로드합니다."""
    css_path: Path = BASE_DIR / "assets" / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as css_file:
            st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="네이버 마켓 인사이트",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_custom_css()

    pages = [
        st.Page(render_overview_page, title="종합", icon="📊", url_path="overview", default=True),
        st.Page(render_trends_page, title="검색 트렌드", icon="📈", url_path="trends"),
        st.Page(render_channels_page, title="채널 분석", icon="🧭", url_path="channels"),
        st.Page(render_text_insights_page, title="텍스트", icon="🔠", url_path="text-insights"),
        st.Page(render_complaints_page, title="민원 분석", icon="🙋", url_path="complaints"),
        st.Page(render_explorer_page, title="데이터 탐색", icon="🔎", url_path="data-explorer"),
        st.Page(render_settings_page, title="설정", icon="⚙️", url_path="settings"),
    ]
    navigation = st.navigation(pages, position="top")
    navigation.run()


if __name__ == "__main__":
    main()
