#!/usr/bin/env python3
import argparse
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as E

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
S = '{http://www.w3.org/2000/svg}'


def role_image(svg, origin, output):
    root = deepcopy(E.fromstring(svg))
    assert len([e for e in root.iter() if e.get('id') == origin]) == 1, origin

    def keep(element):
        if element.get('id') == origin or element.tag in {S + 'defs', S + 'style'}:
            return
        for child in list(element):
            if child.tag in {S + tag for tag in ['path', 'use', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'text', 'image']} and child.get('id') != origin:
                element.remove(child)
            else:
                keep(child)

    keep(root)
    output.write_bytes(E.tostring(root))
    process = subprocess.run(['rsvg-convert', '--zoom', '4', str(output)], capture_output=True, check=True)
    output.with_suffix('.png').write_bytes(process.stdout)
    alpha = Image.open(BytesIO(process.stdout)).convert('RGBA').getchannel('A')
    mask = alpha.point(lambda value: 255 if value > 127 else 0)
    assert mask.getbbox(), ('missing original styled ink', origin)
    return mask


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    command = [args.runner, args.resources, 'svg', str(HERE / 'options.json'), 'unused']
    source = (HERE / 'fixtures/mrest-end-context.krn').read_bytes()
    result = subprocess.run(command, input=source, capture_output=True, check=True)
    (output / 'score.svg').write_bytes(result.stdout)
    assert not result.stderr, result.stderr
    assert subprocess.run(command, input=source, capture_output=True, check=True).stdout == result.stdout
    roles = ['mrest-L7F1', 'clef-L9F1', 'keysig-L10F1']
    masks = {name: role_image(result.stdout, name, output / (name + '.svg')) for name in roles}
    facts = {'command': command, 'bounds': {name: mask.getbbox() for name, mask in masks.items()}, 'overlaps': {}}
    for index, left in enumerate(roles):
        for right in roles[index + 1:]:
            facts['overlaps'][left + '|' + right] = ImageChops.multiply(masks[left], masks[right]).getbbox()
    (output / 'facts.json').write_text(json.dumps(facts, indent=2) + '\n')
    assert not any(facts['overlaps'].values()), ('rest/end-context collision', facts)
    assert masks[roles[0]].getbbox()[2] < masks[roles[1]].getbbox()[0] < masks[roles[2]].getbbox()[0], facts
    print('Full-measure rest, endpoint clef and key retain nonempty original styled ink in clear source order.')


if __name__ == '__main__':
    main()
