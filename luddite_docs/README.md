# Luddite Internal Docs v0.1

작성일: 2026-05-16

이 문서 묶음은 슈카월드 리서치 업무 보조 에이전트 프로젝트 **Luddite**의 구현 전 기준 문서입니다. Codex가 `/Users/bae/Documents/code/luddite`에서 구현할 때 바로 참조할 수 있도록 Markdown과 JSON Schema 형태로 정리했습니다.

## 포함 문서

| 경로 | 용도 |
|---|---|
| `docs/00_project_charter.md` | 프로젝트 목표, 비목표, 성공 기준 |
| `docs/01_corpus_access_map.md` | 접근 가능한 자료와 로컬/Drive/Notion 처리 방식 |
| `docs/02_syuka_content_grammar.md` | 슈카월드식 콘텐츠 문법, seed → 방송 전개 공식 |
| `docs/03_jibi_seed_selection_playbook.md` | `jibi`의 자료 수집·선별 기준 |
| `docs/04_anny_storyline_playbook.md` | `anny`의 스토리라인 작성 기준 |
| `docs/05_piti_ppt_production_spec.md` | `piti`의 PPT 생성 규칙과 notes/source 처리 |
| `docs/06_data_contracts_pipeline_spec.md` | 단계별 데이터 계약과 파이프라인 |
| `docs/07_evaluation_golden_set.md` | 평가 기준과 golden set |
| `docs/08_source_copyright_security_policy.md` | 출처, 저작권, 민감정보 처리 원칙 |
| `docs/09_codex_implementation_brief.md` | Codex 구현용 단계별 작업지시서 |
| `docs/appendix/*.md` | Google Sheet, storyline, 최신 PPT 분석 부록 |
| `specs/*.json` | Codex가 사용할 JSON Schema 초안 |
| `prompts/*/*.md` | 추후 prompt 구현용 skeleton |

## 문서 사용 방식

1. Codex는 먼저 `docs/00_project_charter.md`, `docs/06_data_contracts_pipeline_spec.md`, `docs/09_codex_implementation_brief.md`를 읽는다.
2. Parser 구현은 `docs/01_corpus_access_map.md`와 `specs/*`를 기준으로 한다.
3. Agent 구현은 `docs/02~05`를 기준으로 한다.
4. 평가와 회귀 테스트는 `docs/07_evaluation_golden_set.md`와 `eval/golden_cases/`를 기준으로 한다.

## 현재 버전의 한계

- Google Sheet는 앞부분과 핵심 탭 구조를 확인한 기준으로 정리했다. 전체 행 전수 분석은 추후 필요하다.
- Notion Sketch DB는 접근 가능성을 확인했으나, 최근 50~100개 항목의 정량 분석은 추후 필요하다.
- 최신 PPT 8개는 정밀 분석의 1차 기준으로 삼았다.
- 과거 PPT는 raw 다운로드 후 로컬 파싱이 필요한 경우가 있어, 전체 패턴 분석은 구현 후 진행한다.
