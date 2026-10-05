"""Tests for text normalisation logic."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chatbot.normalizer import normalize


def test_lowercase():
    assert normalize("HELLO LDCE") == "hello ldce"


def test_strip_punctuation():
    result = normalize("cse fee??")
    assert "?" not in result


def test_cse_expansion():
    result = normalize("cse fees")
    assert "computer engineering" in result


def test_mech_expansion():
    result = normalize("mech fees")
    assert "mechanical" in result


def test_whitespace_collapse():
    result = normalize("  what   is   the   fee  ")
    assert "  " not in result
    assert result == result.strip()


def test_hostel_availability_typo():
    result = normalize("hostel avlbl?")
    assert "hostel" in result
    assert "available" in result


def test_aiml_expansion():
    result = normalize("aiml department")
    assert "artificial intelligence" in result


def test_empty_string():
    assert normalize("") == ""


def test_placement_typo():
    result = normalize("placemnt pachage")
    assert "placement" in result
    assert "package" in result
