from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from src.analysis.eda_engine import compute_channel_totals_df, compute_kpi_metrics
from src.api.datalab_client import DataLabApiClient
from src.api.mock_data import generate_mock_search_data, generate_mock_trend_data
from src.api.search_client import SearchApiClient


ITEM_COLUMNS = [
    "keyword",
    "channel_id",
    "channel_name",
    "rank",
    "title",
    "description",
    "link",
    "pub_date",
    "author_or_source",
    "extra",
]


def get_analysis_data() -> dict[str, Any] | None:
    return st.session_state.get("analysis_data")


def validate_controls(controls: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not controls.get("keywords"):
        errors.append("분석할 검색어를 최소 1개 입력해 주세요.")
    if len(controls.get("keywords", [])) > 5:
        errors.append("검색어는 데이터랩 비교 제한에 맞춰 최대 5개까지 입력할 수 있습니다.")
    if not controls.get("selected_channels"):
        errors.append("수집할 채널을 최소 1개 선택해 주세요.")
    if controls.get("start_date", "") > controls.get("end_date", ""):
        errors.append("시작일은 종료일보다 늦을 수 없습니다.")
    return errors


def execute_analysis(controls: dict[str, Any]) -> dict[str, Any] | None:
    """분석을 실행하고 페이지 간 공유할 세션 상태를 갱신합니다."""
    validation_errors = validate_controls(controls)
    if validation_errors:
        for message in validation_errors:
            st.error(message)
        return None

    keywords = controls["keywords"][:5]
    channels = controls["selected_channels"]
    use_mock = bool(controls.get("mock_mode") or not controls.get("has_api_keys"))
    errors: list[dict[str, str]] = []

    if use_mock:
        df_items, totals = generate_mock_search_data(
            keywords=keywords,
            channel_ids=channels,
            display_per_channel=controls["display_count"],
        )
        df_trend = generate_mock_trend_data(
            keywords=keywords,
            start_date=controls["start_date"],
            end_date=controls["end_date"],
            time_unit=controls["time_unit"],
        )
    else:
        try:
            search_client = SearchApiClient()
            df_items, totals = search_client.fetch_all(
                keywords=keywords,
                channel_ids=channels,
                display_per_channel=controls["display_count"],
                sort=controls["sort_order"],
            )
            errors.extend(search_client.errors)
        except Exception as exc:  # 전체 검색 요청 실패도 트렌드 결과와 분리해 보존
            df_items = pd.DataFrame(columns=ITEM_COLUMNS)
            totals = {keyword: {} for keyword in keywords}
            errors.append({"scope": "검색 채널", "message": str(exc)})

        try:
            df_trend = DataLabApiClient().fetch_search_trends(
                keywords=keywords,
                start_date=controls["start_date"],
                end_date=controls["end_date"],
                time_unit=controls["time_unit"],
            )
        except Exception as exc:  # 검색 API 성공 데이터는 그대로 유지
            df_trend = pd.DataFrame(columns=["period", "keyword", "ratio"])
            errors.append({"scope": "데이터랩", "message": str(exc)})

    df_channels = compute_channel_totals_df(totals)
    kpi_data = compute_kpi_metrics(df_items, totals, df_trend)
    data = {
        "df_items": df_items,
        "totals": totals,
        "df_trend": df_trend,
        "df_channels": df_channels,
        "kpi_data": kpi_data,
        "is_simulated": use_mock,
        "source_mode": "mock" if use_mock else "live",
        "keywords": keywords,
        "selected_channels": channels,
        "errors": errors,
        "collected_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        "query": {
            "start_date": controls["start_date"],
            "end_date": controls["end_date"],
            "time_unit": controls["time_unit"],
            "display_count": controls["display_count"],
            "sort_order": controls["sort_order"],
        },
    }
    st.session_state["analysis_data"] = data
    return data


def handle_analysis_request(controls: dict[str, Any]) -> dict[str, Any] | None:
    """명시적으로 실행 버튼을 눌렀을 때만 API 또는 Mock 분석을 수행합니다."""
    if controls.get("run_clicked"):
        with st.spinner("검색 채널과 데이터랩 데이터를 수집·분석하고 있습니다..."):
            return execute_analysis(controls)
    return get_analysis_data()
