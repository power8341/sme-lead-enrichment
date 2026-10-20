# SME Lead Enrichment Flow for Sales

**Status: in progress**

A data enrichment flow that turns a simple list of company names into sales-ready leads. It looks up each company in the French public company register, adds useful business information, gives each lead a simple score and prepares the result for a CRM such as Salesforce.

## Why this project

Sales teams often start with incomplete prospect lists: a company name, sometimes a city, nothing else. Enriching these records with reliable public data helps them focus on the right companies and saves hours of manual research.

## How it works

1. Read a CSV of company names (and optional city).
2. Call the free French public company API (recherche-entreprises.api.gouv.fr) to find each company.
3. Add business information: SIREN number, sector (NAF code), headcount range, creation date, legal form, address.
4. Calculate a simple lead score based on company size, age and sector.
5. Handle errors properly: retries with backoff, rate limiting, logging of companies not found.
6. Export a clean CSV ready to import into a CRM.
7. Optional: push the enriched leads into a Salesforce developer org through the Salesforce REST API.

## Tech stack

Python, requests, pandas, SQL, REST APIs, Salesforce API

## Progress

- [] Project scope and data model
- [ ] API client with retries and logging
- [ ] Enrichment and lead scoring
- [x] CSV export and data quality checks
- [ ] Push to Salesforce developer org
- [ ] Tests and sample output

## Planned structure

```
sme-lead-enrichment/
  data/
    companies_sample.csv
  src/
    api_client.py
    enrich.py
    scoring.py
    salesforce_push.py
  tests/
  README.md
  requirements.txt
```

## Author

Saiteja Eleti - [LinkedIn](https://www.linkedin.com/in/saiteja-eleti-169028332/)
