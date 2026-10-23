#!/usr/bin/env python3
import argparse
import re
import sys
from fractions import Fraction
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as E

M = '{http://www.music-encoding.org/ns/mei}'
S = '{http://www.w3.org/2000/svg}'
ID = '{http://www.w3.org/XML/1998/namespace}id'
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
import ink
args = None


def render(name, runner, suffix=''):
    result = {}
    for mode in ['mei', 'svg', 'observer', 'observer-prefix']:
        process = subprocess.run([runner, args.resources, mode, str(HERE / 'options.json'), 'unused'],
                                 input=(HERE / 'fixtures/mrest-key' / name).read_bytes(), capture_output=True)
        (Path(args.output) / f'{name}{suffix}.{mode}').write_bytes(process.stdout)
        (Path(args.output) / f'{name}{suffix}.{mode}.stderr').write_bytes(process.stderr)
        assert process.returncode == 0 and not process.stderr, (name, mode, process.stderr)
        result[mode] = process.stdout
    return result


def clocks(data):
    return {row[0]: row[1:] for line in data.decode().splitlines() if (row := line.split('\t'))}


def staff_ink(path, origin):
    _, ids, parents = ink.load(path)
    element = ids[origin]
    staff = parents[element]
    while 'staff' not in staff.get('class', '').split():
        staff = parents[staff]
    lines = [float(re.findall(r'[-+]?\d*\.?\d+', child.get('d'))[1])
             for child in staff if ink.local(child) == 'path']
    top, space = lines[0], abs(lines[1] - lines[0])
    ancestors, parent = [], parents.get(element)
    while parent is not None:
        ancestors.append(parent)
        parent = parents.get(parent)
    paint = ink.DEFAULT
    for parent in reversed(ancestors):
        paint = ink.paint(parent, paint)
    paths = ink.paths(element, ids, (1 / space, 0, 0, 1 / space, 0, -top / space), paint)
    return [(path, tuple(round(value, 10) for value in matrix), paint)
            for path, matrix, paint in ink.normalize(paths)] if paths else []


