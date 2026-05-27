# ruff: noqa: E501
"""Human-readable copy for the Jibi research review board."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReviewBoardCopy:
    title: str
    description: str


INTERNAL_LABEL_PATTERNS = (
    "merged_seed",
    "review_primary",
    "review_as_core_seed",
    "review_as_explainer_seed",
    "generic_why",
    "needs_external_sources",
    "evidence_only",
    "demote_or_reject",
    "story_bundle",
)


def compact_text(value: object) -> str:
    return " ".join(str(value or "").split())


def clean_review_title(value: object) -> str:
    title = compact_text(value)
    title = re.sub(r"^\[[^\]]+\]\s*", "", title)
    title = re.sub(r"^\([^)]*(?:보도자료|보도참고자료)[^)]*\)\s*", "", title)
    title = re.sub(r"^\S+·", "", title)
    return title.strip(" -:") or compact_text(value)


def _copy_text(record: dict[str, Any], candidate: dict[str, Any], candidate_title: str) -> str:
    return " ".join(
        [
            str(record.get("bundle_title") or ""),
            str(record.get("why_bundle") or ""),
            str(candidate_title or ""),
            str(candidate.get("title") or ""),
            str(candidate.get("summary") or ""),
            str(candidate.get("why_interesting") or ""),
            str(candidate.get("seed_type") or ""),
            str(candidate.get("source_role_class") or ""),
            str(candidate.get("source") or ""),
        ]
    ).lower()


def _direct_copy_text(
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
) -> str:
    """Text safe for template triggers; exclude generated why copy to avoid overfitting loops."""
    return " ".join(
        [
            str(record.get("bundle_title") or ""),
            str(candidate_title or ""),
            str(candidate.get("title") or ""),
            str(candidate.get("summary") or ""),
            str(candidate.get("seed_type") or ""),
            str(candidate.get("source_role_class") or ""),
            str(candidate.get("source") or ""),
        ]
    ).lower()


def _source_cue(candidate: dict[str, Any]) -> str:
    source = compact_text(candidate.get("source"))
    title = clean_review_title(candidate.get("title"))
    if source and title:
        if title[0] in {"'", '"', "“", "‘"}:
            return f"{source}의 {title}"
        return f"{source}의 '{title}'"
    if source:
        return source
    if title:
        return f"원문 '{title}'"
    return "원문"


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _has_ai_signal(text: str) -> bool:
    return (
        "인공지능" in text
        or "챗gpt" in text
        or "chatgpt" in text
        or "openai" in text
        or bool(re.search(r"\bai\b", text, flags=re.IGNORECASE))
    )


def _has_tokenization_signal(text: str) -> bool:
    return (
        "토큰화" in text
        or "tokenization" in text
        or bool(re.search(r"\brwa\b", text, flags=re.IGNORECASE))
    )


def _has_delivery_platform_signal(text: str) -> bool:
    return (
        "무료배달" in text
        or "배달비" in text
        or "배달앱" in text
        or ("배달" in text and _has_any(text, ("수수료", "점주", "라이더", "자영업")))
    )


def _has_energy_support_signal(text: str) -> bool:
    return "고유가" in text or "유가" in text or ("피해지원금" in text and "에너지" in text)


def _has_factory_capex_signal(text: str) -> bool:
    return _has_any(
        text,
        (
            "공장",
            "배터리공장",
            "합작공장",
            "plant",
            "factory",
            "capex",
            "설비투자",
            "투자 부담",
            "공급과잉",
        ),
    ) and _has_any(
        text,
        (
            "처분",
            "매각",
            "매입",
            "투자",
            "합작",
            "배터리",
            "전기차",
            "ev",
            "보조금",
            "subsidy",
        ),
    )


def _has_cash_reallocation_signal(text: str) -> bool:
    return _has_any(
        text,
        (
            "지분 팔아",
            "지분 매각",
            "지분을 팔",
            "매각대금",
            "자산 매각",
            "손에 쥔",
            "현금 확보",
            "stake sale",
            "sells stake",
            "sold stake",
        ),
    )


def _has_market_note_signal(text: str) -> bool:
    return _has_any(
        text,
        (
            "목표가",
            "특징주",
            "수혜",
            "주가",
            "ipo챗",
            "수요예측",
            "청약",
            "레버리지",
            "증권",
            "analyst",
            "price target",
            "shares fall",
        ),
    )


def _has_equity_financing_signal(text: str) -> bool:
    return _has_any(
        text,
        (
            "유상증자",
            "주주배정",
            "신주",
            "희석",
            "자본확충",
            "rights issue",
            "capital raise",
            "share issue",
        ),
    )


def _has_mou_bulletin_signal(text: str) -> bool:
    return bool(re.search(r"\bmou\b", text, flags=re.IGNORECASE)) or _has_any(
        text,
        (
            "[게시판]",
            "게시판",
            "업무협약",
            "협약",
            "워크숍",
            "포럼",
            "모집",
            "개최",
        ),
    )


def _is_generic_machine_title(title: str) -> bool:
    return compact_text(title) in {
        "근거 자료: 더 큰 이야기 안에서 볼 후보",
        "시장 반응 메모: 단독 seed인지 근거인지",
    }


def review_board_title(
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
) -> str:
    text = _direct_copy_text(record, candidate, candidate_title)
    candidate_text = _direct_copy_text({}, candidate, candidate_title)
    bundle_title = str(record.get("bundle_title") or "")
    if (
        bundle_title
        and _has_mou_bulletin_signal(bundle_title.lower())
        and not _has_mou_bulletin_signal(candidate_text)
    ) or _is_generic_machine_title(bundle_title):
        raw_title = str(candidate_title or candidate.get("title") or bundle_title)
    else:
        raw_title = str(bundle_title or candidate_title or candidate.get("title") or "")
    if "청년" in text and _has_any(text, ("쉬었음", "경제활동참가율", "노동시장")):
        return "일하지도, 구직하지도 않는 청년들: '쉬었음'의 경제학"
    if _has_tokenization_signal(text):
        return "집도, 채권도 쪼개 사고파는 시대: 자산 토큰화"
    if _has_any(
        text,
        (
            "공공/현장 ai",
            "ai 도입",
            "ai 부적절",
            "ai 드론",
            "ai 노사",
            "public_ai",
        ),
    ):
        return "AI가 공무원 보고서와 현장 치안에 들어올 때"
    if _has_delivery_platform_signal(text):
        return "무료배달은 누가 내나: 배달앱 수수료와 업주 부담"
    if "양파" in text:
        return "양파가 너무 많으면 정부는 무엇을 하나"
    if _has_energy_support_signal(text):
        return "고유가 지원금 현황으로 보는 에너지 가격 충격"
    if _has_any(text, ("spacex", "starship", "스타십")):
        return "스페이스X 스타십: 민간 우주개발의 돈과 환경 갈등"
    if _has_any(text, ("반바지", "cool biz", "쿨비즈", "스노우피크")):
        return "반바지가 복지가 되는 시대: 폭염과 회사 복장문화"
    if _has_any(text, ("열사병", "불볕더위", "산업현장", "작업중지권")) and "폭염" in text:
        return "폭염은 산업현장의 새 안전 규칙이 될까"
    if _has_any(text, ("개발제한구역", "그린벨트", "greenbelt")):
        return "그린벨트에 사는 사람들은 왜 생활비 보조를 받나"
    if _has_any(text, ("글로벌 pf", "project finance", "메가뱅크")):
        return "글로벌 PF 대출 5년새 2배: 일본 메가뱅크는 왜 큰손이 됐나"
    if _has_any(text, ("항모", "스텔스기", "carrier")) and "중" in text:
        return "중국 항모 3척과 스텔스기: 해군력이 바뀌는 신호인가"
    if _has_any(text, ("taunting and degrading civilians", "degrading civilians")):
        return "전쟁 중 모욕과 조롱도 왜 국제법 문제가 되나"
    if _has_factory_capex_signal(candidate_text):
        return "전기차 공장 붐 이후 누가 비용을 떠안나"
    if _has_cash_reallocation_signal(candidate_text):
        return "기업은 현금을 어디로 옮기나"
    if _has_equity_financing_signal(candidate_text):
        return "회사가 주주에게 다시 돈을 구할 때"
    if _has_market_note_signal(candidate_text):
        return "시장 반응 메모: 단독 seed인지 근거인지"
    if _has_mou_bulletin_signal(candidate_text):
        return "근거 자료: 더 큰 이야기 안에서 볼 후보"
    return clean_review_title(raw_title or candidate_title)


def _evidence_text(candidate: dict[str, Any]) -> str:
    evidence = candidate.get("evidence_needed") or ""
    if isinstance(evidence, list):
        return ", ".join(str(item) for item in evidence if str(item).strip())
    return compact_text(evidence)


def _history_sentence(status: str) -> str:
    return {
        "seen_before": "이전에 보드에 올라온 적이 있어 새 각도인지 확인해야 합니다.",
        "reviewed_before": "이미 사람이 리뷰한 주제라 지난 의견과 비교해야 합니다.",
        "rejected_before": "이전에 reject 의견이 있던 주제라 다시 올릴 이유가 분명해야 합니다.",
        "promoted_before": "이전에 seed 의견이 있던 주제라 후속 업데이트인지 확인하면 좋습니다.",
    }.get(status, "")


def _sentence(value: str) -> str:
    text = compact_text(value)
    if not text:
        return ""
    if text[-1] in ".?!。！？":
        return text
    return f"{text}."


def _question_first_description(
    *,
    question: str,
    reason: str,
    next_step: str,
    verdict: str = "",
) -> str:
    next_text = compact_text(next_step)
    if next_text.startswith(("리서치 포인트", "확인할 지점", "확인할 것은")):
        next_sentence = _sentence(next_text)
    elif next_text and next_text[-1] in ".?!。！？":
        next_sentence = next_text
    else:
        next_sentence = f"더 볼 지점은 {next_text}입니다."
    parts = [
        f"'{compact_text(question)}' 이 질문으로 열면 시청자가 바로 따라올 수 있습니다.",
        _sentence(reason),
        next_sentence,
    ]
    if verdict:
        parts.append(_sentence(verdict))
    return " ".join(part for part in parts if part)


def _fallback_need_sentence(
    *,
    record: dict[str, Any],
    candidate: dict[str, Any],
    related_titles: str,
    history_status: str,
) -> str:
    needs: list[str] = []
    evidence = _evidence_text(candidate)
    if evidence:
        needs.append(evidence)
    action = str(record.get("suggested_operator_action") or "")
    if "collect_second_source" in action:
        needs.append("두 번째 출처와 숫자")
    elif "collect_price" in action:
        needs.append("가격·생활 영향·산업 자료")
    elif "attach_to_larger_story" in action:
        needs.append("이 자료를 붙일 더 큰 주제")
    if related_titles:
        needs.append("서브 링크의 관련 후보")
    if needs:
        sentence = "리서치 포인트는 " + ", ".join(dict.fromkeys(needs)) + "입니다."
    else:
        sentence = "리서치 포인트는 추가 출처를 붙여 실제 방송 소재인지 확인하는 것입니다."
    history = _history_sentence(history_status)
    return f"{sentence} {history}".strip()


def _fallback_question(
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
) -> str:
    text = _direct_copy_text(record, candidate, candidate_title)
    story_role = str(candidate.get("story_role") or record.get("story_role") or "")
    source_role = str(candidate.get("source_role_class") or record.get("source_role") or "")
    if story_role in {"evidence_for_larger_story", "background_reference"}:
        return "이 자료는 어떤 큰 이야기의 근거로 붙일 때 가장 설득력이 있나?"
    if story_role == "seed_with_supporting_links":
        return "이 후보를 단독 주제로 만들려면 어떤 최신 뉴스와 두 번째 출처가 필요한가?"
    if source_role == "research_note":
        return "이 연구자료를 오늘의 생활경제 질문으로 바꾸려면 어디를 좁혀야 하나?"
    if _has_ai_signal(text):
        return "AI가 실제 조직 안으로 들어올 때 효율과 책임은 어떻게 나뉘나?"
    if _has_any(text, ("규제", "지원", "정책", "보조")):
        return "이 정책은 누구의 비용을 줄이고 누구에게 새 부담을 넘기나?"
    if _has_any(text, ("가격", "물가", "요금", "수수료", "금리")):
        return "이 가격 변화는 시청자의 지갑과 어떤 경로로 연결되나?"
    return "이 후보를 방송 소재로 만들려면 어떤 한 가지 질문으로 좁혀야 하나?"


def _global_section_description(
    *,
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
    related_titles: str,
    history_status: str,
) -> str | None:
    del record, related_titles, history_status
    text = _direct_copy_text({}, candidate, candidate_title)
    source = _source_cue(candidate)
    if _has_any(text, ("datacentre", "datacenter", "data centre", "데이터센터")) and (
        _has_ai_signal(text) or _has_any(text, ("emissions", "electricity", "전력", "배출"))
    ):
        return _question_first_description(
            question="AI 데이터센터는 친환경 인프라인가, 전력 먹는 공장인가?",
            reason=(
                f"{source}은 AI가 클라우드 화면 뒤에서 전기·토지·배출 문제로 바뀌는 지점을 보여줍니다. "
                "선정 이유는 데이터센터를 디지털 산업이 아니라 전력수요와 탄소회계가 붙은 물리적 인프라로 볼 수 있기 때문입니다."
            ),
            next_step="전력 사용량, 배출 산정 방식, 지역 인허가, 빅테크 투자 계획을 붙여 'AI 붐의 숨은 전기요금'으로 설명 가능한지 확인하는 것",
        )
    if _has_any(
        text,
        (
            "energy bills",
            "electricity prices",
            "energy shock",
            "ofgem",
            "전기요금",
            "에너지 요금",
            "전력요금",
        ),
    ):
        return _question_first_description(
            question="전기요금이 오래 비싸지면 가계와 산업은 무엇부터 바뀌나?",
            reason=(
                f"{source}은 에너지 가격 충격이 일시적 뉴스가 아니라 가계 지출, 기업 비용, 전력망 투자 문제로 이어질 수 있음을 보여줍니다. "
                "선정 이유는 전기요금을 물가 기사로 끝내지 않고, 에너지 전환과 생활비 압박이 만나는 구조로 키울 수 있기 때문입니다."
            ),
            next_step="가계 전기요금 추이, 산업용 전력 가격, 규제기관 전망, 정부 보조 또는 요금 설계 논쟁을 붙이는 것",
        )
    if _has_any(
        text,
        (
            "work placements",
            "zero-hours",
            "entry-level jobs",
            "worklessness",
            "search for a job",
            "첫 직장",
            "청년 일자리",
        ),
    ):
        return _question_first_description(
            question="청년의 첫 경력은 왜 점점 더 비싼 관문이 되고 있나?",
            reason=(
                f"{source}은 대학·기업·노동시장이 청년에게 요구하는 '경험'의 기준이 높아지는 장면입니다. "
                "선정 이유는 해외 사례라도 청년이 첫 직장에 들어가기 전부터 인턴십, 현장경험, 네트워크를 요구받는 구조를 설명할 수 있기 때문입니다."
            ),
            next_step="대학 work placement 제도, 무급/저임금 인턴 논쟁, 청년 고용률, 기업의 신입 교육 비용 자료를 붙여 한국 청년 노동시장과 비교 가능한지 보는 것",
        )
    if _has_any(text, ("heatwave", "wet easter", "hot weather", "hottest may")) and _has_any(
        text,
        ("sales", "retail", "b&q", "kingfisher", "diy", "consumer", "소비", "유통"),
    ):
        return _question_first_description(
            question="날씨가 달라지면 사람들의 소비와 기업 실적은 어디서 먼저 흔들리나?",
            reason=(
                f"{source}은 폭염이나 비 많은 연휴가 단순 날씨 뉴스가 아니라 유통·DIY·냉방·정원용품 같은 생활 소비를 바꾸는 장면입니다. "
                "선정 이유는 기후 변화가 먼 미래 이야기가 아니라 계절 장사, 재고, 전력수요, 소비 패턴을 흔드는 생활경제 소재로 이어질 수 있기 때문입니다."
            ),
            next_step="날씨별 판매 품목 변화, 냉방/정원/주택수리 소비, 소매업 실적, 폭염 적응 비용 자료를 붙여 회사 실적 기사에서 생활경제 이야기로 옮기는 것",
        )
    if _has_any(text, ("delivery robots", "robot delivery", "배달 로봇")):
        return _question_first_description(
            question="배달 로봇이 거리로 나오면 편리함과 불편은 누가 나눠 갖나?",
            reason=(
                f"{source}은 기술 데모가 아니라 보도·상점·주민·플랫폼이 같은 공간을 나눠 쓰는 문제를 보여줍니다. "
                "선정 이유는 자동화가 실제 거리로 내려왔을 때 비용절감, 보행권, 안전, 노동 대체가 한꺼번에 충돌하기 때문입니다."
            ),
            next_step="운영 도시, 사고/민원 사례, 배달비 구조, 로봇 규제와 보험 책임 자료를 붙이는 것",
        )
    if _has_ai_signal(text) and _has_any(
        text,
        (
            "copyright",
            "voice",
            "ai slop",
            "music",
            "students",
            "graduation",
            "culture of power",
            "risks to humanity",
            "pope leo",
            "encyclical",
        ),
    ):
        return _question_first_description(
            question="AI가 콘텐츠와 신뢰의 규칙을 어디까지 바꾸고 있나?",
            reason=(
                f"{source}은 AI를 산업 생산성보다 창작자 권리, 목소리 소유권, 교육 현장, 가짜 콘텐츠 신뢰 문제로 보게 해줍니다. "
                "선정 이유는 기술 설명보다 사람들이 실제로 불편해하거나 반발하는 접점을 잡을 수 있기 때문입니다."
            ),
            next_step="저작권 분쟁, 플랫폼 정책, 학교/창작자 반발 사례, 숫자로 확인되는 이용 변화가 붙는지 보는 것",
        )
    if _has_any(text, ("pfas", "forever chemicals", "factory farming", "battery cows", "toxic")):
        return _question_first_description(
            question="싸게 생산한 비용은 환경과 지역사회에 어떻게 돌아오나?",
            reason=(
                f"{source}은 환경 이슈를 캠페인 구호가 아니라 규제, 생산비, 소비자 가격, 지역 피해의 문제로 볼 수 있게 합니다. "
                "선정 이유는 해외 사례라도 오염물질, 대량생산, 처리 비용이라는 구조가 분명하면 방송형 설명 소재로 자랄 수 있기 때문입니다."
            ),
            next_step="규제 기준, 기업 비용, 피해 지역 사례, 소비자 가격과 연결되는 숫자를 붙이는 것",
        )
    return None


def _market_corporate_description(
    *,
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
    related_titles: str,
    history_status: str,
) -> str | None:
    del record, related_titles, history_status
    text = _direct_copy_text({}, candidate, candidate_title)
    source = _source_cue(candidate)
    if _has_factory_capex_signal(text):
        return _question_first_description(
            question="전기차 공장 붐 이후 누가 비용을 떠안나?",
            reason=(
                f"{source}은 회사 하나의 부동산 처분이나 공장 뉴스로 끝내기보다, 전기차·배터리 투자 붐 이후 공장과 현금흐름을 어떻게 재조정하는지 보는 단서입니다. "
                "핵심은 주가가 아니라 보조금, 합작공장, 공급과잉, 설비투자 부담, 현금 회수의 구조입니다."
            ),
            next_step="다른 배터리 업체의 공장 조정, 미국 보조금 조건, 전기차 수요 둔화, 가동률 자료를 붙여 산업 재편 이야기로 커지는지 확인하는 것",
            verdict="단일 기업 기사로만 남으면 evidence이고, 여러 회사 사례가 붙으면 seed 후보가 됩니다",
        )
    if _has_cash_reallocation_signal(text):
        return _question_first_description(
            question="기업이 가진 지분을 팔아 현금을 만들면, 그 돈은 어디로 옮겨가나?",
            reason=(
                f"{source}은 단순 지분 매각 뉴스라기보다, 큰 기업이 전환기에 현금을 확보하고 다음 투자처를 고르는 장면으로 볼 수 있습니다. "
                "다만 한 회사의 다음 행보만 따라가면 투자 기사처럼 보이므로, 자산 매각과 현금 재배치라는 구조로 좁히는 편이 안전합니다."
            ),
            next_step="다른 플랫폼 기업의 자산 매각, AI·콘텐츠·커머스 투자 재원, 부채와 규제 리스크 자료를 붙여 '기업들은 다음 성장판을 어떻게 사나'로 확장 가능한지 보는 것",
            verdict="단일 회사 전망으로 끝나면 evidence이고, 여러 기업의 현금 재배치 흐름이 보이면 seed로 올릴 수 있습니다",
        )
    if _has_equity_financing_signal(text):
        return _question_first_description(
            question="회사가 주주에게 다시 돈을 구하면 누가 비용을 부담하나?",
            reason=(
                f"{source}은 유상증자 자체보다, 금리가 높고 투자비가 큰 시기에 기업이 돈을 조달하는 방식과 기존 주주의 희석 부담을 보여주는 사례입니다. "
                "투자 판단으로 읽히지 않게 하려면 특정 종목보다 산업 전체의 자금조달 압박을 봐야 합니다."
            ),
            next_step="동종 업계 유상증자 사례, 부채비율, 투자계획, 주주배정 구조와 희석 효과를 붙여 기업 자금조달 설명 자료로 쓸 수 있는지 확인하는 것",
            verdict="단독 Top seed보다는 산업 자금조달 이야기의 evidence로 두는 편이 안전합니다",
        )
    if _has_market_note_signal(text):
        return _question_first_description(
            question="시장은 어떤 산업 변화를 이미 가격에 반영하고 있나?",
            reason=(
                f"{source}은 목표가·특징주·수혜주 같은 시장 반응을 보여주지만, 그 자체로는 방송 seed라기보다 기대가 어디에 몰리는지 보여주는 메모에 가깝습니다. "
                "종목 전망처럼 보이면 위험하고, 반도체·배터리·AI 인프라 같은 산업 병목의 보조 근거로 붙일 때 가치가 있습니다."
            ),
            next_step="기업 하나의 목표가가 아니라 공급 부족, CAPEX, 수요처, 경쟁사 사례, 공식 통계가 같은 방향을 가리키는지 확인하는 것",
            verdict="리뷰보드에서는 seed 후보보다 evidence 후보로 보는 편이 안전합니다",
        )
    if _has_mou_bulletin_signal(text):
        return _question_first_description(
            question="이 협약이나 행사는 어떤 큰 변화의 증거로 붙일 때 의미가 있나?",
            reason=(
                f"{source}은 단독으로는 행사·협약·모집 공지에 가깝습니다. "
                "그래도 금융취약층 지원, AI 인력 양성, 산업 전환처럼 더 큰 흐름을 설명할 때 공식 근거로 붙이면 쓸모가 생깁니다."
            ),
            next_step="협약 이후 실제 예산, 참여 기관, 대상 규모, 이전 정책과의 차이, 현장 사례를 확인해 큰 이야기의 근거인지 판단하는 것",
            verdict="단독 seed로 올리기보다 evidence 또는 보강 검색 출발점으로 두는 편이 안전합니다",
        )
    return None


def _template_description(
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
    *,
    related_titles: str,
    history_status: str,
) -> str | None:
    text = _direct_copy_text(record, candidate, candidate_title)
    source = _source_cue(candidate)
    global_section = _global_section_description(
        record=record,
        candidate=candidate,
        candidate_title=candidate_title,
        related_titles=related_titles,
        history_status=history_status,
    )
    if global_section:
        return global_section
    market_corporate = _market_corporate_description(
        record=record,
        candidate=candidate,
        candidate_title=candidate_title,
        related_titles=related_titles,
        history_status=history_status,
    )
    if market_corporate:
        return market_corporate
    if "청년" in text and _has_any(text, ("쉬었음", "경제활동참가율", "노동시장")):
        return _question_first_description(
            question="청년 실업률이 낮아도 왜 일하지도 구직하지도 않는 청년은 늘어날까?",
            reason=(
                "한국은행의 청년 노동시장 자료들이 같은 문제를 다른 지표로 보여줍니다. "
                "실업률만 보면 안 보이는 노동시장 밖 청년을 다루는 주제라, 구직 포기·첫 직장 실패·지역/학력 mismatch·결혼/출산 지연까지 연결할 수 있습니다."
            ),
            next_step="BOK 자료들을 한 묶음으로 보고, 청년 실업률보다 경제활동참가율과 비경제활동인구가 왜 더 중요한지 그림으로 설명하는 것",
            verdict="단독 seed에 가깝지만 비슷한 BOK 후보가 있으면 하나의 청년 노동시장 이탈 묶음으로 보는 편이 좋습니다",
        )
    if _has_tokenization_signal(text):
        return _question_first_description(
            question="코인 가격이 아니라, 집과 채권의 권리를 토큰으로 쪼개면 누가 책임질까?",
            reason=(
                "한국은행 이슈노트는 좋은 배경 자료지만, 이 후보는 원론 설명만으로는 딱딱해질 수 있습니다. "
                "방송 각도는 부동산·채권·펀드 같은 현실 자산의 권리를 디지털 토큰으로 기록하고 쪼개 거래하려는 제도권 금융의 움직임입니다."
            ),
            next_step="STO·조각투자·CBDC 비교표, 실제 분쟁 가능성, 그리고 오늘 이 이슈를 다시 보게 만드는 최신 뉴스 hook을 붙이는 것",
            verdict="BOK는 핵심 근거이고, 단독 seed로 쓰려면 '이 토큰이 진짜 소유권을 보장하나' 같은 책임 질문을 앞에 세워야 합니다",
        )
    if _has_any(
        text,
        ("공공/현장 ai", "ai 도입", "ai 부적절", "ai 드론", "ai 노사", "public_ai"),
    ):
        return _question_first_description(
            question="AI가 공무원 보고서와 현장 판단에 들어오면, 책임은 누가 지는가?",
            reason=(
                f"{source}에서 보이는 것처럼 AI가 보고서 작성, 현장 수색, 행정 책임 같은 공공 업무 안으로 들어오고 있습니다. "
                "선정 이유는 AI가 더 이상 챗봇 데모가 아니라 사람이 책임져야 하는 행정 판단과 현장 판단에 붙기 시작했다는 점입니다."
            ),
            next_step="AI 활용 가이드라인, 오판 사례, 공공기관 도입 통계를 붙여 Top seed로 승격 가능한지 보는 것",
        )
    if _has_delivery_platform_signal(text):
        return _question_first_description(
            question="무료배달 비용은 소비자·점주·플랫폼 중 누가 내고 있나?",
            reason=(
                "무료배달은 소비자에게는 혜택처럼 보이지만, 실제 비용이 플랫폼·점주·배달노동자 사이에서 어떻게 나뉘는지 보면 생활경제 소재가 됩니다. "
                f"{source}은 업주 부담 논쟁을 보여주는 출발점이고, 이 주제는 앱 경제의 성장 비용을 누가 내는지 묻는 이야기로 키울 수 있습니다."
            ),
            next_step="수수료율, 배달비 보조 구조, 자영업자 매출/마진 자료를 붙여 단일 업체 공방이 아니라 플랫폼 비용 배분 구조로 설명하는 것",
        )
    if "양파" in text:
        return _question_first_description(
            question="양파가 너무 많으면 정부는 가격을 어디까지 떠받쳐야 하나?",
            reason=(
                "정책브리핑 보도자료지만 생활경제 seed로 살릴 여지가 있습니다. "
                "양파 소비촉진 행사는 작은 행사처럼 보이지만, 농산물은 생산량이 조금만 흔들려도 산지 가격·도매 가격·마트 가격·농가 소득·정부 개입이 한꺼번에 움직입니다."
            ),
            next_step="최근 양파 산지 가격, 평년 대비 생산량, 소비촉진 예산, 농민과 소비자의 이해관계가 갈리는 지점을 붙여 '농산물 가격은 시장인가 정책인가'로 키울 수 있는지 보는 것",
        )
    if _has_energy_support_signal(text):
        return _question_first_description(
            question="유가가 오르면 정부 지원은 어디까지 생활비를 막아줄 수 있나?",
            reason=(
                "공식 현황 자료라 단독 seed보다는 에너지 가격 충격을 설명하는 근거로 쓰기 좋습니다. "
                "유가가 오르면 물류비·농어민 비용·지방재정 보조가 어떻게 이어지는지 보여줄 수 있고, 지원금 신청/지급 현황은 그 충격이 실제 행정으로 내려온 흔적입니다."
            ),
            next_step="유가 차트, 대상 업종, 지급 규모, 소비자 물가로 이어지는 경로를 붙이는 것",
            verdict="단독 후보보다는 에너지 가격 충격 기획의 evidence로 두는 편이 안전합니다",
        )
    if _has_any(text, ("spacex", "starship", "스타십")):
        return _question_first_description(
            question="민간 우주기업이 국가급 인프라가 되면 돈·허가·환경 갈등은 누가 감당하나?",
            reason=(
                "이 후보는 '스페이스X가 상장하나?'보다, 민간 우주기업이 국가급 인프라가 될 때 돈·허가·환경 갈등이 동시에 커지는 사례로 보는 편이 좋습니다. "
                "스타십 시험발사와 상장 기대는 자금조달 이야기이고, 발사장 주변 환경 비판은 우주산업이 더 이상 낭만적 기술 서사가 아니라 지역사회·규제 문제라는 신호입니다."
            ),
            next_step="발사 실패/성공 타임라인, 텍사스 발사장 환경 쟁점, NASA/미국 정부 의존도, 한국 우주산업과의 거리감을 같이 붙이는 것",
        )
    if _has_any(text, ("반바지", "cool biz", "쿨비즈", "스노우피크")):
        return _question_first_description(
            question="폭염이 심해지면 회사 복장 규칙도 복지가 될 수 있나?",
            reason=(
                "원문은 신제품/핫템 기사라 단독으로는 홍보성 리스크가 큽니다. "
                "그래도 후보로 남긴 이유는 '반바지'가 폭염, 전력수요, 냉방비, 직장 복장문화, 일본 Cool Biz 같은 생활경제 이야기로 확장될 수 있기 때문입니다."
            ),
            next_step="기상청 폭염 데이터, 전력 피크, 기업 복장 규정 사례를 붙여 생활 변화 소재로 살아나는지 확인하는 것",
            verdict="좋은 seed라기보다 약한 hook 검사용이며 자료가 붙지 않으면 reject하는 편이 맞습니다",
        )
    if _has_any(text, ("열사병", "불볕더위", "산업현장", "작업중지권")) and "폭염" in text:
        return _question_first_description(
            question="폭염이 심해지면 현장 노동의 규칙은 어디까지 바뀌어야 하나?",
            reason=(
                "원문은 일본의 역대급 불볕더위와 산업현장 열사병 대책을 다룬 기사입니다. "
                "사무실 복장문화보다, 폭염이 산재 예방 의무·작업 시간 조정·휴식과 냉방 설비·기업 책임을 어떻게 바꾸는지 보는 편이 원문에 맞습니다."
            ),
            next_step="일본의 열사병 통계, 산업현장 규제, 한국의 폭염 산재 인정 사례와 작업중지권 논의를 붙이는 것",
            verdict="생활 hook은 있지만 단독 seed보다는 노동안전/기후적응 자료가 붙을 때 살아나는 후보입니다",
        )
    if _has_any(text, ("개발제한구역", "그린벨트", "greenbelt")):
        return _question_first_description(
            question="도시를 위해 누가 비용을 부담하는가?",
            reason=(
                "지역 기사지만, 개발제한구역이라는 오래된 토지 규제가 실제 주민 생활비 보조로 이어진다는 점이 흥미롭습니다. "
                "그린벨트는 도시 확산을 막는 공익 규제인 동시에, 그 안에 사는 사람에게는 재산권·생활 편의·노후 주택 문제를 만드는 제도입니다."
            ),
            next_step="대상 가구 수, 지원 금액, 그린벨트 면적 지도, 재산권과 공익 규제의 충돌 사례를 붙이는 것",
        )
    if _has_any(text, ("글로벌 pf", "project finance", "메가뱅크")):
        return _question_first_description(
            question="돈이 비싼 시대에 미국 제조업과 인프라를 밀어줄 남은 큰손은 누구인가?",
            reason=(
                "이 후보는 단순 금융시장 뉴스가 아니라, 전 세계 인프라·에너지·데이터센터 같은 대형 프로젝트가 어떤 은행 돈으로 굴러가는지 보여주는 소재입니다. "
                "글로벌 PF 대출이 5년 새 두 배가 되고 일본 메가뱅크가 큰손으로 부상했다면, 저금리 이후 일본 금융기관의 해외 수익 추구와 글로벌 인프라 투자 붐을 함께 설명할 수 있습니다."
            ),
            next_step="국가/섹터별 PF 증가, 부실 위험, 미국 제조업 부흥과 데이터센터 전력 투자, 한국 은행·건설사와의 연결고리를 확인하는 것",
            verdict="일본 메가뱅크 자체보다 '돈이 비싼 시대의 프로젝트 자금'으로 초점을 옮겨야 투자 조언처럼 보이지 않습니다",
        )
    if _has_any(text, ("항모", "스텔스기", "carrier")) and "중" in text:
        return _question_first_description(
            question="중국 항모 전력이 스텔스기 운용 단계로 가면 동아시아 바다는 어떻게 달라지나?",
            reason=(
                "이 후보는 무기 스펙 뉴스로만 보면 군사 매니아 소재에 그칠 수 있지만, 중국 항모 전력이 스텔스기 운용 체계로 가는 신호라면 동아시아 해군력 변화 이야기로 커질 수 있습니다. "
                "한국 시청자에게는 대만해협, 남중국해, 미중 항모 운용 차이, 한국 해상교통로와 연결해야 의미가 생깁니다."
            ),
            next_step="실제 배치 단계인지 추정/선전인지 구분하고, 항모 위치 지도와 함재기 비교표로 설명 가능한지 확인하는 것",
        )
    if _has_any(text, ("taunting and degrading civilians", "degrading civilians")):
        return _question_first_description(
            question="전쟁 중 모욕과 조롱도 왜 국제법 문제가 되나?",
            reason=(
                "이 후보는 전쟁 피해를 사망자 수나 영토 변화가 아니라 '인간의 존엄'과 정보전 관점에서 설명할 수 있다는 점이 흥미롭습니다. "
                "휴대폰 영상과 SNS가 전장을 실시간으로 퍼뜨리면서, 민간인을 조롱하거나 모욕하는 행위도 선전·공포·전쟁범죄 논쟁으로 이어집니다."
            ),
            next_step="실제 사례, 국제법 조항, 최근 분쟁의 미디어 확산 구조를 붙여 설명형 소재가 되는지 확인하는 것",
            verdict="단독 seed로 쓰기엔 무겁고 추상적이어서 보강 자료가 없으면 낮추는 편이 안전합니다",
        )
    return None


def _fallback_description(
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
    *,
    related_titles: str,
    history_status: str,
) -> str:
    source = _source_cue(candidate)
    bundle_type = str(record.get("bundle_type") or "")
    question = _fallback_question(record, candidate, candidate_title)
    if bundle_type == "evidence_cluster":
        opening = (
            f"{source}은 단독 주제보다는 큰 이야기에 붙일 근거 자료로 보는 편이 안전합니다. "
            "회의·현황·지원 같은 공식자료는 숫자와 정책 근거를 확인해주는 역할을 할 때 가치가 커집니다."
        )
    else:
        opening = (
            f"{source}에서 출발한 후보로, 오늘 후보군 안에서는 이야기로 키울 여지가 있어 보입니다. "
            "다만 기사 하나만으로 결론을 내리기보다 생활 영향, 구조적 배경, 반대 근거를 붙여야 방송 소재인지 판단할 수 있습니다."
        )
    return _question_first_description(
        question=question,
        reason=opening,
        next_step=_fallback_need_sentence(
            record=record,
            candidate=candidate,
            related_titles=related_titles,
            history_status=history_status,
        ),
    )


def strip_internal_labels(value: str) -> str:
    text = value
    for label in INTERNAL_LABEL_PATTERNS:
        text = text.replace(label, "")
    return re.sub(r"\s+", " ", text).strip()


def build_review_board_copy(
    *,
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
    related_titles: str,
    history_status: str,
) -> ReviewBoardCopy:
    title = review_board_title(record, candidate, candidate_title)
    templated = _template_description(
        record,
        candidate,
        candidate_title,
        related_titles=related_titles,
        history_status=history_status,
    )
    if templated:
        history = _history_sentence(history_status)
        description = f"{templated} {history}".strip()
    else:
        description = _fallback_description(
            record,
            candidate,
            candidate_title,
            related_titles=related_titles,
            history_status=history_status,
        )
    return ReviewBoardCopy(
        title=strip_internal_labels(title),
        description=strip_internal_labels(description),
    )
