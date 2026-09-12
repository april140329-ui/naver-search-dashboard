from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.complaint_tagging import (
    NO_EXPLICIT_EMOTION,
    UNDETERMINED,
    explode_tag_counts,
    tag_dataframe,
)
from src.utils.complaint_loader import BASELINE_PHASE, ISSUE_PHASE, load_complaint_csv
from src.utils.exporter import dataframe_to_csv_bytes

PHASE_ORDER = [ISSUE_PHASE, BASELINE_PHASE]
PHASE_COLORS = {ISSUE_PHASE: "#e5484d", BASELINE_PHASE: "#7c8797"}
EMOTION_COLORS = {
    "불안": "#f5a524",
    "분노": "#e5484d",
    "실망": "#8b5cf6",
    "혼란·답답": "#0ea5e9",
    NO_EXPLICIT_EMOTION: "#cbd5e1",
    UNDETERMINED: "#94a3b8",
}


def _render_upload_panel() -> pd.DataFrame | None:
    """민원 표본 CSV를 세션 안에서만 사용하도록 업로드받습니다."""
    st.warning(
        "민원 원문에는 개인정보와 민감한 피해 사례가 남아 있을 수 있습니다. "
        "업로드한 파일은 이 세션에서만 사용하며 서버나 저장소에 남기지 않습니다. "
        "공개 자료로 내보낼 때는 비식별 처리한 사례만 사용하세요.",
        icon="🔒",
    )
    uploaded = st.file_uploader(
        "민원 표본 CSV 업로드",
        type=["csv"],
        help="사건내용(본문)과 구간 컬럼이 있는 파일이면 됩니다. utf-8-sig 또는 cp949 인코딩을 지원합니다.",
    )
    if uploaded is None:
        st.info(
            "분석하려면 민원 표본 CSV를 올려주세요. "
            "`구간`, `사건내용`, `사건제목`, `접수일자`, `품목명` 컬럼을 인식합니다.",
            icon="⬆️",
        )
        return None

    try:
        df, warnings = load_complaint_csv(uploaded.getvalue())
    except ValueError as exc:
        st.error(str(exc))
        return None

    for warning in warnings:
        st.caption(f"⚠️ {warning}")
    return df


def _render_sample_composition(df: pd.DataFrame) -> None:
    st.subheader("표본 구성")
    st.caption(
        "구간별 문서 수와 분모를 먼저 확인합니다. 층화표본이라면 이 비율을 전체 민원의 비율로 "
        "발표하지 않습니다."
    )

    composition = (
        df.groupby(["품목", "구간"]).size().reset_index(name="문서수").sort_values(["품목", "구간"])
    )
    cols = st.columns([2, 3], gap="large")
    with cols[0]:
        st.dataframe(composition, hide_index=True, width="stretch")
        undetermined = int(df["본문"].str.len().eq(0).sum())
        st.metric("본문 없음(판단 불가)", f"{undetermined:,}건")
    with cols[1]:
        chart = px.bar(
            composition,
            x="품목",
            y="문서수",
            color="구간",
            barmode="group",
            category_orders={"구간": PHASE_ORDER},
            color_discrete_map=PHASE_COLORS,
            template="plotly_white",
        )
        chart.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(chart, width="stretch")


