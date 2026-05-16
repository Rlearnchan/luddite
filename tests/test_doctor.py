from luddite.doctor import collect_checks


def test_doctor_checks_pass() -> None:
    failed = [check for check in collect_checks() if not check.ok]
    assert failed == []
