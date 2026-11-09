import { useState } from 'react';
import { AudioTranscribe } from './components/AudioTranscribe';
import { BackendStatus } from './components/BackendStatus';
import { InterviewQuestionSpeaker } from './components/InterviewQuestionSpeaker';
import { InterviewHistory } from './components/interview/InterviewHistory';
import { InterviewReport } from './components/interview/InterviewReport';
import { InterviewRoom } from './components/interview/InterviewRoom';
import { InterviewSetup } from './components/interview/InterviewSetup';
import {
  type InterviewSummary,
  type StartInterviewResponse,
} from './services/api';
import './App.css';

type MainTab = 'interview' | 'speech-lab';
type InterviewStep = 'setup' | 'room' | 'report' | 'history';

function App() {
  const [activeTab, setActiveTab] = useState<MainTab>('interview');
  const [interviewStep, setInterviewStep] = useState<InterviewStep>('setup');

  // Active interview state
  const [activeSession, setActiveSession] = useState<StartInterviewResponse | null>(null);
  const [interviewSummary, setInterviewSummary] = useState<InterviewSummary | null>(null);

  const handleInterviewStarted = (session: StartInterviewResponse) => {
    setActiveSession(session);
    setInterviewSummary(null);
    setInterviewStep('room');
  };

  const handleInterviewCompleted = (summary: InterviewSummary) => {
    setInterviewSummary(summary);
    setInterviewStep('report');
  };

  const handleStartNewInterview = () => {
    setActiveSession(null);
    setInterviewSummary(null);
    setInterviewStep('setup');
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-logo" aria-hidden="true">
            🎙️
          </div>
          <div>
            <h1 className="brand-title">VoiceHire AI</h1>
            <p className="brand-tagline">
              Adaptive Multilingual AI Voice Interviewer &bull; Powered by Gnani Prisma &amp; Timbre
            </p>
          </div>
        </div>

        <nav className="header-nav-tabs" aria-label="Main Navigation">
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'interview' ? 'nav-tab-active' : ''}`}
            onClick={() => setActiveTab('interview')}
          >
            🎯 Adaptive Interview
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'speech-lab' ? 'nav-tab-active' : ''}`}
            onClick={() => setActiveTab('speech-lab')}
          >
            🧪 Speech Lab &amp; Diagnostics
          </button>
        </nav>
      </header>

      {/* Main Content */}
      <main className="app-main">
        {activeTab === 'interview' ? (
          <section className="interview-main-section">
            {interviewStep === 'setup' && (
              <InterviewSetup
                onInterviewStarted={handleInterviewStarted}
                onViewHistory={() => setInterviewStep('history')}
              />
            )}

            {interviewStep === 'room' && activeSession && (
              <InterviewRoom
                session={activeSession}
                onComplete={handleInterviewCompleted}
                onExit={handleStartNewInterview}
              />
            )}

            {interviewStep === 'report' && interviewSummary && activeSession && (
              <InterviewReport
                summary={interviewSummary}
                jobRole={activeSession.job_role}
                candidateName={activeSession.candidate_name}
                onStartNew={handleStartNewInterview}
                onViewHistory={() => setInterviewStep('history')}
              />
            )}

            {interviewStep === 'history' && (
              <InterviewHistory onStartNew={handleStartNewInterview} />
            )}
          </section>
        ) : (
          <div className="speech-lab-section">
            {/* Backend Connection Indicator */}
            <section className="status-section">
              <BackendStatus />
            </section>

            {/* TTS: Gnani Timbre v3.0 Interview Question Speaker */}
            <section className="tts-section">
              <InterviewQuestionSpeaker />
            </section>

            {/* STT: Gnani Prisma Speech Transcription */}
            <section className="transcribe-section">
              <AudioTranscribe />
            </section>

            {/* System Architecture Overview */}
            <section className="cards-grid">
              <div className="info-card">
                <div className="card-badge">Adaptive Engine</div>
                <h3>Rule-Based Reasoning</h3>
                <p className="card-url">POST /api/interview/start</p>
                <ul className="feature-list">
                  <li>Transparent rubric &amp; evidence extraction</li>
                  <li>Multi-role question banks (Python, Java, Full Stack, Data)</li>
                  <li>Real-time dynamic difficulty tier adjustment</li>
                </ul>
              </div>

              <div className="info-card">
                <div className="card-badge">Text-to-Speech</div>
                <h3>Gnani Timbre v3.0</h3>
                <p className="card-url">POST /api/speech/synthesize</p>
                <ul className="feature-list">
                  <li>Voice: Riyaa &bull; 48 kHz mono WAV</li>
                  <li>Languages: <code>en-IN</code>, <code>te-IN</code></li>
                  <li>Size fields repaired server-side for clean playback</li>
                </ul>
              </div>

              <div className="info-card">
                <div className="card-badge">Speech-to-Text</div>
                <h3>Gnani Prisma STT</h3>
                <p className="card-url">POST /api/speech/transcribe</p>
                <ul className="feature-list">
                  <li>Web Audio PCM 16-bit 16 kHz WAV recording</li>
                  <li>Multilingual support (<code>en-IN</code>, <code>te-IN</code>)</li>
                  <li>Secure temp audio processing &amp; auto-cleanup</li>
                </ul>
              </div>
            </section>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>
          VoiceHire AI &mdash; Phase 5B: Complete Frontend Voice Interview Experience &bull; Built with
          FastAPI, SQLite &amp; React
        </p>
      </footer>
    </div>
  );
}

export default App;
