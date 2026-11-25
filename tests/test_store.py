from supplysense import store


def test_roundtrip_is_deterministic(tmp_path):
    recs = {
        "b": {
            "id": "b",
            "fuente": "cfe",
            "publicado": "2026-11-02T10:00:00",
            "titulo": "B",
            "vacio": None,
        },
        "a": {"id": "a", "fuente": "cfe", "publicado": "2026-11-01", "titulo": "A"},
        "c": {"id": "c", "fuente": "cfe", "titulo": "sin fecha"},
    }
    changed = store.save("procedimientos", recs, tmp_path)
    assert changed == ["procedimientos/2026/2026-11.jsonl", "procedimientos/sin-fecha.jsonl"]
    assert store.save("procedimientos", recs, tmp_path) == []
    loaded = store.load("procedimientos", tmp_path)
    assert set(loaded) == {"a", "b", "c"}
    assert "vacio" not in loaded["b"]
    text = (tmp_path / "procedimientos/2026/2026-11.jsonl").read_text(encoding="utf-8")
    assert text.index('"id":"a"') < text.index('"id":"b"')


def test_empty_partitions_are_removed(tmp_path):
    store.save("procedimientos", {"a": {"id": "a", "publicado": "2025-01-01"}}, tmp_path)
    changed = store.save("procedimientos", {"b": {"id": "b", "publicado": "2026-01-01"}}, tmp_path)
    assert any("borrado" in c for c in changed)
    assert set(store.load("procedimientos", tmp_path)) == {"b"}


def test_seen_index_roundtrip(tmp_path):
    seen = {"cmx:E-1": "2026-11-25", "cmx:E-2": "2026-10-01", "cmx:c:3": "2026-11-02"}
    changed = store.save_seen(seen, tmp_path)
    assert changed == ["vistos/2026-10.tsv", "vistos/2026-11.tsv"]
    assert store.load_seen(tmp_path) == seen
    assert store.save_seen(seen, tmp_path) == []
