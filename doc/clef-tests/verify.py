#!/usr/bin/env python3
"""Assertions over public-wrapper engraving and the same Toolkit's layout model."""
import argparse
import sys

sys.dont_write_bytecode = True
import json
import subprocess
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = '{http://www.music-encoding.org/ns/mei}'
S = '{http://www.w3.org/2000/svg}'
ID = '{http://www.w3.org/XML/1998/namespace}id'
args = None


def normalized_xml(text):
    root = ET.fromstring(text)
    for element in root.iter():
        element.attrib.pop('isodate', None)
    return ET.tostring(root)


def render(name, mode, text=None, runner=None, suffix=""):
    result = subprocess.run([runner or args.runner, args.resources, mode, str(HERE / 'options.json'), 'unused'],
                            input=(HERE / 'fixtures' / name).read_bytes() if text is None else text, capture_output=True)
    (Path(args.output) / f'{name}{suffix}.{mode}.stdout').write_bytes(result.stdout)
    (Path(args.output) / f'{name}{suffix}.{mode}.stderr').write_bytes(result.stderr)
    if result.returncode:
        raise AssertionError(f'{name} {mode}: {result.returncode}\n{result.stderr.decode()}')
    if result.stderr:
        raise AssertionError(f'{name} {mode}: unexpected diagnostics {result.stderr.decode()}')
    text = result.stdout.decode()
    (Path(args.output) / f'{name}{suffix}.{mode}').write_text(text)
    return text


def model(name):
    return ET.fromstring(render(name, 'mei'))


def lower_layer(root):
    measures = root.findall('.//' + M + 'measure')
    return measures[1].find(M + "staff[@n='2']/" + M + 'layer')


def observations(name, runner=None):
    return {row[0]: dict(zip(('kind', 'measure', 'staff', 'layer', 'time', 'duration'), row[1:]))
            for row in (line.split('\t') for line in render(name, 'observer', runner=runner, suffix='.baseline' if runner else '').splitlines())}


