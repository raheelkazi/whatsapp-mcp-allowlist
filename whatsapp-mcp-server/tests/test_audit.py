# whatsapp-mcp-server/tests/test_audit.py
import json
from audit import log_event, classify, audited


def test_log_event_writes_parseable_json_line(tmp_path):
    path = str(tmp_path / "audit.log")
    log_event({"tool": "send_message", "target": "111@s.whatsapp.net",
               "decision": "allowed", "reason": None}, path)
    lines = open(path).read().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["tool"] == "send_message"
    assert rec["decision"] == "allowed"
    assert "ts" in rec


def test_log_event_appends(tmp_path):
    path = str(tmp_path / "audit.log")
    log_event({"tool": "a"}, path)
    log_event({"tool": "b"}, path)
    assert len(open(path).read().splitlines()) == 2


def test_log_event_swallows_write_errors():
    # a non-existent directory would raise OSError; must be swallowed
    log_event({"tool": "x"}, "/no/such/dir/audit.log")  # must not raise


def test_classify_allowed_and_denied():
    assert classify({"data": 1}) == ("allowed", None)
    assert classify([1, 2, 3]) == ("allowed", None)
    assert classify("a string") == ("allowed", None)
    assert classify({"error": "999 is not in the allowlist."})[0] == "denied"
    assert classify({"error": "x not in the allowlist."})[1] == "not_in_allowlist"
    assert classify({"success": False, "message": "rate limited: hourly cap"})[1] == "rate_limited"
    assert classify({"success": False, "message": "sends disabled (read-only mode)"})[1] == "read_only_mode"
    assert classify({"success": False, "message": "222 is read-only"})[1] == "read_only"


def test_audited_logs_target_and_decision(tmp_path, monkeypatch):
    path = str(tmp_path / "audit.log")
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", path)

    @audited
    def send_message(recipient, message):
        return {"success": True, "message": "sent"}

    send_message("111@s.whatsapp.net", "hi")
    rec = json.loads(open(path).read().splitlines()[0])
    assert rec["tool"] == "send_message"
    assert rec["target"] == "111@s.whatsapp.net"
    assert rec["decision"] == "allowed"


def test_audited_records_denial(tmp_path, monkeypatch):
    path = str(tmp_path / "audit.log")
    monkeypatch.setenv("WHATSAPP_AUDIT_LOG", path)

    @audited
    def send_message(recipient, message):
        return {"success": False, "message": "rate limited: hourly cap reached"}

    send_message("111@s.whatsapp.net", "hi")
    rec = json.loads(open(path).read().splitlines()[0])
    assert rec["decision"] == "denied"
    assert rec["reason"] == "rate_limited"
