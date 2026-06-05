"""Audio visualiser — entry point.

Run this file (in Thonny: normal Run button, py5 imported mode toggle OFF,
since this is class-mode py5 with an explicit run_sketch()).

Wires the audio pipeline (audio.py) to the visual effects (visuals.py).
Visual parameters are randomised: any effect param left as None rolls a
value in a tasteful range. Press 'n' or space for the next visual (a
fresh roll). The audio pipeline is created once and survives switches.
"""

import random

import py5

from music import AudioSampler, AudioAnalyse
from visuals import ScaledBackground, RadialFlare, GlowCircle, GlowCube, LAYER_TOP

# Canvas params
WIDTH = 600
HEIGHT = 600

# audio
SAMPLERATE = 44100
CHUNK_SIZE = 1024
GAIN = 0.02          # raise if reaction is weak, lower if it pins to max

# vis
BASE_RADIUS = 100
MAX_PUMP = 200


class VisualPreset:
    def __init__(self, analysis):
        self.analysis = analysis
        self.effects = []

class Preset1(VisualPreset):
    def build_effects(self):
        """(Re)build the visual layer. Effects with None params self-randomise,
        so each call produces a fresh look. Audio is left untouched."""
        self.effects = [
            ScaledBackground(),                 # zoom/fade -> random
            RadialFlare(self.analysis),         # all flare params -> random
            GlowCircle(self.analysis,
                      base_radius=BASE_RADIUS,  # pinned structural params
                      max_pump=MAX_PUMP),       # num_spikes/spike_length -> random
        ]
        self.main_effects = [e for e in self.effects if e.layer_hint != LAYER_TOP]
        self.top_effects = [e for e in self.effects if e.layer_hint == LAYER_TOP]
        for effect in self.effects:
            effect.setup(self)



class Preset2(VisualPreset):
    def build_effects(self):
        self.effects = [
            ScaledBackground(),
            RadialFlare(self.analysis),
            GlowCube(self.analysis,
                     base_size=80,
                     max_pump=100),
        ]
        self.main_effects = [e for e in self.effects if e.layer_hint != LAYER_TOP]
        self.top_effects = [e for e in self.effects if e.layer_hint == LAYER_TOP]
        for effect in self.effects:
            effect.setup(self)


class MusicVisualiser(py5.Sketch):

    def settings(self):
        self.size(WIDTH, HEIGHT, self.P3D)

    def setup(self):
        # audio set up ONCE — never rebuilt on a visual switch
        self.sampler = AudioSampler(samplerate=SAMPLERATE, chunk_size=CHUNK_SIZE)
        self.analysis = AudioAnalyse(
            self.sampler, bass=True, mid=True, treble=True, gain=GAIN)
        self.background(15)
        self.go_to_next_preset()


    def go_to_next_preset(self):
        self.preset = random.choice([Preset1, Preset2])(self.analysis)
        self.preset.build_effects()

    def draw(self):
        for effect in self.preset.effects:
            effect.update(self)
        for effect in self.preset.main_effects:
            effect.draw(self, self)
        for effect in self.preset.top_effects:
            effect.draw(self, self)

    def key_pressed(self):
        if self.key in 'nN ':
            self.go_to_next_preset()

    def exiting(self):
        self.sampler.close()


def main():
    sketch = MusicVisualiser()
    sketch.run_sketch()


if __name__ == "__main__":
    main()