class FullRestKey(unittest.TestCase):
    def test_tail_key_source_order_time_and_ink(self):
        for name in ['clef-key.krn', 'key-clef.krn', 'invisible.krn', 'cancel.krn']:
            with self.subTest(name=name):
                current = render(name, args.runner)
                model = E.fromstring(current['mei'])
                svg = E.fromstring(current['svg'])
                parents = {child: parent for parent in model.iter() for child in parent}
                times = clocks(current['observer'])
                source = (HERE / 'fixtures/mrest-key' / name).read_text().splitlines()
                keyline = next(i for i, line in enumerate(source, 1) if i > 6 and line.startswith('*k['))
                clefline = next(i for i, line in enumerate(source, 1) if i > 6 and line.startswith('*clef'))
                for field, staff in [(1, '2'), (2, '1')]:
                    keyid = f'keysig-L{keyline}F{field}'
                    matches = [e for e in model.iter(M + 'keySig') if e.get(ID) == keyid]
                    self.assertEqual(len(matches), 1, 'MREST_KEY_LOST: full-rest shortcut must retain the actual source declaration')
                    key = matches[0]
                    self.assertEqual(key.get('sig'), '0' if name == 'cancel.krn' else '3s')
                    self.assertEqual(key.get('type'), 'mid-measure')
                    self.assertEqual(parents[parents[parents[key]]].get('n'), '1')
                    self.assertEqual(parents[parents[key]].get('n'), staff)
                    self.assertEqual(times[keyid][:4], ['keySig', parents[parents[parents[key]]].get(ID), staff, '1'])
                    self.assertEqual(Fraction(times[keyid][4]), Fraction(3, 4))
                    group = next(e for e in svg.iter() if e.get('id') == keyid)
                    uses = list(group.iter(S + 'use'))
                    if name == 'cancel.krn':
                        normal = render('normal-cancel.krn', args.baseline_runner or args.runner, '.normal-control')
                        reference = next(e for e in E.fromstring(normal['svg']).iter() if e.get('id') == keyid)
                        self.assertEqual(key.get('cancelaccid'), 'before')
                        self.assertEqual(len(uses), len(list(reference.iter(S + 'use'))),
                                         'preserve existing normal inline-zero suppression, not a positive paint assertion')
                    else:
                        self.assertEqual(len(uses), 3)
                        self.assertTrue(all((u.get('{http://www.w3.org/1999/xlink}href') or u.get('href', '')).startswith('#E262-') for u in uses))
                    if name != 'cancel.krn':
                        reference_name = 'prefix-g2.krn' if name == 'key-clef.krn' else 'prefix-f4.krn'
                        reference = render(reference_name, args.baseline_runner or args.runner, '.register-control')
                        reference_svg = E.fromstring(reference['svg'])
                        staves = [e for e in reference_svg.iter() if 'staff' in e.get('class', '').split()]
                        staff_element = staves[0 if field == 2 else 1]
                        reference_key = next(e for e in staff_element.iter() if 'keySig' in e.get('class', '').split())
                        self.assertEqual(staff_ink(Path(args.output) / f'{name}.svg', keyid),
                                         staff_ink(Path(args.output) / f'{reference_name}.register-control.svg', reference_key.get('id')),
                                         'actual source key register, complete glyph affine and presentation paint in staff space')
                    if field == 1:
                        clef = next(e for e in parents[key] if e.get(ID) == f'clef-L{clefline}F1')
                        self.assertEqual(list(parents[key]).index(clef) < list(parents[key]).index(key), clefline < keyline)
                        self.assertEqual(Fraction(times[clef.get(ID)][4]), Fraction(3, 4))
                self.assertEqual(len(list(model.iter(M + 'mRest'))), 2)
                measure_id = next(model.iter(M + 'measure')).get(ID)
                endpoints = {r[1]: Fraction(r[2]) for line in current['observer-prefix'].decode().splitlines()
                             if (r := line.split('\t'))[0] == 'measure-end'}
                self.assertEqual(endpoints[measure_id], Fraction(3, 4))
                if name == 'invisible.krn':
                    self.assertTrue(all(e.get('visible') == 'false' for e in model.iter(M + 'mRest')))
                if args.baseline_runner:
                    previous = render(name, args.baseline_runner, '.baseline')
                    old = E.fromstring(previous['mei'])
                    tags = {M + tag for tag in ['note', 'rest', 'mRest', 'clef', 'pedal', 'dir', 'tempo', 'meterSig']}
                    stable = lambda root: {e.get(ID): e.attrib for e in root.iter() if e.tag in tags}
                    self.assertEqual(stable(model), stable(old))
                    selected = lambda rows: {k: v for k, v in clocks(rows).items() if k.startswith(('note-', 'rest-', 'mrest-', 'clef-'))}
                    self.assertEqual(selected(current['observer']), selected(previous['observer']))
                    for field in [1, 2]:
                        origin = f'mrest-L7F{field}'
                        self.assertEqual(staff_ink(Path(args.output) / f'{name}.svg', origin),
                                         staff_ink(Path(args.output) / f'{name}.baseline.svg', origin),
                                         'full-rest glyph, vertical register, affine and inherited presentation preserved through reflow')


    def test_split_layer_has_one_key_owner_at_the_rest_end(self):
        current = render('split.krn', args.runner)
        model = E.fromstring(current['mei'])
        parents = {c: p for p in model.iter() for c in p}
        keys = [e for e in model.iter(M + 'keySig') if e.get(ID) == 'keysig-L10F1']
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0].get('sig'), '3s')
        self.assertEqual(parents[keys[0]].get('n'), '1')
        row = clocks(current['observer'])['keysig-L10F1']
        self.assertEqual(row[2:4], ['1', '1'])
        self.assertEqual(Fraction(row[4]), Fraction(3, 4))
        svg = E.fromstring(current['svg'])
        source = next(e for e in svg.iter() if e.get('id') == 'keysig-L10F1')
        self.assertEqual(len(list(source.iter(S + 'use'))), 3)
        self.assertEqual(len(list(model.iter(M + 'mRest'))), 2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline-runner')
    args, remaining = parser.parse_known_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    unittest.main(argv=['verify-mrest-key.py', *remaining])
