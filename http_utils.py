import time
import requests


def get_json(url, params=None, timeout=10, retries=3, backoff=1):
    last_exc = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last_exc = e
            if attempt < retries - 1:
                time.sleep(backoff * (2 ** attempt))
            else:
                raise
    raise last_exc


def get_content(url, timeout=10, retries=3, backoff=1):
    last_exc = None
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.content
        except requests.RequestException as e:
            last_exc = e
            if attempt < retries - 1:
                time.sleep(backoff * (2 ** attempt))
            else:
                raise
    raise last_exc
