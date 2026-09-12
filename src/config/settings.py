from __future__ import annotations
import os
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from dotenv import set_key

# .env 파일 로드 (루트 디렉토리 기준)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


def get_app_version() -> str:
    """pyproject.toml에 기입된 배포 버전을 조회합니다 (배포 시 버전 확인용 단일 소스)."""
    try:
        return version("naver-search-dashboard")
    except PackageNotFoundError:
        return "dev"


@dataclass
class ChannelConfig:
    id: str
    name: str
    icon: str
    hub_path: str
    dev_path: str
    supports_sort: bool = True
    default_sort: str = "sim"  # sim(유사도순), date(날짜순)


# 네이버 8대 검색 채널 명세
SEARCH_CHANNELS: dict[str, ChannelConfig] = {
    "news": ChannelConfig(
        id="news",
        name="뉴스",
        icon="📰",
        hub_path="/search/v1/news",
        dev_path="/v1/search/news.json",
        supports_sort=True,
    ),
    "blog": ChannelConfig(
        id="blog",
        name="블로그",
        icon="📝",
        hub_path="/search/v1/blog",
        dev_path="/v1/search/blog.json",
        supports_sort=True,
    ),
    "webkr": ChannelConfig(
        id="webkr",
        name="웹문서",
        icon="🌐",
        hub_path="/search/v1/webkr",
        dev_path="/v1/search/webkr.json",
        supports_sort=False,
    ),
    "image": ChannelConfig(
        id="image",
        name="이미지",
        icon="🖼️",
        hub_path="/search/v1/image",
        dev_path="/v1/search/image",
        supports_sort=True,
    ),
    "kin": ChannelConfig(
        id="kin",
        name="지식iN",
        icon="💡",
        hub_path="/search/v1/kin",
        dev_path="/v1/search/kin.json",
        supports_sort=True,
    ),
    "local": ChannelConfig(
        id="local",
        name="지역",
        icon="📍",
        hub_path="/search/v1/local",
        dev_path="/v1/search/local.json",
        supports_sort=True,
        default_sort="random",
    ),
    "cafearticle": ChannelConfig(
        id="cafearticle",
        name="카페글",
        icon="☕",
        hub_path="/search/v1/cafearticle",
        dev_path="/v1/search/cafearticle.json",
        supports_sort=True,
    ),
    "encyc": ChannelConfig(
        id="encyc",
        name="백과사전",
        icon="📚",
        hub_path="/search/v1/encyc",
        dev_path="/v1/search/encyc.json",
        supports_sort=False,
    ),
}

# 엔드포인트 도메인
NAVER_HUB_BASE_URL = "https://naverapihub.apigw.ntruss.com"
NAVER_DEV_BASE_URL = "https://openapi.naver.com"


def get_api_credentials() -> dict[str, Any]:
    """환경변수에서 네이버 API 인증키를 조회하고 플랫폼 유형을 판별합니다."""
    load_dotenv(dotenv_path=ENV_FILE, override=True)

    client_id = os.getenv("NAVER_CLIENT_ID", "").strip() or None
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip() or None

    ncp_id = os.getenv("NCP_APIGW_API_KEY_ID", "").strip() or None
    ncp_secret = os.getenv("NCP_APIGW_API_KEY", "").strip() or None

    final_id = client_id or ncp_id
    final_secret = client_secret or ncp_secret
    is_configured = bool(final_id and final_secret)

    # NAVER API HUB(네이버 클라우드 플랫폼) 여부 판별:
    # 1) ncp_id/secret 설정 시
    # 2) Client Secret 길이가 40자이거나 Client ID 길이가 10자 이하인 경우 (NCP API Gateway Key 규격)
    is_hub = False
    if is_configured:
        if ncp_id and ncp_secret:
            is_hub = True
        elif len(final_secret or "") >= 35 or len(final_id or "") <= 15:
            is_hub = True

    return {
        "client_id": final_id,
        "client_secret": final_secret,
        "is_configured": is_configured,
        "is_hub": is_hub,
    }


def get_channel_endpoint(channel_id: str, is_hub: bool = True) -> str:
    """채널 ID와 인증 유형에 맞는 전체 엔드포인트 URL을 반환합니다."""
    cfg = SEARCH_CHANNELS.get(channel_id)
    if not cfg:
        raise ValueError(f"알 수 없는 채널입니다: {channel_id}")
    if is_hub:
        return f"{NAVER_HUB_BASE_URL}{cfg.hub_path}"
    else:
        return f"{NAVER_DEV_BASE_URL}{cfg.dev_path}"


def get_datalab_endpoint(is_hub: bool = True) -> str:
    """데이터랩 검색어 트렌드 API 엔드포인트 URL을 반환합니다."""
    if is_hub:
        return f"{NAVER_HUB_BASE_URL}/search-trend/v1/search"
    else:
        return f"{NAVER_DEV_BASE_URL}/v1/datalab/search"


def save_api_credentials_to_env(client_id: str, client_secret: str) -> None:
    """사용자가 UI에서 입력한 API 키를 .env 파일에 저장하고 현재 프로세스 환경에 반영합니다."""
    clean_id = client_id.strip()
    clean_secret = client_secret.strip()
    if not clean_id or not clean_secret:
        raise ValueError("Client ID와 Client Secret을 모두 입력해 주세요.")
    if any(char in clean_id + clean_secret for char in ("\r", "\n")):
        raise ValueError("인증 정보에는 줄바꿈 문자를 사용할 수 없습니다.")

    ENV_FILE.touch(exist_ok=True)
    set_key(str(ENV_FILE), "NAVER_CLIENT_ID", clean_id, quote_mode="never")
    set_key(str(ENV_FILE), "NAVER_CLIENT_SECRET", clean_secret, quote_mode="never")
    os.environ["NAVER_CLIENT_ID"] = clean_id
    os.environ["NAVER_CLIENT_SECRET"] = clean_secret
