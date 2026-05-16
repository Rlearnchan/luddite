# Appendix. Legacy PPT Pattern Report

작성일: 2026-05-16
상태: v0.1 draft

## 1. 목적

과거 PPT는 최신 포맷만으로는 잡히지 않는 장기 스타일, 작성자별 차이, 주제별 문법을 보강하기 위한 corpus다.

## 2. 접근 상태

- Google Drive 과거 자료 폴더의 파일 목록은 접근 가능하다.
- 일부 파일은 `application/haansoftpptx`로 잡히며 즉시 텍스트 fetch가 실패할 수 있다.
- raw 다운로드 후 로컬에서 파싱해야 한다.

## 3. 대표 파일 예시

```text
배형찬_출산율.pptx
김성원_자체 핵무장 시대가 오는가.pptx
유상빈_미국이란 전쟁 임박.pptx
배형찬_전쟁AI.pptx
김성원_월 200으로는 성공할 수 없는가.pptx
김성원_미국 피자 업계 근황.pptx
김성원_관세 멸망전 뜨는 미국과 유럽.pptx
반도체 관세 tsmc 실적발표.pptx
관세판결_배형찬.pptx
외환시장_배형찬.pptx
```

## 4. 샘플링 전략

전수 분석보다 대표 샘플링이 먼저다.

```text
작성자별:
- 배형찬
- 김동찬
- 김성원
- 유상빈
- 김예중

주제별:
- 시장/금융
- 정치/지정학
- 생활문화
- 기업/산업
- 과학/기술
- 동물/이색
- BDC

분량별:
- 40~60장 중형
- 70~90장 표준형
- 100장 이상 대형
```

## 5. 분석할 질문

```text
1. 최신 PPT와 과거 PPT의 형식 차이는 무엇인가?
2. 작성자별 도입부/문장/농담 스타일 차이가 있는가?
3. 특정 주제군에 반복되는 section 구조가 있는가?
4. 출처 notes 방식이 언제부터 안정화됐는가?
5. BDC 또는 특수 자료는 일반 방송과 얼마나 다른가?
```

## 6. Codex 작업 항목

```text
[ ] legacy_drive_manifest.jsonl 생성
[ ] raw download script 작성
[ ] haansoftpptx 처리 fallback 조사
[ ] 대표 30~50개 parsing
[ ] 작성자/주제/분량별 summary report 생성
```