def _render_need_comparison(tagged: pd.DataFrame) -> None:
    """H2. 초기와 후속(여기서는 이슈/평시) 구간의 요구 구성 비교."""
    st.subheader("H2 · 구간별 고객 요구 구성")
    st.caption(
        "요구는 복수 라벨이므로 막대 합이 문서 수를 넘을 수 있습니다. "
        "비중의 분모는 해당 구간의 문서 수입니다."
    )

    counts = explode_tag_counts(tagged, "요구_초안", group_column="구간")
    if counts.empty:
        st.info("요구 라벨을 집계할 데이터가 없습니다.")
        return

    chart = px.bar(
        counts,
        x="문서비중(%)",
        y="라벨",
        color="구간",
        barmode="group",
        orientation="h",
        category_orders={"구간": PHASE_ORDER},
        color_discrete_map=PHASE_COLORS,
        template="plotly_white",
        labels={"라벨": ""},
    )
    chart.update_layout(height=460, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(chart, width="stretch")

    pivot = counts.pivot(index="라벨", columns="구간", values="문서비중(%)").fillna(0)
    if ISSUE_PHASE in pivot.columns and BASELINE_PHASE in pivot.columns:
        pivot["차이(이슈-평시)"] = (pivot[ISSUE_PHASE] - pivot[BASELINE_PHASE]).round(1)
        pivot = pivot.sort_values("차이(이슈-평시)", ascending=False)
    st.dataframe(pivot, width="stretch")


def _render_emotion_target(tagged: pd.DataFrame) -> None:
    """H3. 감정 표현과 그 대상의 교차 분석."""
    st.subheader("H3 · 감정 표현과 그 대상")
    st.caption(
        "'명시적 표현 없음'은 감정이 없다는 뜻이 아니라 표현을 찾지 못했다는 뜻이고, "
        "'판단 불가'는 본문이 없어 판단 자체가 불가능한 경우입니다."
    )

    exploded = tagged[["구간", "감정_초안", "감정대상_초안"]].explode("감정_초안").explode("감정대상_초안")
    crosstab = pd.crosstab(exploded["감정_초안"], exploded["감정대상_초안"])
    if crosstab.empty:
        st.info("감정 라벨을 집계할 데이터가 없습니다.")
        return

    left, right = st.columns([3, 2], gap="large")
    with left:
        heat = px.imshow(
            crosstab,
            text_auto=True,
            color_continuous_scale=["#f8fafc", "#e5484d"],
            aspect="auto",
            labels=dict(x="감정 대상", y="감정 표현", color="문서 수"),
        )
        heat.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(heat, width="stretch")
    with right:
        phase_counts = explode_tag_counts(tagged, "감정_초안", group_column="구간")
        chart = px.bar(
            phase_counts,
            x="문서비중(%)",
            y="라벨",
            color="구간",
            barmode="group",
            orientation="h",
            category_orders={"구간": PHASE_ORDER},
            color_discrete_map=PHASE_COLORS,
            template="plotly_white",
            labels={"라벨": ""},
        )
        chart.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(chart, width="stretch")


def _render_problem_distribution(tagged: pd.DataFrame) -> None:
    st.subheader("문제 상황 분포")
    counts = explode_tag_counts(tagged, "문제상황_초안", group_column="구간")
    if counts.empty:
        return
    chart = px.bar(
        counts,
        x="문서비중(%)",
        y="라벨",
        color="구간",
        barmode="group",
        orientation="h",
        category_orders={"구간": PHASE_ORDER},
        color_discrete_map=PHASE_COLORS,
        template="plotly_white",
        labels={"라벨": ""},
    )
    chart.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(chart, width="stretch")


def _render_review_worksheet(tagged: pd.DataFrame) -> None:
    """사람이 검수할 태깅 워크시트와 내보내기."""
    st.subheader("태깅 검수 워크시트")
    st.caption(
        "규칙 기반 초안입니다. 근거 문장을 보고 사람이 확정 라벨을 채우는 것을 전제로 합니다. "
        "내보낸 파일의 빈 확정 컬럼에 검수 결과를 입력하세요."
    )

    filter_cols = st.columns(3)
    with filter_cols[0]:
        phase_filter = st.multiselect(
            "구간", sorted(tagged["구간"].unique()), default=sorted(tagged["구간"].unique())
        )
    with filter_cols[1]:
        emotion_options = sorted({label for labels in tagged["감정_초안"] for label in labels})
        emotion_filter = st.multiselect("감정 초안", emotion_options, default=emotion_options)
    with filter_cols[2]:
        only_with_evidence = st.checkbox("근거 문장이 있는 건만", value=False)

    view = tagged[
        tagged["구간"].isin(phase_filter)
        & tagged["감정_초안"].apply(lambda labels: any(label in emotion_filter for label in labels))
    ]
    if only_with_evidence:
        view = view[view["근거문장_초안"].str.len() > 0]

    display_columns = [
        column
        for column in [
            "품목", "구간", "접수일자", "제목",
            "문제상황_초안", "요구_초안", "감정_초안", "감정대상_초안", "근거문장_초안",
        ]
        if column in view.columns
    ]
    flattened = view[display_columns].copy()
    for column in ("문제상황_초안", "요구_초안", "감정_초안", "감정대상_초안"):
        if column in flattened.columns:
            flattened[column] = flattened[column].apply(lambda labels: ", ".join(labels))

    st.caption(f"{len(flattened):,}건 표시 중")
    st.dataframe(
        flattened,
        hide_index=True,
        width="stretch",
        height=420,
        column_config={
            "제목": st.column_config.TextColumn("제목", width="medium"),
            "근거문장_초안": st.column_config.TextColumn("근거 문장(초안)", width="large"),
        },
    )

    export = flattened.copy()
    for column in ("문제상황_확정", "요구_확정", "감정_확정", "감정대상_확정", "검수자", "불확실성"):
        export[column] = ""
    st.download_button(
        "검수용 워크시트 CSV 내려받기",
        dataframe_to_csv_bytes(export),
        file_name="민원_태깅_검수용.csv",
        mime="text/csv",
    )


def render_complaint_section() -> None:
    """민원 표본을 프로젝트 라벨 체계(문제·요구·감정·감정대상)로 분석합니다."""
    st.info(
        "이 화면은 **규칙 기반 라벨 초안**을 만들어 사람 검수를 돕는 도구입니다. "
        "분류 결과 자체를 확정 태깅이나 감정 모델 성능으로 보고하지 마세요. "
        "검색 지수는 관심의 흐름을 볼 때 쓰고 감정 점수로 사용하지 않습니다.",
        icon="ℹ️",
    )

    df = _render_upload_panel()
    if df is None or df.empty:
        return

    tagged = tag_dataframe(df)

    total = len(tagged)
    undetermined = int(tagged["판단불가"].sum())
    no_emotion = int(tagged["감정_초안"].apply(lambda labels: NO_EXPLICIT_EMOTION in labels).sum())
    with_evidence = int(tagged["근거문장_초안"].str.len().gt(0).sum())

    metric_cols = st.columns(4)
    metric_cols[0].metric("분석 문서", f"{total:,}건")
    metric_cols[1].metric(
        "감정 표현 검출", f"{with_evidence:,}건", delta=f"{with_evidence / total * 100:.1f}%"
    )
    metric_cols[2].metric(
        "명시적 표현 없음",
        f"{no_emotion:,}건",
        help="감정이 없다는 뜻이 아니라 규칙으로 표현을 찾지 못했다는 뜻입니다.",
    )
    metric_cols[3].metric(
        "판단 불가", f"{undetermined:,}건", help="본문이 비어 있어 판단 자체가 불가능한 문서입니다."
    )

    _render_sample_composition(df)
    _render_need_comparison(tagged)
    _render_emotion_target(tagged)
    _render_problem_distribution(tagged)
    _render_review_worksheet(tagged)

    with st.expander("이 규칙 기반 태거의 한계"):
        st.markdown(
            """
- **부분 문자열 오탐**: `전화가`의 `화가`처럼 다른 낱말에 붙은 감정어는 앞 음절 경계로 걸러냅니다.
  다만 `심신불안`처럼 합성어로 쓰이는 감정어는 정상 검출되도록 예외를 두었습니다.
- **부정문**: `걱정 없습니다`처럼 감정어 뒤에 부정 표현이 오면 제외합니다.
  `걱정이 없지는 않습니다` 같은 이중 부정은 규칙으로 처리하지 못하므로 검수가 필요합니다.
- **타인의 감정 인용**: `아이가 놀랐다`처럼 신청인이 아닌 사람의 감정은 구분하지 못합니다.
- **상담원 요약형**: 상담원이 정리한 문장은 고객의 원래 표현과 다를 수 있어 `기록형태`를 함께 봐야 합니다.
- **처리결과 미사용**: 처리결과나 답변으로 고객 감정을 역추정하지 않습니다.
            """
        )
