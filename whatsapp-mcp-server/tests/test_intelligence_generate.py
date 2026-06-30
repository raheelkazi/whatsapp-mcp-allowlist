import pytest
import intelligence


class FakeBlock:
    def __init__(self, text): self.type, self.text = "text", text


class FakeResp:
    def __init__(self, text): self.content = [FakeBlock(text)]


class FakeMessages:
    def __init__(self, text): self._text = text
    def create(self, **kw): return FakeResp(self._text)


class FakeClient:
    def __init__(self, text): self.messages = FakeMessages(text)


def test_generate_text_returns_model_text():
    gt, _ = intelligence.make_generators(FakeClient("A short summary."))
    assert gt("sys", "user") == "A short summary."


def test_generate_json_parses_fenced_json():
    gj_client = FakeClient('```json\n[{"draft": "hi"}]\n```')
    _, gj = intelligence.make_generators(gj_client)
    assert gj("sys", "user") == [{"draft": "hi"}]


def test_generate_json_bad_json_returns_empty_list():
    _, gj = intelligence.make_generators(FakeClient("not json at all"))
    assert gj("sys", "user") == []


def test_make_generators_without_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(intelligence.IntelligenceUnavailable):
        intelligence.make_generators()


def test_generate_json_bare_scalar_returns_empty_list():
    """A bare JSON scalar (e.g. 42) must not propagate — callers expect list|dict."""
    _, gj = intelligence.make_generators(FakeClient("42"))
    assert gj("sys", "user") == []


def test_generate_json_bare_string_returns_empty_list():
    """A bare JSON string (e.g. \"hi\") must return [] not the string itself."""
    _, gj = intelligence.make_generators(FakeClient('"hi"'))
    assert gj("sys", "user") == []


def test_generate_json_bare_bool_returns_empty_list():
    """A bare JSON boolean must return [] not the bool."""
    _, gj = intelligence.make_generators(FakeClient("true"))
    assert gj("sys", "user") == []
