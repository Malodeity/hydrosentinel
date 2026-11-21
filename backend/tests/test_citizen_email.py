"""FR-11: a citizen who gives an email address is told when the report is received, looked at and resolved.

The mail goes through the real smtplib to a small SMTP server that runs inside the test, so the whole path is exercised (connect, EHLO, MAIL, RCPT, DATA),
not a mock of send_email. The rules that matter: nothing is sent unless the citizen asked, the address is never shown anywhere, the email carries no
detail about the report, and a mail problem never stops the report or the repair from being saved.
"""
import socketserver
import threading
import uuid

import pytest

from app import models
from app.config import settings
from tests.test_assignments import _assign, _login, _ticket_id, contractor  # noqa: F401  (fixtures shared with the ticket tests)

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")


class _Sink(socketserver.StreamRequestHandler):
    # just enough SMTP to receive a message: EHLO, MAIL FROM, RCPT TO, DATA, QUIT (it does not offer STARTTLS, like a plain local relay)
    def handle(self):
        send = lambda text: self.wfile.write((text + "\r\n").encode())
        send("220 sink ready")
        data_mode, lines = False, []
        for raw in self.rfile:
            line = raw.decode(errors="replace").rstrip("\r\n")
            if data_mode:
                if line == ".":
                    self.server.inbox.append("\n".join(lines))
                    data_mode, lines = False, []
                    send("250 queued")
                else:
                    lines.append(line[1:] if line.startswith("..") else line)
                continue
            cmd = line.upper()
            if cmd.startswith(("EHLO", "HELO")):
                send("250 sink")
            elif cmd.startswith(("MAIL", "RCPT", "RSET", "NOOP")):
                send("250 ok")
            elif cmd.startswith("DATA"):
                data_mode = True
                send("354 end with a dot")
            elif cmd.startswith("QUIT"):
                send("221 bye")
                return
            else:
                send("500 what")


@pytest.fixture
def smtp(monkeypatch):
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Sink)
    server.daemon_threads = True
    server.inbox = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_port", server.server_address[1])
    monkeypatch.setattr(settings, "smtp_user", None)
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def _uploads(tmp_path, monkeypatch):
    from app.routes import reports as reports_routes

    monkeypatch.setattr(reports_routes, "UPLOAD_ROOT", tmp_path)


def _submit(client, wsa, email=None, description="Burst pipe at 12 Example Street, call 082 555 1234"):
    data = {"wsa_id": str(wsa.id), "issue_type": "leak", "description": description, "lat": "-26.1", "lng": "28.2"}
    if email is not None:
        data["contact_email"] = email
    return client.post("/reports", data=data, files=[("photos", ("a.png", PNG, "image/png"))])


def test_a_citizen_who_gives_an_email_gets_a_receipt_through_real_smtp(client, sample_wsa, smtp):
    resp = _submit(client, sample_wsa, "citizen@example.com")
    assert resp.status_code == 201
    code = resp.json()["reference_code"]
    assert len(smtp.inbox) == 1
    mail = smtp.inbox[0]
    assert "To: citizen@example.com" in mail and code in mail and "We received your report" in mail


def test_the_email_says_nothing_about_the_report_itself(client, sample_wsa, smtp):
    # privacy: a mailbox is not private, so the mail carries only the reference code and the status
    _submit(client, sample_wsa, "citizen@example.com")
    mail = smtp.inbox[0]
    for private in ("12 Example Street", "082 555 1234", "Burst pipe", "-26.1", "28.2", sample_wsa.name):
        assert private not in mail


def test_nothing_is_sent_unless_the_citizen_asked(client, sample_wsa, smtp):
    assert _submit(client, sample_wsa).status_code == 201
    assert _submit(client, sample_wsa, "").status_code == 201
    assert smtp.inbox == []


def test_a_bad_address_is_refused_and_no_report_is_saved(client, sample_wsa, db, smtp):
    before = db.query(models.CitizenReport).count()
    resp = _submit(client, sample_wsa, "not-an-email")
    assert resp.status_code == 422
    assert db.query(models.CitizenReport).count() == before and smtp.inbox == []


def test_the_citizen_is_told_once_when_it_is_looked_at_and_once_when_it_is_resolved(client, auth_headers, sample_wsa, smtp):
    code = _submit(client, sample_wsa, "citizen@example.com").json()
    smtp.inbox.clear()
    rid = code["id"]
    for status_, expected in (("in_review", 1), ("in_review", 1), ("resolved", 2), ("resolved", 2)):   # repeating a status must not send the same mail again
        assert client.patch(f"/reports/{rid}", json={"case_status": status_}, headers=auth_headers).status_code == 200
        assert len(smtp.inbox) == expected
    assert "is being looked at" in smtp.inbox[0] and "is resolved" in smtp.inbox[1]


def test_verifying_a_repair_resolves_the_report_and_tells_the_citizen(client, auth_headers, sample_wsa, contractor, db, smtp):  # noqa: F811
    c, c_user = contractor
    report_id = _submit(client, sample_wsa, "citizen@example.com").json()["id"]
    report = db.query(models.CitizenReport).filter(models.CitizenReport.id == uuid.UUID(report_id)).one()
    tid = _ticket_id(client, auth_headers, report, c)
    ch = _login(client, c_user, "contractor1")
    for action, note in (("accept", None), ("fix", "Replaced the section")):
        assert client.patch(f"/my/tickets/{tid}", json={"action": action, "note": note}, headers=ch).status_code == 200
    smtp.inbox.clear()
    assert client.patch(f"/assignments/{tid}/review", json={"action": "verify"}, headers=auth_headers).status_code == 200
    to_citizen = [m for m in smtp.inbox if "To: citizen@example.com" in m]   # the contractor's staff are emailed too, which is a separate message
    assert len(to_citizen) == 1 and "is resolved" in to_citizen[0]


def test_the_address_is_never_returned_by_any_endpoint(client, auth_headers, sample_wsa, smtp):
    created = _submit(client, sample_wsa, "citizen@example.com").json()
    everything = [
        created,
        client.get(f"/reports/track/{created['reference_code']}").json(),
        client.get("/reports", headers=auth_headers).text,
        client.get("/reports/export.csv", headers=auth_headers).text if client.get("/reports/export.csv", headers=auth_headers).status_code == 200 else "",
    ]
    assert "citizen@example.com" not in str(everything) and "contact_email" not in str(everything)


def test_a_mail_server_that_is_down_never_stops_the_report(client, sample_wsa, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_port", 9)     # nothing listens here
    resp = _submit(client, sample_wsa, "citizen@example.com")
    assert resp.status_code == 201


def test_without_smtp_settings_nothing_is_attempted(client, sample_wsa, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
    assert _submit(client, sample_wsa, "citizen@example.com").status_code == 201


# ---- health check (a limitation from Assignment 4: the model could be missing and nobody would notice) -------------

def test_health_is_ok_when_the_model_and_database_are_there(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["risk_model"] == "loaded"


def test_health_fails_when_the_risk_model_is_missing(client, monkeypatch):
    from main import app

    monkeypatch.setattr(app.state, "risk_model", None)
    resp = client.get("/health")
    assert resp.status_code == 503 and "model" in resp.json()["detail"].lower()
