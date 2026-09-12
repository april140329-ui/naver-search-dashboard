from __future__ import annotations
from typing import Any
import pandas as pd
from src.api.base import BaseApiClient, NaverApiError
from src.config.settings import get_datalab_endpoint


class DataLabApiClient(BaseApiClient):
    """네이버 데이터랩(DataLab) 통합 검색어 트렌드 API 수집기"""

    def fetch_search_trends(
        self,
        keywords: list[str],
        start_date: str,
        end_date: str,
        time_unit: str = "date",  # date, week, month
        device: str | None = None,  # pc, mo, or None
        gender: str | None = None,  # m, f, or None
    ) -> pd.DataFrame:
        """
        다중 검색어에 대한 상대적 검색 비율(0~100) 트렌드 시계열 데이터를 수집합니다.
        
        Args:
            keywords: 검색어 리스트 (최대 5개 그룹)
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            time_unit: 'date' | 'week' | 'month'
            device: 'pc' | 'mo' | None
            gender: 'm' | 'f' | None
        """
        # 최대 5개 키워드 그룹 지원 (네이버 데이터랩 제약조건)
        selected_keywords = [kw.strip() for kw in keywords if kw.strip()][:5]
        if not selected_keywords:
            return pd.DataFrame()

        keyword_groups = [
            {"groupName": kw, "keywords": [kw]} for kw in selected_keywords
        ]

        payload: dict[str, Any] = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": keyword_groups,
        }

        if device in ("pc", "mo"):
            payload["device"] = device
        if gender in ("m", "f"):
            payload["gender"] = gender

        try:
            endpoint = get_datalab_endpoint(is_hub=self.is_hub)
            resp = self.post(endpoint, json_data=payload)
        except NaverApiError as e:
            raise e

        # 응답 데이터 정규화
        results = resp.get("results", [])
        records: list[dict[str, Any]] = []

        for group in results:
            group_name = group.get("title", "")
            data_points = group.get("data", [])
            for point in data_points:
                records.append({
                    "period": point.get("period"),
                    "keyword": group_name,
                    "ratio": float(point.get("ratio", 0.0)),
                })

        if not records:
            return pd.DataFrame(columns=["period", "keyword", "ratio"])

        df = pd.DataFrame(records)
        df["period"] = pd.to_datetime(df["period"])
        return df.sort_values(by=["period", "keyword"]).reset_index(drop=True)
