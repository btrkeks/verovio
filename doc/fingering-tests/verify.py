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


def vertical_bounds(group):
    boxes = group.findall('.//' + SVG + 'rect')
    if not boxes:
        raise AssertionError('The rendered group must expose its glyph bounds')
    return (min(float(box.get('y')) for box in boxes),
            max(float(box.get('y')) + float(box.get('height')) for box in boxes))


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
    def test_horizontal_sequence_is_between_note_and_ornament_on_each_side(self):
        for marker, kind in [('T', 'trill'), ('M', 'mordent'), ('sSS', 'turn')]:
            for side, comment, sign in [('above', 'a', '>'), ('below', 'b', '<')]:
                with self.subTest(ornament=kind, side=side):
                    source = ('!!!RDF**kern: > = above\n!!!RDF**kern: < = below\n'
                              '**kern\t**fing\n*\t*' + ('below' if side == 'above' else 'above')
                              + '\n!\t!LO:FING:' + comment + ':n=1\n1d' + marker + sign
                              + ' 1f\t2/1/2/1 .\n==\t==\n*-\t*-\n')
                    mei = render(source)
                    self.assertEqual([(f.get(XML_ID), f.get('startid'), f.get('place'), ''.join(f.itertext()).strip())
                                      for f in fingerings(mei)],
                                     [('fing-L6F2S1', '#note-L6F1S1', side, '2121')])
                    svg = render(source, 'svg-bounds')
                    groups = [e for e in svg.iter() if e.get('class') == 'fing']
                    self.assertEqual(len(groups), 1)
                    texts = groups[0].findall('.//' + SVG + 'text')
                    self.assertEqual(len(texts), 1, 'All sequence digits share one text line')
                    self.assertEqual(''.join(texts[0].itertext()).strip(), '2121')
                    sequence_top, sequence_bottom = vertical_bounds(groups[0])
                    ornament = next(e for e in svg.iter() if e.get('class') == kind)
                    ornament_top, ornament_bottom = vertical_bounds(ornament)
                    note = next(e for e in svg.iter() if e.get('id') == 'note-L6F1S1')
                    note_top, note_bottom = vertical_bounds(note)
                    if side == 'above':
                        self.assertLess(ornament_bottom, sequence_top)
                        self.assertLess(sequence_bottom, note_top)
                    else:
                        self.assertLess(note_bottom, sequence_top)
                        self.assertLess(sequence_bottom, ornament_top)

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

    def test_roles_are_adjacent_digits_in_one_chord_slot(self):
        for placement in ['above', 'below']:
            for encoded, label in [('2/1', '21'), ('4/3/2', '432'), ('2/1/2/1', '2121')]:
                with self.subTest(placement=placement, encoded=encoded):
                    source = ('**kern\t**fing\n*\t*' + placement
                              + '\n4cT 4e\t' + encoded + ' .\n==\t==\n*-\t*-\n')
                    root = render(source)
                    self.assertEqual([(f.get(XML_ID), f.get('startid'), ''.join(f.itertext()).strip())
                                      for f in fingerings(root)],
                                     [('fing-L3F2S1', '#note-L3F1S1', label)])
                    svg = render(source, 'svg-bounds')
                    group = next(e for e in svg.iter() if e.get('class') == 'fing')
                    texts = group.findall('.//' + SVG + 'text')
                    self.assertEqual(len(texts), 1)
                    self.assertEqual(''.join(texts[0].itertext()).strip(), label)
                    reference = render(source.replace(encoded, label), 'svg-bounds')
                    reference_group = next(e for e in reference.iter() if e.get('class') == 'fing')
                    bounds = [(e.get('x'), e.get('y'), e.get('width'), e.get('height'))
                              for e in group.findall('.//' + SVG + 'rect')]
                    reference_bounds = [(e.get('x'), e.get('y'), e.get('width'), e.get('height'))
                                        for e in reference_group.findall('.//' + SVG + 'rect')]
                    self.assertTrue(bounds)
                    self.assertEqual(bounds, reference_bounds)


class PlacementTests(unittest.TestCase):
    def test_layout_comment_places_each_chord_slot_and_its_role_sequence(self):
        source = '**kern\t**fing\n*\t*above\n!\t!LO:FING:b:n=1\n!\t!LO:FING:a:n=2\n4c 4eT\t1 4/3/2\n==\t==\n*-\t*-\n'
        root = render(source)
        self.assertEqual(sorted((f.get('startid'), f.get('place'), ''.join(f.itertext()).strip()) for f in fingerings(root)),
                         [('#note-L5F1S1', 'below', '1'),
                          ('#note-L5F1S2', 'above', '432')])

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
