#!/usr/bin/env python3
import argparse
import subprocess
import unittest
import xml.etree.ElementTree as E
from pathlib import Path

M = '{http://www.music-encoding.org/ns/mei}'
ID = '{http://www.w3.org/XML/1998/namespace}id'
S = '{http://www.w3.org/2000/svg}'
HERE = Path(__file__).resolve().parent
args = None


def render(source, mode, name):
    result = subprocess.run([args.runner, args.resources, mode, str(HERE / 'options.json'), 'unused'],
                            input=source.encode(), capture_output=True)
    (Path(args.output) / f'{name}.{mode}').write_bytes(result.stdout)
    assert result.returncode == 0 and not result.stderr, (name, mode, result.stderr)
    return E.fromstring(result.stdout)


def notehead_x(svg, note_id):
    note = next(e for e in svg.iter(S + 'g') if e.get('id') == note_id)
    head = next(e for e in note.iter(S + 'g') if 'notehead' in e.get('class', '').split())
    return [float(use.get('transform').split('(')[1].split(',')[0]) for use in head.iter(S + 'use')]


class KeySignatureUnison(unittest.TestCase):
    """Chopin Ballade 1 bar 14: E-flat with a cautionary flat in one voice, from the key in the other."""

    def test_unison_shares_one_notehead(self):
        source = (HERE / 'fixtures/unison/cautionary-and-key.krn').read_text()
        for name, text in [('cautionary', source), ('plain', source.replace('2.e-X', '2.e-'))]:
            with self.subTest(name=name):
                mei = render(text, 'mei', name)
                notes = {e.get(ID): e for e in mei.iter(M + 'note')}
                self.assertEqual(notes['note-L8F3'].get('accid.ges'), 'f',
                                 'UNISON_ACCID_GES: key-signature E-flat must keep its gestural flat')
                svg = render(text, 'svg', name)
                self.assertEqual(notehead_x(svg, 'note-L8F2'), notehead_x(svg, 'note-L8F3'),
                                 'UNISON_NOTEHEAD: the two voices must share one notehead position')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    args, remaining = parser.parse_known_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    unittest.main(argv=['verify-unison.py', *remaining])
