import pytest

from osr_biodiversity.plantnet import PlantNetError, identify, load_api_key, parse_response

SAMPLE = {
    'results': [
        {'score': 0.82, 'species': {
            'scientificNameWithoutAuthor': 'Acer rubrum',
            'commonNames': ['Red maple', 'Swamp maple'],
            'family': {'scientificNameWithoutAuthor': 'Sapindaceae'}}},
        {'score': 0.09, 'species': {
            'scientificNameWithoutAuthor': 'Acer saccharinum', 'commonNames': []}},
        {'score': 0.01, 'species': {'scientificNameWithoutAuthor': 'Acer negundo'}},
        {'score': 0.005, 'species': {'scientificNameWithoutAuthor': 'Acer platanoides'}},
    ]
}


def test_parse_response_keeps_best_three():
    matches = parse_response(SAMPLE)
    assert [m['scientific_name'] for m in matches] == ['Acer rubrum', 'Acer saccharinum', 'Acer negundo']
    assert matches[0]['common_name'] == 'Red maple'
    assert matches[0]['family'] == 'Sapindaceae'
    assert matches[1]['common_name'] == ''


def test_parse_response_handles_empty():
    assert parse_response({}) == []


def test_load_api_key(tmp_path):
    assert load_api_key(tmp_path / 'missing') is None
    key_file = tmp_path / 'key'
    key_file.write_text('  abc123\n')
    assert load_api_key(key_file) == 'abc123'


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError('no json')
        return self._payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


requests = pytest.importorskip('requests')


def test_identify_success_sends_organ_and_key():
    session = FakeSession(FakeResponse(200, SAMPLE))
    matches = identify(b'jpg', 'leaf', 'KEY', session=session)
    assert matches[0]['scientific_name'] == 'Acer rubrum'
    url, kwargs = session.calls[0]
    assert url.endswith('/v2/identify/all')
    assert kwargs['params']['api-key'] == 'KEY'
    assert kwargs['data'] == {'organs': 'leaf'}


def test_identify_unknown_organ_becomes_auto():
    session = FakeSession(FakeResponse(200, SAMPLE))
    identify(b'jpg', 'root', 'KEY', session=session)
    assert session.calls[0][1]['data'] == {'organs': 'auto'}


def test_identify_404_means_no_match():
    assert identify(b'jpg', 'leaf', 'KEY', session=FakeSession(FakeResponse(404))) == []


@pytest.mark.parametrize('status', [401, 403, 429, 500])
def test_identify_http_errors_raise(status):
    with pytest.raises(PlantNetError):
        identify(b'jpg', 'leaf', 'KEY', session=FakeSession(FakeResponse(status)))


def test_identify_no_internet_raises():
    session = FakeSession(error=requests.exceptions.ConnectionError('offline'))
    with pytest.raises(PlantNetError, match='internet'):
        identify(b'jpg', 'leaf', 'KEY', session=session)
