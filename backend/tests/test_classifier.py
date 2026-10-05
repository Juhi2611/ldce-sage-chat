"""Tests for the intent classifier."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chatbot.classifier import (
    train_and_save, predict, detect_smalltalk, CATEGORIES
)


def get_trained_pipeline():
    """Train a fresh pipeline for testing (uses decision_tree for speed)."""
    return train_and_save("decision_tree")


def test_classifier_returns_valid_category():
    pipe = get_trained_pipeline()
    cat, conf = predict("what is the admission process at ldce", pipe)
    assert cat in CATEGORIES
    assert 0.0 <= conf <= 1.0


def test_cse_fee_query():
    """Acceptance check: 'cse fee??' must resolve to Fees."""
    pipe = get_trained_pipeline()
    cat, conf = predict("cse fee??", pipe)
    assert cat == "Fees"


def test_hostel_query():
    pipe = get_trained_pipeline()
    cat, conf = predict("is hostel available at ldce", pipe)
    assert cat == "Hostel"


def test_placement_query():
    pipe = get_trained_pipeline()
    cat, conf = predict("placement record at ldce", pipe)
    assert cat == "Placements"


def test_confidence_range():
    pipe = get_trained_pipeline()
    _, conf = predict("any query", pipe)
    assert 0.0 <= conf <= 1.0


def test_smalltalk_greeting():
    assert detect_smalltalk("hello") == "greeting"
    assert detect_smalltalk("Hi there") == "greeting"
    assert detect_smalltalk("namaste") == "greeting"


def test_smalltalk_thanks():
    assert detect_smalltalk("thank you") == "thanks"
    assert detect_smalltalk("thanks a lot") == "thanks"


def test_smalltalk_goodbye():
    assert detect_smalltalk("bye") == "goodbye"


def test_no_smalltalk():
    assert detect_smalltalk("what is the fee for cse") is None


def test_fallback_path():
    """Low confidence: predict unrelated text and check conf < 1."""
    pipe = get_trained_pipeline()
    _, conf = predict("xyzzy foobar quux", pipe)
    # Confidence should be low on garbage input
    assert conf < 0.99  # decision tree may still pick something; key is < 1
