#!/usr/bin/env python3
import argparse
import subprocess
import unittest
import xml.etree.ElementTree as E
from pathlib import Path

M = '{http://www.music-encoding.org/ns/mei}'
S = '{http://www.w3.org/2000/svg}'
X = '{http://www.w3.org/1999/xlink}href'
HERE = Path(__file__).resolve().parent
args = None


def render(name, mode):
    result = subprocess.run([args.runner, args.resources, mode, str(HERE / 'options.json'), 'unused'],
                            input=(HERE / 'fixtures/meter' / name).read_bytes(), capture_output=True)
    (Path(args.output) / f'{name}.{mode}').write_bytes(result.stdout)
    assert result.returncode == 0 and not result.stderr, (name, mode, result.stderr)
    return E.fromstring(result.stdout)


def glyphs(svg, css_class):
    return [use.get(X).split('-')[0].lstrip('#') for group in svg.iter(S + 'g')
            if css_class in group.get('class', '').split() for use in group.iter(S + 'use')]


class CommonPracticeMeter(unittest.TestCase):
    """*met(...) in common-practice notation keeps its symbol and the *M meter under it."""

    def test_common_and_cut_time_draw_their_symbol_over_the_meter(self):
        for name, sym, count, unit, glyph in [('common.krn', 'common', '4', '4', 'E08A'),
                                              ('cut.krn', 'cut', '2', '2', 'E08B')]:
            with self.subTest(name=name):
                meter = next(render(name, 'mei').iter(M + 'meterSig'))
                self.assertEqual((meter.get('sym'), meter.get('count'), meter.get('unit'), meter.get('visible')),
                                 (sym, count, unit, None), 'METER_SYMBOL')
                self.assertEqual(glyphs(render(name, 'svg'), 'meterSig'), [glyph], 'METER_SYMBOL_INK')

    def test_hidden_meter_keeps_the_measure_length(self):
        meter = next(render('hidden-breve.krn', 'mei').iter(M + 'meterSig'))
        self.assertEqual((meter.get('count'), meter.get('unit'), meter.get('visible')), ('2', '1', 'false'),
                         'HIDDEN_METER_LENGTH')
        self.assertEqual(glyphs(render('hidden-breve.krn', 'svg'), 'mRest'), ['E4E2'],
                         'HIDDEN_METER_LENGTH: a 2/1 bar of rest draws a breve rest')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    args, remaining = parser.parse_known_args()
    Path(args.output).mkdir(parents=True, exist_ok=True)
    unittest.main(argv=['verify-meter.py', *remaining])
