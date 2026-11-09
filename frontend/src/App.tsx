import { useEffect, useState } from 'react';
import { AudioTranscribe } from './components/AudioTranscribe';
import { BackendStatus } from './components/BackendStatus';
import { getBackendWelcome, type WelcomeResponse } from './services/api';
import './App.css';

function App() {
  const [welcomeData, setWelcomeData] = useState<WelcomeResponse | null>(null);

  useEffect(() => {
    // Optionally fetch the root welcome message to show full API connectivity
    getBackendWelcome()
      .then((data) => setWelcomeData(data))
      .catch(() => {
        // Ignored here because BackendStatus handles error reporting for health
      });
  }, []);

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
              Adaptive Multilingual AI Voice Interviewer &bull; Powered by Gnani Prisma
            </p>
          </div>
        </div>
        <div className="phase-pill">Phase 3: Live Microphone Recording</div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        {/* Backend Connection Indicator */}
        <section className="status-section">
          <BackendStatus />
        </section>

        {/* Phase 2 Speech Transcription Testing Card */}
        <section className="transcribe-section">
          <AudioTranscribe />
        </section>

        {/* API Welcome Message Card (if loaded) */}
        {welcomeData && (
          <section className="welcome-card">
            <div className="welcome-header">
              <span className="welcome-icon" aria-hidden="true">
                ✨
              </span>
              <h3>Backend Operational Status</h3>
            </div>
            <p className="welcome-message">{welcomeData.message}</p>
            {welcomeData.docs_url && (
              <a
                href={`http://127.0.0.1:8000${welcomeData.docs_url}`}
                target="_blank"
                rel="noreferrer"
                className="welcome-docs-link"
              >
                Open API Documentation (Swagger UI) &rarr;
              </a>
            )}
          </section>
        )}

        {/* System Architecture Overview */}
        <section className="cards-grid">
          <div className="info-card">
            <div className="card-badge">Speech-to-Text</div>
            <h3>Gnani Prisma STT</h3>
            <p className="card-url">POST /api/speech/transcribe</p>
            <ul className="feature-list">
              <li>Verified <code>gnani-vachana</code> SDK integration</li>
              <li>Multilingual support (<code>en-IN</code>, <code>te-IN</code>)</li>
              <li>Secure temp audio processing & auto-cleanup</li>
            </ul>
          </div>

          <div className="info-card">
            <div className="card-badge">Server</div>
            <h3>Backend (FastAPI)</h3>
            <p className="card-url">http://127.0.0.1:8000</p>
            <ul className="feature-list">
              <li>Multipart audio validation & size limits</li>
              <li>CORS configured for Vite frontend</li>
              <li>Credential protection (secrets strictly masked)</li>
            </ul>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>
          VoiceHire AI &mdash; Phase 3: Live Microphone Recording &bull; Built with
          FastAPI &amp; React
        </p>
      </footer>
    </div>
  );
}

export default App;
