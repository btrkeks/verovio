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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--resources', type=Path, required=True)
    ARGS, rest = parser.parse_known_args()
    unittest.main(argv=['verify.py'] + rest)
