"""
test_app.py — unit tests for the resume screener API.
These run locally and in GitHub Actions CI pipeline.
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ── Mock heavy dependencies before importing app ──────────────────────────────

import sys

# Mock SQLAlchemy so tests don't need a real DB
mock_db = MagicMock()
mock_db.Column = MagicMock(return_value=None)
mock_db.Integer = MagicMock()
mock_db.String = MagicMock(return_value=None)
mock_db.Text = MagicMock()
mock_db.DateTime = MagicMock()
class MockModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

mock_db.Model = MockModel
sys.modules["flask_sqlalchemy"] = MagicMock(SQLAlchemy=MagicMock(return_value=mock_db))

# Mock Prometheus so tests don't register metrics
sys.modules["prometheus_flask_exporter"] = MagicMock()

# Mock sentence_transformers so tests don't load the ML model
sys.modules["sentence_transformers"] = MagicMock()

# Mock screener module with a fixed return value
mock_screener = MagicMock()
mock_screener.score_resume.return_value = {
    "score": 82,
    "match_level": "strong",
    "reasoning": "The resume closely matches the job description with an 82% similarity score.",
}
sys.modules["screener"] = mock_screener


# ── Import app after mocks are in place ───────────────────────────────────────

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with flask_app.test_client() as c:
        yield c


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_health_returns_200(client):
    res = client.get("/health")
    assert res.status_code == 200


def test_health_returns_correct_body(client):
    res = client.get("/health")
    data = json.loads(res.data)
    assert data["status"] == "healthy"
    assert data["service"] == "resume-screener"


def test_screen_missing_body_returns_400(client):
    res = client.post("/screen", content_type="application/json", data="{}")
    assert res.status_code == 400


def test_screen_missing_resume_returns_400(client):
    payload = json.dumps({"job_description": "DevOps engineer with AWS"})
    res = client.post("/screen", content_type="application/json", data=payload)
    assert res.status_code == 400


def test_screen_missing_jd_returns_400(client):
    payload = json.dumps({"resume": "I have AWS experience"})
    res = client.post("/screen", content_type="application/json", data=payload)
    assert res.status_code == 400


def test_screen_valid_request(client):
    with patch("app.db") as mock_db_patch:
        mock_db_patch.session.add = MagicMock()
        mock_db_patch.session.commit = MagicMock()

        payload = json.dumps({
            "job_description": "DevOps engineer with AWS and Docker experience",
            "resume": "I have 2 years of AWS, Docker, and Kubernetes experience",
            "job_title": "DevOps Engineer",
        })
        res = client.post("/screen", content_type="application/json", data=payload)

    assert res.status_code == 200
    data = json.loads(res.data)
    assert "score" in data
    assert "match_level" in data
    assert "reasoning" in data


def test_screen_score_is_a_number(client):
    with patch("app.db"):
        payload = json.dumps({
            "job_description": "Python developer",
            "resume": "Python and Flask developer",
        })
        res = client.post("/screen", content_type="application/json", data=payload)

    data = json.loads(res.data)
    assert isinstance(data.get("score"), int)


def test_results_endpoint(client):
    with patch("app.ScreeningResult") as mock_model:
        mock_model.query.order_by.return_value.limit.return_value.all.return_value = []
        res = client.get("/results")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "results" in data
    assert "count" in data
