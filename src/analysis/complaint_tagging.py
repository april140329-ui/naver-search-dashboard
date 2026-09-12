"""민원 본문에 문제·요구·감정·감정대상 라벨 초안을 붙이는 규칙 기반 태거.

라벨 체계는 분석가이드 7절을 따릅니다. 여기서 나오는 모든 라벨은 사람이 검수하기 위한
**초안**이며, 그 자체로 확정 태깅이 아닙니다. 특히 다음 원칙을 코드로 지킵니다.

- 감정 라벨에는 반드시 근거 문장을 함께 남깁니다.
- '명시적 표현 없음'(표현을 찾았지만 감정어가 없음)과 '판단 불가'(본문이 없어 판단 자체가 불가)를
  구분합니다.
- '전화가'의 '화가'처럼 부분 문자열 오탐을 막기 위해 앞 음절 경계를 확인합니다.
- 부정문('걱정 없다', '화나지 않는다')은 감정 매칭에서 제외합니다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

UNDETERMINED = "판단 불가"
NO_EXPLICIT_EMOTION = "명시적 표현 없음"
TARGET_UNCLEAR = "불명확"

# --- 라벨 사전 ---------------------------------------------------------------

PROBLEM_TAGS: dict[str, tuple[str, ...]] = {
    "안전성 우려": (
        "라돈", "방사능", "유해물질", "유해 물질", "발암", "환경호르몬", "피폭",
        "안전성", "인체에", "친환경 인증", "친환경인증", "검출", "리콜",
    ),
    "제품 하자 주장": (
        "하자", "불량", "파손", "균열", "크랙", "고장", "부러", "갈라",
        "냄새", "악취", "소음", "결함", "찢어", "벗겨", "함몰",
    ),
    "설명 불일치": (
        "광고", "표시", "고지", "상이", "과대", "허위", "인증 취소", "인증취소",
        "설명과 다르", "안내와 다르", "내용과 다르",
    ),
    "반품·환급 거부": (
        "환불 거부", "환불거부", "환불을 거부", "반품 거부", "반품거부",
        "반품이 안", "환불이 안", "불가하다고", "안된다고", "거절",
    ),
    "처리 지연": (
        "지연", "기다", "아직", "연락이 없", "회신이 없", "답변이 없",
        "수차례", "수회", "몇 번", "여러번", "여러 번", "감감무소식",
    ),
    "연락·안내 불일치": (
        "연락두절", "연락 두절", "통화가 안", "연락이 안", "불통",
        "전화를 받지", "받지 않", "회피", "책임회피", "떠넘기",
    ),
}

NEED_TAGS: dict[str, tuple[str, ...]] = {
    "안전성 설명": ("안전한지", "안전성", "유해한지", "안전 확인", "검사를", "측정", "위험한지"),
    "대상 제품 확인": ("대상 제품", "리콜 대상", "해당 모델", "대상인지", "해당되는지", "모델명"),
    "환급": ("환불", "환급", "반품", "대금", "결제 취소", "구입가"),
    "교환": ("교환", "새 제품", "새제품", "다른 제품으로"),
    "수리": ("수리", "as", "a/s", "보수", "정비"),
    "회수": ("회수", "수거", "가져가", "철거"),
    "추가 보상": ("보상", "배상", "손해배상", "치료비", "위자료", "피해보상", "피해 보상"),
    "진행 확인": ("진행", "처리 상황", "언제 되는지", "어떻게 되는지", "확인 부탁", "답변 부탁"),
    "절차·문의처 설명": (
        "어떻게 해야", "방법", "신청", "접수", "문의", "절차", "가능한지", "궁금",
    ),
    "시정": ("시정", "조치", "개선", "재발 방지"),
}

# 감정어는 오탐이 잦아 앞 음절 경계를 함께 확인합니다.
EMOTION_TAGS: dict[str, tuple[str, ...]] = {
    "불안": ("걱정", "불안", "우려", "염려", "무섭", "두렵", "찝찝", "불신"),
    "분노": ("화가", "화나", "분노", "어이없", "황당", "괘씸", "따졌", "부당", "짜증"),
    "실망": ("실망", "배신", "믿었는데", "성의없", "성의 없", "허탈"),
    "혼란·답답": ("답답", "혼란", "막막", "모르겠", "곤란", "당황", "난감"),
}

EMOTION_TARGETS: dict[str, tuple[str, ...]] = {
    "제품·안전": (
        "제품", "침대", "매트", "매트리스", "라돈", "유해", "방사능", "건강",
        "아이", "아기", "가족", "몸", "피부", "냄새",
    ),
    "판매자·제조사 대응": (
        "업체", "사업자", "판매자", "제조사", "본사", "회사", "고객센터", "상담원",
        "대진침대", "크림하우스", "판매처", "쇼핑몰", "담당자",
    ),
    "상담·처리 절차": (
        "처리", "접수", "절차", "상담", "피해구제", "환불 절차", "규정", "약관", "기준",
    ),
}

# 부정문 판정에 사용할 표현 (감정어 뒤쪽 짧은 구간에서 확인)
NEGATION_MARKERS = ("없", "않", "아니", "말고")
NEGATION_WINDOW = 6

# 감정 대상 판정 시 감정어 주변에서 살펴볼 글자 수
TARGET_WINDOW = 40

# 다른 낱말 속에 들어가 오탐을 만드는 감정어에만 앞 음절 경계를 강제합니다.
# 예: '전화가'/'대화가'의 '화가'. 반대로 '심신불안'의 '불안'처럼 합성어로 쓰이는 감정어까지
# 막으면 정상 표현을 놓치므로 기본값은 자유 매칭입니다.
AMBIGUOUS_TERMS = frozenset({"화가", "화나"})


def _boundary_pattern(term: str) -> re.Pattern[str]:
    """오탐 위험이 있는 감정어에는 앞 음절 경계를 붙여 정규식을 만듭니다."""
    escaped = re.escape(term)
    if term[0].isascii():
        return re.compile(rf"(?<![A-Za-z]){escaped}", re.IGNORECASE)
    if term in AMBIGUOUS_TERMS:
        return re.compile(rf"(?<![가-힣]){escaped}")
    return re.compile(escaped)


_EMOTION_PATTERNS = {
    label: [(term, _boundary_pattern(term)) for term in terms]
    for label, terms in EMOTION_TAGS.items()
}


def split_sentences(text: str) -> list[str]:
    """근거 문장 추출을 위해 본문을 문장 단위로 나눕니다."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip() for part in parts if part.strip()]