class ClefImport(unittest.TestCase):
    def test_observer_equivalence_and_units(self):
        name = 'positive-gap.krn'
        self.assertEqual(normalized_xml(render(name, 'mei')), normalized_xml(render(name, 'observer-mei')))
        self.assertEqual(normalized_xml(render(name, 'svg')), normalized_xml(render(name, 'observer-svg')))
        facts = observations(name)
        self.assertEqual(Fraction(facts['note-L7F2']['time']), 0)
        self.assertEqual(Fraction(facts['note-L9F2']['time']), Fraction(1, 4))
        self.assertEqual(Fraction(facts['note-L10F2']['time']), Fraction(1, 2))

    def test_ordinary_null_class_visibility_source_position(self):
        hidden = (HERE / 'fixtures/ordinary-null-hidden.krn').read_bytes()
        visible = (HERE / 'fixtures/ordinary-null-visible.krn').read_bytes()
        self.assertEqual(hidden.replace(b'*clefG2yy', b'*clefG2'), visible)
        self.assertEqual(visible.replace(b'*clefG2\t*', b'*clefG2yy\t*'), hidden)
        for name, invisible in [('ordinary-null-hidden.krn', True), ('ordinary-null-visible.krn', False)]:
            with self.subTest(name=name):
                root = model(name)
                layer = lower_layer(root)
                clefs = [c for c in layer.findall(M + 'clef') if c.get('shape') == 'G' and c.get('line') == '2']
                self.assertEqual(len(clefs), 1, 'required lower-staff G2 layer class missing (upper G2 is irrelevant)')
                clef = clefs[0]
                self.assertEqual(clef.get(ID), 'clef-L9F1')
                self.assertEqual(clef.get('visible') == 'false', invisible)
                self.assertLess(list(layer).index(clef), list(layer).index(layer.find(M + 'note')))
                note = layer.find(M + 'note')
                self.assertEqual((note.get(ID), note.get('dur')), ('note-L10F1', '1'))
                facts = observations(name)
                self.assertEqual(Fraction(facts['clef-L9F1']['time']), 0)
                self.assertEqual(Fraction(facts['note-L10F1']['time']), 0)
                svg = ET.fromstring(render(name, 'svg'))
                group = next((g for g in svg.iter() if g.get('id') == 'clef-L9F1'), None)
                ink = [] if group is None else list(group.iter(S + 'use')) + list(group.iter(S + 'path'))
                self.assertEqual(bool(ink), not invisible)
                if not invisible:
                    uses = list(group.iter(S + 'use'))
                    self.assertTrue(uses)
                    self.assertIn('scale(0.72', uses[0].get('transform', ''))

    def test_held_copy_prefix_opening_and_nested_classes(self):
        for name, owner, copies in [
            ('regression-held.krn', 'clef-L8F1', ['clef-L8F2']),
            ('regression-grace-alias.krn', 'clef-L8F1', ['clef-L8F2', 'clef-L10F2']),
            ('null-interp.krn', 'clef-L7F1', ['clef-L7F2']),
            ('inverse-visible-alias.krn', 'clef-L8F1', ['clef-L8F2']),
            ('inverse-hidden-alias.krn', 'clef-L8F1', ['clef-L8F2']),
        ]:
            with self.subTest(name=name):
                root = model(name)
                clefs = {c.get(ID): c for c in root.iter(M + 'clef')}
                facts = observations(name)
                self.assertEqual(Fraction(facts[owner]['time']), Fraction(1, 4))
                for copy in copies:
                    self.assertEqual(clefs[copy].get('sameas'), '#' + owner)
                    self.assertEqual(clefs[copy].get('shape'), clefs[owner].get('shape'))
                    self.assertEqual(clefs[copy].get('line'), clefs[owner].get('line'))
                    self.assertEqual(facts[copy]['staff'], facts[owner]['staff'])
                if name == 'null-interp.krn':
                    self.assertEqual(clefs['clef-L7F2'].get('visible'), 'false')
        root = model('regression-nested.krn')
        clefs = {c.get(ID): c for c in root.iter(M + 'clef')}
        self.assertEqual(set(clefs), {'clef-L2F1', 'clef-L9F1', 'clef-L9F2', 'clef-L9F3'})
        self.assertEqual(Fraction(observations('regression-nested.krn')['clef-L9F3']['time']), Fraction(1, 4))
        self.assertIsNone(clefs['clef-L9F3'].get('sameas'))
        for name in ['regression-folded-split-hidden.krn', 'regression-folded-split-visible.krn']:
            self.assertEqual(len(list(model(name).iter(M + 'clef'))), 1 if 'hidden' in name else 3)
        root = model('normal-prefix.krn')
        self.assertEqual(len(root.findall('.//' + M + 'layer/' + M + 'clef')), 0)
        self.assertEqual(len(root.findall('.//' + M + 'staffDef/' + M + 'clef')), 3)
        root = model('forced-opening.krn')
        self.assertEqual([e.get(ID) for e in root.iter(M + 'clef')], ['clef-L2F1', 'clef-L3F1'])

    def test_ended_layer_gap_is_independent_and_exact(self):
        root = model('ended-layer-gap.krn')
        clefs = {e.get(ID): e for e in root.iter(M + 'clef')}
        facts = observations('ended-layer-gap.krn')
        for id in ['clef-L9F1', 'clef-L9F1b']:
            self.assertEqual(Fraction(facts[id]['time']), Fraction(1, 2))
            self.assertIsNone(clefs[id].get('sameas'))
        self.assertEqual(Fraction(facts['note-L6F2']['duration']), Fraction(1, 4))

    def test_native_yy_controls_and_five_preserved_ink_shapes(self):
        import ink
        for name, origin in [('regression-g2.krn', 'clef-L10F1'), ('regression-f4.krn', 'clef-L10F1'),
                             ('regression-restated.krn', 'clef-L10F1'), ('regression-octave.krn', 'clef-L10F1'),
                             ('regression-held.krn', 'clef-L8F1')]:
            with self.subTest(name=name):
                source = (HERE / 'fixtures' / name).read_bytes()
                import re
                line, field = map(int, re.fullmatch(r'clef-L(\d+)F(\d+)', origin).groups())
                rows = source.splitlines(keepends=True)
                fields = rows[line - 1].split(b'\t')
                token = fields[field - 1]
                self.assertIn(b'yy', token)
                offset = sum(map(len, rows[:line - 1])) + sum(len(t) + 1 for t in fields[:field - 1]) + token.index(b'yy')
                control = source[:offset] + source[offset + 2:]
                self.assertEqual(control[:offset] + b'yy' + control[offset:], source)
                original = model(name)
                self.assertEqual(next(e for e in original.iter(M + 'clef') if e.get(ID) == origin).get('visible'), 'false')
                svg = render(name, 'svg', text=control, suffix='.control')
                root = ET.fromstring(svg)
                group = next(e for e in root.iter() if e.get('id') == origin)
                self.assertTrue(list(group.iter(S + 'use')))
                self.assertEqual(json.loads(render(name, 'options')), json.loads(render(name, 'options', text=control, suffix='.control')))
                if args.baseline_runner:
                    render(name, 'svg', text=control, runner=args.baseline_runner, suffix='.baseline-control')
                    actual = ink.original(Path(args.output) / f'{name}.control.svg', origin)
                    expected = ink.original(Path(args.output) / f'{name}.baseline-control.svg', origin)
                    self.assertEqual(len(actual), len(expected))
                    for (path, transform, paint), (oldpath, oldtransform, oldpaint) in zip(actual, expected):
                        self.assertEqual(path, oldpath)
                        for x, y in zip(transform, oldtransform): self.assertAlmostEqual(x, y, places=8)
                        self.assertEqual(paint, oldpaint)

    def test_unchanged_attacks_durations_key_meter_and_native_edges(self):
        if not args.baseline_runner: self.skipTest('requires exact baseline library runner')
        for fixture in sorted((HERE / 'fixtures').glob('*.krn')):
            with self.subTest(name=fixture.name):
                name = fixture.name
                current = model(name)
                previous = ET.fromstring(render(name, 'mei', runner=args.baseline_runner, suffix='.baseline'))
                tags = {M + n for n in ['note', 'rest', 'mRest', 'keySig', 'meterSig']}
                semantic = lambda r: {e.get(ID): e.attrib for e in r.iter() if e.tag in tags}
                self.assertEqual(semantic(current), semantic(previous))
                now, old = observations(name), observations(name, runner=args.baseline_runner)
                for id in semantic(current):
                    if id in old:
                        for key in ['time', 'staff', 'layer', 'measure']: self.assertEqual(now[id][key], old[id][key])
                self.assertEqual(len(list(current.iter(M + 'measure'))), len(list(previous.iter(M + 'measure'))))
                if name.startswith('regression-') and name != 'regression-nested.krn':
                    edges = lambda r: {e.get(ID): e.get('sameas') for e in r.iter(M + 'clef')}
                    self.assertEqual(edges(current), edges(previous))

    def test_partial_empty_layer_retains_its_clef_copy(self):
        name = 'partial-empty.krn'
        root = model(name)
        measure = root.findall('.//' + M + 'measure')[1]
        layers = measure.findall(M + "staff[@n='2']/" + M + 'layer')
        self.assertEqual(len(layers), 2)
        facts = observations(name)
        for layer, origin in zip(layers, ['clef-L9F1', 'clef-L9F2']):
            clefs = layer.findall(M + 'clef')
            self.assertEqual(len(clefs), 1, 'partial empty layer must retain its source-owned copy')
            self.assertEqual(clefs[0].get(ID), origin)
            self.assertEqual((clefs[0].get('shape'), clefs[0].get('line')), ('G', '2'))
            self.assertEqual(Fraction(facts[origin]['time']), Fraction(1, 4))
            self.assertEqual(sum(Fraction(facts[e.get(ID)]['duration']) for e in layer.iter(M + 'space')), 1)
            self.assertEqual(len(list(layer.iter(M + 'note'))), 0)

    def test_newly_eligible_empty_and_full_rest(self):
        for name, onset in [('full-rest-zero.krn', Fraction(0)), ('empty-gap.krn', Fraction(1, 4)), ('linked-empty-gap.krn', Fraction(1, 4))]:
            with self.subTest(name=name):
                layer = lower_layer(model(name))
                clefs = layer.findall(M + 'clef')
                self.assertEqual(len(clefs), 1)
                facts = observations(name)
                self.assertEqual(Fraction(facts[clefs[0].get(ID)]['time']), onset)
                if name.startswith('full'):
                    rest = layer.find(M + 'mRest')
                    self.assertIsNotNone(rest)
                    self.assertLess(list(layer).index(clefs[0]), list(layer).index(rest))
                else:
                    self.assertEqual(len(list(layer.iter(M + 'note'))), 0)
                    spaces = list(layer.iter(M + 'space'))
                    self.assertEqual(sum(Fraction(facts[e.get(ID)]['duration']) for e in spaces), 1)

    def test_generated_gap_exact_time_and_conservation(self):
        for name, onset in [('positive-gap.krn', Fraction(1)), ('fractional-gap.krn', Fraction(1, 3)), ('same-onset-gap.krn', Fraction(1))]:
            with self.subTest(name=name):
                layer = lower_layer(model(name))
                clefs = layer.findall(M + 'clef')
                self.assertEqual(len(clefs), 3 if name.startswith('same') else 1)
                facts = observations(name)
                for clef in clefs:
                    self.assertEqual(Fraction(facts[clef.get(ID)]['time']), onset / 4, 'clef must split existing fill at exact time')
                    self.assertIsNone(clef.get('sameas'), 'correctly timed gap anchor is independent')
                notes = layer.findall(M + 'note')
                self.assertEqual(len(notes), 1)
                self.assertEqual(notes[0].get('dur'), '2')
                self.assertEqual(Fraction(facts[notes[0].get(ID)]['time']), Fraction(1, 2))
                spaces = list(layer.iter(M + 'space'))
                durations = [Fraction(facts[s.get(ID)]['duration']) * 4 for s in spaces]
                self.assertEqual(sum(durations), 2, 'same two-quarter finalized fill budget')
                self.assertEqual(len(model(name).findall('.//' + M + 'measure')), 2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline-runner')
    args, remaining = parser.parse_known_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    unittest.main(argv=['verify.py', *remaining])
