import { useState, type ChangeEvent, type FormEvent } from 'react';
import { transcribeAudio, type TranscribeResponse } from '../services/api';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { formatDuration } from '../utils/audioUtils';

const SUPPORTED_LANGUAGES = [
  { code: 'en-IN', name: 'English (India)' },
  { code: 'te-IN', name: 'Telugu' },
  { code: 'hi-IN', name: 'Hindi' },
  { code: 'ta-IN', name: 'Tamil' },
  { code: 'kn-IN', name: 'Kannada' },
];

type InputMode = 'record' | 'upload';

export function AudioTranscribe() {
  const [mode, setMode] = useState<InputMode>('record');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [languageCode, setLanguageCode] = useState<string>('en-IN');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<TranscribeResponse | null>(null);
  const [apiErrorMessage, setApiErrorMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // Hook for live microphone recording via Web Audio API
  const {
    isRecording,
    recordingDuration,
    recordedFile,
    audioUrl,
    error: recorderError,
    isSupported,
    startRecording,
    stopRecording,
    clearRecording,
    clearError: clearRecorderError,
  } = useAudioRecorder();

  // Mode switching guard: Cannot change modes while recording or transcribing
  const handleModeChange = (newMode: InputMode) => {
    if (isRecording || isLoading) return;
    setMode(newMode);
    setApiErrorMessage(null);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setApiErrorMessage(null);
    setResult(null);
    setCopied(false);

    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    } else {
      setSelectedFile(null);
    }
  };

  /**
   * Common transcription submission handler for both recorded WAV files and uploaded audio.
   */
  const executeTranscription = async (fileToTranscribe: File) => {
    setIsLoading(true);
    setApiErrorMessage(null);
    clearRecorderError();
    setResult(null);
    setCopied(false);

    try {
      const response = await transcribeAudio(fileToTranscribe, languageCode);
      setResult(response);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setApiErrorMessage(err.message);
      } else {
        setApiErrorMessage('An unexpected error occurred during transcription.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Submit handler for file upload form
  const handleUploadSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setApiErrorMessage('Please select an audio file to transcribe.');
      return;
    }
    await executeTranscription(selectedFile);
  };

  // Submit handler for recorded audio
  const handleRecordSubmit = async () => {
    if (!recordedFile) {
      setApiErrorMessage('Please record audio before submitting.');
      return;
    }
    await executeTranscription(recordedFile);
  };

  const handleCopy = () => {
    if (result?.transcript) {
      navigator.clipboard.writeText(result.transcript);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="transcribe-card">
      {/* Header */}
      <div className="transcribe-header">
        <div className="transcribe-title-row">
          <div className="transcribe-icon-box" aria-hidden="true">
            🎙️
          </div>
          <div>
            <h3 className="transcribe-title">Speech-to-Text Transcription</h3>
            <p className="transcribe-subtitle">
              Live microphone recording &bull; Gnani Prisma STT &bull; Mono 16 kHz WAV
            </p>
          </div>
        </div>
      </div>

      {/* Input Mode Navigation Tabs */}
      <div className="tab-navigation" role="tablist" aria-label="Input Mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'record'}
          className={`tab-btn ${mode === 'record' ? 'tab-btn-active' : ''}`}
          onClick={() => handleModeChange('record')}
          disabled={isRecording || isLoading}
        >
          <span className="tab-icon" aria-hidden="true">
            🔴
          </span>
          <span>Live Recording</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={mode === 'upload'}
          className={`tab-btn ${mode === 'upload' ? 'tab-btn-active' : ''}`}
          onClick={() => handleModeChange('upload')}
          disabled={isRecording || isLoading}
        >
          <span className="tab-icon" aria-hidden="true">
            📁
          </span>
          <span>Upload Audio File</span>
        </button>
      </div>

      {/* Mode 1: Live Microphone Recording */}
      {mode === 'record' && (
        <div className="recorder-panel">
          {/* Unsupported Browser Warning */}
          {!isSupported && (
            <div className="alert-box alert-warning" role="alert">
              <span className="alert-icon" aria-hidden="true">
                ⚠️
              </span>
              <div>
                <p className="alert-title">Microphone Recording Not Supported</p>
                <p className="alert-text">
                  Your browser does not support the required Web Audio APIs. Please switch to the{' '}
                  <strong>Upload Audio File</strong> tab or use a modern desktop browser.
                </p>
              </div>
            </div>
          )}

          {/* Permission Denied Alert */}
          {recorderError?.type === 'permission_denied' && (
            <div className="alert-box alert-danger" role="alert">
              <span className="alert-icon" aria-hidden="true">
                🚫
              </span>
              <div>
                <p className="alert-title">Microphone Permission Denied</p>
                <p className="alert-text">{recorderError.message}</p>
                <p className="alert-hint">
                  Tip: Click the camera/microphone icon in your browser address bar to grant access, then try again.
                </p>
              </div>
            </div>
          )}

          {/* Generic Recorder Error Alert */}
          {recorderError && recorderError.type !== 'permission_denied' && (
            <div className="alert-box alert-danger" role="alert">
              <span className="alert-icon" aria-hidden="true">
                ⚠️
              </span>
              <div>
                <p className="alert-title">Recording Error</p>
                <p className="alert-text">{recorderError.message}</p>
              </div>
            </div>
          )}

          {/* Recording Controls & Visual Feedback */}
          <div className="recorder-controls-area">
            {!isRecording && !recordedFile && (
              <div className="record-init-state">
                <button
                  type="button"
                  className="btn-record-start"
                  onClick={startRecording}
                  disabled={!isSupported || isLoading}
                >
                  <span className="record-circle-icon" aria-hidden="true" />
                  <span>Start Recording</span>
                </button>
                <p className="record-hint-text">
                  Click to start. Your browser will prompt for microphone permission.
                </p>
              </div>
            )}

            {/* Active Recording State */}
            {isRecording && (
              <div className="record-active-state">
                <div className="recording-status-badge">
                  <span className="record-pulse-dot" aria-hidden="true" />
                  <span className="recording-status-text">Recording Live Audio...</span>
                  <span className="recording-timer">{formatDuration(recordingDuration)}</span>
                </div>

                <div className="audio-wave-animation" aria-hidden="true">
                  <span className="wave-bar bar-1" />
                  <span className="wave-bar bar-2" />
                  <span className="wave-bar bar-3" />
                  <span className="wave-bar bar-4" />
                  <span className="wave-bar bar-5" />
                </div>

                <button
                  type="button"
                  className="btn-record-stop"
                  onClick={stopRecording}
                >
                  <span className="stop-square-icon" aria-hidden="true" />
                  <span>Stop Recording</span>
                </button>
              </div>
            )}

            {/* Post-Recording Preview and Review */}
            {!isRecording && recordedFile && audioUrl && (
              <div className="record-preview-state">
                <div className="preview-header">
                  <span className="preview-label">Recorded Audio Review:</span>
                  <span className="preview-meta">
                    Duration: <strong>{formatDuration(recordingDuration)}</strong> &bull; Size:{' '}
                    <strong>{formatFileSize(recordedFile.size)}</strong> (16 kHz WAV)
                  </span>
                </div>

                <div className="audio-player-wrapper">
                  <audio
                    controls
                    src={audioUrl}
                    className="audio-player"
                    preload="metadata"
                  >
                    Your browser does not support audio playback.
                  </audio>
                </div>

                <div className="preview-action-row">
                  <button
                    type="button"
                    className="btn-record-discard"
                    onClick={clearRecording}
                    disabled={isLoading}
                    title="Discard recording and record again"
                  >
                    🔄 Discard &amp; Record Again
                  </button>

                  <button
                    type="button"
                    className="btn-transcribe"
                    onClick={handleRecordSubmit}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <span className="spinner-small" aria-hidden="true" />
                        <span>Transcribing Recording...</span>
                      </>
                    ) : (
                      <span>Transcribe Recording</span>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Mode 2: File Upload (Preserved functionality) */}
      {mode === 'upload' && (
        <form onSubmit={handleUploadSubmit} className="upload-panel">
          <div className="form-group">
            <label htmlFor="audio-file" className="form-label">
              Select Audio File
            </label>
            <input
              id="audio-file"
              type="file"
              accept=".wav,.mp3,.ogg,.flac,.aac,.m4a,audio/*"
              onChange={handleFileChange}
              disabled={isLoading}
              className="file-input"
            />
            {selectedFile && (
              <p className="file-info">
                Selected: <strong>{selectedFile.name}</strong> (
                {formatFileSize(selectedFile.size)})
              </p>
            )}
          </div>

          <div className="transcribe-actions">
            <button
              type="submit"
              disabled={!selectedFile || isLoading}
              className="btn-transcribe"
            >
              {isLoading ? (
                <>
                  <span className="spinner-small" aria-hidden="true" />
                  <span>Transcribing with Prisma...</span>
                </>
              ) : (
                <span>Transcribe Audio File</span>
              )}
            </button>
          </div>
        </form>
      )}

      {/* Shared Language Selector (reused for both modes) */}
      <div className="shared-settings-row">
        <div className="form-group language-select-group">
          <label htmlFor="language-select" className="form-label">
            Target Language for STT
          </label>
          <select
            id="language-select"
            value={languageCode}
            onChange={(e) => setLanguageCode(e.target.value)}
            disabled={isLoading || isRecording}
            className="select-input"
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} ({lang.code})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* API / Backend Error Message */}
      {apiErrorMessage && (
        <div className="transcribe-error-box" role="alert">
          <div className="error-icon" aria-hidden="true">
            ⚠️
          </div>
          <div>
            <p className="error-heading">Transcription Failed</p>
            <p className="error-text">{apiErrorMessage}</p>
          </div>
        </div>
      )}

      {/* Result Display (reused for both modes) */}
      {result && (
        <div className="transcribe-result-box">
          <div className="result-header">
            <div className="result-tags">
              <span className="tag-badge tag-provider">
                Provider: {result.provider}
              </span>
              <span className="tag-badge tag-lang">
                Language: {result.language_code}
              </span>
              <span className="tag-badge tag-status">Success</span>
            </div>
            <button
              type="button"
              onClick={handleCopy}
              className="btn-copy"
              title="Copy transcript to clipboard"
            >
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>

          <div className="result-content">
            <p className="transcript-label">Transcript:</p>
            <blockquote className="transcript-text">
              {result.transcript || (
                <em className="text-muted">(Empty transcript returned)</em>
              )}
            </blockquote>
          </div>
        </div>
      )}
    </div>
  );
}
