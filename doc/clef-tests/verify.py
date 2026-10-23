#!/usr/bin/env python3
"""Assertions over public-wrapper engraving and the same Toolkit's layout model."""
import argparse
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


def render(name, mode):
    result = subprocess.run([args.runner, args.resources, mode, str(HERE / 'options.json'), 'unused'],
                            input=(HERE / 'fixtures' / name).read_bytes(), capture_output=True)
    if result.returncode:
        raise AssertionError(f'{name} {mode}: {result.returncode}\n{result.stderr.decode()}')
    if result.stderr:
        raise AssertionError(f'{name} {mode}: unexpected diagnostics {result.stderr.decode()}')
    text = result.stdout.decode()
    (Path(args.output) / f'{name}.{mode}').write_text(text)
    return text


def model(name):
    return ET.fromstring(render(name, 'mei'))


def lower_layer(root):
    measures = root.findall('.//' + M + 'measure')
    return measures[1].find(M + "staff[@n='2']/" + M + 'layer')


def observations(name):
    return {row[0]: dict(zip(('kind', 'measure', 'staff', 'layer', 'time'), row[1:]))
            for row in (line.split('\t') for line in render(name, 'observer').splitlines())}


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
                spaces = layer.findall(M + 'space')
                durations = [Fraction(4, int(s.get('dur.ges', s.get('dur')))) * sum(Fraction(1, 2**i) for i in range(int(s.get('dots.ges', s.get('dots', '0'))) + 1)) for s in spaces]
                self.assertEqual(sum(durations), 2, 'same two-quarter finalized fill budget')
                self.assertEqual(len(model(name).findall('.//' + M + 'measure')), 2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    args, remaining = parser.parse_known_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    unittest.main(argv=['verify.py', *remaining])