def _sentence_at(text: str, position: int) -> str:
    """매칭 위치가 포함된 문장을 근거 문장으로 돌려줍니다."""
    cursor = 0
    for sentence in split_sentences(text):
        index = text.find(sentence, cursor)
        if index == -1:
            continue
        if index <= position < index + len(sentence):
            return sentence.strip()
        cursor = index + len(sentence)
    snippet = text[max(0, position - 30) : position + 40].strip()
    return snippet


def _is_negated(text: str, end: int) -> bool:
    """감정어 바로 뒤에 부정 표현이 오면 감정으로 세지 않습니다."""
    tail = text[end : end + NEGATION_WINDOW]
    return any(marker in tail for marker in NEGATION_MARKERS)


def _match_simple_tags(text: str, tag_dict: dict[str, tuple[str, ...]]) -> list[str]:
    lowered = text.lower()
    return [
        label
        for label, terms in tag_dict.items()
        if any(term.lower() in lowered for term in terms)
    ]


@dataclass
class EmotionFinding:
    label: str
    target: str
    evidence: str
    term: str


@dataclass
class TaggingResult:
    problem_tags: list[str] = field(default_factory=list)
    need_tags: list[str] = field(default_factory=list)
    emotion_tags: list[str] = field(default_factory=list)
    emotion_targets: list[str] = field(default_factory=list)
    evidences: list[str] = field(default_factory=list)
    is_undetermined: bool = False


def _detect_emotion_target(text: str, start: int, end: int) -> str:
    """감정어 주변 문맥에서 감정의 대상을 추정합니다."""
    window = text[max(0, start - TARGET_WINDOW) : end + TARGET_WINDOW]
    hits = {
        target: sum(window.count(term) for term in terms)
        for target, terms in EMOTION_TARGETS.items()
    }
    best = max(hits, key=hits.get)
    return best if hits[best] > 0 else TARGET_UNCLEAR


