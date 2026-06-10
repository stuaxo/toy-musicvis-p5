"""Test that GlowCube layers over RadialFlare without entering the feedback loop.

Two checks:
  1. A pixel in the flare region (outside the cube face) is non-black — flare is visible.
  2. After several frames, that pixel is NOT getting brighter over time — the cube
     isn't feeding back into the ZoomFadeFeedback loop and accumulating.

Run:  python test_layering.py
Pass: exits 0
Fail: exits 1 with a description
"""

import sys
import py5
from visuals import FeedbackBuffer, ZoomFadeFeedback, RadialFlare, GlowCube

WIDTH, HEIGHT = 300, 300

# With mid=0, spread=0.5: push=1.0, beads at 40/80/120px from centre along angle=0 (right).
# Cube base_size=60, bass=0: box side=120px, spans cx±60 (x=90..210).
# Bead 2 at cx+80=230 is outside the cube face — good check point.
CHECK_X = WIDTH // 2 + 80
CHECK_Y = HEIGHT // 2

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
        self.feedback = FeedbackBuffer(self, WIDTH, HEIGHT, self.P3D)
        self.zoom_fade = ZoomFadeFeedback(zoom=1.01, fade=20)
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
        for e in [self.flare, self.cube]:
            e.setup(self)

    def draw(self):
        with self.feedback.composite(self, [self.zoom_fade]) as ctx:
            self.flare.draw(self, ctx)

        self.background(15)
        self.feedback.display(self)
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
