import json
from pathlib import Path

from src.matching import best_match, normalise

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "api_responses.json").read_text())


def test_normalise_removes_accents_and_legal_forms():
    assert normalise("Le Slip Français SAS") == "LE SLIP FRANCAIS"


def test_pennylane_picks_the_real_employer_not_the_first_result():
    # The first API result is a 2008 real-estate company with no employees.
    candidates = FIXTURES["Pennylane"]["results"]
    company, score, confidence = best_match("Pennylane", candidates, input_city="Paris")
    assert company["siren"] == "880265921"
    assert confidence == "high"


def test_agicap_matches_the_lyon_company():
    candidates = FIXTURES["Agicap"]["results"]
    company, _, _ = best_match("Agicap", candidates, input_city="Lyon")
    assert company["siege"]["libelle_commune"] == "LYON"


def test_wrong_name_gives_low_confidence():
    # "Boulangerie Utopie" is a brand name; the register returns a different legal name.
    candidates = FIXTURES["Boulangerie Utopie"]["results"]
    _, _, confidence = best_match("Boulangerie Utopie", candidates, input_city="Paris")
    assert confidence == "low"


def test_no_candidates():
    assert best_match("Nothing", []) == (None, 0, "not_found")


def test_brand_name_in_brackets_is_matched():
    # Back Market's legal name is "JUNG S.A.S"; the brand only appears in brackets.
    candidates = [
        {"nom_complet": "BACK MARKET GERMANY GMBH", "nom_raison_sociale": "BACK MARKET GERMANY GMBH",
         "etat_administratif": "A", "tranche_effectif_salarie": "NN", "siege": {"libelle_commune": None}},
        {"nom_complet": "JUNG S.A.S (BACK MARKET) (J.G)", "nom_raison_sociale": "JUNG S.A.S", "siren": "804049476",
         "etat_administratif": "A", "tranche_effectif_salarie": "32", "siege": {"libelle_commune": "PARIS"}},
    ]
    company, _, confidence = best_match("Back Market", candidates, input_city="Paris")
    assert company["siren"] == "804049476" and confidence == "high"


def test_other_city_is_penalised():
    candidates = FIXTURES["Pennylane"]["results"]
    company, score, _ = best_match("Pennylane", candidates, input_city="Marseille")
    assert score < 90
