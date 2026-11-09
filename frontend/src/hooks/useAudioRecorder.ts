import { useState, useRef, useEffect, useCallback } from 'react';
import {
  isAudioRecordingSupported,
  mergeAudioChunks,
  resampleAudioBuffer,
  encodeWAV,
} from '../utils/audioUtils';

export type RecorderErrorType =
  | 'unsupported'
  | 'permission_denied'
  | 'device_not_found'
  | 'recording_error';

export interface RecorderError {
  type: RecorderErrorType;
  message: string;
}

export interface UseAudioRecorderReturn {
  isRecording: boolean;
  recordingDuration: number;
  recordedFile: File | null;
  audioUrl: string | null;
  error: RecorderError | null;
  isSupported: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  clearRecording: () => void;
  clearError: () => void;
}

/**
 * Custom hook providing live microphone audio recording via Web Audio APIs.
 * Automatically handles resampling to 16 kHz mono, PCM 16-bit WAV encoding,
 * duration tracking, browser permissions, error states, and unmount resource cleanup.
 */
export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingDuration, setRecordingDuration] = useState<number>(0);
  const [recordedFile, setRecordedFile] = useState<File | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<RecorderError | null>(null);

  // References to Web Audio resources
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const muteGainNodeRef = useRef<GainNode | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const timerIntervalRef = useRef<number | null>(null);
  const currentAudioUrlRef = useRef<string | null>(null);

  // Keep currentAudioUrlRef synced for unmount cleanup
  useEffect(() => {
    currentAudioUrlRef.current = audioUrl;
  }, [audioUrl]);

  const isSupported = isAudioRecordingSupported();

  /**
   * Internal helper to stop all audio tracks, disconnect nodes, and close AudioContext.
   */
  const cleanupAudioPipeline = useCallback(() => {
    // 1. Stop timer interval
    if (timerIntervalRef.current !== null) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }

    // 2. Stop all microphone tracks immediately
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // Ignore errors on track stop
        }
      });
      mediaStreamRef.current = null;
    }

    // 3. Disconnect audio processor
    if (processorNodeRef.current) {
      try {
        processorNodeRef.current.onaudioprocess = null;
        processorNodeRef.current.disconnect();
      } catch {
        // Ignore disconnect errors
      }
      processorNodeRef.current = null;
    }

    // 4. Disconnect source node
    if (sourceNodeRef.current) {
      try {
        sourceNodeRef.current.disconnect();
      } catch {
        // Ignore disconnect errors
      }
      sourceNodeRef.current = null;
    }

    // 5. Disconnect mute node
    if (muteGainNodeRef.current) {
      try {
        muteGainNodeRef.current.disconnect();
      } catch {
        // Ignore disconnect errors
      }
      muteGainNodeRef.current = null;
    }

    // 6. Close AudioContext
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        audioContextRef.current.close().catch(() => {});
      } catch {
        // Ignore context close errors
      }
      audioContextRef.current = null;
    }
  }, []);

  /**
   * Cleans up all audio resources and revokes previous audio URLs on component unmount.
   */
  useEffect(() => {
    return () => {
      cleanupAudioPipeline();
      if (currentAudioUrlRef.current) {
        URL.revokeObjectURL(currentAudioUrlRef.current);
        currentAudioUrlRef.current = null;
      }
    };
  }, [cleanupAudioPipeline]);

  /**
   * Starts live microphone recording.
   * Prompts for permission only when triggered by user interaction.
   */
  const startRecording = useCallback(async () => {
    // Guard: Check browser support
    if (!isAudioRecordingSupported()) {
      setError({
        type: 'unsupported',
        message:
          'Your browser does not support Web Audio microphone recording. Please use modern Chrome, Edge, Firefox, or Safari.',
      });
      return;
    }

    // Clean up any existing recording session and previous audio preview URL
    cleanupAudioPipeline();
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setRecordedFile(null);
    setError(null);
    setRecordingDuration(0);
    audioChunksRef.current = [];

    try {
      // 1. Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      mediaStreamRef.current = stream;

      // 2. Initialize AudioContext
      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext;

      if (!AudioContextClass) {
        throw new Error('AudioContext not supported by browser.');
      }

      const audioCtx = new AudioContextClass();
      if (audioCtx.state === 'suspended') {
        await audioCtx.resume();
      }
      audioContextRef.current = audioCtx;

      // 3. Create audio processing nodes
      const source = audioCtx.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      // ScriptProcessor bufferSize: 4096 (standard latency/performance tradeoff)
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorNodeRef.current = processor;

      processor.onaudioprocess = (event: AudioProcessingEvent) => {
        const inputData = event.inputBuffer.getChannelData(0);
        // Clone the input Float32Array because the underlying buffer is reused by Web Audio
        audioChunksRef.current.push(new Float32Array(inputData));
      };

      // Mute gain node avoids feedback loop while keeping processor active in Chrome/WebKit
      const muteGain = audioCtx.createGain();
      muteGain.gain.value = 0;
      muteGainNodeRef.current = muteGain;

      source.connect(processor);
      processor.connect(muteGain);
      muteGain.connect(audioCtx.destination);

      // 4. Start duration timer
      setIsRecording(true);
      const startTime = Date.now();
      timerIntervalRef.current = window.setInterval(() => {
        setRecordingDuration(Math.floor((Date.now() - startTime) / 1000));
      }, 500);
    } catch (err: unknown) {
      cleanupAudioPipeline();
      setIsRecording(false);

      if (err instanceof DOMException || (err && typeof err === 'object' && 'name' in err)) {
        const domErr = err as { name: string; message: string };
        if (
          domErr.name === 'NotAllowedError' ||
          domErr.name === 'PermissionDeniedError'
        ) {
          setError({
            type: 'permission_denied',
            message:
              'Microphone access was denied. Please allow microphone permissions in your browser address bar and try again.',
          });
          return;
        }

        if (
          domErr.name === 'NotFoundError' ||
          domErr.name === 'DevicesNotFoundError'
        ) {
          setError({
            type: 'device_not_found',
            message:
              'No microphone found. Please connect an audio input device and try again.',
          });
          return;
        }

        if (domErr.name === 'NotReadableError' || domErr.name === 'TrackStartError') {
          setError({
            type: 'recording_error',
            message:
              'Microphone is currently unavailable or used by another application.',
          });
          return;
        }
      }

      setError({
        type: 'recording_error',
        message:
          err instanceof Error
            ? err.message
            : 'An unexpected error occurred while starting microphone recording.',
      });
    }
  }, [cleanupAudioPipeline, audioUrl]);

  /**
   * Stops live recording, encodes collected audio to 16 kHz PCM WAV,
   * creates the audio playback preview, and releases audio resources.
   */
  const stopRecording = useCallback(() => {
    if (!isRecording) return;

    // Capture context sample rate before closing
    const sampleRate = audioContextRef.current
      ? audioContextRef.current.sampleRate
      : 44100;

    // Release microphone tracks and nodes
    cleanupAudioPipeline();
    setIsRecording(false);

    // Process recorded audio chunks
    const chunks = audioChunksRef.current;
    audioChunksRef.current = [];

    const merged = mergeAudioChunks(chunks);
    if (merged.length === 0) {
      setError({
        type: 'recording_error',
        message: 'No audio samples were recorded. Please try speaking into your microphone again.',
      });
      return;
    }

    // Resample to 16,000 Hz if necessary
    const resampled = resampleAudioBuffer(merged, sampleRate, 16000);

    // Encode to standard 16-bit PCM WAV
    const wavBlob = encodeWAV(resampled, 16000);
    const wavFile = new File(
      [wavBlob],
      `voicehire-recording-${Date.now()}.wav`,
      { type: 'audio/wav' }
    );

    const url = URL.createObjectURL(wavBlob);
    setRecordedFile(wavFile);
    setAudioUrl(url);
  }, [isRecording, cleanupAudioPipeline]);

  /**
   * Discards the current recorded audio and revokes the preview URL.
   */
  const clearRecording = useCallback(() => {
    cleanupAudioPipeline();
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setRecordedFile(null);
    setRecordingDuration(0);
    setIsRecording(false);
  }, [audioUrl, cleanupAudioPipeline]);

  /**
   * Clears any active error message.
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isRecording,
    recordingDuration,
    recordedFile,
    audioUrl,
    error,
    isSupported,
    startRecording,
    stopRecording,
    clearRecording,
    clearError,
  };
}
