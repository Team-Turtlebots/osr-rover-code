from datetime import datetime

import pytest

from osr_biodiversity.observations import ObservationStore


def fixed_clock():
    return datetime(2026, 12, 5, 14, 30, 0)


@pytest.fixture
def store(tmp_path):
    return ObservationStore(tmp_path / 'bio', clock=fixed_clock)


def test_add_photo_saves_file_and_pending_row(store):
    row = store.add_photo(b'jpegdata', source='rover', organ='leaf')
    assert row['id'] == '1'
    assert row['photo'] == '2026-12-05/img_00001.jpg'
    assert row['status'] == 'pending'
    assert row['time'] == '2026-12-05T14:30:00'
    assert store.read_photo(row['photo']) == b'jpegdata'


def test_ids_increase_and_recent_is_newest_first(store):
    for _ in range(3):
        store.add_photo(b'x', source='phone')
    assert [r['id'] for r in store.recent(2)] == ['3', '2']


def test_apply_results_records_top_match_and_alternatives(store):
    row = store.add_photo(b'x', source='rover')
    results = [
        {'scientific_name': 'Acer rubrum', 'common_name': 'Red maple', 'score': 0.82},
        {'scientific_name': 'Acer saccharinum', 'common_name': '', 'score': 0.09},
        {'scientific_name': 'Acer negundo', 'common_name': '', 'score': 0.03},
    ]
    updated = store.apply_results(row['id'], results)
    assert updated['status'] == 'identified'
    assert updated['scientific_name'] == 'Acer rubrum'
    assert updated['score'] == '0.820'
    assert updated['alternatives'] == 'Acer saccharinum (0.09); Acer negundo (0.03)'
    assert store.pending() == []


def test_no_results_means_no_match(store):
    row = store.add_photo(b'x', source='rover')
    assert store.apply_results(row['id'], [])['status'] == 'no_match'


def test_rows_survive_a_restart(tmp_path):
    first = ObservationStore(tmp_path, clock=fixed_clock)
    first.add_photo(b'x', source='rover')
    second = ObservationStore(tmp_path, clock=fixed_clock)
    assert second.add_photo(b'y', source='rover')['id'] == '2'


def test_photo_path_rejects_escaping_the_data_folder(store):
    with pytest.raises(ValueError):
        store.photo_path('../../etc/passwd')


def test_update_rejects_unknown_fields(store):
    row = store.add_photo(b'x', source='rover')
    with pytest.raises(KeyError):
        store.update(row['id'], favourite_color='green')
