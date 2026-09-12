from __future__ import annotations
import math
import random
from datetime import datetime, timedelta
import pandas as pd
from src.config.settings import SEARCH_CHANNELS


def generate_mock_search_data(
    keywords: list[str], channel_ids: list[str], display_per_channel: int = 30
) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    """API 키가 없거나 테스트 모드일 때 사용할 실감나는 모의 검색 데이터 생성기"""
    all_items = []
    totals = {}

    sample_topics = {
        "뉴스": ["신제품 출시 발표", "시장 점유율 급등 분석", "소비자 만족도 1위 달성", "글로벌 트렌드 전망", "전문가 심층 리뷰"],
        "블로그": ["내돈내산 1개월 실사용 후기", "장단점 완벽 비교 가이드", "초보자를 위한 핵심 팁", "구매 전 필수 체크리스트"],
        "카페글": ["가성비 모델 질문드립니다", "실제 체감 성능 어떤가요?", "특가 할인 정보 공유합니다", "회원님들 추천 부탁드려요"],
        "지식iN": ["어떤 모델을 사는 게 더 유리한가요?", "A/S 보증기간 및 유지비 질문", "최신 모델 차이점 알려주세요"],
        "웹문서": ["공식 스펙 및 기술 사양 문서", "시장 조사 통계 리포트", "사용자 매뉴얼 가이드 PDF"],
        "백과사전": ["역사 및 발전 과정 개요", "핵심 기술 원리 및 정의", "산업 표준 및 분류 체계"],
        "지역": ["공식 플래그십 스토어 매장", "공인 서비스 센터 강남점", "체험형 쇼룸 종로점"],
        "이미지": ["공식 렌더링 디자인", "실물 언박싱 포토", "색상별 비교 갤러리"],
    }

    now = datetime.now()

    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        totals[kw] = {}

        # 키워드별 가중치 (비교 시 서로 다른 규모감 부여)
        kw_hash = sum(ord(c) for c in kw)
        base_multiplier = 10000 + (kw_hash % 50000)

        for ch_id in channel_ids:
            cfg = SEARCH_CHANNELS.get(ch_id)
            if not cfg:
                continue

            # 채널별 총량 추정치
            ch_multiplier = {
                "blog": 2.5,
                "cafearticle": 2.0,
                "news": 1.2,
                "webkr": 3.0,
                "kin": 1.5,
                "image": 4.0,
                "encyc": 0.05,
                "local": 0.1,
            }.get(ch_id, 1.0)

            total_count = int(base_multiplier * ch_multiplier)
            totals[kw][ch_id] = total_count

            count = min(display_per_channel, 5 if ch_id == "local" else 50)
            templates = sample_topics.get(cfg.name, ["최신 동향 리포트", "분석 자료"])

            for idx in range(1, count + 1):
                tpl = templates[(idx + kw_hash) % len(templates)]
                post_dt = now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
                date_str = post_dt.strftime("%Y-%m-%d %H:%M")

                title = f"{kw} {tpl} #{idx}"
                desc = f"{kw}에 대한 {cfg.name} 상세 정보입니다. 최신 시장 데이터와 사용자 피드백을 기반으로 종합적인 분석 인사이트를 제공합니다."
                author = f"{kw}_인사이트_{idx}"

                extra = {}
                if ch_id == "image":
                    extra["thumbnail"] = f"https://picsum.photos/seed/{kw}_{idx}/200/150"
                elif ch_id == "local":
                    extra["address"] = f"서울특별시 강남구 테헤란로 {idx*10}길"
                    extra["telephone"] = f"02-555-{idx:04d}"

                all_items.append({
                    "keyword": kw,
                    "channel_id": ch_id,
                    "channel_name": cfg.name,
                    "rank": idx,
                    "title": title,
                    "description": desc,
                    "link": "https://search.naver.com/search.naver?query=" + kw,
                    "pub_date": date_str,
                    "author_or_source": author,
                    "extra": extra,
                })

    return pd.DataFrame(all_items), totals


def generate_mock_trend_data(
    keywords: list[str], start_date: str, end_date: str, time_unit: str = "date"
) -> pd.DataFrame:
    """API 키가 없거나 테스트 모드일 때 사용할 실감나는 모의 데이터랩 시계열 트렌드 생성기"""
    try:
        s_dt = datetime.strptime(start_date, "%Y-%m-%d")
        e_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except Exception:
        e_dt = datetime.now()
        s_dt = e_dt - timedelta(days=90)

    if s_dt > e_dt:
        s_dt = e_dt - timedelta(days=30)

    freq = "D" if time_unit == "date" else ("W" if time_unit == "week" else "MS")
    periods = pd.date_range(start=s_dt, end=e_dt, freq=freq)

    records = []
    for kw_idx, kw in enumerate(keywords):
        kw = kw.strip()
        if not kw:
            continue
        # 고유 패턴 생성을 위한 시드
        random.seed(sum(ord(c) for c in kw) + kw_idx * 100)
        base_level = random.uniform(30.0, 70.0)
        amplitude = random.uniform(10.0, 25.0)

        for step, dt in enumerate(periods):
            # 주기적 변동 + 랜덤 노이즈 + 특정 시점 스파이크(이벤트)
            sine_wave = math.sin(step / 5.0) * amplitude
            noise = random.uniform(-5.0, 5.0)
            spike = 30.0 if step in (len(periods) // 3, len(periods) // 2) else 0.0

            ratio = max(1.0, min(100.0, base_level + sine_wave + noise + spike))
            records.append({
                "period": dt,
                "keyword": kw,
                "ratio": round(ratio, 2),
            })

    df = pd.DataFrame(records)
    return df
