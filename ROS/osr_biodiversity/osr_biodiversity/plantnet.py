"""Client for the Pl@ntNet identification API (https://my.plantnet.org).

    results = identify(jpeg_bytes, 'leaf', api_key)
    # [{'scientific_name': 'Acer rubrum', 'common_name': 'Red maple',
    #   'family': 'Sapindaceae', 'score': 0.82}, ...]

No ROS imports, so it can be unit-tested without ROS. `requests` is imported
inside identify() so the parsing code can be tested without it.

API details (endpoint, parameters, response fields) were written from memory of
the v2 API. Check them against https://my.plantnet.org/doc if a call fails.
"""
import os

API_URL = 'https://my-api.plantnet.org/v2/identify/{project}'
ORGANS = ('auto', 'leaf', 'flower', 'fruit', 'bark')


class PlantNetError(Exception):
    """Identification failed in a way the user should hear about (no internet,
    bad API key, quota used up). The photo stays 'pending' so it can be retried."""


def load_api_key(path):
    """Read the API key from a file. Returns None if the file doesn't exist or is empty."""
    path = os.path.expanduser(path)
    try:
        with open(path, encoding='utf-8') as f:
            key = f.read().strip()
    except FileNotFoundError:
        return None
    return key or None


def parse_response(data, limit=3):
    """Turn a Pl@ntNet JSON response into a short list of matches, best first."""
    matches = []
    for result in data.get('results', [])[:limit]:
        species = result.get('species') or {}
        name = (species.get('scientificNameWithoutAuthor')
                or species.get('scientificName') or '').strip()
        if not name:
            continue
        common_names = species.get('commonNames') or []
        family = (species.get('family') or {}).get('scientificNameWithoutAuthor', '')
        matches.append({
            'scientific_name': name,
            'common_name': common_names[0] if common_names else '',
            'family': family,
            'score': float(result.get('score', 0.0)),
        })
    return matches


def identify(jpeg_bytes, organ, api_key, lang='en', project='all', timeout=20.0,
             session=None):
    """Send one photo to Pl@ntNet. Returns matches (an empty list means 'no match').

    Raises PlantNetError for problems the user can fix or retry later.
    `session` lets tests pass a fake; normally it's the requests module.
    """
    import requests

    if organ not in ORGANS:
        organ = 'auto'
    http = session or requests
    try:
        response = http.post(
            API_URL.format(project=project),
            params={'api-key': api_key, 'lang': lang},
            files=[('images', ('photo.jpg', jpeg_bytes, 'image/jpeg'))],
            data={'organs': organ},
            timeout=timeout,
        )
    except requests.exceptions.RequestException as e:
        raise PlantNetError(f"Couldn't reach Pl@ntNet. Check the rover has internet. ({e.__class__.__name__})") from e

    status = response.status_code
    if status == 404:          # Pl@ntNet answers 404 when no species matches
        return []
    if status in (401, 403):
        raise PlantNetError('Pl@ntNet rejected the API key. Check the key file on the rover.')
    if status == 429:
        raise PlantNetError("Pl@ntNet's daily identification limit is used up. Try again tomorrow.")
    if status >= 400:
        raise PlantNetError(f'Pl@ntNet returned an error (HTTP {status}).')
    try:
        return parse_response(response.json())
    except ValueError as e:
        raise PlantNetError("Pl@ntNet sent a reply the rover couldn't read.") from e
