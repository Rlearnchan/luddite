# 01. Corpus & Access Map

작성일: 2026-05-16
상태: v0.1 draft

## 1. 목적

이 문서는 Luddite가 참조할 수 있는 자료의 위치, 접근 방식, 파싱 방식, 주의점을 정리한다. Codex는 이 문서를 기준으로 parser와 manifest builder를 구현한다.

## 2. 전체 자료 지도

| Corpus | 위치 | 현재 접근 | 주 용도 |
|---|---|---:|---|
| Google Sheet `슈카월드_리서치의 사본` | Google Drive | 가능 | jibi 기준 데이터, 리서치 가이드 |
| Notion `Luddite` | Notion | 가능 | 프로젝트 초안 |
| Notion `Sketch 보기` DB | Notion | 가능 | anny/jibi 정답 사례, 채택/방송 링크 |
| 최신 PPT 8개 | Drive `20260517 방송용 (직원)`, 로컬 `./data/ppt` | 가능 | golden set, piti 규격 추출 |
| 과거 PPT | Drive 과거 자료 폴더 | 목록/raw 가능 | legacy pattern, 작성자별 스타일 |
| Storyline RTF 43개 | `storyline.zip`, 로컬 `./data/storylines` | 가능 | anny 초안 사고방식 학습 |
| 리서치 인수인계 | Google Sheet | 가능 | 금칙/선호/참고 사이트, 보안 주의 |

## 3. Google Sheet

확인된 스프레드시트 정보:

- 제목: `슈카월드_리서치의 사본`
- timezone: `Asia/Seoul`
- 주요 시트:
  - `주제 찾기`
  - `작업 현황`
  - `방송 주제`
  - `쇼츠 제작`
  - `리서치 인수인계`
  - `슈카월드 채널`

### 3.1 `주제 찾기`

초기 확인 결과 앞쪽 컬럼은 다음 구조에 가깝다.

| 컬럼 | 의미 |
|---|---|
| 제목 | 후보 주제명 |
| 링크 | seed URL |
| 제작 여부 | PPT/스토리 제작 여부 |
| 방송 활용 여부 | 실제 방송 활용 여부 |
| 이유 | 채택/사용/미사용 이유 |

사용 방식:

- `jibi`의 positive/negative example로 사용한다.
- `제작 O / 방송 O`: 좋은 seed 후보
- `제작 O / 방송 X`: 만들었지만 최종 탈락한 사례. 매우 중요하다.
- `제작 X`: 수집은 되었으나 확장성/위험/시의성/흥미 부족 가능성이 있는 사례다.

### 3.2 `리서치 인수인계`

포함 내용:

- 리서치팀 가이드라인
- 기피 주제
- 선호 주제
- 참고 사이트
- 이미지 사용 주의사항
- BDC 제작 방식
- 참고 영상 목록

보안 주의:

- 계정, 비밀번호, 내부 연락처 등 민감정보가 포함되어 있다.
- 이 시트는 절대 통째로 LLM prompt에 넣지 않는다.
- parser는 기본적으로 redaction을 수행해야 한다.

필수 redaction pattern:

```text
아이디 / ID / 계정 / 비번 / PW / 비밀번호 / 전화번호 / 메일 / 인증 담당자
```

### 3.3 `방송 주제`, `슈카월드 채널`

추후 해야 할 일:

- seed 제목과 최종 영상 제목의 변환 패턴 분석
- 방송화된 주제군 분류
- 조회수/성과 데이터가 있다면 topic-success correlation 확인

## 4. Notion

### 4.1 Luddite 초안

역할:

- 프로젝트의 원래 문제의식 확인
- `jibi`, `anny`, `piti` 이름과 역할의 source

### 4.2 `Sketch 보기` DB

확인된 주요 속성:

| 속성 | 의미 |
|---|---|
| `제목` | sketch 제목 |
| `제작` | 제작일 |
| `방송` | 방송 링크 |
| `상태` | 추천/미사용 등 |
| `파일` | 관련 파일 relation |
| `채택여부` | 선택 여부 |

사용 방식:

