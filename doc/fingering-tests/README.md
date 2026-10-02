# Humdrum fingering regression tests

These tests import Humdrum through the public C wrapper, inspect the generated
MEI note links, and check the SVG fingering text. They use the same compiled
library as the caller instead of a separate importer implementation.

Build Verovio first, then link the runner against its static library:

```sh
c++ -std=c++20 -Itools doc/fingering-tests/render.cpp /absolute/path/libverovio.a -pthread -o /tmp/verovio-fingering-render
python3 doc/fingering-tests/verify.py --runner /tmp/verovio-fingering-render --resources "$PWD/data"
```

Pass a unittest class name after the options to run one regression group.
The resources must include the font data that matches the library.

A chord's fingering token has one space-separated slot per kern subtoken,
in kern source order. A `.` skips that note. Exact slot counts link each
fingering to its note; older mismatched counts keep their chord anchor.
Several space-separated fingers on a single note keep their shared anchor.

Generated engraving also accepts these forms within one chord slot:

- `3-4` draws two digits joined by a substitution arc. The importer emits a
  SMuFL symbol in MEI. `DrawFing` draws its Bravura outline directly into the
  SVG, with no extra text font required.
- `2/1` draws adjacent ornament fingering digits as `21` on one line.
  A longer sequence such as `2/1/2/1` draws `2121`. The entire label keeps
  one XML ID and the slot's note anchor.

A local layout comment in the `**fing` field places the following data token:
`!LO:FING:a` means above and `!LO:FING:b` means below. An optional `:n=2`
selects the second chord slot. Each sequence in that slot follows the same
placement. The comments override `*above` and `*below` for that data token.

Ornament fingerings sit between the note and its ornament sign. The floating
positioning pass places fingerings before ornaments, so the sign clears the
full horizontal label on either side of the staff. The regression runner's
`svg-bounds` mode checks the label against adjacent literal text and verifies
that its glyph bounds clear both the note and the ornament sign.

The two arc paths and their bounds come from the bundled original Bravura SVG
under `fonts/Bravura`. `fonts/supported.xml` includes ED20 and ED21, and
`include/vrv/smufl.h` was regenerated with `fonts/generate.py smufl`.
Leipzig's required glyph count excludes only these Bravura-only arc glyphs;
the existing required glyph count remains enforced.
