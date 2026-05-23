# Google Sheet `jibi 후보` Schema

작성일: 2026-05-17  
업데이트: 2026-05-22  
상태: Jibi MVP staging schema + bundle review board

## 1. 설계 변경

기존 계획:

```text
jibi → 기존 `주제 찾기` 탭에 직접 append
```

수정 계획:

```text
jibi → 새 시트 `jibi 후보`에 append
사람 검토 → 필요 시 `주제 찾기`로 promote
```

## 2. 이유

- 사람 row와 bot row가 섞이지 않는다.
- 봇 전용 metadata 컬럼을 자유롭게 둔다.
- append-only 운영이 쉽다.
- overwrite 방지가 쉽다.
- 사람이 `review_result=promote`한 후보만 기존 `주제 찾기`로 이동할 수 있다.

## 3. Sheet Name

추천:

```text
jibi 후보
```

대안:

```text
jibi 수집
Luddite 후보
```

## 4. Column Schema

The first 25 columns intentionally preserve the original MVP sheet order. New
slideability fields are appended after `notes` so old reviewed rows keep their
human-review cell meanings when row 1 is upgraded.

| column | type | 설명 |
|---|---|---|
| `digest_date` | date | digest 기준일 |
| `collected_at` | datetime | 최초 수집 시각 |
| `last_seen_at` | datetime | 마지막 재등장 시각 |
| `jibi_id` | string | stable candidate id |
| `duplicate_key` | string | dedupe key |
| `source_url_canonical` | string | canonical URL |
| `rank` | int | 해당 digest 순위 |
| `status` | string | 기본 `new` |
| `주제명` | string | 사람이 보는 제목 |
| `링크` | url | 대표 링크 |
| `출처` | string | Reuters/AP/FT/연합 등 |
| `source_type` | string | rss/manual/subscription_manual/etc |
| `jibi_grade` | string | A/B/C/D |
| `total_score` | number | rule-based score |
| `recommended_action` | string | send/gather/editorial/keep/reject |
| `risk_level` | string | low/medium/high |
| `risk_flags` | string | comma-separated |
| `why_interesting` | text | 2~3줄 설명 |
| `possible_expansions` | text | bullet 또는 `;` 구분 |
| `evidence_needed` | text | 추가 자료 |
| `중복후보` | string | duplicate_of candidate id |
| `reviewer` | string | 검토자 |
| `review_result` | string | blank/keep/promote/etc |
| `promoted_to_topic_finding` | bool/string | 승격 여부 |
| `notes` | text | 사람이 남기는 메모 |
| `slideability_score` | number/string | 첫 화면/증거물로 보여주기 쉬운 정도 |
| `slideability` | string | visualizability와 대표 proof object 요약 |
| `first_slide_idea` | text | 첫 장면 아이디어 |
| `likely_proof_object_types` | text | diagram/chart/source_card 등 |
| `visual_risks` | text | 시각화 또는 출처 리스크 |

## 5. review_result Enum

```text
blank
keep
promote
needs_more_evidence
editorial_review
reject
```

## 6. Append Rules

```text
- jibi는 append-only
- 사람 row overwrite 금지
- 기존 `주제 찾기` 탭 직접 수정 금지
- duplicate_key 또는 source_url_canonical이 이미 있으면 1.0에서는 append skip
- last_seen_at update는 overwrite 위험이 있으므로 1.0에서는 하지 않음
```

1.0 정책:

```text
append-only 유지
중복이면 skipped_duplicates report에 기록
기존 row update/delete 금지
```

1.0 이후:

```text
같은 duplicate_key가 7일 이내 재등장하면 last_seen_at/update_count만 업데이트
```

## 6.1 Authentication and First Run

1.0 기본 인증 방식은 service account다.

```text
- service account email을 공유 Google Sheet editor로 추가
- service account JSON은 git에 넣지 않음
- 커밋되는 config는 config/google_sheets.example.yaml placeholder만 사용
- 실제 spreadsheet id와 credential path는 env 또는 gitignored config/google_sheets.local.yaml에 둠
- LUDDITE_GOOGLE_SPREADSHEET_ID, LUDDITE_GOOGLE_TARGET_SHEET="jibi 후보" 사용
- GOOGLE_APPLICATION_CREDENTIALS 또는 LUDDITE_GOOGLE_SERVICE_ACCOUNT_JSON로 key 경로 지정
- OAuth는 service account 초대가 어려울 때의 fallback
```

