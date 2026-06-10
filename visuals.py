"""Visual effects.

Each effect owns three phases:

    setup(sketch)        one-time initialisation
    update(sketch)       per-frame state changes, NO drawing
    draw(sketch, ctx)    per-frame drawing onto ctx

`ctx` is the drawing surface: normally the sketch itself, but it can be
a Py5Graphics buffer instead — the same draw() works on either.

Effects may offer a `layer_hint` suggesting where they'd like to sit in
the stack. It is only a hint: the Visualiser reads it and decides the
actual arrangement. Effects that don't care inherit the default (main).
"""

import random
from contextlib import contextmanager

import py5

# layer hints — the Visualiser interprets these
LAYER_MAIN = "main"   # feeds the feedback loop (caught in the grab + trails)
LAYER_TOP = "top"     # drawn fresh on top each frame, never grabbed


class FeedbackBuffer:
    """Generic double-buffer manager for ping-ponging frame states.

    This architecture relies on the "Double Buffering" (or Ping-Pong) 
    graphics pattern. It prevents visual tearing and hardware pipeline 
    stalls that occur when attempting to read from and write to the 
    same GPU texture simultaneously.

    Further Reading & Context:
    - Game Programming Patterns (Double Buffer):
      https://gameprogrammingpatterns.com/double-buffer.html
    - OpenGL Ping-Ponging (LearnOpenGL):
      https://learnopengl.com/Advanced-Lighting/Bloom
    """

    def __init__(self, sketch, width, height, renderer):
        # Tied directly to the sketch instance to inherit the OpenGL context
        self.buf_a = sketch.create_graphics(width, height, renderer)
        self.buf_b = sketch.create_graphics(width, height, renderer)
        self.curr_buf = self.buf_a
        self.prev_buf = self.buf_b
        self.clear()

    def clear(self):
        """Wipe accumulated trails."""
        for buf in (self.buf_a, self.buf_b):
            buf.begin_draw()
            buf.background(15)
            buf.end_draw()

    @contextmanager
    def composite(self, sketch, feedback_effects):
        """Prepares the historical texture, yields for drawing, then swaps buffers."""
        self.curr_buf.begin_draw()
        
        # --- CRITICAL FIX ---
        # Clear the color and depth buffers for the fresh frame pass
        # so the GPU doesn't depth-clip our feedback history!
        self.curr_buf.background(15)
        
        # Sequentially apply feedback/post-processing effects
        for effect in feedback_effects:
            effect.apply(sketch, self.prev_buf, self.curr_buf)

        try:
            yield self.curr_buf
        finally:
            self.curr_buf.end_draw()
            # Ping-pong swap
            self.curr_buf, self.prev_buf = self.prev_buf, self.curr_buf

    def display(self, sketch):
        """Blit the completed layer to the main sketch canvas safely."""
        sketch.hint(sketch.DISABLE_DEPTH_TEST)
        sketch.image(self.prev_buf, 0, 0)
        sketch.hint(sketch.ENABLE_DEPTH_TEST)


class FeedbackEffect:
    """Base class for effects modifying the historical accumulation stream."""
    def setup(self, preset):
        pass
    def update(self, sketch):
        pass
    def apply(self, sketch, prev_buf, curr_buf):
        pass


class ZoomFadeFeedback(FeedbackEffect):
    """Classic Milkdrop-style expanding trail effect."""

    def __init__(self, zoom=None, fade=None):
        self.zoom = zoom if zoom is not None else random.uniform(1.006, 1.018)
        self.fade = fade if fade is not None else random.randint(14, 26)

    def apply(self, sketch, prev_buf, curr_buf):
        cx, cy = curr_buf.width / 2, curr_buf.height / 2

        # Matrix isolation lives inside the effect, protecting the pipeline
        curr_buf.push_matrix()
        curr_buf.translate(cx, cy)
        curr_buf.scale(self.zoom)
        curr_buf.translate(-cx, -cy)

        # Disable the depth test so that 3D objects aren't clipped by the background
        curr_buf.hint(curr_buf.DISABLE_DEPTH_TEST)

        curr_buf.tint(255, 255 - self.fade)
        curr_buf.image(prev_buf, 0, 0)
        curr_buf.no_tint()

        curr_buf.hint(curr_buf.ENABLE_DEPTH_TEST)

        curr_buf.pop_matrix()



class VisualEffect:
    """Base class. Effects override whichever phases they need and may
    set a layer_hint to suggest their place in the stack."""

    layer_hint = LAYER_MAIN
    feeds_back = True

    def setup(self, sketch):
        pass

    def update(self, sketch):
        pass

    def draw(self, sketch, ctx):
        pass

    def end(self, sketch):
        pass


