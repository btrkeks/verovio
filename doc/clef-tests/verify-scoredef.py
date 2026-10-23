#!/usr/bin/env python3
import argparse
from collections import Counter
import subprocess
import unittest
import xml.etree.ElementTree as E
from pathlib import Path

M = '{http://www.music-encoding.org/ns/mei}'
ID = '{http://www.w3.org/XML/1998/namespace}id'
S = '{http://www.w3.org/2000/svg}'
HERE = Path(__file__).resolve().parent
args = None


def render(name, mode, runner=None, suffix=''):
    result = subprocess.run([runner or args.runner, args.resources, mode, str(HERE / 'options.json'), 'unused'],
                            input=(HERE / 'fixtures/scoredef' / name).read_bytes(), capture_output=True)
    (Path(args.output) / f'{name}{suffix}.{mode}').write_bytes(result.stdout)
    (Path(args.output) / f'{name}{suffix}.{mode}.stderr').write_bytes(result.stderr)
    assert result.returncode == 0 and not result.stderr, (name, mode, result.stderr)
    return result.stdout


class ScoreDefPlacement(unittest.TestCase):
    def test_changes_immediately_precede_resolved_measure(self):
        for name in ['global.krn', 'staff.krn', 'transpose.krn']:
            with self.subTest(name=name):
                root = E.fromstring(render(name, 'mei'))
                parents = {child: parent for parent in root.iter() for child in parent}
                measures = {int(e.get('n')): e for e in root.iter(M + 'measure')}
                self.assertEqual(len(measures), 6)
                for number, role in [(2, 'ordinary'), (3, 'new-section'), (4, 'new-ending'),
                                     (5, 'continuing-ending'), (6, 'leaving-ending')]:
                    with self.subTest(number=number, role=role):
                        measure = measures[number]
                        container = parents[measure]
                        children = list(container)
                        self.assertGreater(children.index(measure), 0, "scoreDef must precede the first measure too")
                        previous = children[children.index(measure) - 1]
                        self.assertEqual(previous.tag, M + 'scoreDef',
                                         'SCOREDEF_PLACEMENT: change must immediately precede its measure in the same actual container')
                        self.assertTrue(list(previous.iter(M + 'keySig')))
                        self.assertEqual(len(list(previous.iter(M + 'meterSig'))), 2)
                        if number in [4, 5]:
                            self.assertEqual((container.tag, container.get(ID)), (M + 'ending', 'label-B1'))
                        else:
                            self.assertEqual(container.tag, M + 'section')
                svg = E.fromstring(render(name, 'svg'))
                for number in range(2, 7):
                    group = next(e for e in svg.iter() if e.get('id') == measures[number].get(ID))
                    keys = [e for e in group.iter() if 'keySig' in e.get('class', '').split()]
                    self.assertTrue(keys, (name, number, 'actual source key ink must be in target measure'))
                    self.assertTrue(any(list(e.iter(S + 'use')) for e in keys))

    def test_notes_state_and_signature_attributes_preserved(self):
        if not args.baseline_runner:
            self.skipTest('requires actual selected app archive runner')
        for name in ['global.krn', 'staff.krn', 'transpose.krn']:
            with self.subTest(name=name):
                now = E.fromstring(render(name, 'mei'))
                old = E.fromstring(render(name, 'mei', args.baseline_runner, '.baseline'))
                tags = {M + n for n in ['note', 'rest', 'clef', 'keySig', 'meterSig']}
                def facts(root):
                    source = {e.get(ID): e.attrib for e in root.iter() if e.tag in tags and '-L' in e.get(ID, '')}
                    parents = {child: parent for parent in root.iter() for child in parent}
                    generated = Counter((e.tag, parents[e].get('n'), tuple(sorted((k, v) for k, v in e.attrib.items() if k != ID)))
                                        for e in root.iter() if e.tag in tags and '-L' not in e.get(ID, ''))
                    return source, generated
                self.assertEqual(facts(now), facts(old))
                state = lambda r: [{k: v for k, v in e.attrib.items() if k != ID} for e in r.iter(M + 'staffDef') if e.get('trans.semi') is not None]
                self.assertEqual(state(now), state(old))
                current = render(name, 'observer').decode().splitlines()
                previous = render(name, 'observer', args.baseline_runner, '.baseline').decode().splitlines()
                stable = lambda rows: {r.split('\t')[0]: r.split('\t')[1:] for r in rows if r.startswith(('note-', 'rest-', 'clef-'))}
                self.assertEqual(stable(current), stable(previous))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline-runner')
    args, remaining = parser.parse_known_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    unittest.main(argv=['verify-scoredef.py', *remaining])
