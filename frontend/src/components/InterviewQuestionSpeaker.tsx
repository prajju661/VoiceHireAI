/**
 * InterviewQuestionSpeaker — Text-to-Speech component for VoiceHire AI.
 *
 * Uses the Gnani Timbre v3.0 backend endpoint to synthesize interview
 * questions into spoken audio. The API key is handled entirely server-side.
 */
import { useState, useEffect, useRef, type ChangeEvent } from 'react';
import {
  synthesizeSpeech,
  type TTSLanguageCode,
  type TTSVoice,
} from '../services/api';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const DEFAULT_QUESTION =
  'Tell me about yourself and your technical background.';

const TTS_LANGUAGES: { code: TTSLanguageCode; label: string }[] = [
  { code: 'en-IN', label: 'English (India)' },
  { code: 'te-IN', label: 'Telugu' },
];

const TTS_VOICES: { value: TTSVoice; label: string }[] = [
  { value: 'Riyaa', label: 'Riyaa' },
];

const MAX_TEXT_LENGTH = 800;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function InterviewQuestionSpeaker() {
  const [questionText, setQuestionText] = useState<string>(DEFAULT_QUESTION);
  const [languageCode, setLanguageCode] = useState<TTSLanguageCode>('en-IN');
  const [voice, setVoice] = useState<TTSVoice>('Riyaa');
  const [speed, setSpeed] = useState<number>(1.0);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const previousUrlRef = useRef<string | null>(null);

  // Revoke old object URL to avoid memory leaks when audio changes
  const revokeCurrentUrl = () => {
    if (previousUrlRef.current) {
      URL.revokeObjectURL(previousUrlRef.current);
      previousUrlRef.current = null;
    }
  };

  // Revoke on unmount
  useEffect(() => {
    return () => {
      revokeCurrentUrl();
    };
  }, []);

  const handleTextChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setQuestionText(e.target.value);
    // Clear previous audio when the text changes
    if (audioUrl) {
      revokeCurrentUrl();
      setAudioUrl(null);
    }
    setErrorMessage(null);
  };

  const handleLanguageChange = (e: ChangeEvent<HTMLSelectElement>) => {
    setLanguageCode(e.target.value as TTSLanguageCode);
    // Clear previous audio when language changes
    if (audioUrl) {
      revokeCurrentUrl();
      setAudioUrl(null);
    }
    setErrorMessage(null);
  };

  const handleSpeak = async () => {
    const trimmed = questionText.trim();
    if (!trimmed) {
      setErrorMessage('Please enter a question before clicking Speak.');
      return;
    }
    if (trimmed.length > MAX_TEXT_LENGTH) {
      setErrorMessage(
        `Text is too long (${trimmed.length} characters). Maximum is ${MAX_TEXT_LENGTH} characters.`
      );
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    // Revoke the old URL before we create a new one
    revokeCurrentUrl();
    setAudioUrl(null);

    try {
      const blob = await synthesizeSpeech({
        text: trimmed,
        voice,
        language_code: languageCode,
        speed,
      });

      const url = URL.createObjectURL(blob);
      previousUrlRef.current = url;
      setAudioUrl(url);

      // Auto-play once the audio element has loaded
      // (the onCanPlay handler below triggers play)
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'An unexpected error occurred during speech synthesis.';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerate = () => {
    void handleSpeak();
  };

  const remainingChars = MAX_TEXT_LENGTH - questionText.length;
  const isOverLimit = remainingChars < 0;
  const canSpeak = !isLoading && questionText.trim().length > 0 && !isOverLimit;

  return (
    <div className="tts-card">
      {/* Header */}
      <div className="tts-header">
        <div className="tts-title-row">
          <div className="tts-icon-box" aria-hidden="true">
            🔊
          </div>
          <div>
            <h3 className="tts-title">Interview Question Speaker</h3>
            <p className="tts-subtitle">
              Gnani Timbre v3.0 &bull; Voice: Riyaa &bull; 48 kHz WAV
            </p>
          </div>
        </div>
      </div>

      {/* Question Textarea */}
      <div className="tts-form-group">
        <label htmlFor="tts-question" className="form-label">
          Interview Question
        </label>
        <textarea
          id="tts-question"
          className={`tts-textarea${isOverLimit ? ' tts-textarea--error' : ''}`}
          value={questionText}
          onChange={handleTextChange}
          disabled={isLoading}
          rows={3}
          maxLength={MAX_TEXT_LENGTH + 50} /* soft guard; server enforces 800 */
          placeholder="Type the interview question to be spoken aloud…"
          aria-describedby="tts-char-count"
        />
        <p
          id="tts-char-count"
          className={`tts-char-count${isOverLimit ? ' tts-char-count--error' : ''}`}
          aria-live="polite"
        >
          {isOverLimit
            ? `${Math.abs(remainingChars)} characters over limit`
            : `${remainingChars} characters remaining`}
        </p>
      </div>

      {/* Controls Row: Language + Voice + Speed */}
      <div className="tts-controls-row">
        <div className="tts-control-group">
          <label htmlFor="tts-language" className="form-label">
            Language
          </label>
          <select
            id="tts-language"
            className="select-input"
            value={languageCode}
            onChange={handleLanguageChange}
            disabled={isLoading}
          >
            {TTS_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>

        <div className="tts-control-group">
          <label htmlFor="tts-voice" className="form-label">
            Voice
          </label>
          <select
            id="tts-voice"
            className="select-input"
            value={voice}
            onChange={(e) => setVoice(e.target.value as TTSVoice)}
            disabled={isLoading}
          >
            {TTS_VOICES.map((v) => (
              <option key={v.value} value={v.value}>
                {v.label}
              </option>
            ))}
          </select>
        </div>

        <div className="tts-control-group">
          <label htmlFor="tts-speed" className="form-label">
            Speed — {speed.toFixed(1)}×
          </label>
          <input
            id="tts-speed"
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            value={speed}
            onChange={(e) => setSpeed(parseFloat(e.target.value))}
            disabled={isLoading}
            className="tts-speed-slider"
            aria-label={`Speech speed: ${speed.toFixed(1)}x`}
          />
        </div>
      </div>

      {/* Speak Button */}
      <div className="tts-action-row">
        <button
          type="button"
          className="btn-speak"
          onClick={handleSpeak}
          disabled={!canSpeak}
          aria-label={isLoading ? 'Generating speech…' : 'Speak question aloud'}
        >
          {isLoading ? (
            <>
              <span className="spinner-small" aria-hidden="true" />
              <span>Generating Speech…</span>
            </>
          ) : (
            <>
              <span aria-hidden="true">🔊</span>
              <span>Speak Question</span>
            </>
          )}
        </button>
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="tts-error-box" role="alert">
          <span className="error-icon" aria-hidden="true">
            ⚠️
          </span>
          <div>
            <p className="error-heading">Speech Synthesis Failed</p>
            <p className="error-text">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Audio Playback */}
      {audioUrl && !isLoading && (
        <div className="tts-audio-panel">
          <div className="tts-audio-header">
            <span className="tts-audio-label">
              ✅ Audio ready — {languageCode} · Voice: {voice} · {speed.toFixed(1)}×
            </span>
          </div>

          <div className="audio-player-wrapper">
            <audio
              ref={audioRef}
              key={audioUrl} /* remount element when URL changes */
              controls
              src={audioUrl}
              className="audio-player"
              preload="auto"
              onCanPlay={() => {
                // Auto-play after synthesis
                audioRef.current?.play().catch(() => {
                  // Auto-play blocked by browser policy — user can press play manually
                });
              }}
            >
              Your browser does not support audio playback.
            </audio>
          </div>

          <div className="tts-replay-row">
            <button
              type="button"
              className="btn-tts-secondary"
              onClick={handleRegenerate}
              disabled={isLoading}
              title="Re-synthesize and play again"
            >
              🔄 Regenerate
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

