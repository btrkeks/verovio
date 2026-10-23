# Layer clef import assertions

Link `render.cpp` to the exact caller's static library, with matching headers
and resources. Build outputs must live outside the source checkout.

```sh
c++ -std=c++20 -Itools -Iinclude -Iinclude/vrv -Iinclude/tuning-library -Iinclude/hum -Iinclude/midi -Iinclude/json -Iinclude/pugi -Ilibmei/dist -Ilibmei/addons doc/clef-tests/render.cpp /absolute/libverovio.a -pthread -o /outside/clef-render
python3 doc/clef-tests/verify.py --runner /outside/clef-render --resources /matching/resources --output /outside/proof --baseline-runner /outside/old-clef-render
```

The observer subclasses Toolkit to read its protected document after the normal
load/render path. The suite compares its MEI and SVG with the public C wrapper
before trusting alignment times. Alignment units are one per whole note;
fixtures calibrate them with quarter and whole notes. Parser onset evidence is
recorded separately through the caller's unchanged kern_parser API.

This suite is bounded to the import cases it asserts. Own-grace paint order and
interior sounding holds without a timed canonical peer are separate limitations.
No golden images are captured.

The baseline runner must be linked to the caller's unchanged selected library.
With it, the suite also compares note/rest/control semantics and native note times,
preserves existing alias edges, and independently compares five visible-source
controls at staff space, including all affine components and effective paint.
Without it, the explicit baseline-comparison test is skipped.

The green result covers these assertions. The conflicting held-clef buffer,
nested note routing, own-grace paint order and sounding-interior timing fixtures
also retain pre-existing limitations. Their presence is not a conformance claim
for those behaviors. The suite creates no bytecode or build output in this tree.

For the direction-carrier matrix, also pass `--previous-runner` linked to the
actual 933e68a6 library. New direction objects compare with the selected old
baseline; their other semantics compare with that already corrected prior
library. Native-only `*join`/`*Xjoin` cases cover early returns and are not
accepted-parser fixtures. Meter-restatement and unpainted direction objects
remain preservation controls, not newly supported text painting.

`verify-mrest-key.py` checks source keys at the existing single-rest endpoint,
clef/key order and register, invisible rests, split-layer ownership and unchanged
rest/fill/event data. Its zero-key case preserves the selected normal handler's
existing empty inline group; it is not a new cancellation-paint success. Interior
rest keys and compressed multirests retain their old omissions.

`verify-empty-span.py` checks context carried across no-data barline spans,
actual measure/container identity, repeat/double bars, per-staff transposition,
initial/ignored/terminal spans and previously emitted tail keys. Link this
`render.cpp` for its additional `observer-prefix` mode: scoreDef alignment time
-1 is the existing layout-prefix sentinel, while `measure-end` reports the
measure aligner's actual endpoint. Default observer output remains unchanged.
Pass absolute verifier paths when using Clef's heavy-gate runner.

Same-onset key-before-clef sources preserve MEI order and key register. The normal
renderer’s paint priority is a separate baseline limitation, not an alignment
correction made by these import assertions.
