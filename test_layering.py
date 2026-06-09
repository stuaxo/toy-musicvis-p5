"""Test that GlowCube layers over RadialFlare without entering the feedback loop.

Two checks:
  1. A pixel in the flare region (outside the cube face) is non-black — flare is visible.
  2. After several frames, that pixel is NOT getting brighter over time — the cube
     isn't feeding back into the ScaledBackground loop and accumulating.

Run:  python test_layering.py
Pass: exits 0
Fail: exits 1 with a description
"""

import sys
import py5
from visuals import ScaledBackground, RadialFlare, GlowCube

WIDTH, HEIGHT = 300, 300

# With mid=0, spread=0.5: push=1.0, beads at 40/80/120px from centre along angle=0 (right).
# Cube base_size=60, bass=0: box side=120px, spans cx±60 (x=90..210).
# Bead 2 at cx+80=230 is outside the cube face — good check point.
CHECK_X = WIDTH // 2 + 80
CHECK_Y = HEIGHT // 2

# Capture brightness at two points in time: if cube trails are feeding back,
# brightness at CHECK_X,CHECK_Y will be much higher later than earlier.
CAPTURE_FRAMES = [5, 25]


class MockAnalysis:
    bass = 0.0
    mid = 0.0
    treble = 0.0
    def update(self):
        pass


class LayeringTest(py5.Sketch):
    samples = []
    error = None

    def settings(self):
        self.size(WIDTH, HEIGHT, self.P3D)

    def setup(self):
        analysis = MockAnalysis()
        self.main_buf = self.create_graphics(WIDTH, HEIGHT, self.P3D)
        self.main_buf.begin_draw()
        self.main_buf.background(15)
        self.main_buf.end_draw()

        self.flare = RadialFlare(
            analysis,
            num_spokes=1,
            beads_per_spoke=6,
            spacing=40,
            spread=0.5,
            rotate_speed=0.0,
        )
        self.cube = GlowCube(
            analysis,
            base_size=60,
            max_pump=0,
            yaw_speed=0.0,
            pitch_speed=0.0,
        )
        self.bg = ScaledBackground(zoom=1.01, fade=20)

        for e in [self.bg, self.flare, self.cube]:
            e.setup(self)

    def draw(self):
        self.main_buf.begin_draw()
        self.bg.draw(self, self.main_buf)
        self.flare.draw(self, self.main_buf)
        self.main_buf.end_draw()

        self.background(15)
        self.image(self.main_buf, 0, 0)
        self.cube.draw(self, self)

        if self.frame_count in CAPTURE_FRAMES:
            self.load_np_pixels()
            pixel = self.np_pixels[CHECK_Y, CHECK_X]
            brightness = int(pixel[0]) + int(pixel[1]) + int(pixel[2])
            LayeringTest.samples.append((self.frame_count, brightness, tuple(int(x) for x in pixel[:3])))

        if self.frame_count >= max(CAPTURE_FRAMES):
            self.exit_sketch()


sketch = LayeringTest()
sketch.run_sketch(block=True)

if LayeringTest.error:
    print(f"ERROR: {LayeringTest.error}")
    sys.exit(1)

if len(LayeringTest.samples) < 2:
    print("ERROR: not enough samples captured")
    sys.exit(1)

failures = []

for frame, brightness, rgb in LayeringTest.samples:
    print(f"  frame {frame:2d}  pixel ({CHECK_X},{CHECK_Y})  rgb={rgb}  brightness={brightness}")
    if brightness <= 30:
        failures.append(f"frame {frame}: pixel too dark (brightness={brightness}) — flare not visible")

# If the cube is trailing into the feedback loop, brightness will compound
# dramatically. Allow for some ScaledBackground accumulation of the flare itself,
# but the cube face colour (blue, ~80,130,255) would push brightness very high.
early_b = LayeringTest.samples[0][1]
late_b  = LayeringTest.samples[-1][1]
if late_b > early_b * 4:
    failures.append(
        f"brightness grew {early_b}→{late_b} over {max(CAPTURE_FRAMES)-min(CAPTURE_FRAMES)} frames "
        f"— cube may be feeding into the feedback loop"
    )

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1)

print("PASS: RadialFlare visible, cube not accumulating in feedback loop")
