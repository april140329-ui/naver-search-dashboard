from __future__ import annotations
from typing import Any
import pandas as pd
from src.api.base import BaseApiClient, NaverApiError
from src.config.settings import SEARCH_CHANNELS, ChannelConfig, get_channel_endpoint
from src.utils.text_cleaner import clean_html_tags, parse_naver_pubdate


class SearchApiClient(BaseApiClient):
    """네이버 8대 검색 채널(뉴스, 블로그, 웹문서, 이미지, 지식iN, 지역, 카페, 백과사전) 수집기"""

    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        super().__init__(client_id=client_id, client_secret=client_secret)
        self.errors: list[dict[str, str]] = []

    def fetch_channel(
        self,
        channel_id: str,
        keyword: str,
        display: int = 100,
        start: int = 1,
        sort: str | None = None,
    ) -> dict[str, Any]:
        """단일 채널 및 키워드에 대한 검색 결과를 조회합니다."""
        channel_cfg = SEARCH_CHANNELS.get(channel_id)
        if not channel_cfg:
            raise ValueError(f"지원하지 않는 검색 채널입니다: {channel_id}")

        params: dict[str, Any] = {
            "query": keyword,
            "display": min(display, 100),
            "start": start,
        }

        # 지역 검색은 display 최대 5
        if channel_id == "local":
            params["display"] = min(display, 5)

        if channel_cfg.supports_sort:
            params["sort"] = sort or channel_cfg.default_sort

        endpoint = get_channel_endpoint(channel_id, is_hub=self.is_hub)
        raw_data = self.get(endpoint, params=params)
        return raw_data

    def fetch_all(
        self,
        keywords: list[str],
        channel_ids: list[str],
        display_per_channel: int = 50,
        sort: str = "sim",
    ) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
        """
        다중 키워드 및 다중 채널에 대해 일괄 검색을 수행하고 정제된 DataFrame과 채널별 총 검색량(total)을 반환합니다.
        
        Returns:
            df: 모든 검색 결과가 정규화된 판다스 데이터프레임
            totals: {keyword: {channel_id: total_count}} 형태의 총 검색량 메타데이터
        """
        all_items: list[dict[str, Any]] = []
        totals: dict[str, dict[str, int]] = {}
        self.errors = []

        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            totals[kw] = {}

            for ch_id in channel_ids:
                cfg = SEARCH_CHANNELS.get(ch_id)
                if not cfg:
                    continue

                try:
                    res = self.fetch_channel(
                        channel_id=ch_id,
                        keyword=kw,
                        display=display_per_channel,
                        sort=cfg.default_sort if ch_id == "local" else (sort if cfg.supports_sort else None),
                    )
                    total_count = res.get("total", 0)
                    totals[kw][ch_id] = total_count

                    raw_items = res.get("items", [])
                    for idx, item in enumerate(raw_items, start=1):
                        normalized = self._normalize_item(item, ch_id, cfg.name, kw, idx)
                        all_items.append(normalized)

                except NaverApiError as e:
                    totals[kw][ch_id] = 0
                    # 오류를 분석용 검색 결과 행에 섞지 않고 별도 상태로 보관합니다.
                    self.errors.append({
                        "scope": f"{kw} · {cfg.name}",
                        "message": str(e),
                    })

        columns = [
            "keyword", "channel_id", "channel_name", "rank", "title",
            "description", "link", "pub_date", "author_or_source", "extra",
        ]
        df = pd.DataFrame(all_items, columns=columns)
        return df, totals

    def _normalize_item(
        self, item: dict[str, Any], channel_id: str, channel_name: str, keyword: str, rank: int
    ) -> dict[str, Any]:
        """네이버 채널별 서로 다른 필드명을 통일된 포맷으로 정규화합니다."""
        title = clean_html_tags(item.get("title", ""))
        description = clean_html_tags(
            item.get("description") or item.get("address") or item.get("roadAddress") or ""
        )
        link = item.get("link") or item.get("originallink") or ""
        pub_date = parse_naver_pubdate(item.get("pubDate") or item.get("postdate"))

        # 채널별 특정 작성자/출처 필드
        author = ""
        if channel_id == "blog":
            author = item.get("bloggername", "")
        elif channel_id == "cafearticle":
            author = item.get("cafename", "")
        elif channel_id == "local":
            author = item.get("category", "")
        elif channel_id == "news":
            author = item.get("originallink", "")

        extra: dict[str, Any] = {}
        if channel_id == "image":
            extra["thumbnail"] = item.get("thumbnail", "")
            extra["sizeheight"] = item.get("sizeheight", "")
            extra["sizewidth"] = item.get("sizewidth", "")
        elif channel_id == "local":
            extra["telephone"] = item.get("telephone", "")
            extra["address"] = item.get("address", "")
            extra["roadAddress"] = item.get("roadAddress", "")

        return {
            "keyword": keyword,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "rank": rank,
            "title": title,
            "description": description,
            "link": link,
            "pub_date": pub_date,
            "author_or_source": author,
            "extra": extra,
        }
