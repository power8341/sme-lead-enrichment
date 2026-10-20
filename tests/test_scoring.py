from datetime import date

from src.scoring import score_lead

TODAY = date(2026, 10, 20)


def company(**overrides):
    base = {
        "etat_administratif": "A", "tranche_effectif_salarie": "12",
        "date_creation": "2018-01-01", "section_activite_principale": "J",
        "nombre_etablissements_ouverts": 1,
    }
    base.update(overrides)
    return base


def test_tech_sme_is_hot():
    score, rating, reasons = score_lead(company(), today=TODAY)
    assert rating == "Hot" and score == 80
    assert any("headcount 20-49" in r for r in reasons)


def test_closed_company_is_disqualified():
    assert score_lead(company(etat_administratif="C"), today=TODAY)[1] == "Disqualified"


def test_large_company_scores_lower_than_sme():
    sme = score_lead(company(), today=TODAY)[0]
    large = score_lead(company(tranche_effectif_salarie="32"), today=TODAY)[0]
    assert large < sme


def test_score_never_above_100():
    score, _, _ = score_lead(company(nombre_etablissements_ouverts=5), today=TODAY)
    assert score <= 100
