import io
from datetime import datetime

import pytest

pytest.importorskip('flask')

from osr_biodiversity.observations import ObservationStore  # noqa: E402
from osr_biodiversity.plantnet import PlantNetError  # noqa: E402
from osr_biodiversity.web_app import create_app  # noqa: E402

MATCH = [{'scientific_name': 'Acer rubrum', 'common_name': 'Red maple',
          'family': 'Sapindaceae', 'score': 0.82}]


class FakeCamera:
    def __init__(self, jpeg=b'\xff\xd8camera\xff\xd9'):
        self.jpeg = jpeg

    def __call__(self, max_width=None, quality=None):
        return self.jpeg


def make_client(tmp_path, camera=None, identifier=None):
    store = ObservationStore(tmp_path, clock=lambda: datetime(2026, 12, 5, 10, 0, 0))
    app = create_app(camera or FakeCamera(), store, identifier=identifier,
                     get_status=lambda: {'camera_ok': True},
                     normalize_upload=lambda data: data)
    return app.test_client(), store


def test_page_loads(tmp_path):
    client, _ = make_client(tmp_path)
    r = client.get('/')
    assert r.status_code == 200
    assert b'Marpy Field Station' in r.data


def test_identify_from_camera_records_match(tmp_path):
    seen = []
    client, store = make_client(tmp_path, identifier=lambda jpeg, organ: seen.append(organ) or MATCH)
    r = client.post('/api/identify', data={'organ': 'leaf'})
    body = r.get_json()
    assert r.status_code == 200
    assert body['results'][0]['scientific_name'] == 'Acer rubrum'
    assert body['observation']['status'] == 'identified'
    assert seen == ['leaf']
    assert store.read_photo(body['observation']['photo']) == b'\xff\xd8camera\xff\xd9'


def test_identify_without_camera_frame_is_503(tmp_path):
    client, _ = make_client(tmp_path, camera=FakeCamera(jpeg=None))
    assert client.post('/api/identify').status_code == 503


def test_without_api_key_photo_stays_pending(tmp_path):
    client, store = make_client(tmp_path, identifier=None)
    body = client.post('/api/identify').get_json()
    assert body['observation']['status'] == 'pending'
    assert len(store.pending()) == 1


def test_plantnet_error_keeps_photo_pending_with_note(tmp_path):
    def offline(jpeg, organ):
        raise PlantNetError('no internet')
    client, store = make_client(tmp_path, identifier=offline)
    body = client.post('/api/identify').get_json()
    assert body['observation']['status'] == 'pending'
    assert body['observation']['notes'] == 'no internet'


def test_upload_from_phone(tmp_path):
    client, _ = make_client(tmp_path, identifier=lambda jpeg, organ: MATCH)
    r = client.post('/api/upload', data={'organ': 'flower',
                                         'photo': (io.BytesIO(b'phonejpeg'), 'IMG_1.jpg')},
                    content_type='multipart/form-data')
    body = r.get_json()
    assert body['observation']['source'] == 'phone'
    assert body['observation']['organ'] == 'flower'


def test_upload_without_file_is_400(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.post('/api/upload', data={}).status_code == 400


def test_retry_identifies_pending_photos(tmp_path):
    client, store = make_client(tmp_path, identifier=None)
    client.post('/api/identify')
    client.post('/api/identify')
    # now "the key works": build a new app on the same store
    app = create_app(FakeCamera(), store, identifier=lambda jpeg, organ: MATCH,
                     normalize_upload=lambda data: data)
    body = app.test_client().post('/api/retry').get_json()
    assert body['identified'] == 2
    assert body['still_pending'] == 0


def test_observations_photo_and_csv_routes(tmp_path):
    client, _ = make_client(tmp_path, identifier=lambda jpeg, organ: MATCH)
    photo = client.post('/api/identify').get_json()['observation']['photo']
    listing = client.get('/api/observations').get_json()['observations']
    assert listing[0]['scientific_name'] == 'Acer rubrum'
    assert client.get('/photos/' + photo).status_code == 200
    assert client.get('/photos/../observations.csv').status_code == 404
    assert b'Acer rubrum' in client.get('/observations.csv').data


def test_status(tmp_path):
    client, _ = make_client(tmp_path, identifier=None)
    s = client.get('/api/status').get_json()
    assert s == {'plantnet_ready': False, 'pending': 0, 'camera_ok': True}
