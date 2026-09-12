from __future__ import annotations

import streamlit as st

from src.api.search_client import SearchApiClient
from src.components.page_shell import render_page_header
from src.config.settings import get_api_credentials, get_app_version, save_api_credentials_to_env


def render_settings_page() -> None:
    render_page_header(
        "설정 및 데이터 상태",
        "API 연결 방식과 수집 제한을 확인하고 인증 정보를 안전하게 갱신합니다.",
        eyebrow="SETTINGS & HEALTH",
    )
    credentials = get_api_credentials()

    status1, status2, status3, status4 = st.columns(4)
    status1.metric("API 상태", "등록됨" if credentials["is_configured"] else "미등록")
    connection_type = "미설정"
    if credentials["is_configured"]:
        connection_type = "API HUB" if credentials["is_hub"] else "Developers"
    status2.metric("연결 유형", connection_type)
    status3.metric("현재 분석", "있음" if st.session_state.get("analysis_data") else "없음")
    status4.metric("배포 버전", f"v{get_app_version()}", help="pyproject.toml의 version 필드 기준입니다.")

    left, right = st.columns([3, 2])
    with left:
        st.markdown("### API 인증 정보")
        st.caption("입력값은 이 컴퓨터의 `.env`에 저장됩니다. 공유 서버에서는 서버 환경변수 또는 Streamlit Secrets를 사용하세요.")
        with st.form("credentials_form", clear_on_submit=True):
            client_id = st.text_input("Client ID", type="password", autocomplete="off")
            client_secret = st.text_input("Client Secret", type="password", autocomplete="off")
            save_clicked = st.form_submit_button("인증 정보 저장", type="primary", width="stretch")
        if save_clicked:
            try:
                save_api_credentials_to_env(client_id, client_secret)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state["analysis_data"] = None
                st.success("인증 정보를 저장했습니다. 왼쪽 분석 패널에서 LIVE 모드를 선택해 실행하세요.")
                st.rerun()

        if credentials["is_configured"] and st.button("연결 테스트", width="stretch"):
            try:
                result = SearchApiClient().fetch_channel("news", "네이버", display=1)
                st.success(f"검색 API 연결에 성공했습니다. 응답 추정 결과: {result.get('total', 0):,}건")
            except Exception as exc:
                st.error(f"연결 실패: {exc}")

    with right:
        st.markdown("### 수집 기준")
        st.dataframe(
            {
                "항목": ["검색어", "일반 채널 표본", "지역 채널 표본", "트렌드 지수", "실패 처리"],
                "기준": [
                    "최대 5개",
                    "채널·검색어별 최대 100건",
                    "채널·검색어별 최대 5건",
                    "절대 검색량이 아닌 0~100 상대값",
                    "성공 데이터 유지, 오류 채널만 제외",
                ],
            },
            hide_index=True,
            width="stretch",
        )
        st.info("API의 `total`은 실제로 내려받은 행 수가 아니라 검색 결과 추정량입니다. 종합 화면에서 수집 표본과 분리해 표시합니다.")
