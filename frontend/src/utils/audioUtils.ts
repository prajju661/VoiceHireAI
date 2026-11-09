/**
 * Audio processing and WAV encoding utilities for VoiceHire AI.
 * Captures raw Web Audio buffers, resamples them to 16 kHz mono,
 * and serializes them into valid 16-bit PCM WAV binary format.
 */

/**
 * Checks whether the browser environment supports required Web Audio and media APIs.
 */
export function isAudioRecordingSupported(): boolean {
  if (typeof window === 'undefined') return false;

  const hasMediaDevices =
    !!navigator &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === 'function';

  const hasAudioContext =
    typeof window.AudioContext !== 'undefined' ||
    typeof (window as unknown as { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext !== 'undefined';

  return hasMediaDevices && hasAudioContext;
}

/**
 * Merges an array of Float32Array audio chunks into a single Float32Array.
 */
export function mergeAudioChunks(chunks: Float32Array[]): Float32Array {
  let totalLength = 0;
  for (let i = 0; i < chunks.length; i++) {
    totalLength += chunks[i].length;
  }

  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (let i = 0; i < chunks.length; i++) {
    merged.set(chunks[i], offset);
    offset += chunks[i].length;
  }

  return merged;
}

/**
 * Resamples a Float32Array audio buffer from sourceSampleRate to targetSampleRate
 * using linear interpolation.
 *
 * @param audioData Input audio sample buffer
 * @param sourceSampleRate Input sample rate (e.g., 44100 or 48000 Hz)
 * @param targetSampleRate Desired sample rate (defaults to 16000 Hz for speech recognition)
 */
export function resampleAudioBuffer(
  audioData: Float32Array,
  sourceSampleRate: number,
  targetSampleRate: number = 16000
): Float32Array {
  if (
    audioData.length === 0 ||
    sourceSampleRate <= 0 ||
    targetSampleRate <= 0 ||
    sourceSampleRate === targetSampleRate
  ) {
    return audioData;
  }

  const ratio = sourceSampleRate / targetSampleRate;
  const newLength = Math.round(audioData.length / ratio);
  const result = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const originalPos = i * ratio;
    const index = Math.floor(originalPos);
    const fraction = originalPos - index;
    const nextIndex = Math.min(index + 1, audioData.length - 1);

    result[i] =
      audioData[index] * (1 - fraction) + audioData[nextIndex] * fraction;
  }

  return result;
}

/**
 * Encodes Float32Array audio samples into a standard 16-bit PCM RIFF WAV Blob.
 *
 * @param samples Audio samples with values normalized to [-1.0, 1.0]
 * @param sampleRate Output sample rate in Hz (default: 16000)
 * @returns Blob containing standard mono 16-bit PCM WAV audio
 */
export function encodeWAV(
  samples: Float32Array,
  sampleRate: number = 16000
): Blob {
  const numChannels = 1;
  const bitsPerSample = 16;
  const bytesPerSample = bitsPerSample / 8;
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = samples.length * bytesPerSample;
  const headerSize = 44;
  const totalSize = headerSize + dataSize;

  const buffer = new ArrayBuffer(totalSize);
  const view = new DataView(buffer);

  // Helper to write ASCII strings into DataView
  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  // 1. RIFF Chunk Descriptor
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true); // ChunkSize = 36 + SubChunk2Size
  writeString(8, 'WAVE');

  // 2. "fmt " Sub-chunk
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size = 16 for PCM
  view.setUint16(20, 1, true); // AudioFormat = 1 (Linear PCM, uncompressed)
  view.setUint16(22, numChannels, true); // NumChannels = 1 (Mono)
  view.setUint32(24, sampleRate, true); // SampleRate (16000)
  view.setUint32(28, byteRate, true); // ByteRate = SampleRate * BlockAlign
  view.setUint16(32, blockAlign, true); // BlockAlign = NumChannels * BytesPerSample
  view.setUint16(34, bitsPerSample, true); // BitsPerSample = 16

  // 3. "data" Sub-chunk
  writeString(36, 'data');
  view.setUint32(40, dataSize, true); // Subchunk2Size = NumSamples * NumChannels * BytesPerSample

  // 4. Write PCM 16-bit audio samples (little-endian)
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    // Clamp sample to range [-1.0, 1.0] to prevent integer overflow/wrap-around
    const s = Math.max(-1, Math.min(1, samples[i]));
    const int16 = s < 0 ? Math.round(s * 0x8000) : Math.round(s * 0x7fff);
    view.setInt16(offset, int16, true);
    offset += 2;
  }

  return new Blob([view], { type: 'audio/wav' });
}

/**
 * Formats elapsed duration in seconds into MM:SS string representation.
 */
export function formatDuration(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(safeSeconds / 60);
  const secs = safeSeconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}