첫 실제 실행은 아래 순서로 한다.

```text
dry-run -> 1~2 row test CSV append -> full preview append -> same preview duplicate rerun
```

테스트 row 확인 전에는 full preview를 append하지 않는다.

## 7. Styling

jibi row는 시각적으로 구분한다.

예:

```text
- header frozen
- jibi rows light blue/gray background
- source_type/subscription rows light yellow
- high risk rows light red
- editorial_review rows orange
```

## 8. Visible Sheet Restrictions

Visible sheet에는 넣지 않는다.

```text
- 구독 기사 원문 전문
- 내부 계정/비밀번호/메일
- 광고주 민감 정보
- 미공개 내부 회의 내용
```

넣을 수 있는 것:

```text
- 링크
- 제목
- 짧은 요약
- why_interesting
- risk_flags
- recommended_action
```

## 9. Promotion Flow

미래 설계:

```text
jibi 후보 row
→ 사람이 review_result=promote
→ promote script가 `주제 찾기`에 복사
→ promoted_to_topic_finding = TRUE
→ promoted_at 기록
```

아직 구현하지 않는다.

## 10. CSV Preview

`outputs/daily_digest/YYYY-MM-DD_sheet_append_preview.csv`는 `jibi 후보` 시트 컬럼과 동일하게 만든다.

Rejected item은 기본 preview에 넣지 않는다. 필요하면 나중에 별도
`rejected_preview.csv`를 설계한다.

## 11. Bundle Review Board Mode

리서치팀 평가 단계에서는 같은 `jibi 후보` 탭을 후보 행 append 화면이 아니라
그날의 스토리 번들 리뷰 보드로 쓸 수 있다. 새 도구나 새 공유 문서를 만들지
않기 위한 운영 모드다.

렌더러는 일반 후보 append CSV와 함께 아래 파일을 만든다.

```text
outputs/daily_digest/YYYY-MM-DD_bundle_review_sheet.csv
```

이 CSV는 `bundle_review` 스키마를 사용한다.

사람이 보기 쉽도록 visible schema는 13개 컬럼만 둔다.

| column | 설명 |
|---|---|
| `순번` | 리뷰 보드 순위 |
| `구분` | `bundle`, `묶인 후보`, `근거 후보` |
| `검토대상` | 사람이 먼저 판단할 이야기 묶음 |
| `후보` | 대표 또는 하위 후보 제목 |
| `출처` | 대표 또는 하위 후보 출처 |
| `링크` | 대표 또는 하위 후보 링크 |
| `Jibi판정` | bundle/storyline/action 판정을 한 칸으로 요약 |
| `왜_이렇게_올렸나` | 왜 단독 seed, 묶인 후보, evidence인지 한 문장 |
| `같이볼것` | 함께 볼 supporting/evidence 또는 상위 묶음 |
| `review_result` | 사람이 남기는 결론 |
| `research_team_note` | 한 줄 평가 |
| `reviewer` | 검토자 |
| `review_item_id` | 추후 회수/분석용 id |

Top10 후보가 bundle로 접히면서 별도 행에서 사라지는 일을 피하기 위해
supporting/evidence 하위 후보도 별도 행으로 올린다. 이 행들은 탈락이 아니라
`묶인 후보` 또는 `근거 후보`로 표시해 “단독 후보가 아닌 판단이 맞았는지”를
검토받는다.

실제 공유 시트에 반영할 때는 append가 아니라 replace를 권장한다. 기존
`jibi 후보` 내용은 운영 실험 중 중요하지 않다고 보고, 매 run마다 최신 리뷰
보드만 보이게 하는 방식이다.

```bash
PYTHONPATH=src .venv/bin/python -m luddite append-jibi-sheet \
  --preview-csv outputs/daily_digest/YYYY-MM-DD_bundle_review_sheet.csv \
  --schema bundle_review \
  --replace-existing \
  --dry-run
```

실제 반영:

```bash
JIBI_SHEET_SCHEMA=bundle_review JIBI_APPEND_MODE=staging_replace make jibi-manual-update
```
