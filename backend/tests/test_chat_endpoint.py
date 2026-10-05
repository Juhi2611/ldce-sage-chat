"""FastAPI integration tests for chat, feedback, analytics, and admin endpoints.

Uses FastAPI TestClient with an isolated test SQLite database.
"""
import sys
import os
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.config import settings
from app.models import Enquiry, Session as SessionModel, Feedback

from sqlalchemy.pool import StaticPool

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_smalltalk_not_logged():
    """'hi' returns smalltalk and is NOT logged to enquiries table."""
    res = client.post("/api/chat", json={"session_id": "s-test-01", "query": "hi"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_smalltalk"] is True
    assert "Namaste" in data["answer_markdown"] or "help" in data["answer_markdown"]

    db = TestingSessionLocal()
    try:
        count = db.query(Enquiry).count()
        assert count == 0
    finally:
        db.close()


def test_cse_fee_logged():
    """'cse fee??' returns Fees + Computer Engineering and is logged."""
    res = client.post("/api/chat", json={"session_id": "s-test-02", "query": "cse fee??"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_smalltalk"] is False
    assert data["department"] == "Computer Engineering"
    assert data["resolved"] is True
    assert data["enquiry_id"] is not None

    db = TestingSessionLocal()
    try:
        enq = db.query(Enquiry).filter(Enquiry.id == data["enquiry_id"]).first()
        assert enq is not None
        assert enq.predicted_category == "Fees"
        assert enq.predicted_department == "Computer Engineering"
    finally:
        db.close()


def test_gibberish_fallback():
    """Gibberish input returns fallback with resolved=False and 3 suggestions."""
    res = client.post("/api/chat", json={"session_id": "s-test-03", "query": "xyzzy foobar quux 12345"})
    assert res.status_code == 200
    data = res.json()
    assert data["resolved"] is False
    assert len(data["suggestions"]) == 3
    assert "not quite sure" in data["answer_markdown"].lower()


def test_phone_number_masked():
    """Message containing a phone number is masked in the stored enquiry row."""
    res = client.post(
        "/api/chat",
        json={"session_id": "s-test-04", "query": "my contact number is 9876543210 for cse admission"}
    )
    assert res.status_code == 200
    data = res.json()
    enq_id = data["enquiry_id"]

    db = TestingSessionLocal()
    try:
        enq = db.query(Enquiry).filter(Enquiry.id == enq_id).first()
        assert enq is not None
        assert "9876543210" not in enq.raw_question
        assert "[PHONE]" in enq.raw_question
    finally:
        db.close()


def test_feedback_saved():
    """Posting feedback for an enquiry saves the record."""
    # First submit an enquiry
    chat_res = client.post("/api/chat", json={"session_id": "s-test-05", "query": "hostel fees"})
    enq_id = chat_res.json()["enquiry_id"]

    fb_res = client.post("/api/feedback", json={"enquiry_id": enq_id, "rating": "up"})
    assert fb_res.status_code == 200

    db = TestingSessionLocal()
    try:
        fb = db.query(Feedback).filter(Feedback.enquiry_id == enq_id).first()
        assert fb is not None
        assert fb.rating == "up"
    finally:
        db.close()


def test_admin_auth():
    """Admin endpoints return 401 without token and 200 with valid X-Admin-Token."""
    # Without token
    res_no_auth = client.get("/api/admin/verify-token")
    assert res_no_auth.status_code == 401

    # With invalid token
    res_bad_auth = client.get("/api/admin/verify-token", headers={"X-Admin-Token": "wrong"})
    assert res_bad_auth.status_code == 401

    # With valid token
    headers = {"X-Admin-Token": settings.admin_token}
    res_ok = client.get("/api/admin/verify-token", headers=headers)
    assert res_ok.status_code == 200
    assert res_ok.json() == {"valid": True}


def test_analytics_empty_and_seeded_db():
    """Analytics summary returns valid shape on empty DB and handles include_synthetic filter."""
    # Empty DB check
    res_empty = client.get("/api/analytics/summary")
    assert res_empty.status_code == 200
    data_empty = res_empty.json()
    assert data_empty["recentLogCount"] == 0

    # Seed one real row and one synthetic row directly
    db = TestingSessionLocal()
    try:
        s1 = SessionModel(id="sess-real")
        db.add(s1)
        e_real = Enquiry(
            session_id="sess-real", raw_question="real query",
            normalized_question="real query", predicted_category="Fees",
            predicted_department="Computer Engineering", confidence=0.8,
            resolved=True, is_synthetic=False
        )
        e_synth = Enquiry(
            session_id="sess-real", raw_question="synthetic query",
            normalized_question="synthetic query", predicted_category="Hostel",
            predicted_department=None, confidence=0.9,
            resolved=True, is_synthetic=True
        )
        db.add_all([e_real, e_synth])
        db.commit()
    finally:
        db.close()

    # With include_synthetic=true -> total 2
    res_with_synth = client.get("/api/analytics/summary?include_synthetic=true")
    assert res_with_synth.status_code == 200
    assert res_with_synth.json()["recentLogCount"] == 2

    # With include_synthetic=false -> total 1
    res_no_synth = client.get("/api/analytics/summary?include_synthetic=false")
    assert res_no_synth.status_code == 200
    assert res_no_synth.json()["recentLogCount"] == 1
