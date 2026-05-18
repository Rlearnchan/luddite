# RSS Terms / Enablement Review

Date: 2026-05-18  
Milestone: 1.1.2  
Status: review gate before RSS item ingestion

## Purpose

`rss_verified` means a source passed technical fetch + parse probing. It does
not mean Luddite may run operational collection. Operational collection is
controlled separately by `collection_enabled`.

Default policy:

```text
rss_verified + terms_check_required=true + collection_enabled=false
```

Until terms and usage scope are reviewed, Luddite must not enable scheduled or
bulk collection for that source.

## Storage Policy

Allowed for future ingestion:

```text
source_id
source_name
title
url
source_url_canonical
published_at
short feed summary / excerpt when present in feed metadata
duplicate_key
collected_at
```

Not allowed by default:

```text
full article text
subscription article body
paywalled original text
large copied excerpts
images copied from source pages
```

Visible digest and Google Sheet output should use title, URL, source, timestamp,
and short human-facing summary only.

## Source Review

| source | verified_feed_url | terms_check_required | collection_enabled | recommendation | notes |
|---|---|---:|---:|---|---|
| BBC | `https://feeds.bbci.co.uk/news/rss.xml` | true | false | terms pending | Technical fetch+parse passed. Keep disabled until operational use is reviewed. |
| The Guardian | `https://www.theguardian.com/international/rss` | true | false | terms pending | Technical fetch+parse passed via HTML autodiscovery. Keep disabled until terms/use scope are reviewed. |
| NPR | `https://feeds.npr.org/1002/rss.xml` | true | false | terms pending | Technical fetch+parse passed via HTML autodiscovery. Keep disabled until operational use is reviewed. |
| Le Monde | `https://www.lemonde.fr/rss/une.xml` | true | false | keep disabled | RSS usage appears oriented toward personal/non-commercial/non-collective use; keep `collection_enabled=false` unless terms are explicitly cleared. |
| Atlas Obscura | `https://www.atlasobscura.com/feeds/latest` | true | false | terms pending | Technical fetch+parse passed. Good weird/culture hook source, but keep disabled until terms/use scope are reviewed. |

## Enablement Rules

A source can move to `collection_enabled=true` only when:

```text
1. verified_feed_url exists
2. terms_check_required is false, or review explicitly approves the usage
3. storage is limited to metadata and short feed summary
4. full article scraping remains disabled
5. source_url_canonical and duplicate_key generation are defined
6. operator updates config/rss_collection_allowlist.yaml intentionally
```

## 1.2 Readiness

Milestone 1.2 RSS item ingestion should not start until:

```text
- collection_enabled=true sources: at least 2-3
- terms_check_required sources are not enabled without review
- storage schema is metadata-first
- article full text storage remains forbidden by default
- source_url_canonical / duplicate_key are generated
- import-articles pipeline integration is designed
```

Still out of scope for 1.1.2:

```text
RSS item -> raw_articles ingestion
24/7 RSS collector
jibi digest automatic RSS connection
Google Sheet append scheduling
Slack bot
LLM API calls
syuka-ops DB integration
주제 찾기 promote automation
```
