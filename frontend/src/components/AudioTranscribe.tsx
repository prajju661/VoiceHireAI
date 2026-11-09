import { useState, type ChangeEvent, type FormEvent } from 'react';
import { transcribeAudio, type TranscribeResponse } from '../services/api';

const SUPPORTED_LANGUAGES = [
  { code: 'en-IN', name: 'English (India)' },
  { code: 'te-IN', name: 'Telugu' },
  { code: 'hi-IN', name: 'Hindi' },
  { code: 'ta-IN', name: 'Tamil' },
  { code: 'kn-IN', name: 'Kannada' },
];

export function AudioTranscribe() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [languageCode, setLanguageCode] = useState<string>('en-IN');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<TranscribeResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setErrorMessage(null);
    setResult(null);
    setCopied(false);

    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
    } else {
      setSelectedFile(null);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!selectedFile) {
      setErrorMessage('Please select an audio file to transcribe.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setResult(null);
    setCopied(false);

    try {
      const response = await transcribeAudio(selectedFile, languageCode);
      setResult(response);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected error occurred during transcription.');
      }
    } finally {
      setIsLoading(false);
    }
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
      <div className="transcribe-header">
        <div className="transcribe-title-row">
          <div className="transcribe-icon-box" aria-hidden="true">
            🎧
          </div>
          <div>
            <h3 className="transcribe-title">Speech-to-Text Transcription</h3>
            <p className="transcribe-subtitle">
              Powered by Gnani Prisma &bull; Supports WAV, MP3, OGG, FLAC, AAC, M4A
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="transcribe-form">
        <div className="form-grid">
          {/* File Picker */}
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

          {/* Language Selector */}
          <div className="form-group">
            <label htmlFor="language-select" className="form-label">
              Language
            </label>
            <select
              id="language-select"
              value={languageCode}
              onChange={(e) => setLanguageCode(e.target.value)}
              disabled={isLoading}
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

        {/* Action Button */}
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
              <span>Transcribe Audio</span>
            )}
          </button>
        </div>
      </form>

      {/* Error Message */}
      {errorMessage && (
        <div className="transcribe-error-box" role="alert">
          <div className="error-icon" aria-hidden="true">
            ⚠️
          </div>
          <div>
            <p className="error-heading">Transcription Failed</p>
            <p className="error-text">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Result Display */}
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
