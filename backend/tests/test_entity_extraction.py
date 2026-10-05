"""Tests for entity extraction (department & topic detection)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chatbot.entity_extraction import extract_department, extract_topic, CANONICAL_DEPARTMENTS


def test_cse_alias():
    assert extract_department("cse fee") == "Computer Engineering"


def test_comp_alias():
    assert extract_department("comp engineering course") == "Computer Engineering"


def test_it_alias():
    assert extract_department("it department") == "Information Technology"


def test_aiml_alias():
    assert extract_department("aiml at ldce") == "Artificial Intelligence and Machine Learning"


def test_mech_alias():
    assert extract_department("mech syllabus") == "Mechanical Engineering"


def test_ec_alias():
    assert extract_department("ec department overview") == "Electronics and Communication Engineering"


def test_electrical_alias():
    assert extract_department("electrical engineering fees") == "Electrical Engineering"


def test_ic_alias():
    assert extract_department("ic engineering") == "Instrumentation and Control Engineering"


def test_no_department():
    assert extract_department("what is the fee structure") is None


def test_fees_topic():
    assert extract_topic("how much is the tuition fee") == "fees"


def test_hostel_topic():
    assert extract_topic("hostel available for girls") == "hostel"


def test_placement_topic():
    assert extract_topic("placement companies at ldce") == "placement"


def test_scholarship_topic():
    assert extract_topic("scholarship for sc st students") == "scholarship"


def test_no_topic():
    assert extract_topic("hello world xyz") is None


def test_canonical_departments_count():
    # Exactly 17 UG departments as listed on ldce.ac.in
    assert len(CANONICAL_DEPARTMENTS) == 17
