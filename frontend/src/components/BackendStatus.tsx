import { useEffect, useState, useCallback } from 'react';
import {
  checkBackendHealth,
  API_BASE_URL,
  type HealthResponse,
} from '../services/api';

type ConnectionState = 'checking' | 'connected' | 'disconnected';

export function BackendStatus() {
  const [status, setStatus] = useState<ConnectionState>('checking');
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const performHealthCheck = useCallback(async () => {
    setStatus('checking');
    setErrorMessage(null);

    try {
      const data = await checkBackendHealth();
      setHealthData(data);
      setStatus('connected');
      setLastChecked(new Date());
    } catch (err: unknown) {
      setHealthData(null);
      setStatus('disconnected');
      setLastChecked(new Date());

      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected network error occurred.');
      }
    }
  }, []);

  // Call the backend /health endpoint on initial page load
  useEffect(() => {
    let isMounted = true;

    checkBackendHealth()
      .then((data) => {
        if (isMounted) {
          setHealthData(data);
          setStatus('connected');
          setLastChecked(new Date());
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setHealthData(null);
          setStatus('disconnected');
          setLastChecked(new Date());
          if (err instanceof Error) {
            setErrorMessage(err.message);
          } else {
            setErrorMessage('An unexpected network error occurred.');
          }
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="status-card">
      <div className="status-header">
        <div className="status-title-row">
          <span className="status-label">Backend Connection</span>
          <div className={`status-badge status-${status}`}>
            <span className="status-dot" aria-hidden="true" />
            <span className="status-text">
              {status === 'checking' && 'Checking...'}
              {status === 'connected' && 'Connected'}
              {status === 'disconnected' && 'Disconnected'}
            </span>
          </div>
        </div>
        <p className="status-subtitle">
          Target API: <code>{API_BASE_URL}</code>
        </p>
      </div>

      <div className="status-body">
        {status === 'checking' && (
          <div className="status-message status-checking-msg">
            <span className="spinner" aria-hidden="true" />
            <span>Verifying connection to FastAPI backend...</span>
          </div>
        )}

        {status === 'connected' && healthData && (
          <div className="status-details">
            <div className="detail-item">
              <span className="detail-label">Application:</span>
              <span className="detail-value">{healthData.application}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Health Status:</span>
              <span className="detail-value highlight-success">
                {healthData.status}
              </span>
            </div>
            {lastChecked && (
              <div className="detail-item">
                <span className="detail-label">Last Checked:</span>
                <span className="detail-value">
                  {lastChecked.toLocaleTimeString()}
                </span>
              </div>
            )}
          </div>
        )}

        {status === 'disconnected' && (
          <div className="status-error-box">
            <p className="error-title">Unable to reach the backend server</p>
            <p className="error-description">
              {errorMessage || 'Network request failed. Is the backend running?'}
            </p>
            <p className="error-hint">
              Tip: Ensure the FastAPI server is running with:
              <br />
              <code>uvicorn backend.app.main:app --reload --port 8000</code>
            </p>
          </div>
        )}
      </div>

      <div className="status-actions">
        <button
          type="button"
          onClick={performHealthCheck}
          disabled={status === 'checking'}
          className="btn-refresh"
        >
          {status === 'checking' ? 'Checking...' : 'Check Again'}
        </button>
      </div>
    </div>
  );
}
