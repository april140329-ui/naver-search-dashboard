from __future__ import annotations
from typing import Any
import requests
from src.config.settings import get_api_credentials


class NaverApiError(Exception):
    """네이버 API 호출 중 발생한 예외"""
    def __init__(self, message: str, status_code: int | None = None, error_code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class BaseApiClient:
    """네이버 API 공통 HTTP 요청 클라이언트"""

    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        creds = get_api_credentials()
        self.client_id = client_id or creds["client_id"]
        self.client_secret = client_secret or creds["client_secret"]
        self.is_hub = creds.get("is_hub", True)
        self.session = requests.Session()

    def get_headers(self) -> dict[str, str]:
        if not self.client_id or not self.client_secret:
            raise NaverApiError("네이버 API Client ID 및 Secret이 설정되지 않았습니다. .env 파일을 확인해 주세요.")

        if self.is_hub:
            return {
                "X-NCP-APIGW-API-KEY-ID": self.client_id,
                "X-NCP-APIGW-API-KEY": self.client_secret,
                "Content-Type": "application/json",
            }
        else:
            return {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
                "Content-Type": "application/json",
            }

    def get(self, url: str, params: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
        headers = self.get_headers()
        try:
            resp = self.session.get(url, headers=headers, params=params, timeout=timeout)
        except requests.RequestException as e:
            raise NaverApiError(f"네트워크 요청 실패: {e}")

        self._handle_response_error(resp)
        return resp.json()

    def post(self, url: str, json_data: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        headers = self.get_headers()
        try:
            resp = self.session.post(url, headers=headers, json=json_data, timeout=timeout)
        except requests.RequestException as e:
            raise NaverApiError(f"네트워크 요청 실패: {e}")

        self._handle_response_error(resp)
        return resp.json()

    def _handle_response_error(self, resp: requests.Response) -> None:
        if resp.status_code == 200:
            return

        status_code = resp.status_code
        err_msg = f"HTTP {status_code}"
        err_code = None

        try:
            data = resp.json()
            err_msg = data.get("errorMessage") or data.get("message") or resp.text
            err_code = data.get("errorCode") or data.get("code")
        except Exception:
            err_msg = resp.text

        if status_code == 401:
            friendly_msg = f"인증 실패(401): API Client ID/Secret이 올바르지 않습니다. ({err_msg})"
        elif status_code == 403:
            friendly_msg = f"접근 거부(403): 네이버 개발자 콘솔에서 해당 API 권한이 활성화되어 있는지 확인하세요. ({err_msg})"
        elif status_code == 429:
            friendly_msg = f"호출 한도 초과(429): 일일 검색 API 허용 쿼터가 초과되었습니다. ({err_msg})"
        elif status_code == 400:
            friendly_msg = f"잘못된 요청(400): 파라미터 규격을 확인하세요. ({err_msg})"
        else:
            friendly_msg = f"API 오류({status_code}): {err_msg}"

        raise NaverApiError(friendly_msg, status_code=status_code, error_code=err_code)
