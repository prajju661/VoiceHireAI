import { useState, useEffect, useRef, useCallback } from 'react';
import {
  completeInterview,
  submitAnswer,
  synthesizeSpeech,
  transcribeAudio,
  type InterviewQuestion,
  type InterviewSummary,
  type StartInterviewResponse,
  type SubmitAnswerResponse,
  type TTSLanguageCode,
} from '../../services/api';
import { useAudioRecorder } from '../../hooks/useAudioRecorder';
import { formatDuration } from '../../utils/audioUtils';

interface InterviewRoomProps {
  session: StartInterviewResponse;
  onComplete: (summary: InterviewSummary) => void;
  onExit: () => void;
}

export function InterviewRoom({ session, onComplete, onExit }: InterviewRoomProps) {
  // Turn & Question state
  const [currentQuestion, setCurrentQuestion] = useState<InterviewQuestion>(session.first_question);
  const [turnNumber, setTurnNumber] = useState<number>(session.turn_number);
  const [currentDifficulty, setCurrentDifficulty] = useState<string>(session.current_difficulty);

  // Audio synthesis state (Timbre TTS)
  const [isSynthesizing, setIsSynthesizing] = useState<boolean>(true);
  const [questionAudioUrl, setQuestionAudioUrl] = useState<string | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState<boolean>(false);
  const [ttsError, setTtsError] = useState<string | null>(null);

  // Answer & Transcription state (Prisma STT)
  const [transcriptText, setTranscriptText] = useState<string>('');
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Evaluation & Next question state
  const [evaluationResult, setEvaluationResult] = useState<SubmitAnswerResponse | null>(null);

  // End interview modal state
  const [showEndModal, setShowEndModal] = useState<boolean>(false);
  const [isEnding, setIsEnding] = useState<boolean>(false);

  // Refs for audio elements and URL cleanup
  const questionAudioRef = useRef<HTMLAudioElement | null>(null);
  const currentQuestionUrlRef = useRef<string | null>(null);

  // Live microphone hook
  const {
    isRecording,
    recordingDuration,
    recordedFile,
    audioUrl: recordedAudioUrl,
    error: recorderError,
    isSupported: isMicSupported,
    startRecording,
    stopRecording,
    clearRecording,
  } = useAudioRecorder();

  // Helper to safely revoke question audio object URLs
  const revokeQuestionAudio = useCallback(() => {
    if (currentQuestionUrlRef.current) {
      URL.revokeObjectURL(currentQuestionUrlRef.current);
      currentQuestionUrlRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      revokeQuestionAudio();
    };
  }, [revokeQuestionAudio]);

  /**
   * Synthesize question using Gnani Timbre TTS
   */
  const playQuestionAudio = useCallback(async (question: InterviewQuestion) => {
    setIsSynthesizing(true);
    setTtsError(null);
    revokeQuestionAudio();
    setQuestionAudioUrl(null);

    // Map language for Timbre TTS: te-IN for Telugu; en-IN for English and code-mixed
    const ttsLanguage: TTSLanguageCode = question.language === 'te-IN' ? 'te-IN' : 'en-IN';

    try {
      const audioBlob = await synthesizeSpeech({
        text: question.question_text,
        language_code: ttsLanguage,
        voice: 'Riyaa',
        speed: 1.0,
      });

      const url = URL.createObjectURL(audioBlob);
      currentQuestionUrlRef.current = url;
      setQuestionAudioUrl(url);

      // Attempt automatic playback
      const audio = new Audio(url);
      questionAudioRef.current = audio;

      audio.onplay = () => setIsAudioPlaying(true);
      audio.onended = () => setIsAudioPlaying(false);
      audio.onpause = () => setIsAudioPlaying(false);
      audio.onerror = () => {
        setIsAudioPlaying(false);
      };

      try {
        await audio.play();
      } catch {
        // Autoplay may be blocked by browser policy without user gesture;
        // The UI will display the manual play button.
        setIsAudioPlaying(false);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setTtsError(err.message);
      } else {
        setTtsError('Unable to synthesize question audio.');
      }
    } finally {
      setIsSynthesizing(false);
    }
  }, [revokeQuestionAudio]);

  // Speak initial question on mount
  useEffect(() => {
    let ignore = false;
    const ttsLanguage: TTSLanguageCode =
      session.first_question.language === 'te-IN' ? 'te-IN' : 'en-IN';

    synthesizeSpeech({
      text: session.first_question.question_text,
      language_code: ttsLanguage,
      voice: 'Riyaa',
      speed: 1.0,
    })
      .then((audioBlob) => {
        if (!ignore) {
          const url = URL.createObjectURL(audioBlob);
          currentQuestionUrlRef.current = url;
          setQuestionAudioUrl(url);
          setIsSynthesizing(false);

          const audio = new Audio(url);
          questionAudioRef.current = audio;
          audio.onplay = () => setIsAudioPlaying(true);
          audio.onended = () => setIsAudioPlaying(false);
          audio.onpause = () => setIsAudioPlaying(false);
          audio.play().catch(() => {
            setIsAudioPlaying(false);
          });
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          setTtsError(
            err instanceof Error ? err.message : 'Unable to synthesize question audio.'
          );
          setIsSynthesizing(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [session.first_question]);

  /**
   * Toggle manual question audio playback
   */
  const handleToggleQuestionAudio = () => {
    if (!questionAudioUrl) {
      playQuestionAudio(currentQuestion);
      return;
    }

    if (questionAudioRef.current) {
      if (isAudioPlaying) {
        questionAudioRef.current.pause();
      } else {
        questionAudioRef.current.play().catch(() => {});
      }
    } else {
      const audio = new Audio(questionAudioUrl);
      questionAudioRef.current = audio;
      audio.onplay = () => setIsAudioPlaying(true);
      audio.onended = () => setIsAudioPlaying(false);
      audio.onpause = () => setIsAudioPlaying(false);
      audio.play().catch(() => {});
    }
  };

  /**
   * Finish microphone recording and automatically trigger Prisma STT transcription
   */
  const handleFinishRecording = () => {
    stopRecording();
  };

  // Watch for recordedFile update after stopping recording to trigger Prisma STT
  useEffect(() => {
    if (recordedFile && !isRecording && !transcriptText) {
      const transcribe = async () => {
        setIsTranscribing(true);
        setErrorMessage(null);
        try {
          const sttLang = currentQuestion.language === 'te-IN' ? 'te-IN' : 'en-IN';
          const response = await transcribeAudio(recordedFile, sttLang);
          setTranscriptText(response.transcript);
        } catch (err: unknown) {
          if (err instanceof Error) {
            setErrorMessage(`Transcription notice: ${err.message}. You can type or edit your answer directly.`);
          } else {
            setErrorMessage('Unable to transcribe audio. You may type your answer directly.');
          }
        } finally {
          setIsTranscribing(false);
        }
      };

      transcribe();
    }
  }, [recordedFile, isRecording, currentQuestion.language, transcriptText]);

  /**
   * Submit candidate answer to backend
   */
  const handleSubmitAnswer = async () => {
    const trimmed = transcriptText.trim();
    if (!trimmed) {
      setErrorMessage('Please provide an answer before submitting.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await submitAnswer(session.session_id, {
        answer_text: trimmed,
      });

      setEvaluationResult(response);
      setCurrentDifficulty(response.updated_difficulty);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to submit answer. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Advance to the next question received from evaluation
   */
  const handleAdvanceToNextQuestion = () => {
    if (!evaluationResult) return;

    const nextQ = evaluationResult.next_question;
    setCurrentQuestion(nextQ);
    setTurnNumber((prev) => prev + 1);
    setCurrentDifficulty(evaluationResult.updated_difficulty);

    // Reset turn states
    setEvaluationResult(null);
    setTranscriptText('');
    setErrorMessage(null);
    clearRecording();

    // Synthesize and play next question
    playQuestionAudio(nextQ);
  };

  /**
   * Conclude the interview and fetch final performance report
   */
  const handleConfirmEndInterview = async () => {
    setIsEnding(true);
    setErrorMessage(null);

    try {
      const summary = await completeInterview(session.session_id);
      setShowEndModal(false);
      onComplete(summary);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to complete interview session.');
      }
      setIsEnding(false);
    }
  };

  return (
    <div className="interview-room-container">
      {/* Top Header / Meta Bar */}
      <div className="room-header-bar">
        <div className="room-meta-left">
          <div className="meta-badge-role">{session.job_role}</div>
          <div className="meta-badge-lang">{session.language}</div>
          <div className="meta-badge-diff">Tier: {currentDifficulty}</div>
          {session.candidate_name && (
            <div className="meta-candidate-name">Candidate: {session.candidate_name}</div>
          )}
        </div>

        <div className="room-meta-right">
          <button
            type="button"
            className="btn-end-interview"
            onClick={() => setShowEndModal(true)}
            disabled={isSubmitting || isEnding}
          >
            ⏹ Conclude Interview
          </button>
        </div>
      </div>

      {/* Main Question Card */}
      <div className="question-card">
        <div className="question-header">
          <div className="question-turn-badge">Question {turnNumber}</div>
          <div className="question-category-pill">{currentQuestion.category}</div>
        </div>

        <h3 className="question-prompt-text">{currentQuestion.question_text}</h3>

        {/* Audio Player for Question (Gnani Timbre v3.0) */}
        <div className="question-audio-controls">
          <button
            type="button"
            className={`btn-audio-speak ${isAudioPlaying ? 'btn-audio-playing' : ''}`}
            onClick={handleToggleQuestionAudio}
            disabled={isSynthesizing}
            aria-label={isAudioPlaying ? 'Pause question audio' : 'Play question audio'}
          >
            {isSynthesizing ? (
              <>
                <span className="btn-spinner" aria-hidden="true"></span>
                <span>Generating Voice (Timbre)...</span>
              </>
            ) : isAudioPlaying ? (
              <>
                <span aria-hidden="true">⏸</span>
                <span>Pause Question</span>
              </>
            ) : (
              <>
                <span aria-hidden="true">🔊</span>
                <span>{questionAudioUrl ? 'Replay Question Voice' : 'Speak Question Voice'}</span>
              </>
            )}
          </button>

          {ttsError && <span className="tts-inline-error">⚠️ {ttsError}</span>}
        </div>
      </div>

      {/* Answer & Recording Section (Hidden when evaluation result is being reviewed) */}
      {!evaluationResult && (
        <div className="answer-card">
          <div className="answer-card-header">
            <h4>Your Verbal Answer</h4>
            <p className="answer-subtitle">
              Record your response with your microphone or edit the transcribed text below.
            </p>
          </div>

          {/* Recording Toolbar */}
          <div className="recorder-toolbar">
            {!isRecording ? (
              <button
                type="button"
                className="btn-start-record"
                onClick={startRecording}
                disabled={!isMicSupported || isTranscribing || isSubmitting}
              >
                <span className="mic-icon" aria-hidden="true">🎙️</span>
                <span>{recordedFile ? 'Record Again' : 'Start Speaking Answer'}</span>
              </button>
            ) : (
              <div className="recording-live-box">
                <div className="recording-indicator">
                  <span className="recording-pulse" aria-hidden="true"></span>
                  <span className="recording-label">Recording:</span>
                  <span className="recording-timer">{formatDuration(recordingDuration)}</span>
                </div>

                <button
                  type="button"
                  className="btn-stop-record"
                  onClick={handleFinishRecording}
                >
                  ⏹ Finish & Transcribe
                </button>
              </div>
            )}

            {/* Mic error notice */}
            {recorderError && (
              <div className="recorder-error-alert" role="alert">
                ⚠️ {recorderError.message}
              </div>
            )}
          </div>

          {/* Recorded Audio Preview */}
          {recordedAudioUrl && !isRecording && (
            <div className="recorded-preview-row">
              <span className="preview-label">Audio preview:</span>
              <audio controls src={recordedAudioUrl} className="preview-audio-player" />
            </div>
          )}

          {/* Transcription Loading Spinner */}
          {isTranscribing && (
            <div className="transcribing-notice">
              <span className="btn-spinner" aria-hidden="true"></span>
              <span>Transcribing your speech via Gnani Prisma STT...</span>
            </div>
          )}

          {/* Transcript / Answer Text Area */}
          <div className="transcript-input-group">
            <label htmlFor="answer-transcript" className="form-label">
              Answer Transcript <span className="label-optional">(editable)</span>:
            </label>
            <textarea
              id="answer-transcript"
              className="answer-textarea"
              rows={5}
              placeholder="Your transcribed answer will appear here. You can also type or make corrections before submitting..."
              value={transcriptText}
              onChange={(e) => setTranscriptText(e.target.value)}
              disabled={isSubmitting || isTranscribing}
            />
            <div className="textarea-footer">
              <span className="char-count">{transcriptText.trim().split(/\s+/).filter(Boolean).length} words</span>
            </div>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="room-error-banner" role="alert">
              ⚠️ {errorMessage}
            </div>
          )}

          {/* Submit Button */}
          <div className="answer-submit-row">
            <button
              type="button"
              className="btn-submit-answer"
              onClick={handleSubmitAnswer}
              disabled={!transcriptText.trim() || isSubmitting || isRecording || isTranscribing}
            >
              {isSubmitting ? (
                <>
                  <span className="btn-spinner" aria-hidden="true"></span>
                  <span>Evaluating with Reasoning Engine...</span>
                </>
              ) : (
                <>
                  <span aria-hidden="true">✔️</span>
                  <span>Submit Answer</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Immediate Evaluation Feedback Card */}
      {evaluationResult && (
        <div className="evaluation-card">
          <div className="eval-header-row">
            <div>
              <span className="eval-badge">Turn {evaluationResult.turn_number} Evaluation</span>
              <h4 className="eval-title">Answer Feedback & Assessment</h4>
            </div>
            <div className="eval-score-box">
              <span className="eval-score-number">{evaluationResult.score.toFixed(1)}</span>
              <span className="eval-score-max">/ 100</span>
            </div>
          </div>

          {/* Difficulty Adjustment Banner */}
          <div className="difficulty-adjustment-banner">
            <span>Adaptive Engine:</span>
            <strong>Difficulty adjusted to {evaluationResult.updated_difficulty.toUpperCase()}</strong>
          </div>

          {/* Feedback Explanation */}
          <div className="eval-feedback-text">
            {evaluationResult.feedback}
          </div>

          {/* Strengths & Improvement Areas Grid */}
          <div className="eval-details-grid">
            {evaluationResult.strengths.length > 0 && (
              <div className="eval-strengths-box">
                <h5>Demonstrated Strengths</h5>
                <ul>
                  {evaluationResult.strengths.map((s, idx) => (
                    <li key={idx}>✓ {s}</li>
                  ))}
                </ul>
              </div>
            )}

            {evaluationResult.improvement_areas.length > 0 && (
              <div className="eval-improvements-box">
                <h5>Growth & Missing Concepts</h5>
                <ul>
                  {evaluationResult.improvement_areas.map((area, idx) => (
                    <li key={idx}>• {area}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Evidence Quotes */}
          {evaluationResult.evidence_from_answer.length > 0 && (
            <div className="eval-evidence-box">
              <h5>Evidence Extracted from Your Answer</h5>
              <div className="evidence-quotes-list">
                {evaluationResult.evidence_from_answer.map((quote, idx) => (
                  <span key={idx} className="evidence-quote-pill">{quote}</span>
                ))}
              </div>
            </div>
          )}

          {/* Advance Action */}
          <div className="eval-next-action-row">
            <button
              type="button"
              className="btn-advance-question"
              onClick={handleAdvanceToNextQuestion}
            >
              <span>Proceed to Question {turnNumber + 1}</span>
              <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      )}

      {/* Confirmation Modal to End Interview */}
      {showEndModal && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div className="modal-content">
            <h3 id="modal-title" className="modal-title">Conclude Interview Session?</h3>
            <p className="modal-body">
              Are you sure you want to end this interview now? All answered questions will be
              compiled into your comprehensive performance summary report.
            </p>

            {errorMessage && (
              <div className="modal-error-alert" role="alert">
                ⚠️ {errorMessage}
              </div>
            )}

            <div className="modal-actions">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => {
                  setShowEndModal(false);
                  onExit();
                }}
                disabled={isEnding}
              >
                Discard &amp; Exit
              </button>
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setShowEndModal(false)}
                disabled={isEnding}
              >
                Continue Interview
              </button>
              <button
                type="button"
                className="btn-modal-confirm"
                onClick={handleConfirmEndInterview}
                disabled={isEnding}
              >
                {isEnding ? (
                  <>
                    <span className="btn-spinner" aria-hidden="true"></span>
                    <span>Compiling Report...</span>
                  </>
                ) : (
                  <span>Yes, End & Generate Report</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
