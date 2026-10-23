#!/usr/bin/env python3
import argparse
from fractions import Fraction
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as E

M = '{http://www.music-encoding.org/ns/mei}'
S = '{http://www.w3.org/2000/svg}'
ID = '{http://www.w3.org/XML/1998/namespace}id'
HERE = Path(__file__).resolve().parent
args = None


def render(name, runner, suffix=''):
    result = {}
    for mode in ['mei', 'svg', 'observer']:
        process = subprocess.run([runner, args.resources, mode, str(HERE / 'options.json'), 'unused'],
                                 input=(HERE / 'fixtures/mrest-key' / name).read_bytes(), capture_output=True)
        (Path(args.output) / f'{name}{suffix}.{mode}').write_bytes(process.stdout)
        (Path(args.output) / f'{name}{suffix}.{mode}.stderr').write_bytes(process.stderr)
        assert process.returncode == 0 and not process.stderr, (name, mode, process.stderr)
        result[mode] = process.stdout
    return result


def clocks(data):
    return {row[0]: row[1:] for line in data.decode().splitlines() if (row := line.split('\t'))}


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
                    self.assertEqual(parents[parents[key]].get('n'), staff)
                    self.assertEqual(times[keyid][:4], ['keySig', parents[parents[parents[key]]].get(ID), staff, '1'])
                    self.assertEqual(Fraction(times[keyid][4]), Fraction(3, 4))
                    group = next(e for e in svg.iter() if e.get('id') == keyid)
                    uses = list(group.iter(S + 'use'))
                    self.assertEqual(len(uses), 5 if name == 'cancel.krn' else 3)
                    glyph = '#E261-' if name == 'cancel.krn' else '#E262-'
                    self.assertTrue(all((u.get('{http://www.w3.org/1999/xlink}href') or u.get('href', '')).startswith(glyph) for u in uses))
                    if field == 1:
                        clef = next(e for e in parents[key] if e.get(ID) == f'clef-L{clefline}F1')
                        self.assertEqual(list(parents[key]).index(clef) < list(parents[key]).index(key), clefline < keyline)
                        self.assertEqual(Fraction(times[clef.get(ID)][4]), Fraction(3, 4))
                self.assertEqual(len(list(model.iter(M + 'mRest'))), 2)
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline-runner')
    args, remaining = parser.parse_known_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    unittest.main(argv=['verify-mrest-key.py', *remaining])