class RadialFlare(VisualEffect):
    """Small light-blue circles strung along invisible rotating spokes,
    drifting outward from the centre like a soft, beaded lens flare.

    Stays on the main layer so the beads get caught in the feedback and
    leave curved spiral trails as they rotate + zoom outward.
    """

    def __init__(self, analysis, num_spokes=None, beads_per_spoke=None,
                 spacing=None, spread=None, rotate_speed=None):
        self.analysis = analysis
        # None means "pick a random value in a tasteful range"
        if num_spokes is None:
            num_spokes = random.randint(5, 12)
        if beads_per_spoke is None:
            beads_per_spoke = random.randint(5, 8)
        if spacing is None:
            spacing = random.uniform(35, 55)
        if spread is None:
            spread = random.uniform(0.3, 0.6)
        if rotate_speed is None:
            # random magnitude AND direction
            rotate_speed = random.choice([-1, 1]) * random.uniform(0.002, 0.007)
        self.num_spokes = num_spokes
        self.beads_per_spoke = beads_per_spoke
        self.spacing = spacing            # base px between beads along a spoke
        self.spread = spread              # how much audio pushes beads outward
        self.rotate_speed = rotate_speed  # radians added per frame
        self.angle = 0.0
        self.level = 0.0

    def update(self, sketch):
        # mid band, so it isn't fighting bass (core) or treble (rim)
        self.level = self.analysis.mid
        self.angle += self.rotate_speed

    def draw(self, sketch, ctx):
        cx, cy = sketch.width / 2, sketch.height / 2
        push = 1.0 + min(self.level * self.spread, 2.0)

        ctx.no_stroke()
        for s in range(self.num_spokes):
            spoke_angle = self.angle + py5.TWO_PI * s / self.num_spokes
            dx, dy = py5.cos(spoke_angle), py5.sin(spoke_angle)
            for b in range(1, self.beads_per_spoke + 1):
                dist = b * self.spacing * push
                x = cx + dx * dist
                y = cy + dy * dist
                falloff = 1.0 - (b - 1) / self.beads_per_spoke
                size = 3 + 9 * falloff
                alpha = 30 + 90 * falloff
                ctx.fill(150, 200, 255, alpha)
                ctx.circle(x, y, size)

    

class GlowCircle(VisualEffect):
    """Bass-pumped glow core with a treble-reactive jagged rim.

    Hints the top layer: drawn fresh on top every frame and never caught
    in the feedback, so the bright core doesn't compound into saturation.
    """

    layer_hint = LAYER_TOP
    feeds_back = True

    def __init__(self, analysis, base_radius=100, max_pump=200,
                 num_spikes=None, spike_length=None):
        self.analysis = analysis
        # base_radius and max_pump are structural — kept stable, not random
        self.base_radius = base_radius
        self.max_pump = max_pump
        # None means "pick a random value in a tasteful range"
        if num_spikes is None:
            num_spikes = random.choice([60, 90, 120, 160])
        if spike_length is None:
            spike_length = random.uniform(0.7, 1.4)
        self.num_spikes = num_spikes
        self.spike_length = spike_length
        self.bass = 0.0
        self.treble = 0.0

    def update(self, sketch):
        self.bass = self.analysis.bass
        self.treble = self.analysis.treble

    def draw(self, sketch, ctx):
        cx, cy = sketch.width / 2, sketch.height / 2
        radius = self.base_radius + min(self.bass, self.max_pump)

        # glow core: three stacked translucent circles
        ctx.no_stroke()
        ctx.fill(100, 150, 255, 60)
        ctx.circle(cx, cy, (radius + 40) * 2)
        ctx.fill(100, 150, 255, 120)
        ctx.circle(cx, cy, (radius + 15) * 2)
        ctx.fill(120, 170, 255)
        ctx.circle(cx, cy, radius * 2)

        # treble spikes around the rim
        ctx.stroke(180, 220, 255)
        ctx.stroke_weight(2)
        ctx.no_fill()
        ctx.begin_shape()
        for i in range(self.num_spikes):
            angle = py5.TWO_PI * i / self.num_spikes
            jag = (1.0 if i % 2 == 0 else 0.4) + py5.random(0.3)
            r = radius + self.treble * self.spike_length * jag
            ctx.vertex(cx + py5.cos(angle) * r, cy + py5.sin(angle) * r)
        ctx.end_shape(ctx.CLOSE)


class GlowCube(VisualEffect):
    """Bass-pumped rotating wireframe cube using py5's native P3D box().

    Requires the sketch to use the P3D renderer (self.P3D in settings()).
    Bass pumps the size; treble shifts the edge colour toward white.
    Drawn in four glow passes (wide+dim → narrow+bright) for a neon look.
    """

    layer_hint = LAYER_TOP
    feeds_back = True

    def __init__(self, analysis, base_size=80, max_pump=100,
                 yaw_speed=None, pitch_speed=None):
        self.analysis = analysis
        self.base_size = base_size
        self.max_pump = max_pump
        if yaw_speed is None:
            yaw_speed = random.choice([-1, 1]) * random.uniform(0.008, 0.020)
        if pitch_speed is None:
            pitch_speed = random.choice([-1, 1]) * random.uniform(0.005, 0.015)
        self.yaw_speed = yaw_speed
        self.pitch_speed = pitch_speed
        self.yaw = 0.0
        self.pitch = 0.0
        self.bass = 0.0
        self.treble = 0.0

    def setup(self, sketch):
        # Offscreen P3D buffer — keeps its depth buffer separate from the
        # main 2D canvas so ScaledBackground feedback is unaffected.
        self.pg = sketch.create_graphics(sketch.width, sketch.height, sketch.P3D)

    def update(self, sketch):
        self.bass = self.analysis.bass
        self.treble = self.analysis.treble
        self.yaw += self.yaw_speed
        self.pitch += self.pitch_speed

    def draw(self, sketch, ctx):
        cx, cy = sketch.width / 2, sketch.height / 2
        side = (self.base_size + min(self.bass, self.max_pump)) * 2
        treble_t = min(self.treble / 100.0, 1.0)

        self.pg.begin_draw()
        self.pg.clear()  # transparent + depth reset
        self.pg.ambient_light(40, 40, 100)
        self.pg.point_light(220, 230, 255, cx, cy - 300, 500)
        self.pg.push_matrix()
        self.pg.translate(cx, cy, 0)
        self.pg.rotate_x(self.pitch)
        self.pg.rotate_y(self.yaw)
        self.pg.fill(80, 130, 255)
        self.pg.stroke(int(180 + 75 * treble_t), 220, 255)
        self.pg.stroke_weight(1)
        self.pg.box(side)
        self.pg.pop_matrix()
        self.pg.no_lights()
        self.pg.end_draw()

        ctx.image(self.pg, 0, 0)
