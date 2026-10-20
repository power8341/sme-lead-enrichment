"""Push enriched leads into Salesforce as Lead records (REST API).

Runs in dry-run mode by default: it prints what would be sent without calling
Salesforce. To send for real, create a free Salesforce Developer org, then set:

    SF_INSTANCE_URL   e.g. https://yourorg.my.salesforce.com
    SF_ACCESS_TOKEN   e.g. from `sf org display --target-org yourorg`

Usage:
    python -m src.salesforce_push --input output/enriched_leads.csv            (dry run)
    python -m src.salesforce_push --input output/enriched_leads.csv --send     (real)
"""

import argparse
import json
import logging
import os

import pandas as pd
import requests

API_VERSION = "v61.0"
logger = logging.getLogger("salesforce_push")


def to_lead(row):
    """Map one enriched row to standard Salesforce Lead fields."""
    return {
        "Company": row["legal_name"],
        "LastName": "To be identified",  # required field on Lead; the contact is found later by Sales
        "Street": row.get("address"),
        "PostalCode": row.get("postal_code"),
        "City": row.get("city"),
        "Country": "France",
        "LeadSource": "Public register enrichment",
        "Rating": row["lead_rating"] if row["lead_rating"] in ("Hot", "Warm", "Cold") else None,
        "Description": (
            f"SIREN {row['siren']} | NAF {row.get('naf_code')} | headcount {row.get('headcount_band')} | "
            f"score {row['lead_score']} ({row.get('score_reasons')})"
        ),
    }


class SalesforceClient:
    def __init__(self, instance_url, access_token):
        self.base = f"{instance_url.rstrip('/')}/services/data/{API_VERSION}"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        })

    def lead_exists(self, siren):
        soql = f"SELECT Id FROM Lead WHERE Description LIKE 'SIREN {siren}%' LIMIT 1"
        response = self.session.get(f"{self.base}/query", params={"q": soql}, timeout=15)
        response.raise_for_status()
        return response.json()["totalSize"] > 0

    def create_lead(self, lead):
        response = self.session.post(f"{self.base}/sobjects/Lead", data=json.dumps(lead), timeout=15)
        response.raise_for_status()
        return response.json()["id"]


def push(input_path, send=False, min_confidence=("high", "medium")):
    leads = pd.read_csv(input_path, dtype={"siren": str, "postal_code": str})
    leads = leads[leads["match_confidence"].isin(min_confidence)]
    leads = leads[leads["lead_rating"] != "Disqualified"]
    leads = leads.where(pd.notna(leads), None)

    if not send:
        for _, row in leads.iterrows():
            logger.info("[dry run] would create: %s", json.dumps(to_lead(row), ensure_ascii=False))
        logger.info("[dry run] %d leads ready. Use --send to create them in Salesforce.", len(leads))
        return {"created": 0, "skipped": 0, "ready": len(leads)}

    client = SalesforceClient(os.environ["SF_INSTANCE_URL"], os.environ["SF_ACCESS_TOKEN"])
    created = skipped = 0
    for _, row in leads.iterrows():
        if client.lead_exists(row["siren"]):  # idempotent: never create the same lead twice
            skipped += 1
            continue
        lead_id = client.create_lead(to_lead(row))
        created += 1
        logger.info("Created Lead %s for %s", lead_id, row["legal_name"])

    logger.info("Done: %d created, %d already in Salesforce", created, skipped)
    return {"created": created, "skipped": skipped, "ready": len(leads)}


def main():
    parser = argparse.ArgumentParser(description="Push enriched leads to Salesforce")
    parser.add_argument("--input", default="output/enriched_leads.csv")
    parser.add_argument("--send", action="store_true", help="really create the leads")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    push(args.input, send=args.send)


if __name__ == "__main__":
    main()
