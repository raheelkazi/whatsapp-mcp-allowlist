# whatsapp-mcp-server/tests/test_intelligence.py
import intelligence

ALLOW = {
    "111@s.whatsapp.net": {"label": "Mom", "mode": "read+send"},
    "222@g.us": {"label": "Work", "mode": "read"},
}


def _fetch(jid):
    return {"111@s.whatsapp.net": "Mom: did you call the plumber?",
            "222@g.us": ""}.get(jid, "")


def test_gather_skips_empty_and_scopes_to_allowlist():
    got = intelligence.gather(ALLOW, _fetch)
    assert got == {"111@s.whatsapp.net": "Mom: did you call the plumber?"}


def test_summarize_calls_generate_per_chat():
    calls = []
    def gen(system, user):
        calls.append(user)
        return "Asked about the plumber."
    out = intelligence.summarize(ALLOW, _fetch, gen)
    assert out == [{"chat_jid": "111@s.whatsapp.net", "label": "Mom",
                    "summary": "Asked about the plumber."}]
    assert "plumber" in calls[0]  # the chat text was passed to the model


def test_suggest_returns_drafts_from_model_json():
    def gen_json(system, user):
        return [{"draft": "Yes, called them this morning!"}]
    out = intelligence.suggest(ALLOW, _fetch, gen_json)
    assert out[0]["chat_jid"] == "111@s.whatsapp.net"
    assert out[0]["label"] == "Mom"
    assert out[0]["draft"] == "Yes, called them this morning!"


def test_reminders_passes_all_chat_text_and_returns_items():
    seen = {}
    def gen_json(system, user):
        seen["user"] = user
        return [{"kind": "unanswered", "text": "Reply to Mom about the plumber",
                 "related_chat_jid": "111@s.whatsapp.net", "suggested_action": "reply"}]
    out = intelligence.reminders(ALLOW, _fetch, gen_json)
    assert out[0]["kind"] == "unanswered"
    assert "Mom" in seen["user"]  # label included so the model can name the chat
