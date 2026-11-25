"""Photo and observation log for Marpy.

Photos are saved as JPEG files in one folder per day, and every photo gets one
row in a single observations.csv:

    <data_dir>/
        observations.csv
        2026-12-05/img_00001.jpg
        2026-12-05/img_00002.jpg

This module has no ROS imports, so it can be unit-tested without ROS.
"""
import csv
import os
import tempfile
import threading
from datetime import datetime

FIELDS = [
    'id',               # 1, 2, 3, ...
    'time',             # local time the photo was taken, ISO 8601
    'photo',            # path relative to data_dir, e.g. 2026-12-05/img_00001.jpg
    'source',           # 'rover' (rover camera) or 'phone' (uploaded from a phone)
    'organ',            # plant part sent to Pl@ntNet: auto, leaf, flower, fruit, bark
    'status',           # pending, identified, no_match
    'scientific_name',  # top match
    'common_name',
    'score',            # 0.0 - 1.0 confidence of the top match
    'alternatives',     # next matches, "Name (0.09); Name (0.03)"
    'latitude',         # empty until a GPS is added
    'longitude',
    'reviewed',         # 'yes' once a person has checked the ID
    'notes',            # last error message, or a person's notes
]

STATUS_PENDING = 'pending'
STATUS_IDENTIFIED = 'identified'
STATUS_NO_MATCH = 'no_match'


class ObservationStore:
    """Thread-safe store of photos plus a CSV log. One instance per data folder."""

    def __init__(self, data_dir, clock=datetime.now):
        self.data_dir = os.path.realpath(os.path.expanduser(data_dir))
        self.csv_path = os.path.join(self.data_dir, 'observations.csv')
        self._clock = clock
        self._lock = threading.Lock()
        os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.csv_path):
            self._write_rows([])

    # ---- public API -------------------------------------------------------

    def add_photo(self, jpeg_bytes, source, organ='auto', latitude='', longitude=''):
        """Save a photo and add a 'pending' row for it. Returns the new row."""
        with self._lock:
            now = self._clock()
            rows = self._read_rows()
            obs_id = max((int(r['id']) for r in rows), default=0) + 1
            day = now.strftime('%Y-%m-%d')
            rel_path = f'{day}/img_{obs_id:05d}.jpg'
            abs_path = os.path.join(self.data_dir, rel_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, 'wb') as f:
                f.write(jpeg_bytes)

            row = {field: '' for field in FIELDS}
            row.update({
                'id': str(obs_id),
                'time': now.isoformat(timespec='seconds'),
                'photo': rel_path,
                'source': source,
                'organ': organ,
                'status': STATUS_PENDING,
                'latitude': str(latitude),
                'longitude': str(longitude),
                'reviewed': 'no',
            })
            rows.append(row)
            self._write_rows(rows)
            return dict(row)

    def update(self, obs_id, **fields):
        """Change fields of one row. Returns the updated row."""
        unknown = set(fields) - set(FIELDS)
        if unknown:
            raise KeyError(f'unknown observation fields: {sorted(unknown)}')
        with self._lock:
            rows = self._read_rows()
            for row in rows:
                if row['id'] == str(obs_id):
                    row.update({k: str(v) for k, v in fields.items()})
                    self._write_rows(rows)
                    return dict(row)
        raise KeyError(f'no observation with id {obs_id}')

    def apply_results(self, obs_id, results):
        """Record identification results (as returned by plantnet.identify)."""
        if not results:
            return self.update(obs_id, status=STATUS_NO_MATCH, scientific_name='',
                               common_name='', score='', alternatives='', notes='')
        top = results[0]
        alternatives = '; '.join(
            f"{r['scientific_name']} ({r['score']:.2f})" for r in results[1:3])
        return self.update(
            obs_id,
            status=STATUS_IDENTIFIED,
            scientific_name=top['scientific_name'],
            common_name=top.get('common_name', ''),
            score=f"{top['score']:.3f}",
            alternatives=alternatives,
            notes='',
        )

    def get(self, obs_id):
        with self._lock:
            for row in self._read_rows():
                if row['id'] == str(obs_id):
                    return dict(row)
        raise KeyError(f'no observation with id {obs_id}')

    def recent(self, limit=20):
        """Newest rows first."""
        with self._lock:
            rows = self._read_rows()
        return [dict(r) for r in reversed(rows[-limit:])] if limit > 0 else []

    def pending(self):
        with self._lock:
            return [dict(r) for r in self._read_rows() if r['status'] == STATUS_PENDING]

    def photo_path(self, rel_path):
        """Absolute path of a saved photo. Rejects paths outside data_dir."""
        abs_path = os.path.realpath(os.path.join(self.data_dir, rel_path))
        if not abs_path.startswith(self.data_dir + os.sep):
            raise ValueError(f'photo path outside the data folder: {rel_path}')
        return abs_path

    def read_photo(self, rel_path):
        with open(self.photo_path(rel_path), 'rb') as f:
            return f.read()

    # ---- CSV helpers (call with the lock held) ---------------------------

    def _read_rows(self):
        with open(self.csv_path, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            for field in FIELDS:          # tolerate CSVs from older versions
                row.setdefault(field, '')
        return rows

    def _write_rows(self, rows):
        # write to a temp file, then rename, so a crash never leaves half a CSV
        fd, tmp_path = tempfile.mkstemp(dir=self.data_dir, suffix='.csv.tmp')
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, self.csv_path)
