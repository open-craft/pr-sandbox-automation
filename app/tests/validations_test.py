from fastapi.testclient import TestClient
import hmac
import hashlib

from app.main import app

client = TestClient(app)


def test_malformed_signature_validation():
    payload = b'{"title":"Dummy Payload","description":"This is a dummy test payload"}'
    response = client.post(
        "/github-webhook/",
        headers={"X-Hub-Signature-256": "000000000000000000000000"},
        content=payload,
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "request_not_actionable",
                "loc": ["body"],
                "msg": "x-hub-signature-256 header missing or malformed",
            }
        ]
    }


def test_incorrect_signature_validation():
    payload = b'{"title":"Dummy Payload","description":"This is a dummy test payload"}'
    response = client.post(
        "/github-webhook/",
        headers={"X-Hub-Signature-256": "sha256=000000000000000000000000"},
        content=payload,
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Request signature could not be validated"}


def test_valid_signature_validation(mock_get_secret):
    payload = b'{"title":"Dummy Payload","description":"This is a dummy test payload"}'
    payload_signature = hmac.new(
        mock_get_secret("pr-sandbox-github-webhook-secret").encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    response = client.post(
        "/github-webhook/",
        headers={"X-Hub-Signature-256": f"sha256={payload_signature}"},
        content=payload,
    )
    # The response should be a 422 error due to missing required fields in the dummy request
    assert response.status_code == 422
    resp = response.json()
    assert "detail" in resp
    assert "type" in resp["detail"][0]
    assert resp["detail"][0]["type"] == "missing"
