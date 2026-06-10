"""Audio visualiser — entry point.

Run this file (in Thonny: normal Run button, py5 imported mode toggle OFF,
since this is class-mode py5 with an explicit run_sketch()).

Wires the audio pipeline (audio.py) to the visual effects (visuals.py).
Visual parameters are randomised: any effect param left as None rolls a
value in a tasteful range. Press 'n' or space for the next visual (a
fresh roll). The audio pipeline is created once and survives switches.
"""

import random
from datetime import datetime

import py5

from music import AudioSampler, AudioAnalyse
from visuals import FeedbackBuffer, ZoomFadeFeedback, RadialFlare, GlowCircle, GlowCube, LAYER_TOP

# Canvas params
WIDTH = 600
HEIGHT = 600

# audio
SAMPLERATE = 44100
CHUNK_SIZE = 1024
GAIN = 0.02
""" Raise if reaction is weak, lower if it pins to max """

# vis
BASE_RADIUS = 100
MAX_PUMP = 200


class VisualPreset:
    def __init__(self, analysis, sketch):
        self.analysis = analysis
        self.sketch = sketch
        self.effects = []
        self.feedback_effects = []
        self.composite_effects = []
        self.screen_effects = []

class Preset1(VisualPreset):
    def build_effects(self):
        """(Re)build the visual layer. Effects with None params self-randomise,
        so each call produces a fresh look. Audio is left untouched."""
        self.feedback_effects = [ZoomFadeFeedback()]
        self.effects = [
            RadialFlare(self.analysis),
            GlowCircle(self.analysis,
                      base_radius=BASE_RADIUS,
                      max_pump=MAX_PUMP),
        ]
        self.composite_effects = sorted(
            [e for e in self.effects if e.feeds_back],
            key=lambda e: e.layer_hint == LAYER_TOP,
        )
        self.screen_effects = [e for e in self.effects if not e.feeds_back]
        for effect in self.effects:
            effect.setup(self.sketch)

class Preset2(VisualPreset):
    def build_effects(self):
        self.feedback_effects = [ZoomFadeFeedback()]
        self.effects = [
            RadialFlare(self.analysis),
            GlowCube(self.analysis,
                     base_size=80,
                     max_pump=100),
        ]
        self.composite_effects = sorted(
            [e for e in self.effects if e.feeds_back],
            key=lambda e: e.layer_hint == LAYER_TOP,
        )
        self.screen_effects = [e for e in self.effects if not e.feeds_back]
        for effect in self.effects:
            effect.setup(self.sketch)


class MusicVisualiser(py5.Sketch):

    def __init__(self, analysis):
        super().__init__()
        self.analysis = analysis

    def settings(self):
        self.size(WIDTH, HEIGHT, self.P2D)

    def setup(self):
        self.feedback = FeedbackBuffer(self, WIDTH, HEIGHT, self.P3D)
        self.go_to_next_preset()

    def go_to_next_preset(self):
        if hasattr(self, 'preset'):
            for effect in self.preset.effects:
                effect.end(self)
        self.feedback.clear()
        self.preset = random.choice([Preset1, Preset2])(self.analysis)
        self.preset.build_effects()

    def update(self):
        self.analysis.update()
        for effect in self.preset.effects:
            effect.update(self)

    def draw(self):
        self.update()
        
        with self.feedback.composite(self, self.preset.feedback_effects) as ctx:
            for effect in self.preset.composite_effects:
                effect.draw(self, ctx)

        self.background(15)
        self.feedback.display(self)

        for effect in self.preset.screen_effects:
            effect.draw(self, self)

    def save_layers(self):
        prefix = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.feedback.prev_buf.save(f"{prefix}_1_feedback.png")

        effects_buf = self.create_graphics(self.width, self.height, self.P3D)
        effects_buf.begin_draw()
        effects_buf.background(0)
        for effect in self.preset.composite_effects + self.preset.screen_effects:
            effect.draw(self, effects_buf)
        effects_buf.end_draw()
        effects_buf.save(f"{prefix}_2_effects.png")

        self.save_frame(f"{prefix}_3_full.png")
        print(f"Saved layers: {prefix}_*.png")

    def key_pressed(self):
        if self.key in 'nN ':
            self.go_to_next_preset()
        elif self.key in 'sS':
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.save_frame(filename)
            print(f"Saved {filename}")
        elif self.key in 'dD':
            self.save_layers()

    def exiting(self):
        self.analysis.sampler.close()


def main():
    # Audio must be initialised on the main Python thread before the JVM
    # timer thread starts calling setup() — sounddevice's cffi callbacks
    # crash when first registered from within a JPype-proxied JVM thread.
    sampler = AudioSampler(samplerate=SAMPLERATE, chunk_size=CHUNK_SIZE)
    analysis = AudioAnalyse(sampler, bass=True, mid=True, treble=True, gain=GAIN)
    sketch = MusicVisualiser(analysis)
    sketch.run_sketch()


if __name__ == "__main__":
    main()
