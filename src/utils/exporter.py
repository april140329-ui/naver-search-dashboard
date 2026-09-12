from __future__ import annotations
import io
import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """DataFrame을 UTF-8-SIG 인코딩의 CSV 바이너리로 변환합니다 (엑셀 한글 깨짐 방지)."""
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "SearchData") -> bytes:
    """DataFrame을 xlsx 바이너리로 변환합니다."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()
