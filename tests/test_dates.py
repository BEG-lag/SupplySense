from supplysense.dates import day_of, from_dmy, from_dotnet, from_local, from_utc_iso


def test_from_dotnet_converts_to_mexico_city():
    assert from_dotnet("/Date(1795623289860)/") == "2026-11-25T10:14:49"
    assert from_dotnet(None) is None


def test_from_utc_iso():
    assert from_utc_iso("2026-11-19T06:00:00Z") == "2026-11-19T00:00:00"


def test_from_local():
    assert from_local("2026-11-20 19:17:22") == "2026-11-20T19:17:22"
    assert from_local("2026-11-20") == "2026-11-20"
    assert from_local("20/11/2026") is None
    assert from_local("") is None


def test_from_dmy():
    assert from_dmy("04/12/2026 09:00 hrs") == "2026-12-04T09:00:00"
    assert from_dmy("04/12/2026") == "2026-12-04"
    assert from_dmy("31/02/2026") is None


def test_day_of():
    assert day_of("2026-11-25T10:00:00") == "2026-11-25"
    assert day_of(None) is None