- `anny`의 storyline reference로 사용
- `jibi`의 채택 사례 분석에 사용
- 방송 링크가 있는 항목은 실제 사용된 정답 사례로 취급

추후 읽을 것:

- 최근 50~100개 Sketch 항목
- `상태=추천` 항목
- `방송` 컬럼이 있는 항목
- `파일` relation이 있는 항목
- BDC 항목

## 5. 최신 PPT 8개

위치:

```text
Google Drive/20260517 방송용 (직원)
로컬 ./data/ppt
```

파일 목록:

| 파일 | 슬라이드 수 | 주 용도 |
|---|---:|---|
| `국민도 주주가 되는가_배형찬.pptx` | 114 | 대형 정책/시장 이슈 |
| `대혼돈의 영국_김동찬 김성원.pptx` | 99 | 해외정치 + 지역경제 |
| `미중 정상회담_김동찬.pptx` | 92 | 지정학 프리퀄 |
| `요즘 뜨는 레이저 치료_김동찬.pptx` | 85 | 방산기술 + 말장난 회수 |
| `슈승님의 은혜_김동찬.pptx` | 79 | 내부 밈 + 사회 변화 |
| `여름에 회사에서 반바지 입어도 되나요_김동찬.pptx` | 75 | 날씨 + 직장문화 |
| `전당포 주식회사_배형찬.pptx` | 55 | 해외기업 + 신흥국 금융 |
| `코카콜라를 이기는 방법_김성원.pptx` | 55 | 이색동물 + 인도 재벌/소비재 |

파싱 포인트:

- visible text
- speaker notes
- notes 내 `[내용]`, `[내용 2]`, `[이미지]`
- URL domain
- slide count
- section title slide
- media count
- 첫 슬라이드/마지막 슬라이드

중요 발견:

- 최신 PPT는 Google Drive fetch로 텍스트 추출 가능하다.
- Google Slides API의 native presentation endpoint는 Office `.pptx`에 대해 실패할 수 있다.
- 로컬에서는 `.pptx` 파일 내부 XML을 읽어 notes와 media를 추출하는 방식이 안정적이다.

## 6. 과거 PPT

Drive 과거 폴더는 파일 목록과 raw 다운로드가 가능하다. 일부 파일은 MIME type이 `application/haansoftpptx`로 잡혀 즉시 텍스트 fetch가 실패할 수 있다.

구현 방침:

1. Drive API로 raw 다운로드
2. 로컬에 저장
3. `python-pptx` + OOXML 직접 파싱 병행
4. 실패 파일은 LibreOffice 변환 시도
5. 변환 실패 시 manifest에 `parse_status=failed` 기록

## 7. Storyline RTF

`storyline.zip`에는 RTF storyline 43개가 있다. 이 자료는 `anny`의 핵심 reference다.

추출할 필드:

- file name
- normalized title
- plain text
- URL list
- estimated sections
- source density
- seed type 추정
- 한국 연결 여부
- punchline 여부

주의:

- 일부 파일은 `무제 XX` 제목이다.
- 일부 URL에는 tracking parameter가 섞여 있다.
- URL canonicalization이 필요하다.

## 8. Corpus manifest 설계

모든 원천 자료는 하나의 manifest에 등록한다.

```json
{
  "corpus_id": "ppt_latest_20260517_pawn_company",
  "kind": "pptx",
  "title": "전당포 주식회사_배형찬",
  "path": "data/ppt/전당포 주식회사_배형찬.pptx",
  "source": "google_drive",
  "access_method": "raw_download",
  "parse_status": "parsed",
  "created_at": "2026-05-14T01:45:49Z",
  "modified_at": "2026-05-14T01:45:58Z",
  "notes": "latest golden set"
}
```

## 9. 다음 작업

- `fetch_sheets.py`: Sheet → csv/jsonl, redaction 포함
- `parse_storylines.py`: RTF/text → parsed_storylines.jsonl
- `parse_pptx.py`: PPTX → parsed_latest_ppts.jsonl
- `build_corpus_manifest.py`: Drive/Notion/local 자료 manifest화
