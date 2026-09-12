from __future__ import annotations

import html
from typing import Any

import streamlit as st

from src.components.sidebar import render_sidebar
from src.services.analysis_service import execute_analysis, handle_analysis_request


def render_page_header(title: str, description: str, eyebrow: str = "NAVER MARKET INSIGHT") -> None:
    st.markdown(
        f"""
        <div class="page-header">
            <span class="page-eyebrow">{html.escape(eyebrow)}</span>
            <h1>{html.escape(title)}</h1>
            <p>{html.escape(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def prepare_analysis_page() -> tuple[dict[str, Any], dict[str, Any] | None]:
    controls = render_sidebar()
    data = handle_analysis_request(controls)
    return controls, data


def render_data_status(data: dict[str, Any]) -> None:
    keywords = ", ".join(data.get("keywords", []))
    query = data.get("query", {})
    mode = "DEMO" if data.get("is_simulated") else "LIVE"
    status_class = "status-demo" if data.get("is_simulated") else "status-live"
    st.markdown(
        f"""
        <div class="scope-bar">
            <div><span class="status-pill {status_class}">{mode}</span><strong>{html.escape(keywords)}</strong></div>
            <div>{html.escape(query.get('start_date', '-'))} ~ {html.escape(query.get('end_date', '-'))}</div>
            <div>{len(data.get('selected_channels', []))}개 채널 · {html.escape(data.get('collected_at', '-'))} 수집</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    errors = data.get("errors", [])
    if errors:
        st.warning(f"일부 데이터 수집에 실패했습니다. 성공한 데이터만 표시합니다. ({len(errors)}건)")
        with st.expander("수집 오류 확인"):
            for error in errors:
                st.write(f"- **{error.get('scope', 'API')}**: {error.get('message', '')}")
    elif data.get("is_simulated"):
        st.info("현재 화면은 모의 데이터입니다. 실제 분석은 설정 페이지에서 API 키를 등록한 뒤 LIVE 모드로 실행하세요.")


def render_empty_state(controls: dict[str, Any], allow_demo: bool = True) -> None:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-icon">↗</div>
            <h3>분석 조건을 정하고 첫 리포트를 만들어 보세요</h3>
            <p>왼쪽 패널에서 최대 5개 검색어와 채널을 선택한 뒤 <b>분석 실행</b>을 누르면 결과가 모든 페이지에 유지됩니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if allow_demo:
        col_demo, _ = st.columns([1, 3])
        with col_demo:
            if st.button("데모 데이터 바로 보기", type="primary", width="stretch"):
                demo_controls = {**controls, "mock_mode": True, "run_clicked": True}
                with st.spinner("데모 리포트를 준비하고 있습니다..."):
                    execute_analysis(demo_controls)
                st.rerun()
