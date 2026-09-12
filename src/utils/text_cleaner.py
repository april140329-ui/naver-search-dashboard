from __future__ import annotations
import html
import re
from urllib.parse import urlparse

# 네이버 API는 검색 일치 단어에 <b>, </b> 태그를 포함하여 반환함
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def clean_html_tags(text: str | None) -> str:
    """HTML 태그(<b>, </b> 등) 및 HTML 엔티티(&quot;, &amp; 등)를 깨끗한 텍스트로 변환합니다."""
    if not text:
        return ""
    # 1. HTML 엔티티 언이스케이프 (&quot; -> ", &amp; -> & 등)
    unescaped = html.unescape(text)
    # 2. 태그 제거
    cleaned = HTML_TAG_PATTERN.sub("", unescaped)
    # 3. 불필요한 연속 공백 축약
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_domain(url: str | None) -> str:
    """URL에서 언론사/출처 대용으로 쓸 수 있는 도메인(www. 제외)만 추출합니다."""
    if not url:
        return ""
    netloc = urlparse(url).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


def parse_naver_pubdate(pub_date_str: str | None) -> str:
    """네이버 API의 pubDate(예: 'Wed, 09 Sep 2026 18:30:00 +0900' 또는 '20260909')를 'YYYY-MM-DD HH:MM'으로 정규화합니다."""
    if not pub_date_str:
        return ""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        # 'YYYYMMDD' 형식 처리
        if len(pub_date_str) == 8 and pub_date_str.isdigit():
            return f"{pub_date_str[:4]}-{pub_date_str[4:6]}-{pub_date_str[6:]}"
        return pub_date_str
