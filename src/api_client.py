"""Client for the French public company register API (recherche-entreprises.api.gouv.fr).

The API is free and needs no key. It allows about 7 requests per second, so the
client waits between calls and retries automatically on temporary errors.
"""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://recherche-entreprises.api.gouv.fr/search"
logger = logging.getLogger(__name__)


class CompanyRegisterClient:
    def __init__(self, min_interval=0.2, timeout=10, max_retries=4):
        self.min_interval = min_interval  # seconds between two calls (rate limit)
        self.timeout = timeout
        self._last_call = 0.0

        retry = Retry(
            total=max_retries,
            backoff_factor=1,  # waits 1s, 2s, 4s, 8s between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
        )
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update({"User-Agent": "sme-lead-enrichment/1.0"})

    def _wait_for_rate_limit(self):
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()

    def search(self, name, postal_code=None, per_page=5):
        """Return the list of candidate companies for a name (can be empty)."""
        params = {"q": name, "page": 1, "per_page": per_page}
        if postal_code:
            params["code_postal"] = postal_code

        self._wait_for_rate_limit()
        try:
            response = self.session.get(BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as error:
            logger.error("API call failed for %r: %s", name, error)
            raise

        results = response.json().get("results", [])
        logger.debug("%d candidates for %r", len(results), name)
        return results
