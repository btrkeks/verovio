#!/usr/bin/env python3
"""Check imported MEI anchors and rendered fingering text using the C wrapper."""
import argparse
from pathlib import Path
import subprocess
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--resources', type=Path, required=True)
    ARGS, rest = parser.parse_known_args()
    unittest.main(argv=['verify.py'] + rest)
