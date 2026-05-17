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
