#!/usr/bin/env python3
"""Check imported MEI anchors and rendered fingering text using the C wrapper."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

MEI = '{http://www.music-encoding.org/ns/mei}'
SVG = '{http://www.w3.org/2000/svg}'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'


def render(source, output='mei'):
    result = subprocess.run([str(ARGS.runner), str(ARGS.resources), output],
                            input=source, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    if 'font could not be loaded' in result.stderr or 'Expected ' in result.stderr:
        raise AssertionError(result.stderr)
    return ET.fromstring(result.stdout)


def fingerings(root):
    return root.findall('.//' + MEI + 'fing')


class SubspineTests(unittest.TestCase):
    def test_matching_subspine_with_rest_in_first_voice(self):
        source = '**kern\t**fing\n*^\t*^\n4r\t4c\t.\t3\n*v\t*v\t*\t*\n*\t*v\t*v\n==\t==\n*-\t*-\n'
        root = render(source)
        fings = fingerings(root)
        self.assertEqual([(f.get('startid'), ''.join(f.itertext()).strip()) for f in fings],
                         [('#note-L3F2', '3')])
        svg = render(source, 'svg')
        group = next(e for e in svg.iter() if e.get('id') == 'fing-L3F4')
        self.assertEqual(''.join(group.itertext()).strip(), '3')

    def test_matching_null_voice_uses_timestamp(self):
        source = '**kern\t**fing\n*^\t*^\n4c\t2e\t1\t3\n4d\t.\t2\t4\n*v\t*v\t*\t*\n*\t*v\t*v\n==\t==\n*-\t*-\n'
        root = render(source)
        fings = fingerings(root)
        f = next(f for f in fings if f.get(XML_ID) == 'fing-L4F4')
        self.assertEqual(f.get('tstamp'), '2')
        self.assertIsNone(f.get('startid'))
        self.assertEqual(next(f for f in fings if f.get(XML_ID) == 'fing-L4F3').get('startid'), '#note-L4F1')


class ChordTests(unittest.TestCase):
    def test_each_chord_slot_links_to_its_note(self):
        source = '**kern\t**fing\n4e 4c 4g\t3 1 5\n==\t==\n*-\t*-\n'
        root = render(source)
        self.assertEqual([(f.get(XML_ID), f.get('startid'), ''.join(f.itertext()).strip()) for f in fingerings(root)],
                         [('fing-L2F2S1', '#note-L2F1S1', '3'),
                          ('fing-L2F2S2', '#note-L2F1S2', '1'),
                          ('fing-L2F2S3', '#note-L2F1S3', '5')])
        svg = render(source, 'svg')
        groups = [e for e in svg.iter() if e.get('class') == 'fing']
        self.assertEqual([''.join(g.itertext()).strip() for g in groups], ['3', '1', '5'])

    def test_null_chord_slots_preserve_note_index(self):
        source = '**kern\t**fing\n4c 4e 4g\t. 4 .\n==\t==\n*-\t*-\n'
        self.assertEqual([(f.get('startid'), ''.join(f.itertext()).strip()) for f in fingerings(render(source))],
                         [('#note-L2F1S2', '4')])

    def test_legacy_chord_count_mismatch_keeps_chord_anchor(self):
        source = '**kern\t**fing\n4c 4e 4g\t3\n==\t==\n*-\t*-\n'
        self.assertEqual([(f.get('startid'), ''.join(f.itertext()).strip()) for f in fingerings(render(source))],
                         [('#chord-L2F1', '3')])

    def test_several_fingers_on_one_note_keep_stacked_anchor(self):
        source = '**kern\t**fing\n4cT\t3 4\n==\t==\n*-\t*-\n'
        self.assertEqual([(f.get(XML_ID), f.get('startid'), ''.join(f.itertext()).strip()) for f in fingerings(render(source))],
                         [('fing-L2F2S1', '#note-L2F1', '3'), ('fing-L2F2S2', '#note-L2F1', '4')])


class CrossStaffTests(unittest.TestCase):
    def test_each_hand_follows_its_drawn_staff(self):
        source = '**kern\t**fing\t**kern\t**fing\n*clefF4\t*\t*clefG2\t*\n4C<\t3\t4c>\t2\n==\t==\t==\t==\n*-\t*-\t*-\t*-\n!!!RDF**kern: < = above\n!!!RDF**kern: > = below\n'
        root = render(source)
        self.assertEqual([(f.get('startid'), f.get('staff')) for f in fingerings(root)],
                         [('#note-L3F1', '1'), ('#note-L3F3', '2')])
        svg = render(source, 'svg')
        groups = [e for e in svg.iter() if e.get('class') == 'fing']
        self.assertEqual([''.join(g.itertext()).strip() for g in groups], ['3', '2'])

    def test_entire_moved_chord_inherits_chord_staff(self):
        source = '**kern\t**kern\t**fing\n*clefF4\t*clefG2\t*\n4C\t4c> 4e>\t1 3\n==\t==\t==\n*-\t*-\t*-\n!!!RDF**kern: > = below\n'
        root = render(source)
        self.assertEqual([(f.get('startid'), f.get('staff')) for f in fingerings(root)],
                         [('#note-L3F2S1', '2'), ('#note-L3F2S2', '2')])
        self.assertEqual(root.find('.//' + MEI + 'chord').get('staff'), '2')

    def test_mixed_chord_fingerings_follow_each_note(self):
        source = '**kern\t**kern\t**fing\n*clefF4\t*clefG2\t*\n4C\t4c 4e>\t1 3\n==\t==\t==\n*-\t*-\t*-\n!!!RDF**kern: > = below\n'
        root = render(source)
        self.assertEqual([(f.get('startid'), f.get('staff')) for f in fingerings(root)],
                         [('#note-L3F2S1', '1'), ('#note-L3F2S2', '2')])


class EngravingTests(unittest.TestCase):
    def test_substitution_arcs_above_and_below(self):
        source = '**kern\t**fing\n*\t*above\n4c\t3-4\n*\t*below\n4d\t2-1\n==\t==\n*-\t*-\n'
        root = render(source)
        fings = fingerings(root)
        self.assertEqual([(f.get('startid'), f.get('place')) for f in fings],
                         [('#note-L3F1', 'above'), ('#note-L5F1', 'below')])
        symbols = root.findall('.//' + MEI + 'symbol')
        self.assertEqual([(s.get('glyph.auth'), s.get('glyph.name')) for s in symbols],
                         [('smufl', 'fingeringSubstitutionAbove'), ('smufl', 'fingeringSubstitutionBelow')])
        svg = render(source, 'svg')
        groups = [e for e in svg.iter() if e.get('class') == 'fing']
        self.assertEqual([''.join(''.join(g.itertext()).split()) for g in groups], ['34', '21'])
        for group, code in zip(groups, ['ED20', 'ED21']):
            use = group.find('.//' + SVG + 'use')
            self.assertIsNotNone(use, 'The arc must be an SVG outline, not an external font glyph')
            reference = use.get('{http://www.w3.org/1999/xlink}href') or use.get('href')
            self.assertTrue(reference.startswith('#' + code))
            glyph = next(e for e in svg.iter() if e.get('id') == reference[1:])
            self.assertIsNotNone(glyph.find(SVG + 'path'))

    def test_role_stack_uses_one_chord_slot_and_top_to_bottom_order(self):
        for placement in ['above', 'below']:
            with self.subTest(placement=placement):
                source = '**kern\t**fing\n*\t*' + placement + '\n4cT 4e\t4/3/2 .\n==\t==\n*-\t*-\n'
                root = render(source)
                fings = fingerings(root)
                self.assertEqual(sorted((f.get(XML_ID), f.get('startid'), ''.join(f.itertext()).strip()) for f in fings),
                                 [('fing-L3F2S1N1', '#note-L3F1S1', '4'),
                                  ('fing-L3F2S1N2', '#note-L3F1S1', '3'),
                                  ('fing-L3F2S1N3', '#note-L3F1S1', '2')])
                svg = render(source, 'svg')
                groups = [e for e in svg.iter() if e.get('class') == 'fing']
                texts = [g.find('.//' + SVG + 'text') for g in groups]
                self.assertEqual([''.join(t.itertext()).strip() for t in sorted(texts, key=lambda t: float(t.get('y')))],
                                 ['4', '3', '2'])


class PlacementTests(unittest.TestCase):
    def test_layout_comment_places_each_chord_slot_and_its_role_stack(self):
        source = '**kern\t**fing\n*\t*above\n!\t!LO:FING:b:n=1\n!\t!LO:FING:a:n=2\n4c 4eT\t1 4/3/2\n==\t==\n*-\t*-\n'
        root = render(source)
        self.assertEqual(sorted((f.get('startid'), f.get('place'), ''.join(f.itertext()).strip()) for f in fingerings(root)),
                         [('#note-L5F1S1', 'below', '1'),
                          ('#note-L5F1S2', 'above', '2'),
                          ('#note-L5F1S2', 'above', '3'),
                          ('#note-L5F1S2', 'above', '4')])

    def test_layout_comment_without_slot_applies_to_whole_token(self):
        source = '**kern\t**fing\n!\t!LO:FING:b\n4c 4e\t1 3\n==\t==\n*-\t*-\n'
        self.assertEqual([(f.get('startid'), f.get('place')) for f in fingerings(render(source))],
                         [('#note-L3F1S1', 'below'), ('#note-L3F1S2', 'below')])


class ResourceTests(unittest.TestCase):
    def test_existing_leipzig_glyphs_remain_required(self):
        render('**kern\n4c\n==\n*-\n')
        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory)
            for entry in ARGS.resources.resolve().iterdir():
                if entry.name != 'Leipzig.xml':
                    (resources / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
            font = ET.parse(ARGS.resources / 'Leipzig.xml')
            root = font.getroot()
            root.remove(next(g for g in root if g.get('c') == 'E050'))
            font.write(resources / 'Leipzig.xml')
            result = subprocess.run([str(ARGS.runner), str(resources), 'mei'],
                                    input='**kern\n4c\n==\n*-\n', text=True, capture_output=True)
            self.assertIn('Leipzig font could not be loaded', result.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--resources', type=Path, required=True)
    ARGS, rest = parser.parse_known_args()
    unittest.main(argv=['verify.py'] + rest)
