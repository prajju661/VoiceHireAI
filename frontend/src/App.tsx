import { useEffect, useState } from 'react';
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
              AI-Powered Voice Interview Screening Platform
            </p>
          </div>
        </div>
        <div className="phase-pill">Phase 1: Foundation</div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        <section className="hero-section">
          <h2>Frontend & Backend Integration</h2>
          <p className="hero-description">
            Live status monitor verifying communication between the React +
            Vite frontend and the FastAPI backend.
          </p>
        </section>

        {/* Backend Connection Indicator */}
        <section className="status-section">
          <BackendStatus />
        </section>

        {/* API Welcome Message Card (if loaded) */}
        {welcomeData && (
          <section className="welcome-card">
            <div className="welcome-header">
              <span className="welcome-icon" aria-hidden="true">
                ✨
              </span>
              <h3>Backend Message</h3>
            </div>
            <p className="welcome-message">{welcomeData.message}</p>
            {welcomeData.docs_url && (
              <a
                href={`http://127.0.0.1:8000${welcomeData.docs_url}`}
                target="_blank"
                rel="noreferrer"
                className="welcome-docs-link"
              >
                Open API Docs (Swagger UI) &rarr;
              </a>
            )}
          </section>
        )}

        {/* System Architecture Overview */}
        <section className="cards-grid">
          <div className="info-card">
            <div className="card-badge">Client</div>
            <h3>Frontend (React + Vite)</h3>
            <p className="card-url">http://localhost:5173</p>
            <ul className="feature-list">
              <li>TypeScript & modern React hooks</li>
              <li>Dynamic environment config (<code>.env</code>)</li>
              <li>Graceful network error handling</li>
            </ul>
          </div>

          <div className="info-card">
            <div className="card-badge">Server</div>
            <h3>Backend (FastAPI)</h3>
            <p className="card-url">http://127.0.0.1:8000</p>
            <ul className="feature-list">
              <li>High-performance async ASGI server</li>
              <li>CORS configured for Vite frontend</li>
              <li>Automated health check endpoints</li>
            </ul>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>VoiceHire AI &mdash; Phase 1 Complete &bull; Built with FastAPI & React</p>
      </footer>
    </div>
  );
}

export default App;
