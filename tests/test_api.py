"""REST API tests (offline: replay mode against committed data/recordings)."""
import pytest
from fastapi.testclient import TestClient

from flyercheck import pipeline
from flyercheck.api import create_app
from flyercheck.llm.port import LLMError

SAMPLE = "data/samples/Designer.pdf"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    out = tmp_path_factory.mktemp("api-out")
    return TestClient(create_app(out_dir=str(out), recordings_dir="data/recordings"))


@pytest.fixture(scope="module")
def run_id(client):
    with open(SAMPLE, "rb") as fh:
        r = client.post("/v1/validations", files={"file": ("Designer.pdf", fh, "application/pdf")},
                        data={"mode": "replay", "year": "2026"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["offers"] > 0 and body["status_counts"]["fail"] >= 1
    assert body["findings_url"] == f"/v1/validations/{body['run_id']}/findings"
    return body["run_id"]


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_upload_and_findings(client, run_id):
    findings = client.get(f"/v1/validations/{run_id}/findings").json()
    pizza = next(f for f in findings if f["id"] == "R-01:o-6")
    assert pizza["check_id"] == "R-01" and pizza["status"] == "fail"
    assert "pizza" in (pizza["offer_name"] or "").lower()
    fails = client.get(f"/v1/validations/{run_id}/findings", params={"status": "fail"}).json()
    assert fails and all(f["status"] == "fail" for f in fails)
    assert len(fails) < len(findings)


def test_summary_list_and_report(client, run_id):
    s = client.get(f"/v1/validations/{run_id}").json()
    assert s["run_id"] == run_id and "findings" not in s
    assert set(s["decision_counts"]) == {"confirm", "reject", "escalate"}
    runs = client.get("/v1/validations").json()
    assert any(r["run_id"] == run_id and r["filename"].endswith("Designer.pdf") for r in runs)
    rep = client.get(f"/v1/validations/{run_id}/report")
    assert rep.status_code == 200 and rep.headers["content-type"].startswith("text/html")


def test_decision_roundtrip_raw_and_encoded(client, run_id):
    r = client.post(f"/v1/validations/{run_id}/findings/R-01:o-6/decision",
                    json={"decision": "escalate", "reviewer": "anna", "reason": "check with category mgmt"})
    assert r.status_code == 201, r.text
    assert r.json()["finding_id"] == "R-01:o-6" and r.json()["decided_at"]
    r = client.post(f"/v1/validations/{run_id}/findings/R-01%3Ao-6/decision",
                    json={"decision": "confirm", "reviewer": "anna"})
    assert r.status_code == 201, r.text

    decisions = client.get(f"/v1/validations/{run_id}/decisions").json()
    assert [d["decision"] for d in decisions if d["finding_id"] == "R-01:o-6"] == ["escalate", "confirm"]
    pizza = next(f for f in client.get(f"/v1/validations/{run_id}/findings").json() if f["id"] == "R-01:o-6")
    assert pizza["decision"]["decision"] == "confirm"  # latest wins
    assert client.get(f"/v1/validations/{run_id}").json()["decision_counts"]["confirm"] >= 1


def test_decision_validation_and_404(client, run_id):
    assert client.post(f"/v1/validations/{run_id}/findings/R-01:o-6/decision",
                       json={"decision": "maybe"}).status_code == 422
    assert client.post(f"/v1/validations/{run_id}/findings/X-99:o-1/decision",
                       json={"decision": "confirm"}).status_code == 404
    assert client.post("/v1/validations/nope-123/findings/R-01:o-6/decision",
                       json={"decision": "confirm"}).status_code == 404


def test_unknown_run_404(client):
    for suffix in ("", "/findings", "/report", "/decisions"):
        assert client.get(f"/v1/validations/unknown-run{suffix}").status_code == 404


def test_bad_extension_400(client):
    r = client.post("/v1/validations", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


@pytest.mark.parametrize("bad", ["..", "..%2F..%2Fetc", "a.b", "%2E%2E"])
def test_traversal_run_id_rejected(client, bad):
    r = client.get(f"/v1/validations/{bad}/findings")
    assert r.status_code in (400, 404)


def test_invalid_run_id_is_400(client):
    assert client.get("/v1/validations/a.b").status_code == 400


def test_llm_error_422(client, monkeypatch):
    def boom(*a, **kw):
        raise LLMError("replay miss: no recording for key abc")

    monkeypatch.setattr(pipeline, "run", boom)
    r = client.post("/v1/validations", files={"file": ("x.png", b"\x89PNG", "image/png")})
    assert r.status_code == 422 and "replay miss" in r.json()["detail"]
