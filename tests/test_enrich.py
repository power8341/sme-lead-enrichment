import json
from datetime import date
from pathlib import Path

import pandas as pd

from src.enrich import run
from src.salesforce_push import push, to_lead

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "api_responses.json").read_text())


class FakeClient:
    """Returns saved API responses instead of calling the real API."""
    def search(self, name, postal_code=None, per_page=5):
        if name == "Broken":
            raise ConnectionError("API down")
        return FIXTURES.get(name, {"results": []})["results"]


def test_full_run(tmp_path):
    source = tmp_path / "in.csv"
    pd.DataFrame({
        "company_name": ["Pennylane", "Agicap", "Unknown Company", "Broken"],
        "city": ["Paris", "Lyon", None, None],
        "postal_code": [None, None, None, None],
    }).to_csv(source, index=False)

    out = tmp_path / "out.csv"
    result = run(source, out, client=FakeClient(), today=date(2026, 10, 20))

    assert out.exists()
    by_name = result.set_index("input_name")
    assert by_name.loc["Pennylane", "siren"] == "880265921"
    assert by_name.loc["Unknown Company", "match_confidence"] == "not_found"
    assert by_name.loc["Broken", "match_confidence"] == "error"  # one failure does not stop the run


def test_salesforce_dry_run(tmp_path):
    source = tmp_path / "in.csv"
    pd.DataFrame({"company_name": ["Pennylane"], "city": ["Paris"], "postal_code": [None]}).to_csv(source, index=False)
    out = tmp_path / "out.csv"
    run(source, out, client=FakeClient(), today=date(2026, 10, 20))
    summary = push(out, send=False)
    assert summary == {"created": 0, "skipped": 0, "ready": 1}


def test_lead_mapping():
    lead = to_lead({"legal_name": "PENNYLANE", "address": "x", "postal_code": "75009", "city": "PARIS",
                    "lead_rating": "Warm", "siren": "880265921", "naf_code": "62.01Z",
                    "headcount_band": "250-499", "lead_score": 55, "score_reasons": "r"})
    assert lead["Company"] == "PENNYLANE" and lead["Rating"] == "Warm"
    assert lead["Description"].startswith("SIREN 880265921")
