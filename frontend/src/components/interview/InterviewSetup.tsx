import { useState, type FormEvent } from 'react';
import {
  startInterview,
  type DifficultyLevel,
  type InterviewLanguage,
  type JobRole,
  type StartInterviewResponse,
} from '../../services/api';

interface InterviewSetupProps {
  onInterviewStarted: (session: StartInterviewResponse) => void;
  onViewHistory: () => void;
}

const SUPPORTED_ROLES: { value: JobRole; label: string; description: string }[] = [
  {
    value: 'Python Developer',
    label: 'Python Developer',
    description: 'Data structures, generators, decorators, GIL, async/await, and architecture',
  },
  {
    value: 'Java Developer',
    label: 'Java Developer',
    description: 'OOP, Collections, JVM memory, Spring microservices, and thread management',
  },
  {
    value: 'Full Stack Developer',
    label: 'Full Stack Developer',
    description: 'Web architecture, React state, REST APIs, databases, and microservices',
  },
  {
    value: 'Data Analyst',
    label: 'Data Analyst',
    description: 'SQL joins, Pandas data wrangling, window functions, and analytics',
  },
];

const SUPPORTED_LANGUAGES: { value: InterviewLanguage; label: string; badge: string }[] = [
  { value: 'en-IN', label: 'English (India)', badge: 'EN' },
  { value: 'te-IN', label: 'Telugu (తెలుగు)', badge: 'TE' },
  { value: 'te-en', label: 'Telugu-English Code-Mixed (Tanglish)', badge: 'TE-EN' },
];

const DIFFICULTY_LEVELS: { value: DifficultyLevel; label: string; hint: string }[] = [
  { value: 'beginner', label: 'Beginner', hint: 'Core fundamentals & syntax' },
  { value: 'intermediate', label: 'Intermediate', hint: 'Applied patterns & best practices' },
  { value: 'advanced', label: 'Advanced', hint: 'System design, internals & optimization' },
];

export function InterviewSetup({ onInterviewStarted, onViewHistory }: InterviewSetupProps) {
  const [candidateName, setCandidateName] = useState<string>('');
  const [candidateEmail, setCandidateEmail] = useState<string>('');
  const [selectedRole, setSelectedRole] = useState<JobRole>('Python Developer');
  const [selectedLanguage, setSelectedLanguage] = useState<InterviewLanguage>('en-IN');
  const [selectedDifficulty, setSelectedDifficulty] = useState<DifficultyLevel>('intermediate');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await startInterview({
        job_role: selectedRole,
        language: selectedLanguage,
        initial_difficulty: selectedDifficulty,
        candidate_name: candidateName.trim() || undefined,
        candidate_email: candidateEmail.trim() || undefined,
      });

      onInterviewStarted(response);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to start interview session. Please check your backend.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="interview-setup-card">
      <div className="setup-header">
        <div className="setup-badge">AI Voice Screening</div>
        <h2 className="setup-title">Configure Your Interview Session</h2>
        <p className="setup-subtitle">
          VoiceHire AI adapts question difficulty in real-time based on your verbal answers,
          powered by Gnani Timbre TTS speech generation and Gnani Prisma STT transcription.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="setup-form" noValidate>
        {/* Candidate Details (Optional) */}
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="candidate-name" className="form-label">
              Candidate Name <span className="label-optional">(optional)</span>
            </label>
            <input
              id="candidate-name"
              type="text"
              className="form-input"
              placeholder="e.g. Priya Sharma"
              value={candidateName}
              onChange={(e) => setCandidateName(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="candidate-email" className="form-label">
              Candidate Email <span className="label-optional">(optional)</span>
            </label>
            <input
              id="candidate-email"
              type="email"
              className="form-input"
              placeholder="e.g. priya@example.com"
              value={candidateEmail}
              onChange={(e) => setCandidateEmail(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

        {/* Job Role Selection */}
        <div className="form-group">
          <label htmlFor="job-role" className="form-label">
            Target Job Role <span className="label-required">*</span>
          </label>
          <div className="role-selection-grid">
            {SUPPORTED_ROLES.map((role) => (
              <button
                key={role.value}
                type="button"
                className={`role-choice-card ${selectedRole === role.value ? 'role-choice-selected' : ''}`}
                onClick={() => setSelectedRole(role.value)}
                disabled={isLoading}
              >
                <div className="role-choice-title">{role.label}</div>
                <div className="role-choice-desc">{role.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Language Selection */}
        <div className="form-group">
          <label htmlFor="interview-lang" className="form-label">
            Interview Language <span className="label-required">*</span>
          </label>
          <div className="lang-pill-row">
            {SUPPORTED_LANGUAGES.map((lang) => (
              <button
                key={lang.value}
                type="button"
                className={`lang-pill ${selectedLanguage === lang.value ? 'lang-pill-selected' : ''}`}
                onClick={() => setSelectedLanguage(lang.value)}
                disabled={isLoading}
              >
                <span className="lang-badge">{lang.badge}</span>
                <span>{lang.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Starting Difficulty */}
        <div className="form-group">
          <label htmlFor="difficulty-tier" className="form-label">
            Starting Difficulty Tier <span className="label-required">*</span>
          </label>
          <div className="diff-pill-row">
            {DIFFICULTY_LEVELS.map((diff) => (
              <button
                key={diff.value}
                type="button"
                className={`diff-pill ${selectedDifficulty === diff.value ? 'diff-pill-selected' : ''}`}
                onClick={() => setSelectedDifficulty(diff.value)}
                disabled={isLoading}
              >
                <span className="diff-label">{diff.label}</span>
                <span className="diff-hint">{diff.hint}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Error Message */}
        {errorMessage && (
          <div className="setup-error-banner" role="alert">
            <span className="error-icon" aria-hidden="true">⚠️</span>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="setup-actions">
          <button
            type="submit"
            className="btn-start-interview"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="btn-spinner" aria-hidden="true"></span>
                <span>Starting Session...</span>
              </>
            ) : (
              <>
                <span aria-hidden="true">🚀</span>
                <span>Start Voice Interview</span>
              </>
            )}
          </button>

          <button
            type="button"
            className="btn-secondary-history"
            onClick={onViewHistory}
            disabled={isLoading}
          >
            📋 Past Interviews History
          </button>
        </div>
      </form>
    </div>
  );
}
