"""Streamlit AppTest용 개별 페이지 스모크 진입점."""
from __future__ import annotations

import os

from src.pages.channels import render_channels_page
from src.pages.complaints import render_complaints_page
from src.pages.explorer import render_explorer_page
from src.pages.overview import render_overview_page
from src.pages.settings_page import render_settings_page
from src.pages.text_insights_page import render_text_insights_page
from src.pages.trends import render_trends_page


PAGES = {
    "overview": render_overview_page,
    "trends": render_trends_page,
    "channels": render_channels_page,
    "text": render_text_insights_page,
    "complaints": render_complaints_page,
    "explorer": render_explorer_page,
    "settings": render_settings_page,
}

PAGES[os.getenv("DASHBOARD_TEST_PAGE", "overview")]()
