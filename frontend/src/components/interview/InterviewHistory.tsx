import { useState, useEffect, useCallback } from 'react';
import {
  deleteInterview,
  getInterviewSession,
  listInterviews,
  type InterviewSessionDetails,
  type SessionSummaryItem,
} from '../../services/api';

interface InterviewHistoryProps {
  onStartNew: () => void;
}

export function InterviewHistory({ onStartNew }: InterviewHistoryProps) {
  const [sessions, setSessions] = useState<SessionSummaryItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Selected session for viewing details modal
  const [selectedSession, setSelectedSession] = useState<InterviewSessionDetails | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState<boolean>(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  // Deletion state
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await listInterviews(50, 0);
      setSessions(data.sessions);
      setTotalCount(data.total);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to load past interview sessions.');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    listInterviews(50, 0)
      .then((data) => {
        if (!ignore) {
          setSessions(data.sessions);
          setTotalCount(data.total);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          setErrorMessage(
            err instanceof Error ? err.message : 'Failed to load past interview sessions.'
          );
          setIsLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  const handleViewDetails = async (sessionId: string) => {
    setIsLoadingDetails(true);
    setDetailsError(null);
    try {
      const details = await getInterviewSession(sessionId);
      setSelectedSession(details);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setDetailsError(err.message);
      } else {
        setDetailsError('Failed to load session details.');
      }
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!window.confirm('Are you sure you want to delete this interview record? This action cannot be undone.')) {
      return;
    }

    setDeletingId(sessionId);
    try {
      await deleteInterview(sessionId);
      // Remove from local list
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      setTotalCount((prev) => Math.max(0, prev - 1));
      if (selectedSession?.session_id === sessionId) {
        setSelectedSession(null);
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete session.');
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="interview-history-card">
      <div className="history-header">
        <div>
          <div className="history-badge">Session Records</div>
          <h2 className="history-title">Interview History & Audits</h2>
          <p className="history-subtitle">
            Review past voice interview evaluations, turns, and scores recorded in SQLite.
          </p>
        </div>

        <div className="history-header-actions">
          <button
            type="button"
            className="btn-secondary-action"
            onClick={fetchSessions}
            disabled={isLoading}
          >
            🔄 Refresh
          </button>
          <button type="button" className="btn-primary-action" onClick={onStartNew}>
            + Start New Interview
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="history-error-banner" role="alert">
          ⚠️ {errorMessage}
        </div>
      )}

      {isLoading ? (
        <div className="history-loading-box">
          <span className="btn-spinner" aria-hidden="true"></span>
          <span>Loading session records...</span>
        </div>
      ) : sessions.length === 0 ? (
        <div className="history-empty-box">
          <span className="empty-icon" aria-hidden="true">📂</span>
          <h4>No Interview Sessions Recorded Yet</h4>
          <p>Start your first adaptive voice interview to see performance history here.</p>
          <button type="button" className="btn-primary-action" onClick={onStartNew}>
            🚀 Start an Interview
          </button>
        </div>
      ) : (
        <div className="history-table-wrapper">
          <table className="history-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Candidate</th>
                <th>Job Role</th>
                <th>Language</th>
                <th>Tier</th>
                <th>Status</th>
                <th>Score</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.id}>
                  <td className="table-date">{formatDate(session.created_at)}</td>
                  <td>{session.candidate_name || 'Anonymous'}</td>
                  <td><strong>{session.job_role}</strong></td>
                  <td><span className="lang-code-pill">{session.language}</span></td>
                  <td><span className="diff-code-pill">{session.difficulty}</span></td>
                  <td>
                    <span className={`status-pill status-${session.status}`}>
                      {session.status}
                    </span>
                  </td>
                  <td>
                    {session.overall_score !== null ? (
                      <span className="score-cell-badge">
                        {session.overall_score.toFixed(1)} / 100
                      </span>
                    ) : (
                      <span className="score-pending-text">In Progress</span>
                    )}
                  </td>
                  <td className="table-actions">
                    <button
                      type="button"
                      className="btn-action-view"
                      onClick={() => handleViewDetails(session.id)}
                      disabled={isLoadingDetails}
                    >
                      Inspect
                    </button>
                    <button
                      type="button"
                      className="btn-action-delete"
                      onClick={() => handleDeleteSession(session.id)}
                      disabled={deletingId === session.id}
                    >
                      {deletingId === session.id ? '...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="table-footer-meta">
            Total recorded sessions: {totalCount}
          </div>
        </div>
      )}

      {/* Session Details Modal */}
      {selectedSession && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-content modal-large">
            <div className="modal-header-row">
              <div>
                <span className="modal-tag">Session Audit #{selectedSession.session_id.slice(0, 8)}</span>
                <h3>{selectedSession.job_role} Screening</h3>
                <p className="modal-meta">
                  Date: {formatDate(selectedSession.created_at)} &bull; Language: {selectedSession.language} &bull; Status: {selectedSession.status}
                </p>
              </div>
              <button
                type="button"
                className="btn-modal-close"
                onClick={() => setSelectedSession(null)}
              >
                ✕
              </button>
            </div>

            {detailsError && (
              <div className="history-error-banner" role="alert">
                ⚠️ {detailsError}
              </div>
            )}

            <div className="modal-scrollable-body">
              {/* Overall Score */}
              <div className="modal-score-summary">
                <span className="score-label">Overall Session Score:</span>
                <span className="score-value">
                  {selectedSession.overall_score !== null
                    ? `${selectedSession.overall_score.toFixed(1)} / 100`
                    : 'Not finalized'}
                </span>
              </div>

              {/* Turns History */}
              <h4 className="turns-heading">Interview Turns ({selectedSession.turns.length})</h4>
              {selectedSession.turns.length === 0 ? (
                <p className="no-turns-notice">No questions were answered in this session.</p>
              ) : (
                <div className="turns-list">
                  {selectedSession.turns.map((turn) => (
                    <div key={turn.id} className="turn-history-item">
                      <div className="turn-header-row">
                        <span className="turn-num-badge">Question {turn.turn_number}</span>
                        <span className="turn-cat-pill">{turn.question_category}</span>
                        {turn.score !== null && (
                          <span className="turn-score-badge">Score: {turn.score.toFixed(1)} / 100</span>
                        )}
                      </div>

                      <p className="turn-q-text"><strong>Q:</strong> {turn.question_text}</p>

                      {turn.answer_text ? (
                        <div className="turn-answer-box">
                          <p className="turn-a-text"><strong>Answer:</strong> "{turn.answer_text}"</p>
                          {turn.feedback && (
                            <p className="turn-feedback-text"><strong>Feedback:</strong> {turn.feedback}</p>
                          )}
                          {turn.strengths && turn.strengths.length > 0 && (
                            <div className="turn-strengths">
                              <strong>Strengths:</strong>
                              <ul>
                                {turn.strengths.map((s, idx) => (
                                  <li key={idx}>✓ {s}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      ) : (
                        <p className="turn-unanswered">Pending answer</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setSelectedSession(null)}
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
