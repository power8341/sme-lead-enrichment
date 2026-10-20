# SME Lead Enrichment Flow for Sales

A data enrichment flow that turns a simple list of company names into sales-ready leads. It looks up each company in the French public company register, picks the right legal entity, adds business information, gives each lead an explainable score and prepares the result for Salesforce.

## Why this project

Sales teams often start with incomplete prospect lists: a company name, maybe a city. Enriching these records with reliable public data helps them focus on the right companies and saves hours of manual research.

The hard part is not calling the API, it is **picking the right company**. A search for "Pennylane" returns 10 companies with that name, and the first result is a 2008 real-estate company with no employees. This project scores every candidate and shows a confidence level, so Sales knows which leads to trust and which to check by hand.

## How it works

```
companies.csv  ->  public register API  ->  best match  ->  lead score  ->  enriched_leads.csv  ->  Salesforce Leads
(name, city)       (up to 5 candidates)     (confidence)    (Hot/Warm/Cold)                        (dry run by default)
```

1. **API client** (`src/api_client.py`): calls the free API recherche-entreprises.api.gouv.fr (no key needed), with a rate limit (about 5 calls per second), automatic retries with backoff on 429 and 5xx errors, timeouts and logging.
2. **Matching** (`src/matching.py`): scores each candidate from 0 to 100 using name similarity (accents, punctuation and legal forms removed, brand names in brackets included), active status, real employer, and city match or mismatch. Result: high, medium or low confidence.
3. **Lead scoring** (`src/scoring.py`): simple rules a Sales manager can read: headcount (SMEs score highest), company age, sector and number of sites. Every score comes with its reasons.
4. **Enrichment run** (`src/enrich.py`): processes the CSV, never stops on one bad row, sorts by score and writes the output.
5. **Salesforce push** (`src/salesforce_push.py`): maps leads to standard Lead fields, skips low-confidence matches and closed companies, checks for duplicates by SIREN before creating, and runs in dry-run mode unless `--send` is given.

## Example result

Run on 20 October 2026 with real public register data ([full file](output/example_enriched_leads.csv)):

| Input name | Confidence | Legal name | City | Headcount | Score | Rating |
|---|---|---|---|---|---|---|
| Le Slip Francais | high | LE SLIP FRANCAIS | Paris | 50-99 | 75 | Hot |
| Ankorstore | high | ANKORSTORE | Paris | 100-199 | 70 | Hot |
| Ulule | high | ULULE | Paris | 50-99 | 70 | Hot |
| Ornikar | **medium** | ORNIKAR ASSURANCES | Paris | 20-49 | 65 | Warm |
| Back Market | high | JUNG S.A.S | Paris | 250-499 | 55 | Warm |
| Pennylane | high | PENNYLANE | Paris | 250-499 | 50 | Warm |
| Swile | high | SWILE | Montpellier | 500-999 | 40 | Cold |
| Livementor | not found | - | - | - | - | - |

What the results show:
- **Pennylane**: the right company (the 2019 software company with 250 to 499 employees) was picked, not the first API result.
- **Back Market**: matched through its brand name, because its legal name is JUNG S.A.S.
- **Ornikar**: medium confidence, so it is flagged for a manual check. The register returned the insurance subsidiary, not the main company.
- **Livementor**: not found under that name, so it is reported instead of being guessed.

## How to run

```bash
pip install -r requirements.txt

# 1. Enrich the sample list (calls the real public API)
python -m src.enrich --input data/companies_sample.csv --output output/enriched_leads.csv

# 2. Preview the Salesforce leads (dry run, nothing is sent)
python -m src.salesforce_push --input output/enriched_leads.csv

# 3. Send to a free Salesforce Developer org
export SF_INSTANCE_URL=https://yourorg.my.salesforce.com
export SF_ACCESS_TOKEN=your_token      # for example from: sf org display --target-org yourorg
python -m src.salesforce_push --input output/enriched_leads.csv --send

# Run the tests (they use saved API responses, no network needed)
python -m pytest -q
```

## Design choices

- **Explainable over clever**: the lead score is a few readable rules, not a black box, so Sales can challenge it.
- **Confidence before automation**: only high and medium matches go to Salesforce. Low matches stay in the file for a human check.
- **Idempotent push**: running the push twice never creates the same lead twice.
- **Fail soft**: one API error is logged and the run continues.

## Limits and next steps

- Brand names often differ from legal names. Next step: also search by trade names (enseignes) and the website domain.
- The score rules are a starting point. With real conversion data, they could be tuned or replaced by a simple model.
- Add the contact person through a B2B data provider, so the Lead gets a real name and email.

## Tech stack

Python, requests, pandas, REST APIs, Salesforce REST API, pytest

## Project structure

```
sme-lead-enrichment/
  data/companies_sample.csv
  src/
    api_client.py        API calls, rate limit, retries
    matching.py          pick the right company and confidence level
    scoring.py           explainable lead score
    enrich.py            main run
    salesforce_push.py   create Leads in Salesforce
  tests/                 14 tests with saved API responses
  output/example_enriched_leads.csv
```

## Author

Saiteja Eleti - [LinkedIn](https://www.linkedin.com/in/saiteja-eleti-169028332/)
