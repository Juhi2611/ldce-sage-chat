"""Text normalisation for both training and inference.

Applies: lowercase → expand common abbreviations → strip punctuation →
         collapse whitespace.
"""
import re
import string

# --- Abbreviation / spelling-fix map ---
_ABBREVS: dict[str, str] = {
    r"\bcse\b": "computer engineering",
    r"\bce\b": "computer engineering",
    r"\bcomp eng\b": "computer engineering",
    r"\bcomp\b": "computer",
    r"\bit dept\b": "information technology",
    r"\baiml\b": "artificial intelligence machine learning",
    r"\bai ml\b": "artificial intelligence machine learning",
    r"\bai/ml\b": "artificial intelligence machine learning",
    r"\bec dept\b": "electronics communication engineering",
    r"\bece\b": "electronics communication engineering",
    r"\bec\b": "electronics",
    r"\bee\b": "electrical engineering",
    r"\bic\b": "instrumentation control",
    r"\bmech\b": "mechanical",
    r"\bauto\b": "automobile",
    r"\bbme\b": "biomedical engineering",
    r"\bchem\b": "chemical",
    r"\btxtl\b": "textile",
    r"\bplstc\b": "plastic technology",
    r"\bfee\b": "fees",
    r"\bfees\b": "fees",
    r"\bamt\b": "amount",
    r"\bavlbl\b": "available",
    r"\bavail\b": "available",
    r"\badmsn\b": "admission",
    r"\bplacemnt\b": "placement",
    r"\bplacment\b": "placement",
    r"\bplacement\b": "placement",
    r"\bpachage\b": "package",
    r"\bpackge\b": "package",
    r"\beligbility\b": "eligibility",
    r"\beligibilty\b": "eligibility",
    r"\belibility\b": "eligibility",
    r"\bcutof\b": "cutoff",
    r"\bcutt off\b": "cutoff",
    r"\bscholarshp\b": "scholarship",
    r"\bcolege\b": "college",
    r"\bcolleg\b": "college",
    r"\bldce\b": "ldce",
    r"\binfo\b": "information",
    r"\bpls\b": "please",
    r"\bplz\b": "please",
    r"\bwht\b": "what",
    r"\bhw\b": "how",
    r"\bhos+tel\b": "hostel",
    r"\btranspt\b": "transport",
    r"\btnp\b": "training placement",
    r"\bt&p\b": "training placement",
}


def normalize(text: str) -> str:
    """Return a cleaned, normalised version of *text*.

    Steps
    -----
    1. Lowercase
    2. Expand common abbreviations and fix common typos
    3. Remove punctuation (keep hyphens inside words, slash, ampersand)
    4. Collapse whitespace
    """
    text = text.lower().strip()

    for pattern, replacement in _ABBREVS.items():
        text = re.sub(pattern, replacement, text)

    # Replace punctuation except hyphens inside words
    text = re.sub(r"[^\w\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
