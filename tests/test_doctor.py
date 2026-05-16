from luddite.doctor import collect_checks, collect_corpus_checks


def test_doctor_checks_pass_without_raw_corpus_requirement() -> None:
    failed = [check for check in collect_checks() if not check.ok]
    assert failed == []


def test_corpus_checks_are_separate() -> None:
    names = {check.name for check in collect_checks()}
    corpus_names = {check.name for check in collect_corpus_checks()}

    assert not any(name.startswith("corpus:") for name in names)
    assert {"corpus:storylines", "corpus:latest_ppt", "corpus:sheets_raw_dir"} <= corpus_names
