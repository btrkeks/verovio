# Layer clef import assertions

Link `render.cpp` to the exact caller's static library, with matching headers
and resources. Build outputs must live outside the source checkout.

```sh
c++ -std=c++20 -Itools -Iinclude -Iinclude/vrv -Iinclude/tuning-library -Iinclude/hum -Iinclude/midi -Iinclude/json -Iinclude/pugi -Ilibmei/dist -Ilibmei/addons doc/clef-tests/render.cpp /absolute/libverovio.a -pthread -o /outside/clef-render
python3 doc/clef-tests/verify.py --runner /outside/clef-render --resources /matching/resources --output /outside/proof
```

The observer subclasses Toolkit to read its protected document after the normal
load/render path. The suite compares its MEI and SVG with the public C wrapper
before trusting alignment times. Alignment units are one per whole note;
fixtures calibrate them with quarter and whole notes. Parser onset evidence is
recorded separately through the caller's unchanged kern_parser API.

This suite is bounded to the import cases it asserts. Own-grace paint order and
interior sounding holds without a timed canonical peer are separate limitations.
No golden images are captured.
