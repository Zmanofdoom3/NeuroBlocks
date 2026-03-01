import numpy as np
import time
from typing import TYPE_CHECKING
# try to import pylsl at runtime; if unavailable we disable LSL-dependent features.
try:
    from pylsl import resolve_stream, StreamInlet  # type: ignore
    _PYLSL_AVAILABLE = True
except Exception:
    resolve_stream = None
    StreamInlet = None
    _PYLSL_AVAILABLE = False
from settings import CALIBRATION_TIME

class BCIEngine:
    def __init__(self, debug=False):
        self.connected = False
        self.inlet = None
        self.baseline_alpha = 0
        self.baseline_beta = 0
        self.calibrated = False
        self.start_time = time.time()
        self.samples_collected = 0
        self.debug = bool(debug)

        # optional bci-essentials integration detection
        try:
            import bci_essentials as be  # type: ignore
            self.be = be
            self.be_available = True
        except Exception:
            self.be = None
            self.be_available = False
            if self.debug:
                print("bci-essentials not available, continuing without it")

        if _PYLSL_AVAILABLE:
            try:
                streams = resolve_stream('type', 'EEG', timeout=3)
                if streams:
                    self.inlet = StreamInlet(streams[0])
                    self.connected = True
                    print("EEG Connected")
                else:
                    print("No EEG Stream Found")
            except Exception as e:
                print("EEG Connection Failed:", e)
        else:
            if self.debug:
                print("pylsl not installed; skipping EEG stream connection and running in offline/debug mode")

    def band_power(self, data, sfreq):
        # keep the existing internal implementation as a fallback
        freqs = np.fft.rfftfreq(len(data), 1/sfreq)
        fft = np.abs(np.fft.rfft(data))

        def band(low, high):
            idx = np.where((freqs >= low) & (freqs <= high))
            return np.mean(fft[idx]) if len(idx[0]) > 0 else 0

        # If bci-essentials is installed and provides a simple bandpower helper,
        # prefer it for potentially improved algorithms (but we check safely).
        if self.be_available:
            try:
                # try common helper names safely; fall back on local FFT if not present
                if hasattr(self.be, "bandpower"):
                    a = float(self.be.bandpower(data, sfreq, [8, 12]))
                    b = float(self.be.bandpower(data, sfreq, [13, 30]))
                    return a, b
                if hasattr(self.be, "spectral") and hasattr(self.be.spectral, "psd"):
                    # best-effort attempt; still fall back if shape/names differ
                    # keep fallback below as main method
                    pass
            except Exception:
                if self.debug:
                    print("bci-essentials helper call failed, falling back to local FFT")

        return band(8,12), band(13,30)

    def update(self):
        if not self.connected:
            return None

        samples, _ = self.inlet.pull_chunk(timeout=0.0)
        if not samples:
            return None

        data = np.array(samples).T
        channel = data[0]
        sfreq = 256

        alpha, beta = self.band_power(channel, sfreq)

        if self.debug:
            print(f"[BCI DEBUG] raw alpha={alpha:.3f} beta={beta:.3f}")

        if not self.calibrated:
            if time.time() - self.start_time < CALIBRATION_TIME:
                self.baseline_alpha += alpha
                self.baseline_beta += beta
                self.samples_collected += 1
                if self.debug:
                    print(f"[BCI DEBUG] Calibrating... samples={self.samples_collected}")
                return None
            else:
                if self.samples_collected > 0:
                    self.baseline_alpha /= self.samples_collected
                    self.baseline_beta /= self.samples_collected
                else:
                    self.baseline_alpha = alpha
                    self.baseline_beta = beta
                self.calibrated = True
                print("Calibration Complete")
                if self.debug:
                    print(f"[BCI DEBUG] baselines alpha={self.baseline_alpha:.3f} beta={self.baseline_beta:.3f}")

        # decision thresholds (kept from original)
        move_left = alpha > self.baseline_alpha * 1.3
        move_right = alpha < self.baseline_alpha * 0.7
        rotate = alpha > self.baseline_alpha * 1.6
        drop_speed = max(1, beta / self.baseline_beta) if self.baseline_beta > 0 else 1

        commands = {
            "left": move_left,
            "right": move_right,
            "rotate": rotate,
            "drop_multiplier": drop_speed
        }

        if self.debug:
            print(f"[BCI DEBUG] commands={commands}")

        return commands
