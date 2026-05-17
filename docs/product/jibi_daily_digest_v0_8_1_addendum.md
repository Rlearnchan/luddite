# jibi Daily Digest MVP v0.8.1 Addendum

## Updated priority

jibi is the first product priority.

PPT generation is long-term. The first useful demo is a daily topic digest.

## Usage

- Collect every day.
- Send or generate digest on weekdays by default.
- Allow on-demand query anytime.
- Store candidates in DB so anny can connect old and new evidence later.

## Human-facing candidate count

```text
Digest: 10 candidates
Stored daily candidates: 30-50
```

## Output channels

Preferred order:

1. Markdown report
2. Google Sheet append
3. Luddite Slack bot digest/query

## Ranking principles

User-stated priority:

```text
조회수 가능성
→ 자료의 풍부함
→ 숫자/통계의 강함
→ 엥? hook
→ 농담/밈 회수
→ 시의성
```

Implementation mapping:

```text
broadcast_potential_proxy
evidence_depth
numbers_strength
weird_hook
punchline_potential
timeliness
risk_penalty
```

## Absolute no-go

- direct evaluation of a specific party or president

## Editorial review

Most other sensitive topics are not always forbidden but must be escalated:

- Israel/Palestine
- praising Chinese companies
- domestic company investment framing
- medical efficacy claims
- sexual/sensitive topics
- entertainment/sports
- history
- crime/drugs
