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


def _has_tokenization_signal(text: str) -> bool:
    return (
        "토큰화" in text
        or "tokenization" in text
        or bool(re.search(r"\brwa\b", text, flags=re.IGNORECASE))
    )


def review_board_title(
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
) -> str:
    raw_title = str(record.get("bundle_title") or candidate_title or candidate.get("title") or "")
    text = _copy_text(record, candidate, candidate_title)
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
    if _has_any(text, ("무료배달", "배달비", "수수료", "플랫폼")):
        return "무료배달은 누가 내나: 배달앱 수수료와 업주 부담"
    if "양파" in text:
        return "양파가 너무 많으면 정부는 무엇을 하나"
    if _has_any(text, ("고유가", "유가", "피해지원금", "지원금")):
        return "고유가 지원금 현황으로 보는 에너지 가격 충격"
    if _has_any(text, ("spacex", "starship", "스타십")):
        return "스페이스X 스타십: 민간 우주개발의 돈과 환경 갈등"
    if _has_any(text, ("반바지", "cool biz", "쿨비즈", "스노우피크")):
        return "반바지가 복지가 되는 시대: 폭염과 회사 복장문화"
    if _has_any(text, ("개발제한구역", "그린벨트", "greenbelt")):
        return "그린벨트에 사는 사람들은 왜 생활비 보조를 받나"
    if _has_any(text, ("글로벌 pf", "project finance", "메가뱅크")):
        return "글로벌 PF 대출 5년새 2배: 일본 메가뱅크는 왜 큰손이 됐나"
    if _has_any(text, ("항모", "스텔스기", "carrier")) and "중" in text:
        return "중국 항모 3척과 스텔스기: 해군력이 바뀌는 신호인가"
    if _has_any(text, ("taunting and degrading civilians", "degrading civilians")):
        return "전쟁 중 모욕과 조롱도 왜 국제법 문제가 되나"
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
    text = _copy_text(record, candidate, candidate_title)
    story_role = str(candidate.get("story_role") or record.get("story_role") or "")
    source_role = str(candidate.get("source_role_class") or record.get("source_role") or "")
    if story_role in {"evidence_for_larger_story", "background_reference"}:
        return "이 자료는 어떤 큰 이야기의 근거로 붙일 때 가장 설득력이 있나?"
    if story_role == "seed_with_supporting_links":
        return "이 후보를 단독 주제로 만들려면 어떤 최신 뉴스와 두 번째 출처가 필요한가?"
    if source_role == "research_note":
        return "이 연구자료를 오늘의 생활경제 질문으로 바꾸려면 어디를 좁혀야 하나?"
    if _has_any(text, ("ai", "인공지능")):
        return "AI가 실제 조직 안으로 들어올 때 효율과 책임은 어떻게 나뉘나?"
    if _has_any(text, ("규제", "지원", "정책", "보조")):
        return "이 정책은 누구의 비용을 줄이고 누구에게 새 부담을 넘기나?"
    if _has_any(text, ("가격", "물가", "요금", "수수료", "금리")):
        return "이 가격 변화는 시청자의 지갑과 어떤 경로로 연결되나?"
    return "이 후보를 방송 소재로 만들려면 어떤 한 가지 질문으로 좁혀야 하나?"


def _template_description(
    record: dict[str, Any],
    candidate: dict[str, Any],
    candidate_title: str,
    *,
    related_titles: str,
    history_status: str,
) -> str | None:
    text = _copy_text(record, candidate, candidate_title)
    source = _source_cue(candidate)
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
    if _has_any(text, ("무료배달", "배달비", "수수료", "플랫폼")):
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
    if _has_any(text, ("고유가", "유가", "피해지원금", "지원금")):
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
