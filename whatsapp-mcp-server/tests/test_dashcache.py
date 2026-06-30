import dashcache


def test_missing_file_returns_empty(tmp_path):
    assert dashcache.load(str(tmp_path / "nope.json")) == {}
    assert dashcache.get_section(str(tmp_path / "nope.json"), "summaries") is None


def test_put_then_get_roundtrips(tmp_path):
    path = str(tmp_path / "cache.json")
    stored = dashcache.put_section(path, "summaries", [{"chat_jid": "1", "summary": "x"}])
    assert stored["data"] == [{"chat_jid": "1", "summary": "x"}]
    assert "generated_at" in stored
    got = dashcache.get_section(path, "summaries")
    assert got["data"] == [{"chat_jid": "1", "summary": "x"}]


def test_put_merges_sections(tmp_path):
    path = str(tmp_path / "cache.json")
    dashcache.put_section(path, "summaries", [1])
    dashcache.put_section(path, "reminders", [2])
    assert dashcache.get_section(path, "summaries")["data"] == [1]
    assert dashcache.get_section(path, "reminders")["data"] == [2]


def test_clear_removes_all_sections(tmp_path):
    path = str(tmp_path / "cache.json")
    dashcache.put_section(path, "summaries", [1])
    dashcache.put_section(path, "reminders", [2])
    dashcache.clear(path)
    assert dashcache.load(path) == {}
    assert dashcache.get_section(path, "summaries") is None


def test_clear_missing_file_is_noop(tmp_path):
    dashcache.clear(str(tmp_path / "nope.json"))  # must not raise
