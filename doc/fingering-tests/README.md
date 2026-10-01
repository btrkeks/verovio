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
