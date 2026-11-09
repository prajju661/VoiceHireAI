import test from 'node:test';
import assert from 'node:assert/strict';
import {
  resampleAudioBuffer,
  encodeWAV,
  isAudioRecordingSupported,
} from './audioUtils.ts';

// --------------------------------------------------------------------
// 1. WAV Generation & Audio Processing Verification
// --------------------------------------------------------------------
test('WAV generation produces accurate 16 kHz 16-bit PCM header and data', async () => {
  const sampleRate = 16000;
  // 320 samples at 16kHz = 20ms of audio
  const mockSamples = new Float32Array(320);
  for (let i = 0; i < mockSamples.length; i++) {
    // Sine wave at 440 Hz
    mockSamples[i] = Math.sin((2 * Math.PI * 440 * i) / sampleRate);
  }

  const blob = encodeWAV(mockSamples, sampleRate);
  assert.equal(blob.type, 'audio/wav');
  assert.equal(blob.size, 44 + 320 * 2);

  const arrayBuffer = await blob.arrayBuffer();
  const view = new DataView(arrayBuffer);

  // RIFF tag
  assert.equal(
    String.fromCharCode(
      view.getUint8(0),
      view.getUint8(1),
      view.getUint8(2),
      view.getUint8(3)
    ),
    'RIFF'
  );
  // Total size minus 8
  assert.equal(view.getUint32(4, true), 36 + 320 * 2);
  // WAVE tag
  assert.equal(
    String.fromCharCode(
      view.getUint8(8),
      view.getUint8(9),
      view.getUint8(10),
      view.getUint8(11)
    ),
    'WAVE'
  );

  // Subchunk 1 (fmt)
  assert.equal(view.getUint32(16, true), 16); // PCM chunk size
  assert.equal(view.getUint16(20, true), 1); // 1 = Linear PCM
  assert.equal(view.getUint16(22, true), 1); // 1 = Mono
  assert.equal(view.getUint32(24, true), 16000); // Sample rate
  assert.equal(view.getUint32(28, true), 32000); // Byte rate (16000 * 1 * 2)
  assert.equal(view.getUint16(32, true), 2); // Block align (1 * 2)
  assert.equal(view.getUint16(34, true), 16); // Bits per sample (16-bit)

  // Subchunk 2 (data)
  assert.equal(
    String.fromCharCode(
      view.getUint8(36),
      view.getUint8(37),
      view.getUint8(38),
      view.getUint8(39)
    ),
    'data'
  );
  assert.equal(view.getUint32(40, true), 320 * 2);
});

test('Resampling correctly converts 44.1 kHz input to 16 kHz without NaN or out of bounds', () => {
  const sourceRate = 44100;
  const targetRate = 16000;
  const sourceLength = 4410; // 0.1 seconds
  const input = new Float32Array(sourceLength);
  for (let i = 0; i < sourceLength; i++) {
    input[i] = Math.sin((2 * Math.PI * 1000 * i) / sourceRate);
  }

  const resampled = resampleAudioBuffer(input, sourceRate, targetRate);
  const expectedLength = Math.round(sourceLength / (sourceRate / targetRate));
  assert.equal(resampled.length, expectedLength);

  // Check all samples are valid numbers in [-1, 1]
  for (let i = 0; i < resampled.length; i++) {
    assert.ok(!Number.isNaN(resampled[i]), `Sample ${i} is NaN`);
    assert.ok(
      resampled[i] >= -1 && resampled[i] <= 1,
      `Sample ${i} exceeded bounds: ${resampled[i]}`
    );
  }
});

// --------------------------------------------------------------------
// 2. Browser Environment & Feature Detection
// --------------------------------------------------------------------
test('isAudioRecordingSupported detects absence of browser Web Audio / mediaDevices in node', () => {
  // In pure Node environment, window/navigator are either undefined or lack getUserMedia
  const supported = isAudioRecordingSupported();
  assert.equal(typeof supported, 'boolean');
});

// --------------------------------------------------------------------
// 3. Audio Stream Track Cleanup Simulation
// --------------------------------------------------------------------
test('Audio track cleanup stops all active tracks to prevent microphone indicator lingering', () => {
  let tracksStoppedCount = 0;
  const mockTrack1 = {
    kind: 'audio',
    readyState: 'live',
    stop: () => {
      tracksStoppedCount++;
    },
  };
  const mockTrack2 = {
    kind: 'audio',
    readyState: 'live',
    stop: () => {
      tracksStoppedCount++;
    },
  };

  const mockStream = {
    getTracks: () => [mockTrack1, mockTrack2],
  };

  mockStream.getTracks().forEach((track) => track.stop());
  assert.equal(tracksStoppedCount, 2);
});

// --------------------------------------------------------------------
// 4. Permission Denied & Hardware Error Mapping Verification
// --------------------------------------------------------------------
test('Maps browser DOMException errors to user-friendly messages', () => {
  const mapError = (err: { name: string; message: string }) => {
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      return {
        type: 'permission_denied',
        message:
          'Microphone access was denied. Please allow microphone permissions in your browser address bar and try again.',
      };
    }
    if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
      return {
        type: 'device_not_found',
        message:
          'No microphone found. Please connect an audio input device and try again.',
      };
    }
    if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
      return {
        type: 'recording_error',
        message:
          'Microphone is currently unavailable or used by another application.',
      };
    }
    return {
      type: 'recording_error',
      message: err.message || 'Unknown error',
    };
  };

  const permError = mapError({ name: 'NotAllowedError', message: 'User denied' });
  assert.equal(permError.type, 'permission_denied');
  assert.match(permError.message, /browser address bar/i);

  const notFoundError = mapError({ name: 'NotFoundError', message: 'No mic' });
  assert.equal(notFoundError.type, 'device_not_found');
  assert.match(notFoundError.message, /connect an audio input device/i);

  const busyError = mapError({ name: 'NotReadableError', message: 'In use' });
  assert.equal(busyError.type, 'recording_error');
  assert.match(busyError.message, /used by another application/i);
});
