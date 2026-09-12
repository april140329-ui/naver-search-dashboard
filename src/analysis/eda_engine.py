from __future__ import annotations
import re
from collections import Counter
from typing import Any
import pandas as pd
from src.config.settings import SEARCH_CHANNELS

# 한국어 텍스트 분석 불용어
KOREAN_STOPWORDS = {
    "있다", "하다", "되다", "이다", "같다", "대해", "위해", "통해", "관련",
    "대한", "통한", "이", "그", "저", "것", "수", "등", "및", "더", "때",
    "내", "중", "제", "개", "점", "전", "후", "이번", "지난", "모든",
    "그리고", "하지만", "그러나", "또한", "또는", "경우", "모두", "어떤",
    "네이버", "검색", "결과", "정보", "확인", "보기", "바로가기", "더보기",
}

DAYS_OF_WEEK = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def compute_channel_totals_df(totals: dict[str, dict[str, int]]) -> pd.DataFrame:
    """총 검색 결과수 딕셔너리를 시각화 및 분석용 정규화 DataFrame으로 변환합니다."""
    rows = []
    for kw, ch_map in totals.items():
        kw_sum = sum(ch_map.values())
        for ch_id, count in ch_map.items():
            cfg = SEARCH_CHANNELS.get(ch_id)
            ch_name = cfg.name if cfg else ch_id
            share = (count / kw_sum * 100) if kw_sum > 0 else 0.0
            rows.append({
                "keyword": kw,
                "channel_id": ch_id,
                "channel_name": ch_name,
                "total_count": count,
                "share_pct": round(share, 2),
            })
    return pd.DataFrame(rows)


def compute_kpi_metrics(
    df_items: pd.DataFrame, totals: dict[str, dict[str, int]], df_trend: pd.DataFrame
) -> dict[str, Any]:
    """대시보드 상단 핵심 KPI 요약 지표를 산출합니다."""
    estimated_total = sum(
        sum(ch_map.values()) for ch_map in totals.values()
    ) if totals else len(df_items)

    kw_totals = {kw: sum(ch_map.values()) for kw, ch_map in totals.items()} if totals else {}
    top_keyword = max(kw_totals, key=kw_totals.get) if kw_totals else "N/A"
    top_keyword_count = kw_totals.get(top_keyword, 0)

    ch_aggregate: dict[str, int] = {}
    for ch_map in totals.values():
        for ch_id, count in ch_map.items():
            ch_aggregate[ch_id] = ch_aggregate.get(ch_id, 0) + count

    top_ch_id = max(ch_aggregate, key=ch_aggregate.get) if ch_aggregate else "N/A"
    top_ch_cfg = SEARCH_CHANNELS.get(top_ch_id)
    top_channel_name = top_ch_cfg.name if top_ch_cfg else top_ch_id

    trend_leader = "N/A"
    trend_leader_avg = 0.0
    peak_info = {"keyword": "N/A", "date": "N/A", "ratio": 0.0}

    if not df_trend.empty and "ratio" in df_trend.columns:
        avg_series = df_trend.groupby("keyword")["ratio"].mean()
        if not avg_series.empty:
            trend_leader = avg_series.idxmax()
            trend_leader_avg = round(float(avg_series.max()), 1)

        max_row = df_trend.loc[df_trend["ratio"].idxmax()]
        peak_info = {
            "keyword": str(max_row["keyword"]),
            "date": pd.to_datetime(max_row["period"]).strftime("%Y-%m-%d"),
            "ratio": round(float(max_row["ratio"]), 1),
        }

    return {
        # grand_total은 이전 코드와의 호환을 위해 유지하되 UI에서는 추정량으로 명시합니다.
        "grand_total": estimated_total,
        "estimated_total": estimated_total,
        "top_keyword": top_keyword,
        "top_keyword_count": top_keyword_count,
        "top_channel_name": top_channel_name,
        "trend_leader": trend_leader,
        "trend_leader_avg": trend_leader_avg,
        "peak_info": peak_info,
        "collected_items_count": len(df_items),
    }


