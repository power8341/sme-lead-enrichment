"""Pick the right company among several candidates.

A search for "Pennylane" in the public register returns 10 companies with that
name: a real-estate company from 2008, a closed company, and the fintech. Taking
the first result blindly gives the wrong company, so each candidate gets a match
score and we keep the best one, with a confidence level the Sales team can see.
"""

import re
import unicodedata
from difflib import SequenceMatcher


def normalise(text):
    """Uppercase, remove accents, punctuation and common legal suffixes."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"\(.*?\)", " ", text.upper())
    text = re.sub(r"[^A-Z0-9 ]", " ", text)
    text = re.sub(r"\b(SAS|SASU|SARL|SA|EURL|SCI|GMBH|LTD)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def name_similarity(a, b):
    return SequenceMatcher(None, normalise(a), normalise(b)).ratio()


def brand_names(nom_complet):
    """Brand names often appear in brackets: 'JUNG S.A.S (BACK MARKET) (J.G)'."""
    return re.findall(r"\(([^)]*)\)", nom_complet or "")


def candidate_score(input_name, candidate, input_postal_code=None, input_city=None):
    """Score from 0 to 100: how likely this candidate is the company we want."""
    siege = candidate.get("siege") or {}
    names = [candidate.get("nom_raison_sociale"), candidate.get("nom_complet")]
    names += brand_names(candidate.get("nom_complet"))
    best_name = max(name_similarity(input_name, n) for n in names)
    score = best_name * 60  # name is the main signal

    if candidate.get("etat_administratif") == "A":  # active company
        score += 15
    if candidate.get("tranche_effectif_salarie") not in (None, "NN", "00"):  # real employer
        score += 15
    city = normalise(siege.get("libelle_commune"))
    if input_postal_code and siege.get("code_postal") == str(input_postal_code):
        score += 10
    elif input_city and city.startswith(normalise(input_city)):
        score += 10
    elif input_city and city:  # the company is registered in another city
        score -= 15
    return round(max(score, 0), 1)


def best_match(input_name, candidates, input_postal_code=None, input_city=None):
    """Return (best_candidate, score, confidence) or (None, 0, 'not_found')."""
    if not candidates:
        return None, 0, "not_found"
    scored = [
        (candidate_score(input_name, c, input_postal_code, input_city), c) for c in candidates
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    score, candidate = scored[0]

    if score >= 80:
        confidence = "high"
    elif score >= 60:
        confidence = "medium"
    else:
        confidence = "low"
    return candidate, score, confidence
