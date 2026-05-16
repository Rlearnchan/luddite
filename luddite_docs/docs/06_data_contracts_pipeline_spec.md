# 06. Data Contracts & Pipeline Spec

작성일: 2026-05-16
상태: v0.1 draft

## 1. 목적

Luddite는 여러 에이전트가 이어지는 시스템이다. 각 단계 산출물의 형식을 고정하지 않으면 구현이 쉽게 흔들린다. 이 문서는 `jibi → anny → piti` 사이의 데이터 계약을 정의한다.

## 2. 전체 파이프라인

```text
source article / sheet / notion / ppt / storyline
  ↓
corpus_item
  ↓
jibi_candidate
  ↓
evidence_cluster
  ↓
anny_storyline
  ↓
piti_deck_plan
  ↓
pptx + generation_report
```

## 3. Corpus item

모든 원자료는 `corpus_item`으로 등록한다.

```json
{
  "corpus_id": "ppt_latest_20260517_pawn_company",
  "kind": "pptx",
  "title": "전당포 주식회사_배형찬",
  "source_system": "google_drive",
  "local_path": "data/ppt/전당포 주식회사_배형찬.pptx",
  "remote_url": "...",
  "created_at": "2026-05-14T01:45:49Z",
  "modified_at": "2026-05-14T01:45:58Z",
  "parse_status": "parsed",
  "metadata": {
    "slide_count": 55,
    "url_count": 75
  }
}
```

## 4. jibi_candidate

`jibi_candidate`는 기사나 자료 하나에서 시작한 방송 후보이다.

필수 필드:

- `candidate_id`
- `title`
- `seed_url`
- `source`
- `published_at`
- `summary`
- `seed_type`
- `why_interesting`
- `why_shuka`
- `possible_expansions`
- `korea_bridge`
- `scores`
- `risk_flags`

## 5. evidence_cluster

`evidence_cluster`는 storyline 작성에 필요한 근거 묶음이다.

```json
{
  "cluster_id": "f88_vietnam_pawn_lending",
  "candidate_id": "...",
  "core_claim": "F88은 베트남 전당대출 시장의 제도권화 사례다.",
  "evidence_items": [
    {
      "url": "...",
      "source": "Nikkei Asia",
      "kind": "article",
      "claim_supported": "F88 revenue and store growth",
      "reliability": "high",
      "notes": "seed article"
    }
  ],
  "missing_evidence": ["베트남 오토바이 보급률 공식 통계"],
  "risk_flags": []
}
```

## 6. anny_storyline

`anny_storyline`은 PPT로 바로 옮길 수 있는 slide-ready outline이다.

필수 구조:

```json
{
  "storyline_id": "...",
  "title": "...",
  "subtitle": "...",
  "one_liner": "...",
  "archetypes": ["..."],
  "estimated_slide_count": 55,
  "sections": [
    {
      "section_no": 1,
      "section_title": "...",
      "section_intent": "hook_and_proof",
      "slides": [
        {
          "slide_no": 1,
          "slide_type": "title",
          "headline": "...",
          "body": [],
          "source_urls": [],
          "image_urls": [],
          "speaker_notes": "",
          "needs_fact_check": false,
          "risk_flags": []
        }
      ]
    }
  ],
  "open_questions": [],
  "global_risk_flags": []
}
```

## 7. piti_deck_plan

`piti_deck_plan`은 PPT 생성 직전의 layout plan이다.

```json
{
  "deck_id": "...",
  "storyline_id": "...",
  "theme": "syuka_default_v0",
  "slides": [
    {
      "slide_no": 1,
      "slide_type": "title",
      "layout": "title_center",
      "headline": "...",
      "body": [],
      "notes": "...",
      "image_slots": [],
      "warnings": []
    }
  ],
  "generation_options": {
    "aspect_ratio": "16:9",
    "default_font": "Malgun Gothic",
    "default_body_pt": 28
  }
}
```

## 8. 상태 관리

### 8.1 Candidate status

```text
collected → shortlisted → researching → storyline_requested → drafted → deck_requested → deck_generated → reviewed → used/discarded
```

### 8.2 Parse status

```text
pending → parsed → partial → failed → needs_manual
```

## 9. URL canonicalization

모든 URL은 저장 전 정규화한다.

- `utm_*` 제거
- `fbclid`, `gclid` 제거
- trailing slash 정리
- fragment 제거. 단, 필요한 앵커는 보존 가능
- YouTube timestamp는 필요하면 별도 필드로 분리

```json
{
  "url": "https://example.com/article?utm_source=chatgpt.com",
  "canonical_url": "https://example.com/article",
  "removed_params": ["utm_source"]
}
```

## 10. Risk flags

공통 risk flag:

```text
politics
company_promo
company_attack
medical
legal
copyright_image
subscription_source
sensitive_group
insufficient_evidence
live_breaking_news
credential_leak
```

## 11. Storage proposal

```text
data/
  manifests/corpus_manifest.jsonl
  sheets/*.csv
  storylines/parsed_storylines.jsonl
  ppt/parsed_latest_ppts.jsonl
  notion/sketch_items.jsonl
  candidates/jibi_candidates.jsonl
  storylines/generated/*.json
  decks/plans/*.json
outputs/
  daily_digest/*.md
  decks/*.pptx
  reports/*.md
```

## 12. Validation

모든 JSON 산출물은 `specs/*.json`으로 validate한다.

검증 실패 시:

- 산출물 저장은 하되 `validation_status=failed`
- error report 생성
- downstream agent로 넘기지 않음
