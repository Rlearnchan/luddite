# Jibi Selection Architecture Cleanup + Anny Handoff v0

2026-05-28 운영 메모.

- 이번 정리는 LLM production selection 도입이 아니라, 기존 Jibi 보드 선별 책임을 board scoring, topic diversity, story angle, board selection, Anny handoff 계약으로 분리하는 구조 정리다.
- Google Sheet visible columns와 replace 흐름은 유지한다. 새 정보는 metadata/report/handoff JSON에만 추가한다.
- Anny handoff는 `jibi_anny_seed_v0` 스키마의 report-only 계약이며, 다음 PR에서 LLM Story Angle Advisor를 붙일 수 있는 입력/출력 표면으로 사용한다.
- `recommended_visible_board_size`는 운영 판단용 report-only 값이다. 이번 단계에서는 고정 10개 보드 행 수를 직접 줄이지 않는다.
