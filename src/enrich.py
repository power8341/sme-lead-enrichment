"""Enrich a CSV of company names and export sales-ready leads.

Usage:
    python -m src.enrich --input data/companies_sample.csv --output output/enriched_leads.csv
"""

import argparse
import logging
from datetime import date

import pandas as pd

from src.api_client import CompanyRegisterClient
from src.matching import best_match
from src.scoring import HEADCOUNT_LABELS, score_lead

logger = logging.getLogger("enrich")

OUTPUT_COLUMNS = [
    "input_name", "match_confidence", "match_score", "siren", "siret", "legal_name",
    "naf_code", "sector_section", "company_category", "headcount_band", "date_creation",
    "address", "postal_code", "city", "lead_score", "lead_rating", "score_reasons",
]


def enrich_row(client, row, today=None):
    name = str(row["company_name"]).strip()
    postal = row.get("postal_code") if pd.notna(row.get("postal_code")) else None
    city = row.get("city") if pd.notna(row.get("city")) else None

    candidates = client.search(name, postal_code=postal)
    company, match_score, confidence = best_match(name, candidates, postal, city)
    if company is None:
        return {"input_name": name, "match_confidence": "not_found", "match_score": 0}

    siege = company.get("siege") or {}
    score, rating, reasons = score_lead(company, today=today)
    return {
        "input_name": name,
        "match_confidence": confidence,
        "match_score": match_score,
        "siren": company.get("siren"),
        "siret": siege.get("siret"),
        "legal_name": company.get("nom_raison_sociale") or company.get("nom_complet"),
        "naf_code": company.get("activite_principale"),
        "sector_section": company.get("section_activite_principale"),
        "company_category": company.get("categorie_entreprise"),
        "headcount_band": HEADCOUNT_LABELS.get(company.get("tranche_effectif_salarie"), "unknown"),
        "date_creation": company.get("date_creation"),
        "address": siege.get("adresse"),
        "postal_code": siege.get("code_postal"),
        "city": siege.get("libelle_commune"),
        "lead_score": score,
        "lead_rating": rating,
        "score_reasons": "; ".join(reasons),
    }


def run(input_path, output_path, client=None, today=None):
    client = client or CompanyRegisterClient()
    companies = pd.read_csv(input_path, dtype={"postal_code": str})
    rows, errors = [], 0

    for _, row in companies.iterrows():
        try:
            rows.append(enrich_row(client, row, today=today))
        except Exception as error:  # one bad row must not stop the whole run
            errors += 1
            logger.error("Could not enrich %r: %s", row.get("company_name"), error)
            rows.append({"input_name": row.get("company_name"), "match_confidence": "error"})

    result = pd.DataFrame(rows).reindex(columns=OUTPUT_COLUMNS)
    result = result.sort_values("lead_score", ascending=False, na_position="last")
    result.to_csv(output_path, index=False)

    summary = result["match_confidence"].value_counts().to_dict()
    logger.info("Enriched %d companies -> %s | %s | errors: %d",
                len(result), output_path, summary, errors)
    return result


def main():
    parser = argparse.ArgumentParser(description="Enrich company names with public register data")
    parser.add_argument("--input", default="data/companies_sample.csv")
    parser.add_argument("--output", default="output/enriched_leads.csv")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(args.input, args.output, today=date.today())


if __name__ == "__main__":
    main()
