"""
Wake detector — two claps + "JARVIS" keyword activates the voice agent.

Pipeline:
  sounddevice (always-on mic)
    → clap detector (energy spike × 2 within 1.5 s)
    → wait for "JARVIS" (speech_recognition + Google free API)
    → fire callback to start the voice session

Install deps:
  uv add sounddevice numpy SpeechRecognition
"""

import logging
import time
import threading
from typing import Callable

logger = logging.getLogger("jarvis.wake")


class ClapDetector:
    """
    Detects exactly 2 hand-claps within a 1.5 s window using amplitude thresholding.
    """

    SAMPLE_RATE = 16_000
    BLOCK_SIZE = 512           # ~32 ms per block
    CLAP_THRESHOLD = 0.35      # Amplitude [0.0 – 1.0] to count as a clap
    MIN_GAP_S = 0.10           # Minimum gap between two clap events (s)
    WINDOW_S = 1.5             # Time window within which 2 claps must occur

    def __init__(self, on_double_clap: Callable):
        self._callback = on_double_clap
        self._clap_times: list[float] = []
        self._cooldown_until: float = 0.0
        self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        try:
            import numpy as np
            amplitude = float(np.abs(indata).max())
            now = time.monotonic()

            if amplitude > self.CLAP_THRESHOLD and now > self._cooldown_until:
                self._cooldown_until = now + self.MIN_GAP_S
                self._clap_times.append(now)
                logger.debug("Clap detected (amp=%.2f)", amplitude)

            # Prune old claps outside the window
            self._clap_times = [t for t in self._clap_times if now - t <= self.WINDOW_S]

            if len(self._clap_times) >= 2:
                logger.info("Double clap detected!")
                self._clap_times.clear()
                self._cooldown_until = now + 1.0  # 1s cooldown after trigger
                self._callback()
        except Exception as e:
            logger.error("Clap callback error: %s", e)

    def start(self):
        try:
            import sounddevice as sd
            self._stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                blocksize=self.BLOCK_SIZE,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info("Clap detector started")
        except ImportError:
            logger.error("sounddevice not installed — run: uv add sounddevice numpy")
        except Exception as e:
            logger.error("Could not start clap detector: %s", e)

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None


class KeywordListener:
    """
    After claps are detected, listens for the spoken keyword 'JARVIS'.
    Uses SpeechRecognition with Google's free API — no key needed.
    """

    TIMEOUT_S = 5       # How long to wait for speech after clap
    KEYWORD = "jarvis"

    def __init__(self, on_keyword: Callable):
        self._callback = on_keyword

    def listen(self):
        """Blocking: record a short phrase and check for the keyword."""
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True

            with sr.Microphone(sample_rate=16000) as source:
                logger.info("Listening for 'JARVIS'...")
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                try:
                    audio = recognizer.listen(source, timeout=self.TIMEOUT_S, phrase_time_limit=3)
                except sr.WaitTimeoutError:
                    logger.debug("Keyword timeout — no speech detected")
                    return

            text = recognizer.recognize_google(audio).lower()
            logger.info("Heard: '%s'", text)

            if self.KEYWORD in text:
                logger.info("JARVIS keyword confirmed!")
                self._callback()
        except ImportError:
            logger.error("SpeechRecognition not installed — run: uv add SpeechRecognition")
        except Exception as e:
            logger.debug("Keyword listen error: %s", e)


class WakeDetector:
    """
    Full wake detection pipeline:
      1. Always-on clap listener
      2. On double clap → start keyword listener
      3. On 'JARVIS' heard → fire on_wake callback

    Usage:
        detector = WakeDetector(on_wake=my_callback)
        detector.start()          # non-blocking, runs in background thread
        ...
        detector.stop()
    """

    def __init__(self, on_wake: Callable):
        self._on_wake = on_wake
        self._keyword = KeywordListener(on_keyword=self._on_wake)
        self._clap = ClapDetector(on_double_clap=self._on_clap_detected)
        self._listening_for_keyword = False
        self._lock = threading.Lock()

    def _on_clap_detected(self):
        with self._lock:
            if self._listening_for_keyword:
                return  # Already waiting — ignore
            self._listening_for_keyword = True

        # Spawn a thread so clap stream isn't blocked
        t = threading.Thread(target=self._keyword_thread, daemon=True)
        t.start()

    def _keyword_thread(self):
        try:
            self._keyword.listen()
        finally:
            with self._lock:
                self._listening_for_keyword = False

    def start(self):
        logger.info("Wake detector armed — clap twice, then say 'JARVIS'")
        self._clap.start()

    def stop(self):
        self._clap.stop()
        logger.info("Wake detector stopped")
