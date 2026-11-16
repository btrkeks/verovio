#!/usr/bin/env python3
import argparse
import re
import subprocess
import unittest
import xml.etree.ElementTree as E
from pathlib import Path

S = '{http://www.w3.org/2000/svg}'
HERE = Path(__file__).resolve().parent
EMPTY_SYSTEM_ELEMENTS = {'pb', 'sb', 'section'}
args = None


def render(name):
    result = subprocess.run([args.runner, args.resources, 'svg', str(HERE / 'options.json'), 'unused'],
                            input=(HERE / 'fixtures/scoredef' / name).read_bytes(), capture_output=True)
    (Path(args.output) / f'{name}.svg').write_bytes(result.stdout)
    (Path(args.output) / f'{name}.svg.stderr').write_bytes(result.stderr)
    assert result.returncode == 0 and not result.stderr, (name, result.stderr)
    return result.stdout


class EditorPlaceholders(unittest.TestCase):
    """Clef has no editor: empty system elements carry no hidden selection ink."""

    def test_empty_system_elements_draw_no_ink(self):
        for name in ['global.krn', 'staff.krn', 'transpose.krn']:
            with self.subTest(name=name):
                svg = E.fromstring(render(name))
                seen = set()
                for group in svg.iter(S + 'g'):
                    classes = set(group.get('class', '').split())
                    kind = classes & EMPTY_SYSTEM_ELEMENTS
                    if not kind:
                        continue
                    seen |= kind
                    self.assertEqual(list(group), [], (name, group.get('id'), 'PLACEHOLDER_INK'))
                self.assertIn('section', seen, name)
                self.assertIn('pb', seen, name)
                for group in svg.iter(S + 'g'):
                    if 'scoreDef' in group.get('class', '').split():
                        self.assertFalse([e for e in group if e.tag == S + 'ellipse'],
                                         (name, group.get('id'), 'PLACEHOLDER_INK'))

    def test_stylesheet_has_no_placeholder_rule(self):
        svg = render('global.krn').decode()
        styles = ''.join(re.findall(r'<style[^>]*>(.*?)</style>', svg, re.S))
        self.assertTrue(styles)
        self.assertNotIn('placeholder', styles)
        self.assertNotIn('visibility', styles)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    args, remaining = parser.parse_known_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    unittest.main(argv=['verify-placeholders.py', *remaining])
