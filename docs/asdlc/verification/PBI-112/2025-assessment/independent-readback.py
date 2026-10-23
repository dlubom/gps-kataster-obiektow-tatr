#!/usr/bin/env python3
"""Independent byte/CSV readback; never imports analysis.py or uses NumPy.

Run from the repository: .venv/bin/python <path-to-this-file>
Only PyYAML is external. Writes independent-readback.json beside this script.
Checks numerical reproduction, not whether an entrance/threshold was identified.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
import struct
from collections import Counter, defaultdict, namedtuple
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
FIELDS = ('record_index X_easting Y_northing Z classification PointSourceId '
          'return_number number_of_returns scan_direction_flag edge_of_flight_line '
          'synthetic keypoint withheld scan_angle_rank gps_time intensity red green blue').split()
Point = namedtuple('Point', FIELDS)
CHECKS = 0


def check(condition, message):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(message)


def equal(actual, expected, label, tolerance=1e-7):
    if isinstance(actual, (float, int)) and isinstance(expected, (float, int)):
        check(abs(actual-expected) <= tolerance, f'{label}: {actual!r} != {expected!r}')
    elif isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        check(len(actual) == len(expected), label+' length')
        for a, e in zip(actual, expected):
            equal(a, e, label, tolerance)
    else:
        check(actual == expected, f'{label}: {actual!r} != {expected!r}')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(rows, field):
    return {str(k): v for k, v in sorted(Counter(getattr(p, field) for p in rows).items())}


def acceptable(p):
    return p.classification not in (7, 18) and not p.withheld


def xyz(p):
    return p.X_easting, p.Y_northing, p.Z


def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def csv_rows(base, name):
    with (base/name).open(newline='') as stream:
        return list(csv.DictReader(stream))


def record_check(row, points, clip):
    p = points[int(row['record_index'])]
    if 'clip' in row:
        equal(row['clip'], clip, 'record clip')
    for field in FIELDS:
        equal(float(row[field]), getattr(p, field), f'{clip} #{p.record_index} {field}')
    return p


def read_las(path):
    raw = path.read_bytes()
    check(raw[:4] == b'LASF' and raw[24:26] == bytes([1, 2]), path.name+' LAS 1.2')
    start = struct.unpack_from('<I', raw, 96)[0]
    fmt, size, n = struct.unpack_from('<BHI', raw, 104)
    check(fmt == 3 and size == 34 and len(raw) == start+n*size, path.name+' record layout')
    scale, offset = struct.unpack_from('<3d', raw, 131), struct.unpack_from('<3d', raw, 155)
    equal(scale, (.01, .01, .01), 'scale'); equal(offset, (0., 0., 0.), 'offset')
    points = []
    for i, r in enumerate(struct.iter_unpack('<3iHBBbBHd3H', raw[start:])):
        x, y, z = (r[k]*scale[k]+offset[k] for k in range(3))
        intensity, bits, flags, scan, _, sid, gps, red, green, blue = r[3:]
        points.append(Point(i, x, y, z, flags & 31, sid, bits & 7, (bits >> 3) & 7,
                            bits >> 6 & 1, bits >> 7 & 1, flags >> 5 & 1,
                            flags >> 6 & 1, flags >> 7 & 1, scan, gps,
                            intensity, red, green, blue))
    # Read GeoTIFF keys independently of the analytical reader.
    position = struct.unpack_from('<H', raw, 94)[0]
    keys, vlr_ids = {}, []
    for _ in range(struct.unpack_from('<I', raw, 100)[0]):
        _, _, rid, length, _ = struct.unpack_from('<H16sHH32s', raw, position)
        position += 54; payload = raw[position:position+length]; position += length
        vlr_ids.append(rid)
        if rid == 34735:
            values = struct.unpack('<'+'H'*(length//2), payload)
            for k in range(4, len(values), 4):
                keys[values[k]] = values[k+1:k+4]
    equal(keys[3072], (0, 1, 2180), 'horizontal EPSG')
    check(not any(k in keys for k in range(4096, 4100)), 'no vertical GeoTIFF CRS')
    check(2112 not in vlr_ids, 'no WKT CRS VLR')
    return points


def centroid(rows):
    return [math.fsum(xyz(p)[k] for p in rows)/len(rows) for k in range(3)]


def extrema(rows, function):
    return [function(xyz(p)[k] for p in rows) for k in range(3)]


def grid_groups(rows, origin, width):
    # Integer centimetres avoid float ambiguity at half-open cell boundaries.
    step = round(width*100); groups = defaultdict(list)
    for p in rows:
        key = tuple((round(xyz(p)[k]*100)-origin[k])//step for k in (0, 1))
        groups[key].append(p)
    return groups


def validate(base, data_dir, result):
    report = json.loads((base/'analysis.json').read_text())
    manifest = json.loads((base.parent/'inspection.json').read_text())
    watched = [base/'analysis.json', base.parent/'inspection.json', Path(__file__)]
    watched += sorted(base.glob('*.csv'))
    watched += [ROOT/s['yaml']['path'] for s in report['sites']]
    initial = {str(p.relative_to(ROOT)): sha(p) for p in watched}
    result['input_sha256'] = initial
    result['source_files'] = {}
    for name, expected in manifest.items():
        path = data_dir/name
        equal(path.stat().st_size, expected['bytes'], name+' size')
        equal(sha(path), expected['sha256'], name+' hash')
        result['source_files'][name] = {'sha256': expected['sha256'], 'bytes': expected['bytes']}
    markers = csv_rows(base, 'markers.csv')
    spread = csv_rows(base, 'vertical-spread-diagnostic.csv')
    clouds, per_site = {}, []
    for site in report['sites']:
        clip = site['file']; points = read_las(data_dir/clip); clouds[clip] = points
        valid = [p for p in points if acceptable(p)]
        origin = [round(min(xyz(p)[k] for p in points)*100) for k in (0, 1)]
        equal(len(points), manifest[clip]['count'], clip+' count')
        equal(counts(points, 'classification'), manifest[clip]['class_counts'], 'classes')
        equal(counts(points, 'PointSourceId'), manifest[clip]['source_id_counts'], 'sources')
        equal(len(valid), site['counts']['accepted'], 'accepted count')
        original = yaml.safe_load((ROOT/site['yaml']['path']).read_text())
        equal(original['measurements'], site['yaml']['original_measurements'], 'YAML measurements')
        equal(sha(ROOT/site['yaml']['path']), site['yaml']['sha256'], 'YAML SHA')
        stats = {'clip': clip, 'all_records': len(points), 'measurements': [], 'section_csv_rows': 0}
        for m in site['measurements']:
            y = next(v for v in original['measurements'] if v['id'] == m['id'])
            equal([m['X'], m['Y'], m['Z']], [y['y_1992'], y['x_1992'], y['elevation_m']], 'axis mapping')
            equal(y['elevation_datum'], 'unknown', 'catalogue datum')
            near = [(distance(xyz(p), (m['X'], m['Y'])), p) for p in valid]
            d, p = min(near, key=lambda v: (v[0], v[1].record_index))
            pr = m['nearest_xy_record']; record_check(pr, points, clip)
            equal(p.record_index, pr['record_index'], 'nearest accepted XY'); equal(d, pr['distance_xy_m'], 'nearest dXY')
            marker = next(v for v in markers if v['object'] == m['object'] and v['id'] == m['id'])
            equal([float(marker[k]) for k in ('X', 'Y', 'Z')], [m['X'], m['Y'], m['Z']], 'marker XYZ')
            equal(int(marker['nearest_record_index']), p.record_index, 'marker index')
            equal([float(marker[k]) for k in ('nearest_X', 'nearest_Y', 'nearest_Z')], xyz(p), 'marker nearest XYZ')
            equal([float(marker[k]) for k in ('anchor_X_unmeasured', 'anchor_Y_unmeasured', 'anchor_Z_unmeasured')], [m['X'], m['Y'], p.Z], 'unmeasured anchor')
            equal(float(marker['nearest_distance_xy_m']), d, 'marker nearest dXY')
            for radial in m['radial_diagnostics']:
                subset = [q for dd, q in near if dd <= radial['radius_m']]; zs = sorted(q.Z for q in subset)
                quantiles = []
                for fraction in (0., .1, .5, .9, 1.):
                    if zs:
                        pos = (len(zs)-1)*fraction; lower = int(pos); upper = min(lower+1, len(zs)-1)
                        quantiles.append(zs[lower]+(zs[upper]-zs[lower])*(pos-lower))
                equal(len(subset), radial['count'], 'radial count')
                equal(quantiles, radial['z_quantiles_0_10_50_90_100'], 'radial quantiles')
                equal(counts(subset, 'classification'), radial['classification'], 'radial classes')
                equal(counts(subset, 'PointSourceId'), radial['PointSourceId'], 'radial sources')
            for group in m['nearest_xy_by_group']:
                dd, q = min(((dd, q) for dd, q in near if q.PointSourceId == group['PointSourceId']
                             and (group['subset'] == 'accepted' or q.classification == 2)), key=lambda v: (v[0], v[1].record_index))
                equal(q.record_index, group['record_index'], 'group nearest'); equal(dd, group['distance_xy_m'], 'group dXY')
                record_check(group, points, clip)
            angle = math.radians(site['exposure_azimuth_deg']); sn, cs = math.sin(angle), math.cos(angle)
            uv = [(q, (q.X_easting-m['X'])*sn+(q.Y_northing-m['Y'])*cs,
                   (q.X_easting-m['X'])*cs-(q.Y_northing-m['Y'])*sn) for dd, q in near if dd <= 13]
            section_rows = csv_rows(base, f"{site['slug']}-{m['source'].lower()}-sections-1m.csv")
            expected_indices = set()
            for section in m['sections']:
                values = [(q, u, v) if section['orientation'] == 'podłużny' else (q, v, u) for q, u, v in uv]
                selected = [(q, along, cross) for q, along, cross in values if abs(along) <= 12 and abs(cross) <= section['full_width_m']/2]
                equal(len(selected), section['count'], 'section count')
                equal(counts([v[0] for v in selected], 'classification'), section['class_counts'], 'section classes')
                equal(counts([v[0] for v in selected], 'PointSourceId'), section['PointSourceId_counts'], 'section sources')
                if section['full_width_m'] == 1:
                    expected_indices.update((section['orientation'], q.record_index) for q, _, _ in selected)
            equal({(r['section'], int(r['record_index'])) for r in section_rows}, expected_indices, 'CSV section completeness')
            equal(len(section_rows), len(expected_indices), 'CSV section uniqueness')
            for row in section_rows:
                q = record_check(row, points, clip); dx, dy = q.X_easting-m['X'], q.Y_northing-m['Y']
                along, cross = dx*sn+dy*cs, dx*cs-dy*sn
                if row['section'] != 'podłużny': along, cross = cross, along
                equal(float(row['along_m']), along, 'CSV along', 5.1e-7); equal(float(row['cross_m']), cross, 'CSV cross', 5.1e-7)
            for width in (.25, .5, 1.):
                groups = grid_groups([q for dd, q in near if dd <= 12], origin, width)
                keys = sorted((k for k in groups if len(groups[k]) >= 8), key=lambda k: (-(max(q.Z for q in groups[k])-min(q.Z for q in groups[k])), k))[:20]
                rows = [r for r in spread if r['object'] == m['object'] and r['source_position'] == m['source'] and float(r['cell_size_m']) == width]
                equal(len(rows), len(keys), 'spread top20 count')
                for row, key in zip(rows, keys):
                    subset = groups[key]; lo = min(subset, key=lambda q: (q.Z, q.record_index)); hi = max(subset, key=lambda q: (q.Z, -q.record_index))
                    equal([float(row['cell_Xmin']), float(row['cell_Ymin'])], [origin[k]/100+key[k]*width for k in (0, 1)], 'spread cell')
                    equal(int(row['point_count']), len(subset), 'spread count'); equal(int(row['min_record_index']), lo.record_index, 'spread min index'); equal(int(row['max_record_index']), hi.record_index, 'spread max index')
                    equal(float(row['z_span_m']), hi.Z-lo.Z, 'spread span')
            stats['section_csv_rows'] += len(section_rows)
            stats['measurements'].append({'id': m['id'], 'source': m['source'], 'nearest_record_index': p.record_index, 'nearest_dxy_m': d, 'nearest_xyz': xyz(p), 'radial_ranges_checked': len(m['radial_diagnostics'])})
        per_site.append(stats)
    result['sites'] = per_site
    result['candidates'] = candidate_checks(base, report, clouds)
    support = csv_rows(base, 'support-points.csv')
    for row in support: record_check(row, clouds[row['clip']], row['clip'])
    result['support_rows_checked'] = len(support)
    for path in watched: equal(sha(path), initial[str(path.relative_to(ROOT))], 'input stable '+path.name)


def candidate_checks(base, report, clouds):
    pairs_csv = csv_rows(base, 'candidate-near-vertical-pairs.csv')
    cells_csv = csv_rows(base, 'candidate-stacked-cells-05m.csv'); results = []
    mapping = {'PW-C1': 'pod-wanta', 'SN-C1': 'sniezna'}
    for candidate in report['candidate_observations']:
        cid = candidate['candidate_id']; cfg = candidate['parameters']
        site = next(s for s in report['sites'] if s['slug'] == mapping[cid]); points = clouds[site['file']]
        x0, x1, y0, y1 = cfg['roi_xy']; a, b, c, d, e, f = cfg['lower_box_xyz']
        roi = [p for p in points if acceptable(p) and x0 <= p.X_easting <= x1 and y0 <= p.Y_northing <= y1]
        low = [p for p in roi if a <= p.X_easting <= b and c <= p.Y_northing <= d and e <= p.Z <= f]
        low_ids = {p.record_index for p in low}
        equal(len(low), candidate['lower_selected_points'], 'candidate lower count')
        equal(counts(low, 'classification'), candidate['lower_class_counts'], 'candidate classes')
        equal(counts(low, 'PointSourceId'), candidate['lower_PointSourceId_counts'], 'candidate sources')
        equal(extrema(low, min), candidate['lower_actual_xyz_min'], 'candidate min'); equal(extrema(low, max), candidate['lower_actual_xyz_max'], 'candidate max')
        equal(centroid(low), candidate['lower_sample_centroid_xyz'], 'candidate centroid')
        equal(len({(p.PointSourceId, p.gps_time) for p in low}), candidate['lower_unique_source_gps_time_pairs'], 'unique source/GPS pairs')
        ground = [p for p in low if p.classification == 2]
        equal(len(ground), candidate['lower_class2_sensitivity']['n'], 'class2 lower count'); equal(centroid(ground), candidate['lower_class2_sensitivity']['centroid_xyz'], 'class2 centroid')
        for sid, expected in candidate['lower_by_source'].items():
            selected = [p for p in low if p.PointSourceId == int(sid)]
            equal(len(selected), expected['n'], 'source lower count'); equal(counts(selected, 'classification'), expected['classes'], 'source lower classes')
            equal(extrema(selected, min), expected['min_xyz'], 'source min'); equal(extrema(selected, max), expected['max_xyz'], 'source max'); equal(centroid(selected), expected['centroid_xyz'], 'source centroid')
        rows = csv_rows(base, site['slug']+'-candidate-points.csv')
        equal({int(r['record_index']) for r in rows}, {p.record_index for p in roi}, 'candidate CSV completeness'); equal(len(rows), len(roi), 'candidate CSV uniqueness')
        for row in rows:
            p = record_check(row, points, site['file']); equal(int(row['selected_lower_box']), int(p.record_index in low_ids), 'candidate lower flag')
        expected_pairs = set()
        for p, q in combinations(roi, 2):
            if distance(xyz(p), xyz(q)) <= .12 and abs(p.Z-q.Z) >= 1.3:
                lo, hi = sorted((p, q), key=lambda v: v.Z); expected_pairs.add((lo.record_index, hi.record_index))
        rows = [r for r in pairs_csv if r['candidate_id'] == cid]
        equal({(int(r['lower_record_index']), int(r['upper_record_index'])) for r in rows}, expected_pairs, 'near-vertical pairs completeness'); equal(len(rows), len(expected_pairs), 'pair uniqueness')
        for row in rows:
            lo, hi = points[int(row['lower_record_index'])], points[int(row['upper_record_index'])]
            equal(float(row['distance_xy_m']), distance(xyz(lo), xyz(hi)), 'pair dXY'); equal(float(row['delta_z_m']), hi.Z-lo.Z, 'pair deltaZ')
            for side, p in [('lower', lo), ('upper', hi)]:
                equal(int(row[side+'_class']), p.classification, 'pair class'); equal(int(row[side+'_PointSourceId']), p.PointSourceId, 'pair source')
        for pair in candidate['representative_pairs']:
            lo = record_check(pair['lower'], points, site['file']); hi = record_check(pair['upper'], points, site['file'])
            check((lo.record_index, hi.record_index) in expected_pairs, 'representative pair membership')
            equal(pair['distance_xy_m'], distance(xyz(lo), xyz(hi)), 'representative dXY'); equal(pair['delta_z_m'], hi.Z-lo.Z, 'representative deltaZ')
        origin = [round(min(xyz(p)[k] for p in points)*100) for k in (0, 1)]
        groups = grid_groups(roi, origin, .5); summary = {}
        for subset in ('accepted', 'class2'):
            expected_cells = {}; same_source = {sid: 0 for sid in counts(points, 'PointSourceId')}
            for key, group in groups.items():
                group = [p for p in group if subset == 'accepted' or p.classification == 2]
                lower = [p for p in group if p.record_index in low_ids]; upper = [p for p in group if p.Z >= cfg['upper_z_min']]
                if len(lower) >= 2 and len(upper) >= 2:
                    expected_cells[key] = lower, upper
                    for sid in same_source:
                        if sum(p.PointSourceId == int(sid) for p in lower) >= 2 and sum(p.PointSourceId == int(sid) for p in upper) >= 2: same_source[sid] += 1
            rows = [r for r in cells_csv if r['candidate_id'] == cid and r['subset'] == subset]
            equal(len(rows), len(expected_cells), 'stacked cell count'); equal(len(rows), candidate['stacked_cells'][subset], 'JSON stacked count')
            equal(same_source, candidate['stacked_cells'][subset+'_by_same_PointSourceId'], 'stacked same-source counts')
            seen = set()
            for row in rows:
                key = tuple(round((float(row[field])-origin[k]/100)/.5) for k, field in enumerate(('cell_Xmin', 'cell_Ymin')))
                check(key in expected_cells and key not in seen, 'stacked cell membership/uniqueness'); seen.add(key)
                for side, selected in zip(('lower', 'upper'), expected_cells[key]):
                    equal([int(i) for i in row[side+'_record_indices'].split(';')], [p.record_index for p in selected], 'stacked indices')
                    equal(int(row[side+'_count']), len(selected), 'stacked count'); equal(float(row[side+'_z_min']), min(p.Z for p in selected), 'stacked min'); equal(float(row[side+'_z_max']), max(p.Z for p in selected), 'stacked max')
                    equal(json.loads(row[side+'_source_counts']), counts(selected, 'PointSourceId'), 'stacked sources')
            summary[subset] = len(rows)
        results.append({'candidate_id': cid, 'roi_records': len(roi), 'lower_records': len(low), 'near_vertical_pairs': len(expected_pairs), 'stacked_cells': summary})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT/'build/research/lidar-2026-10-23')
    parser.add_argument('--assessment-dir', type=Path, default=HERE)
    args = parser.parse_args(); result = {'status': 'running', 'utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(), 'pyyaml': yaml.__version__, 'method': 'independent struct reader, scalar arithmetic, integer-centimetre grid; analysis.py not imported', 'limitations': ['Does not validate visual interpretation, entrance identity or threshold location.', 'Does not resolve unknown catalogue vertical datums or prove distinct flight directions.', 'CSV/JSON numbers are checked; PNG pixels and GUI state are not checked by this script.']}
    try:
        validate(args.assessment_dir, args.data_dir, result)
        result['status'] = 'PASS'
    except Exception as error:
        result['status'] = 'FAIL'; result['error'] = f'{type(error).__name__}: {error}'
    result['assertions'] = CHECKS
    output = args.assessment_dir/'independent-readback.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'assertions': CHECKS, 'output': str(output), 'error': result.get('error')}, ensure_ascii=False))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
