// Microphone capture -> chroma frames.
//
// Audio never leaves the browser and raw PCM is never retained. What we
// keep is the derived chroma stream: 24 floats per frame at 20 Hz, about
// 2 KB/s, from which the original audio cannot be reconstructed. See
// decisions/0018-microphone-score-following.md and the privacy note.

import {
  FEATURE_DIM,
  chromaFromSpectrum,
  createChromaMapping,
  normalizeFeature,
  type ChromaMapping,
} from "./chroma";
import type { LiveFrames } from "./align";
import { FRAME_RATE } from "./reference";

export type CaptureOptions = {
  frameRate: number;
  // Bin width is sampleRate/fftSize. At 48 kHz, 16384 gives ~2.9 Hz,
  // which resolves semitones down to the guitar's low E (82 Hz, where
  // neighbouring semitones are only ~5 Hz apart). Halving this saves
  // latency and loses the bass register.
  fftSize: number;
  // Frames whose energy sits within this factor of the running noise
  // floor are marked silent. Silence carries no positional information
  // and is excluded from alignment evidence rather than matched against
  // whatever reference frame happens to be quiet.
  silenceSnr: number;
};

export const DEFAULT_CAPTURE_OPTIONS: CaptureOptions = {
  frameRate: FRAME_RATE,
  fftSize: 16384,
  silenceSnr: 2.5,
};

export type CaptureFrame = {
  index: number;
  chroma: Float32Array;
  silent: boolean;
  energy: number;
};

export type CaptureSession = {
  stop: () => LiveFrames;
  readonly frameCount: number;
  readonly sampleRate: number;
  // Frames actually produced divided by frames the wall clock expected.
  // A value well below 1 means the browser throttled our timer and the
  // take's timing is not trustworthy.
  readonly captureRatio: number;
};

export class MicrophoneUnavailableError extends Error {
  constructor(cause: unknown) {
    super(
      cause instanceof Error && cause.name === "NotAllowedError"
        ? "Microphone permission was denied."
        : "No microphone is available.",
    );
    this.name = "MicrophoneUnavailableError";
  }
}

// Growable frame buffer. A take's length is not known in advance and
// reallocating per frame at 20 Hz would churn; doubling keeps it to
// log(n) copies.
class FrameBuffer {
  private data = new Float32Array(FEATURE_DIM * 1024);
  private silentFlags = new Uint8Array(1024);
  count = 0;

  push(chroma: Float32Array, silent: boolean): void {
    if ((this.count + 1) * FEATURE_DIM > this.data.length) {
      const grown = new Float32Array(this.data.length * 2);
      grown.set(this.data);
      this.data = grown;
      const grownFlags = new Uint8Array(this.silentFlags.length * 2);
      grownFlags.set(this.silentFlags);
      this.silentFlags = grownFlags;
    }
    this.data.set(chroma, this.count * FEATURE_DIM);
    this.silentFlags[this.count] = silent ? 1 : 0;
    this.count++;
  }

  finish(frameRate: number): LiveFrames {
    return {
      frames: this.data.slice(0, this.count * FEATURE_DIM),
      frameCount: this.count,
      silent: this.silentFlags.slice(0, this.count),
      frameRate,
    };
  }
}

// Minimum-statistics noise floor. Tracks the quietest energy seen and
// lets it drift upward slowly, so the gate adapts to a noisy room
// without a calibration step and without latching onto one quiet frame
// for the whole take.
class NoiseFloor {
  private floor = Infinity;
  private static readonly RISE = 1.0008;
  // Absolute backstop for a genuinely silent input, so a digital-silence
  // stream does not drive the floor to zero and mark noise as signal.
  private static readonly ABSOLUTE = 1e-4;

  update(energy: number): number {
    if (!Number.isFinite(energy)) return this.threshold();
    this.floor = this.floor === Infinity ? energy : Math.min(this.floor * NoiseFloor.RISE, energy);
    return this.threshold();
  }

  threshold(): number {
    return Math.max(NoiseFloor.ABSOLUTE, this.floor === Infinity ? 0 : this.floor);
  }
}

export async function startCapture(
  onFrame?: (frame: CaptureFrame) => void,
  options: Partial<CaptureOptions> = {},
): Promise<CaptureSession> {
  const opts = { ...DEFAULT_CAPTURE_OPTIONS, ...options };

  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      // Every one of these is a speech-optimized processor that mangles
      // musical signal: echo cancellation notches out sustained tones,
      // noise suppression treats a quiet passage as background, and
      // auto gain destroys the dynamics we measure tempo from.
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      },
    });
  } catch (e) {
    throw new MicrophoneUnavailableError(e);
  }

  const context = new AudioContext();
  const source = context.createMediaStreamSource(stream);
  const analyser = context.createAnalyser();
  analyser.fftSize = opts.fftSize;
  // Smoothing averages successive spectra, which blurs exactly the
  // onsets the aligner uses to place the player in time.
  analyser.smoothingTimeConstant = 0;
  source.connect(analyser);

  const mapping: ChromaMapping = createChromaMapping(context.sampleRate, opts.fftSize);
  const spectrum = new Float32Array(analyser.frequencyBinCount);
  const scratch = new Float32Array(FEATURE_DIM);
  const buffer = new FrameBuffer();
  const noiseFloor = new NoiseFloor();

  const startedAt = performance.now();
  let stopped = false;

  const timer = setInterval(() => {
    if (stopped) return;
    analyser.getFloatFrequencyData(spectrum);
    const { chroma, energy } = chromaFromSpectrum(spectrum, mapping, scratch);
    const threshold = noiseFloor.update(energy);
    const silent = energy < threshold * opts.silenceSnr;
    normalizeFeature(chroma);
    buffer.push(chroma, silent);
    onFrame?.({ index: buffer.count - 1, chroma, silent, energy });
  }, 1000 / opts.frameRate);

  return {
    get frameCount() {
      return buffer.count;
    },
    sampleRate: context.sampleRate,
    get captureRatio() {
      const expected = ((performance.now() - startedAt) / 1000) * opts.frameRate;
      return expected > 0 ? buffer.count / expected : 1;
    },
    stop: () => {
      stopped = true;
      clearInterval(timer);
      source.disconnect();
      for (const track of stream.getTracks()) track.stop();
      void context.close();
      return buffer.finish(opts.frameRate);
    },
  };
}
