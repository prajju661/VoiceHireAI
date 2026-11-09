import test from 'node:test';
import assert from 'node:assert/strict';
import {
  mergeAudioChunks,
  resampleAudioBuffer,
  encodeWAV,
  formatDuration,
} from './audioUtils.ts';

test('formatDuration formats seconds properly', () => {
  assert.equal(formatDuration(0), '00:00');
  assert.equal(formatDuration(5), '00:05');
  assert.equal(formatDuration(59), '00:59');
  assert.equal(formatDuration(60), '01:00');
  assert.equal(formatDuration(75), '01:15');
  assert.equal(formatDuration(3605), '60:05');
  assert.equal(formatDuration(-10), '00:00');
});

test('mergeAudioChunks merges multiple Float32Array chunks', () => {
  const c1 = new Float32Array([0.1, 0.2]);
  const c2 = new Float32Array([0.3, 0.4, 0.5]);
  const merged = mergeAudioChunks([c1, c2]);

  assert.equal(merged.length, 5);
  assert.equal(Math.round(merged[0] * 10) / 10, 0.1);
  assert.equal(Math.round(merged[1] * 10) / 10, 0.2);
  assert.equal(Math.round(merged[2] * 10) / 10, 0.3);
  assert.equal(Math.round(merged[3] * 10) / 10, 0.4);
  assert.equal(Math.round(merged[4] * 10) / 10, 0.5);
});

test('mergeAudioChunks handles empty chunk lists', () => {
  const merged = mergeAudioChunks([]);
  assert.equal(merged.length, 0);
});

test('resampleAudioBuffer preserves identical sample rates', () => {
  const input = new Float32Array([0.1, -0.2, 0.5]);
  const output = resampleAudioBuffer(input, 16000, 16000);
  assert.equal(output.length, 3);
  assert.equal(output[0], input[0]);
  assert.equal(output[1], input[1]);
  assert.equal(output[2], input[2]);
});

test('resampleAudioBuffer downsamples 48000 Hz to 16000 Hz by factor of 3', () => {
  // 48000 -> 16000 is exactly a 3:1 ratio
  const input = new Float32Array(300);
  for (let i = 0; i < input.length; i++) {
    input[i] = Math.sin((i / 48000) * 2 * Math.PI * 440);
  }

  const output = resampleAudioBuffer(input, 48000, 16000);
  assert.equal(output.length, 100);
  assert.equal(output[0], input[0]);
});

test('resampleAudioBuffer handles empty buffers and invalid rates safely', () => {
  assert.equal(resampleAudioBuffer(new Float32Array(0), 48000, 16000).length, 0);
  const input = new Float32Array([1, 2]);
  assert.equal(resampleAudioBuffer(input, 0, 16000), input);
  assert.equal(resampleAudioBuffer(input, 48000, -1), input);
});

test('encodeWAV generates a valid mono 16-bit PCM WAV binary structure', async () => {
  const sampleRate = 16000;
  // 160 samples = 10 milliseconds of audio
  const samples = new Float32Array(160);
  for (let i = 0; i < samples.length; i++) {
    samples[i] = (i % 2 === 0 ? 0.5 : -0.5);
  }

  const wavBlob = encodeWAV(samples, sampleRate);
  assert.equal(wavBlob.type, 'audio/wav');

  // Verify byte length: 44 bytes header + (160 * 2) bytes PCM data = 364 bytes
  const arrayBuffer = await wavBlob.arrayBuffer();
  assert.equal(arrayBuffer.byteLength, 44 + 160 * 2);

  const view = new DataView(arrayBuffer);

  // Read ASCII helper
  const readString = (offset: number, length: number) => {
    let str = '';
    for (let i = 0; i < length; i++) {
      str += String.fromCharCode(view.getUint8(offset + i));
    }
    return str;
  };

  // RIFF header
  assert.equal(readString(0, 4), 'RIFF');
  assert.equal(view.getUint32(4, true), 36 + 160 * 2);
  assert.equal(readString(8, 4), 'WAVE');

  // fmt chunk
  assert.equal(readString(12, 4), 'fmt ');
  assert.equal(view.getUint32(16, true), 16); // Subchunk1Size
  assert.equal(view.getUint16(20, true), 1); // PCM AudioFormat
  assert.equal(view.getUint16(22, true), 1); // 1 Channel (Mono)
  assert.equal(view.getUint32(24, true), 16000); // 16000 Hz SampleRate
  assert.equal(view.getUint32(28, true), 32000); // ByteRate = 16000 * 2
  assert.equal(view.getUint16(32, true), 2); // BlockAlign = 2
  assert.equal(view.getUint16(34, true), 16); // BitsPerSample = 16

  // data chunk
  assert.equal(readString(36, 4), 'data');
  assert.equal(view.getUint32(40, true), 160 * 2); // DataSize

  // First sample: 0.5 * 32767 = ~16384
  const firstSample = view.getInt16(44, true);
  assert.ok(firstSample >= 16383 && firstSample <= 16384, `Expected ~16384, got ${firstSample}`);

  // Second sample: -0.5 * 32768 = -16384
  const secondSample = view.getInt16(46, true);
  assert.equal(secondSample, -16384);
});

test('encodeWAV clamps out-of-range floats without overflowing 16-bit integer', async () => {
  const samples = new Float32Array([1.5, -2.0]);
  const wavBlob = encodeWAV(samples, 16000);
  const view = new DataView(await wavBlob.arrayBuffer());

  const sample1 = view.getInt16(44, true);
  const sample2 = view.getInt16(46, true);

  // Clamped to 1.0 -> 32767
  assert.equal(sample1, 32767);
  // Clamped to -1.0 -> -32768
  assert.equal(sample2, -32768);
});
