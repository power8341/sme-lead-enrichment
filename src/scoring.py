"""Simple, explainable lead score for SME prospects.

The score (0 to 100) favours small and medium companies that are active,
established and in sectors that often need a business account and finance tools.
Every rule is written in plain code so a Sales manager can ask "why is this
lead Hot?" and get a clear answer from the score_reasons column.
"""

from datetime import date

# INSEE headcount bands (tranche_effectif_salarie) -> readable label
HEADCOUNT_LABELS = {
    "NN": "unknown or no employees", "00": "0", "01": "1-2", "02": "3-5", "03": "6-9",
    "11": "10-19", "12": "20-49", "21": "50-99", "22": "100-199", "31": "200-249",
    "32": "250-499", "41": "500-999", "42": "1000-1999", "51": "2000-4999",
    "52": "5000-9999", "53": "10000+",
}

# Target: small and medium companies (SMEs)
HEADCOUNT_POINTS = {
    "01": 25, "02": 30, "03": 35, "11": 35, "12": 35, "21": 25, "22": 15,
    "31": 10, "32": 5,
}

# NAF sections that are good targets for a business bank and finance tools
SECTOR_POINTS = {
    "J": 20,  # information and communication (tech, software, media)
    "M": 20,  # professional, scientific and technical activities (consulting, agencies)
    "G": 15,  # wholesale and retail trade (e-commerce)
    "I": 15,  # accommodation and food service
    "F": 15,  # construction
    "N": 10,  # administrative and support services
    "C": 10,  # manufacturing
}


def company_age_years(date_creation, today=None):
    if not date_creation:
        return None
    today = today or date.today()
    created = date.fromisoformat(date_creation)
    return (today - created).days / 365.25


def score_lead(company, today=None):
    """Return (score, rating, reasons) for one enriched company."""
    points, reasons = 0, []

    if company.get("etat_administratif") != "A":
        return 0, "Disqualified", ["company is closed"]

    band = company.get("tranche_effectif_salarie")
    head_pts = HEADCOUNT_POINTS.get(band, 0)
    points += head_pts
    reasons.append(f"headcount {HEADCOUNT_LABELS.get(band, 'unknown')} (+{head_pts})")

    age = company_age_years(company.get("date_creation"), today)
    if age is not None:
        age_pts = 25 if 2 <= age <= 15 else (15 if age < 2 else 10)
        points += age_pts
        reasons.append(f"{age:.0f} years old (+{age_pts})")

    section = company.get("section_activite_principale")
    sector_pts = SECTOR_POINTS.get(section, 5)
    points += sector_pts
    reasons.append(f"sector {section} (+{sector_pts})")

    if (company.get("nombre_etablissements_ouverts") or 0) > 1:
        points += 10
        reasons.append("several sites (+10)")

    score = min(points, 100)
    rating = "Hot" if score >= 70 else ("Warm" if score >= 45 else "Cold")
    return score, rating, reasons
