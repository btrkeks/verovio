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


def render(name, mode, runner=None, suffix=''):
    process = subprocess.run([runner or args.runner, args.resources, mode, str(HERE / 'options.json'), 'unused'],
                             input=(HERE / 'fixtures/empty-span' / name).read_bytes(), capture_output=True)
    (Path(args.output) / f'{name}{suffix}.{mode}').write_bytes(process.stdout)
    (Path(args.output) / f'{name}{suffix}.{mode}.stderr').write_bytes(process.stderr)
    assert process.returncode == 0 and not process.stderr, (name, mode, process.stderr)
    return process.stdout


class EmptySpanContext(unittest.TestCase):
    def test_skipped_context_precedes_actual_measure_in_its_container(self):
        for name in ['global.krn', 'staff.krn', 'contexts.krn']:
            with self.subTest(name=name):
                model = E.fromstring(render(name, 'mei'))
                parents = {c: p for p in model.iter() for c in p}
                measures = list(model.iter(M + 'measure'))
                self.assertEqual(len(measures), 3, 'no phantom measures for empty barline spans')
                target = measures[1]
                self.assertEqual(target.get('n'), '2')
                source = (HERE / 'fixtures/empty-span' / name).read_text().splitlines()
                barline = next(i for i, line in enumerate(source, 1) if line.startswith('=2|:'))
                self.assertEqual(target.get(ID), f'measure-L{barline}')
                keyline = max(i for i, line in enumerate(source[:barline], 1) if line.startswith('*k['))
                if name == 'staff.krn':
                    expected = [(f'keysig-L{keyline}F1', '2f'), (f'keysig-L{keyline}F2', '1f')]
                elif name == 'contexts.krn':
                    expected = [(f'keysig-L{keyline}F1', '3f'), (f'keysig-L{keyline}F2', '1f')]
                else:
                    expected = [(f'keysig-L{keyline}F2', '1f')]
                for origin, sig in expected:
                    matches = [e for e in model.iter(M + 'keySig') if e.get(ID) == origin]
                    self.assertEqual(len(matches), 1, 'EMPTY_SPAN_KEY_LOST: preserve declaration before the next actual measure')
                    key = matches[0]
                    self.assertEqual(key.get('sig'), sig)
                    scoredef = parents[key]
                    while scoredef.tag != M + 'scoreDef':
                        scoredef = parents[scoredef]
                    self.assertIs(parents[scoredef], parents[target])
                    siblings = list(parents[target])
                    self.assertGreater(siblings.index(target), 0)
                    self.assertIs(siblings[siblings.index(target) - 1], scoredef)
                self.assertEqual(parents[target].get(ID), 'label-D1' if name == 'contexts.krn' else 'label-D')
                self.assertEqual(target.get('left'), 'rptstart')
                self.assertEqual(measures[0].get('right'), 'dbl')
                svg_bytes = render(name, 'svg')
                self.assertEqual(svg_bytes, render(name, 'observer-svg'), 'public/observer initialization and resources agree')
                svg = E.fromstring(svg_bytes)
                group = next(e for e in svg.iter() if e.get('id') == target.get(ID))
                staves = [e for e in group.iter() if 'staff' in e.get('class', '').split()]
                self.assertEqual(len(staves), 2)
                for index, staff in enumerate(staves):
                    keys = [e for e in staff.iter() if 'keySig' in e.get('class', '').split()]
                    flats = [u for key in keys for u in key.iter(S + 'use')
                             if (u.get('{http://www.w3.org/1999/xlink}href') or u.get('href', '')).startswith('#E260-')]
                    self.assertEqual(len(flats), (2 if name == 'staff.krn' else 3) if name in ['staff.krn', 'contexts.krn'] and index == 1 else 1)
                prefixes = [line.split('\t') for line in render(name, 'observer-prefix').decode().splitlines()]
                target_prefixes = [row for row in prefixes if row[:2] == ['prefix', target.get(ID)]]
                self.assertEqual(len(target_prefixes), 2)
                self.assertTrue(all(Fraction(row[7]) == -1 for row in target_prefixes), 'existing scoreDef alignment sentinel before native time zero')
                if name == 'contexts.krn':
                    self.assertFalse(any(e.get('sig') == '1s' for e in model.iter(M + 'keySig')), 'last declaration at the shared gap wins')
                    self.assertEqual(len(list(model.iter(M + 'meterSig'))), 4)

    def test_preamble_terminal_and_ignored_spans_do_not_create_music(self):
        for name in ['preamble.krn', 'ignored.krn']:
            with self.subTest(name=name):
                now = E.fromstring(render(name, 'mei'))
                expected_count = 1 if name == 'preamble.krn' else 3
                self.assertEqual(len(list(now.iter(M + 'measure'))), expected_count)
                keys = list(now.iter(M + 'keySig'))
                if name == 'ignored.krn':
                    self.assertFalse(any(e.get('sig') in ['1f', '3s'] for e in keys))
                self.assertFalse(any(e.get('sig') == '2f' for e in keys))
                if args.baseline_runner:
                    old = E.fromstring(render(name, 'mei', args.baseline_runner, '.baseline'))
                    tags = {M + tag for tag in ['keySig', 'clef', 'meterSig', 'note', 'rest', 'mRest']}
                    facts = lambda root: {e.get(ID): e.attrib for e in root.iter() if e.tag in tags}
                    self.assertEqual(facts(now), facts(old))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline-runner')
    args, remaining = parser.parse_known_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    unittest.main(argv=['verify-empty-span.py', *remaining])