def find_emotions(text: str) -> list[EmotionFinding]:
    """부정문과 부분 문자열 오탐을 걸러 감정 표현과 근거 문장을 찾습니다."""
    findings: list[EmotionFinding] = []
    seen: set[tuple[str, str]] = set()
    for label, patterns in _EMOTION_PATTERNS.items():
        for term, pattern in patterns:
            for match in pattern.finditer(text):
                if _is_negated(text, match.end()):
                    continue
                evidence = _sentence_at(text, match.start())
                key = (label, evidence)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    EmotionFinding(
                        label=label,
                        target=_detect_emotion_target(text, match.start(), match.end()),
                        evidence=evidence,
                        term=term,
                    )
                )
    return findings


def tag_text(text: str | None, title: str | None = None) -> TaggingResult:
    """민원 하나에 대한 라벨 초안을 만듭니다.

    문제·요구는 제목에도 핵심이 담기므로 제목과 본문을 함께 봅니다. 반면 감정은 근거 문장을
    남겨야 하고 상담원이 붙인 제목이 섞이면 곤란하므로 본문에서만 찾습니다.
    본문이 비어 있으면 감정이 없는 것이 아니라 '판단 불가'로 표시합니다.
    """
    clean = (text or "").strip()
    clean_title = (title or "").strip()
    if not clean:
        return TaggingResult(
            problem_tags=[UNDETERMINED],
            need_tags=[UNDETERMINED],
            emotion_tags=[UNDETERMINED],
            emotion_targets=[UNDETERMINED],
            is_undetermined=True,
        )

    combined = f"{clean_title} {clean}".strip()
    emotions = find_emotions(clean)
    if emotions:
        emotion_labels = list(dict.fromkeys(finding.label for finding in emotions))
        targets = list(dict.fromkeys(finding.target for finding in emotions))
        evidences = [f"[{finding.label}] {finding.evidence}" for finding in emotions]
    else:
        emotion_labels = [NO_EXPLICIT_EMOTION]
        targets = [TARGET_UNCLEAR]
        evidences = []

    return TaggingResult(
        problem_tags=_match_simple_tags(combined, PROBLEM_TAGS) or ["기타"],
        need_tags=_match_simple_tags(combined, NEED_TAGS) or ["불명확"],
        emotion_tags=emotion_labels,
        emotion_targets=targets,
        evidences=evidences,
    )


def tag_dataframe(
    df: pd.DataFrame, text_column: str = "본문", title_column: str = "제목"
) -> pd.DataFrame:
    """DataFrame 전체에 라벨 초안 컬럼을 추가합니다."""
    if df.empty:
        return df

    titles = df[title_column] if title_column in df.columns else [""] * len(df)
    results = [tag_text(body, title) for body, title in zip(df[text_column], titles)]
    tagged = df.copy()
    tagged["문제상황_초안"] = [result.problem_tags for result in results]
    tagged["요구_초안"] = [result.need_tags for result in results]
    tagged["감정_초안"] = [result.emotion_tags for result in results]
    tagged["감정대상_초안"] = [result.emotion_targets for result in results]
    tagged["근거문장_초안"] = [" / ".join(result.evidences) for result in results]
    tagged["판단불가"] = [result.is_undetermined for result in results]
    return tagged


def explode_tag_counts(
    df_tagged: pd.DataFrame, tag_column: str, group_column: str | None = None
) -> pd.DataFrame:
    """복수 라벨 컬럼을 펼쳐 라벨별 문서 수를 셉니다.

    복수 라벨이므로 합계는 문서 수를 넘을 수 있습니다. 비중은 라벨 합이 아니라
    해당 그룹의 문서 수를 분모로 계산합니다.
    """
    if df_tagged.empty or tag_column not in df_tagged.columns:
        return pd.DataFrame()

    columns = [tag_column] if group_column is None else [group_column, tag_column]
    exploded = df_tagged[columns].explode(tag_column)

    if group_column is None:
        counts = exploded[tag_column].value_counts().rename_axis("라벨").reset_index(name="문서수")
        counts["문서비중(%)"] = (counts["문서수"] / len(df_tagged) * 100).round(1)
        return counts

    denominators = df_tagged.groupby(group_column).size()
    counts = (
        exploded.groupby([group_column, tag_column]).size().reset_index(name="문서수")
    )
    counts["문서비중(%)"] = counts.apply(
        lambda row: round(row["문서수"] / denominators[row[group_column]] * 100, 1),
        axis=1,
    )
    return counts.rename(columns={tag_column: "라벨"})
