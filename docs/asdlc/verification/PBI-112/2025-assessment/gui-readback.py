"""Run in CloudCompare Python Editor after gui-cloudcompare.py.
Reads the saved BIN through CloudCompare and compares every source cloud point.
"""
from pathlib import Path
import hashlib
import json
import os
import struct
import sys
from collections import Counter
import numpy as np
import pycc

sys.stdout = open('/tmp/lidar-cc-stdout.log', 'a')
sys.stderr = open('/tmp/lidar-cc-stderr.log', 'a')
repo = Path(os.environ.get('LIDAR_REPO', '/Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr'))
out = repo / 'docs/asdlc/verification/PBI-112/2025-assessment'
build = repo / 'build/research/lidar-2026-10-23'
binfile = build / 'cloudcompare-2025-assessment.bin'
cc = pycc.GetInstance()
params = pycc.FileIOFilter.LoadParameters()
params.alwaysDisplayLoadDialog = False
loaded = cc.loadFile(str(binfile), params)
loaded.setEnabled(False)
sources = {}
for site, filename in [('sniezna', 'sniezna-2025-100m.las'), ('pod-wanta', 'pod-wanta-2025-both-positions.las')]:
    raw = (build / filename).read_bytes()
    offset = struct.unpack_from('<I', raw, 96)[0]
    count = struct.unpack_from('<I', raw, 107)[0]
    dtype = np.dtype({'names': ['x', 'y', 'z', 'psid'], 'formats': ['<i4', '<i4', '<i4', '<u2'], 'offsets': [0, 4, 8, 18], 'itemsize': 34})
    arr = np.frombuffer(raw, dtype=dtype, count=count, offset=offset)
    xyz = np.column_stack([arr['x'], arr['y'], arr['z']]) * np.array(struct.unpack_from('<3d', raw, 131)) + np.array(struct.unpack_from('<3d', raw, 155))
    sources[site] = (arr, xyz)
result = {'bin_sha256': hashlib.sha256(binfile.read_bytes()).hexdigest(), 'clouds': [], 'markers': [], 'labels': [], 'viewports': []}
expected_markers = {}
expected_labels = []
for m in json.loads((out / 'gui-cloudcompare-log.json').read_text())['markers']:
    prefix = m['object_id'] + ' ' + m['source'] + ' ' + m['measurement_id'] + ' '
    for kind, xyz in [('XYZ datum unknown', [m['E'], m['N'], m['Z']]), ('XY / nearest-Z proxy', m['proxy_xyz'])]:
        expected_markers[prefix + kind] = xyz
        expected_labels.append(prefix + kind)


def walk(entity, site=None):
    name = entity.getName()
    if name.startswith('sniezna'):
        site = 'sniezna'
    if name.startswith('pod-wanta'):
        site = 'pod-wanta'
    if isinstance(entity, pycc.ccPointCloud) and name.startswith('PointSourceId'):
        ids = np.asarray(entity.getScalarField(entity.getScalarFieldIndexByName('record_index')).asArray(), dtype=np.int64)
        psid = np.asarray(entity.getScalarField(entity.getScalarFieldIndexByName('PointSourceId')).asArray())
        shift = entity.getGlobalShift()
        actual = np.asarray(entity.points(), dtype=np.float64) - np.array([shift.x, shift.y, shift.z])
        arr, xyz = sources[site]
        error = float(np.max(np.abs(actual - xyz[ids])))
        assert error < 0.0002, (name, error)
        assert np.array_equal(psid, arr['psid'][ids])
        result['clouds'].append({'site': site, 'name': name, 'points': len(ids), 'max_coordinate_error_m': error, 'record_index_and_psid_match': True})
    elif isinstance(entity, pycc.ccPointCloud) and name in expected_markers:
        shift = entity.getGlobalShift()
        actual = np.asarray(entity.points(), dtype=np.float64) - np.array([shift.x, shift.y, shift.z])
        error = float(np.max(np.abs(actual - np.array(expected_markers[name]))))
        assert actual.shape == (1, 3) and error < 0.0002
        result['markers'].append({'name': name, 'max_coordinate_error_m': error})
    elif isinstance(entity, pycc.cc2DLabel):
        result['labels'].append(name)
    elif isinstance(entity, pycc.cc2DViewportObject):
        result['viewports'].append(name)
    for i in range(entity.getChildrenNumber()):
        walk(entity.getChild(i), site)


walk(loaded)
assert len(result['labels']) == 22, len(result['labels'])
assert Counter(result['labels']) == Counter(expected_labels)
assert len(result['markers']) == 22
assert len(result['viewports']) == 11, len(result['viewports'])
assert len(result['clouds']) >= 14
result['status'] = 'PASS'
result['point_total_including_duplicate_crops'] = sum(c['points'] for c in result['clouds'])
result['limits'] = 'Coordinate tolerance covers native float32 storage only, not geodetic accuracy. Marker label identities/counts checked; this does not identify a cave threshold.'
(out / 'gui-readback.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
cc.updateUI()
cc.redrawAll()
