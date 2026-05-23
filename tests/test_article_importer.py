import csv
import json

from luddite.collectors.manual_article_importer import import_articles


def test_import_articles_jsonl_deduplicates_urls(tmp_path) -> None:
    input_dir = tmp_path / "articles"
    input_dir.mkdir()
    output_path = tmp_path / "raw_articles.jsonl"
    report_path = tmp_path / "report.md"
    records = [
        {
            "title": "F88 pawnshop listing",
            "url": "https://example.com/a?utm_source=x",
            "source": "manual",
            "raw_summary": "Vietnam pawnshop listing",
            "tags": ["pawnshop"],
        },
        {
            "title": "Duplicate",
            "url": "https://example.com/a",
            "source": "manual",
        },
    ]
    (input_dir / "sample.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    articles, report = import_articles(
        input_dir=input_dir,
        output_path=output_path,
        report_path=report_path,
    )

    assert len(articles) == 1
    assert report.duplicates == 1
    assert articles[0]["url"] == "https://example.com/a"
    assert output_path.exists()
    assert "Duplicate URLs skipped: 1" in report_path.read_text(encoding="utf-8")


def test_import_articles_csv(tmp_path) -> None:
    input_dir = tmp_path / "articles"
    input_dir.mkdir()
    output_path = tmp_path / "raw_articles.jsonl"
    report_path = tmp_path / "report.md"
    with (input_dir / "sample.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["title", "url", "source", "tags"])
        writer.writeheader()
        writer.writerow(
            {
                "title": "Drone cost asymmetry",
                "url": "https://example.com/drone",
                "source": "manual",
                "tags": "drone,cost",
            }
        )

    articles, report = import_articles(
        input_dir=input_dir,
        output_path=output_path,
        report_path=report_path,
    )

    assert report.imported == 1
    assert articles[0]["tags"] == ["drone", "cost"]


def test_import_articles_input_file_ignores_other_inbox_files(tmp_path) -> None:
    input_dir = tmp_path / "articles"
    input_dir.mkdir()
    output_path = tmp_path / "raw_articles.jsonl"
    report_path = tmp_path / "report.md"
    today = input_dir / "rss_2026-05-23.jsonl"
    old = input_dir / "rss_2026-05-22.jsonl"
    today.write_text(
        json.dumps(
            {
                "title": "Today drone cost asymmetry",
                "url": "https://example.com/today",
                "source": "manual",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    old.write_text(
        json.dumps(
            {
                "title": "Old stale item",
                "url": "https://example.com/old",
                "source": "manual",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    articles, report = import_articles(
        input_dir=input_dir,
        input_files=[today],
        output_path=output_path,
        report_path=report_path,
    )

    assert report.input_mode == "input_file"
    assert report.input_files == 1
    assert [article["title"] for article in articles] == ["Today drone cost asymmetry"]
    report_text = report_path.read_text(encoding="utf-8")
    assert "Input mode: `input_file`" in report_text
    assert "Old stale item" not in output_path.read_text(encoding="utf-8")


def test_import_articles_preserves_cross_feed_source_metadata(tmp_path) -> None:
    input_dir = tmp_path / "articles"
    input_dir.mkdir()
    output_path = tmp_path / "raw_articles.jsonl"
    report_path = tmp_path / "report.md"
    record = {
        "title": "Same Yonhap story",
        "url": "https://www.yna.co.kr/view/AKR20260523000100001",
        "source": "연합뉴스 경제",
        "source_id": "yonhap_economy",
        "source_count": 2,
        "source_sections": ["economy", "industry"],
        "supporting_source_ids": ["yonhap_industry"],
        "tags": ["rss", "korea_business"],
    }
    (input_dir / "rss.jsonl").write_text(
        json.dumps(record, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    articles, report = import_articles(
        input_dir=input_dir,
        output_path=output_path,
        report_path=report_path,
    )

    assert report.imported == 1
    assert articles[0]["source_count"] == 2
    assert articles[0]["source_sections"] == ["economy", "industry"]
    assert articles[0]["supporting_source_ids"] == ["yonhap_industry"]
