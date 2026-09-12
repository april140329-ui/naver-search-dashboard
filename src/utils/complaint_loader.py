"""민원 표본 CSV를 읽어 분석용 스키마로 정규화합니다.

원본 민원 파일에는 개인정보와 민감한 피해 사례가 남아 있을 수 있으므로 레포지토리에
저장하지 않고 실행 시 업로드해 세션 안에서만 사용합니다.
"""
from __future__ import annotations

import io
import re

import pandas as pd

# 업로드 파일에서 찾아볼 컬럼 이름 후보 (표준 이름: 후보들)
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "구간원본": ("구간", "phase", "segment"),
    "사건번호": ("사건번호", "source_id", "접수번호"),
    "접수일자": ("접수일자", "date", "접수일"),
    "품목명": ("품목명", "item", "item_name", "품목"),
    "제목": ("사건제목", "제목", "title"),
    "본문": ("사건내용", "본문", "내용", "content"),
    "기록형태": ("기록형태", "record_style"),
    "처리결과": ("처리결과", "result"),
    "처리결과_3그룹": ("처리결과_3그룹", "result_group"),
}

ISSUE_PHASE = "이슈구간"
BASELINE_PHASE = "평시"


def _resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """업로드 파일의 실제 컬럼명을 표준 이름에 연결합니다."""
    lowered = {str(col).strip().lower(): col for col in df.columns}
    resolved: dict[str, str] = {}
    for standard, candidates in COLUMN_ALIASES.items():
        for candidate in candidates:
            actual = lowered.get(candidate.lower())
            if actual is not None:
                resolved[standard] = actual
                break
    return resolved


def parse_segment(raw_segment: str) -> tuple[str, str, str]:
    """'침대_이슈구간(라돈)' 형태의 구간 값을 품목·구간·사건명으로 나눕니다."""
    text = str(raw_segment or "").strip()
    if not text:
        return ("미상", "미상", "")

    item, _, rest = text.partition("_")
    event_match = re.search(r"\((.*?)\)", rest)
    event = event_match.group(1) if event_match else ""
    phase = ISSUE_PHASE if "이슈" in rest else (BASELINE_PHASE if "평시" in rest else rest.strip() or "미상")
    return (item.strip() or "미상", phase, event)


def load_complaint_csv(uploaded_bytes: bytes) -> tuple[pd.DataFrame, list[str]]:
    """민원 CSV 바이트를 읽어 표준 스키마 DataFrame과 경고 목록을 돌려줍니다.

    공공데이터 특성상 utf-8-sig / cp949 인코딩이 섞여 있어 순서대로 시도합니다.
    """
    warnings: list[str] = []
    raw_df = None
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            raw_df = pd.read_csv(io.BytesIO(uploaded_bytes), encoding=encoding)
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    if raw_df is None:
        raise ValueError("CSV를 읽지 못했습니다. utf-8-sig 또는 cp949로 저장된 파일인지 확인해 주세요.")

    resolved = _resolve_columns(raw_df)
    if "본문" not in resolved:
        raise ValueError(
            "본문 컬럼을 찾지 못했습니다. '사건내용' 또는 '본문' 컬럼이 있는 파일인지 확인해 주세요."
        )

    df = pd.DataFrame()
    for standard, actual in resolved.items():
        df[standard] = raw_df[actual]

    df["본문"] = df["본문"].fillna("").astype(str).str.strip()
    if "제목" in df.columns:
        df["제목"] = df["제목"].fillna("").astype(str).str.strip()
    else:
        df["제목"] = ""
        warnings.append("제목 컬럼이 없어 빈 값으로 채웠습니다.")

    if "구간원본" in df.columns:
        parsed = df["구간원본"].apply(parse_segment)
        df["품목"] = [item for item, _, _ in parsed]
        df["구간"] = [phase for _, phase, _ in parsed]
        df["사건명"] = [event for _, _, event in parsed]
    else:
        df["품목"] = df.get("품목명", "미상")
        df["구간"] = "미상"
        df["사건명"] = ""
        warnings.append("구간 컬럼이 없어 이슈/평시 비교를 할 수 없습니다.")

    if "접수일자" in df.columns:
        df["접수일자"] = pd.to_datetime(df["접수일자"], errors="coerce")
        unparsed = int(df["접수일자"].isna().sum())
        if unparsed:
            warnings.append(f"접수일자를 해석하지 못한 행이 {unparsed}건 있습니다.")

    empty_body = int((df["본문"].str.len() == 0).sum())
    if empty_body:
        warnings.append(
            f"본문이 비어 있는 행이 {empty_body}건 있습니다. 감정 없음이 아니라 '판단 불가'로 처리합니다."
        )

    df["본문길이"] = df["본문"].str.len()
    return df, warnings