def compute_trend_summary_stats(df_trend: pd.DataFrame) -> pd.DataFrame:
    """트렌드 시계열의 기술통계량(평균, 최대, 최소, 표준편차)을 계산합니다."""
    if df_trend.empty or "ratio" not in df_trend.columns:
        return pd.DataFrame()

    stats = (
        df_trend.groupby("keyword")["ratio"]
        .agg(
            평균검색지수="mean",
            최대피크지수="max",
            최소지수="min",
            변동성_표준편차="std",
        )
        .round(2)
        .reset_index()
    )
    return stats


def compute_trend_pivot(df_trend: pd.DataFrame) -> pd.DataFrame:
    """트렌드 데이터를 날짜 기준 키워드 피벗 테이블로 변환합니다."""
    if df_trend.empty:
        return pd.DataFrame()
    # 결측 시점을 0으로 간주하면 인위적인 음의 상관이 생길 수 있어 결측값을 유지합니다.
    pivot_df = df_trend.pivot(index="period", columns="keyword", values="ratio")
    return pivot_df


# =============================================================================
# 채널별 심층 EDA 통계 함수 (기술통계, 교차표, 피벗테이블, 텍스트 분석)
# =============================================================================

def enrich_channel_df(df: pd.DataFrame) -> pd.DataFrame:
    """문서 텍스트 길이, 날짜, 요일, 시간대 등의 파생 변수를 추가하여 EDA를 준비합니다."""
    if df.empty:
        return df

    res = df.copy()
    res["제목글자수"] = res["title"].astype(str).str.len()
    res["본문글자수"] = res["description"].astype(str).str.len()
    res["총글자수"] = res["제목글자수"] + res["본문글자수"]

    # 날짜 파싱
    parsed_dt = pd.to_datetime(res["pub_date"], errors="coerce")
    res["발행일시"] = parsed_dt
    res["발행일자"] = parsed_dt.dt.strftime("%Y-%m-%d")
    res["발행시각"] = parsed_dt.dt.hour

    # 요일 매핑 (0: 월요일 ~ 6: 일요일)
    dow_map = {0: "월요일", 1: "화요일", 2: "수요일", 3: "목요일", 4: "금요일", 5: "토요일", 6: "일요일"}
    res["발행요일"] = parsed_dt.dt.dayofweek.map(dow_map).fillna("미상")

    # 작성자/출처 보정
    if "author_or_source" not in res.columns:
        res["author_or_source"] = ""
    res["작성출처"] = res["author_or_source"].replace("", "기타/미상").fillna("기타/미상")

    return res


def compute_channel_descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    """[통계표 1] 제목 글자수 및 본문 글자수에 대한 키워드별 기술통계량 산출"""
    if df.empty or "제목글자수" not in df.columns:
        return pd.DataFrame()

    stats_list = []
    for kw in df["keyword"].unique():
        sub = df[df["keyword"] == kw]
        t_len = sub["제목글자수"]
        d_len = sub["본문글자수"]

        stats_list.append({
            "키워드": kw,
            "수집건수": len(sub),
            "제목_평균": round(t_len.mean(), 1),
            "제목_표준편차": round(t_len.std(), 1) if len(t_len) > 1 else 0.0,
            "제목_중앙값": round(t_len.median(), 1),
            "제목_최소/최대": f"{t_len.min()} ~ {t_len.max()}",
            "본문_평균": round(d_len.mean(), 1),
            "본문_표준편차": round(d_len.std(), 1) if len(d_len) > 1 else 0.0,
            "본문_중앙값": round(d_len.median(), 1),
            "본문_최소/최대": f"{d_len.min()} ~ {d_len.max()}",
        })

    # 전체 합계 행 추가
    t_all = df["제목글자수"]
    d_all = df["본문글자수"]
    stats_list.append({
        "키워드": "[전체 집계]",
        "수집건수": len(df),
        "제목_평균": round(t_all.mean(), 1),
        "제목_표준편차": round(t_all.std(), 1) if len(t_all) > 1 else 0.0,
        "제목_중앙값": round(t_all.median(), 1),
        "제목_최소/최대": f"{t_all.min()} ~ {t_all.max()}",
        "본문_평균": round(d_all.mean(), 1),
        "본문_표준편차": round(d_all.std(), 1) if len(d_all) > 1 else 0.0,
        "본문_중앙값": round(d_all.median(), 1),
        "본문_최소/최대": f"{d_all.min()} ~ {d_all.max()}",
    })

    return pd.DataFrame(stats_list)


