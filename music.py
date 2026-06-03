"""Audio capture and analysis.

No py5 dependency here — this module only knows about sound devices,
NumPy, and FFT. It can be tested or reused entirely independently of
the visualiser.
"""

import threading

import numpy as np
import sounddevice as sd


class AudioSampler:
    """Singleton that owns the input stream and its callback.

    Guarded as a singleton because there is one physical input device;
    constructing it twice would try to open that device twice and raise
    a "device busy" error. Repeated construction returns the same
    instance and the stream is only started once.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self, samplerate=44100, chunk_size=1024, device=None):
        if self._initialised:          # singleton: only set up once
            return
        self.samplerate = samplerate
        self.chunk_size = chunk_size
        self._latest = np.zeros(chunk_size)
        self._lock = threading.Lock()
        self._stream = sd.InputStream(
            channels=1,
            samplerate=samplerate,
            blocksize=chunk_size,
            device=device,
            callback=self._callback,
        )
        self._stream.start()
        self._initialised = True

    def _callback(self, indata, frames, time, status):
        # Keep the audio-thread callback as tiny as possible: just stash
        # the newest chunk. All heavy lifting happens on the draw thread.
        with self._lock:
            self._latest = indata.mean(axis=1).copy()   # stereo -> mono

    def latest(self):
        """Thread-safe snapshot of the most recent audio chunk."""
        with self._lock:
            return self._latest.copy()

    def close(self):
        self._stream.stop()
        self._stream.close()


class AudioAnalyse:
    """Pulls chunks from a sampler, runs the FFT, exposes band levels.

    Each enabled band is smoothed with a fast-attack / slow-decay
    envelope so the values respond musically instead of jittering.
    """

    # band edges in Hz
    BANDS = {
        "bass":   (20, 250),
        "mid":    (250, 4000),
        "treble": (4000, 20000),
    }

    def __init__(self, sampler, bass=False, mid=False, treble=False,
                 gain=0.02, decay=0.85):
        self.sampler = sampler
        self.gain = gain
        self.decay = decay
        self._active = [name for name, on in
                        (("bass", bass), ("mid", mid), ("treble", treble))
                        if on]
        self._values = {name: 0.0 for name in self._active}
        # freq axis + window depend only on chunk size + rate, so build once
        self._freqs = np.fft.rfftfreq(sampler.chunk_size, 1 / sampler.samplerate)
        self._window = np.hanning(sampler.chunk_size)

    def update(self):
        """Call once per frame: pull audio, FFT, update smoothed bands."""
        chunk = self.sampler.latest()
        mags = np.abs(np.fft.rfft(chunk * self._window))
        for name in self._active:
            lo, hi = self.BANDS[name]
            mask = (self._freqs >= lo) & (self._freqs < hi)
            raw = (mags[mask].sum() if mask.any() else 0.0) * self.gain
            old = self._values[name]
            # fast attack (jump up), slow decay (ease down)
            self._values[name] = (
                raw if raw > old
                else old * self.decay + raw * (1 - self.decay)
            )

    @property
    def bass(self):
        return self._values.get("bass", 0.0)

    @property
    def mid(self):
        return self._values.get("mid", 0.0)

    @property
    def treble(self):
        return self._values.get("treble", 0.0)