def compute_channel_crosstab_source(df: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    """[통계표 2] 키워드 x 주요 출처(언론사/블로거/카페명) 교차표 (Crosstab)"""
    if df.empty or "작성출처" not in df.columns:
        return pd.DataFrame()

    # 상위 N개 출처 선정
    top_sources = (
        df[df["작성출처"] != "기타/미상"]["작성출처"]
        .value_counts()
        .head(top_n)
        .index.tolist()
    )
    if not top_sources:
        top_sources = df["작성출처"].value_counts().head(top_n).index.tolist()

    sub_df = df[df["작성출처"].isin(top_sources)]
    if sub_df.empty:
        return pd.DataFrame()

    ct = pd.crosstab(sub_df["작성출처"], sub_df["keyword"], margins=True, margins_name="합계")
    ct = ct.sort_values(by="합계", ascending=False)
    return ct


def compute_channel_crosstab_dow(df: pd.DataFrame) -> pd.DataFrame:
    """[통계표 3] 키워드 x 요일(월~일) 교차표 (Crosstab)"""
    if df.empty or "발행요일" not in df.columns:
        return pd.DataFrame()

    ct = pd.crosstab(df["keyword"], df["발행요일"], margins=True, margins_name="합계")
    # 요일 순서 정렬
    order = [d for d in DAYS_OF_WEEK if d in ct.columns]
    if "합계" in ct.columns:
        order.append("합계")
    if "미상" in ct.columns:
        order.insert(len(order) - 1, "미상")

    return ct.reindex(columns=order, fill_value=0)


def compute_channel_pivot_table(df: pd.DataFrame) -> pd.DataFrame:
    """[통계표 4] 키워드별 다차원 통계 집계 피벗테이블 (Pivot Table)"""
    if df.empty or "제목글자수" not in df.columns:
        return pd.DataFrame()

    # aggregate functions by keyword
    piv = (
        df.groupby("keyword")
        .agg(
            수집문서수=("title", "count"),
            제목_평균글자수=("제목글자수", "mean"),
            본문_평균글자수=("본문글자수", "mean"),
            총글자수_합계=("총글자수", "sum"),
            최근발행일=("발행일자", "max"),
            최초발행일=("발행일자", "min"),
        )
        .round(1)
        .reset_index()
    )
    return piv


def compute_channel_word_freq_table(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """[통계표 5] 상위 20개 연관어 빈도 및 누적 비중 순위표"""
    if df.empty:
        return pd.DataFrame()

    full_txt = " ".join(df["title"].dropna().tolist() * 2 + df["description"].dropna().tolist())
    tokens = re.findall(r"[가-힣a-zA-Z0-9]{2,}", full_txt)
    words = [t.lower() for t in tokens if t.lower() not in KOREAN_STOPWORDS and not t.isdigit()]

    if not words:
        return pd.DataFrame()

    total_tokens = len(words)
    counter = Counter(words)
    most = counter.most_common(top_n)

    records = []
    cum_pct = 0.0
    for rank, (word, cnt) in enumerate(most, start=1):
        pct = (cnt / total_tokens) * 100
        cum_pct += pct
        records.append({
            "순위": rank,
            "단어": word,
            "출현빈도": cnt,
            "단어비중(%)": round(pct, 2),
            "누적비중(%)": round(cum_pct, 2),
        })

    return pd.DataFrame(records).set_index("순위")
