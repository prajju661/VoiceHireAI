import type { InterviewSummary } from '../../services/api';

interface InterviewReportProps {
  summary: InterviewSummary;
  jobRole: string;
  candidateName?: string | null;
  onStartNew: () => void;
  onViewHistory: () => void;
}

export function InterviewReport({
  summary,
  jobRole,
  candidateName,
  onStartNew,
  onViewHistory,
}: InterviewReportProps) {
  const getTier = (score: number) => {
    if (score >= 80) return { label: 'Strong Hire / High Proficiency', color: 'tier-strong' };
    if (score >= 60) return { label: 'Hire / Proficient', color: 'tier-hire' };
    if (score >= 40) return { label: 'Borderline / Developing', color: 'tier-developing' };
    return { label: 'Needs Preparation', color: 'tier-needs-prep' };
  };

  const tier = getTier(summary.overall_score);

  return (
    <div className="interview-report-card">
      {/* Header Banner */}
      <div className="report-header">
        <div className="report-badge">Interview Performance Summary</div>
        <h2 className="report-title">
          Screening Report: {jobRole}
        </h2>
        {candidateName && <p className="report-candidate">Candidate: {candidateName}</p>}
        <p className="report-subtitle">
          Evaluated by VoiceHire AI Reasoning Engine ({summary.reasoning_provider})
        </p>
      </div>

      {/* Score Overview Row */}
      <div className="score-overview-grid">
        <div className="score-hero-box">
          <span className="score-hero-label">Overall Technical Score</span>
          <div className="score-hero-value">
            <span className="score-number">{summary.overall_score.toFixed(1)}</span>
            <span className="score-total">/ 100</span>
          </div>
          <div className={`score-tier-badge ${tier.color}`}>
            {tier.label}
          </div>
        </div>

        <div className="meta-stats-box">
          <div className="stat-item">
            <span className="stat-label">Questions Evaluated</span>
            <span className="stat-value">{summary.questions_answered}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Final Difficulty Reached</span>
            <span className="stat-value">{summary.final_difficulty.toUpperCase()}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Evaluation Engine</span>
            <span className="stat-value">{summary.reasoning_provider}</span>
          </div>
        </div>
      </div>

      {/* Category Scores Breakdown */}
      {Object.keys(summary.category_scores).length > 0 && (
        <div className="report-section">
          <h4 className="section-title">Category Breakdown</h4>
          <div className="categories-list">
            {Object.entries(summary.category_scores).map(([category, score]) => (
              <div key={category} className="category-score-row">
                <div className="category-info">
                  <span className="category-name">{category}</span>
                  <span className="category-score-num">{score.toFixed(1)}%</span>
                </div>
                <div className="progress-bar-track">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strengths & Improvement Areas */}
      <div className="report-columns-grid">
        {summary.strengths.length > 0 && (
          <div className="report-col-box strengths-col">
            <h4 className="col-title">Demonstrated Technical Strengths</h4>
            <ul className="report-list">
              {summary.strengths.map((str, idx) => (
                <li key={idx}>
                  <span className="list-icon" aria-hidden="true">✓</span>
                  <span>{str}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {summary.improvement_areas.length > 0 && (
          <div className="report-col-box improvements-col">
            <h4 className="col-title">Target Areas for Technical Growth</h4>
            <ul className="report-list">
              {summary.improvement_areas.map((area, idx) => (
                <li key={idx}>
                  <span className="list-icon" aria-hidden="true">•</span>
                  <span>{area}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Recommendations */}
      {summary.recommendations.length > 0 && (
        <div className="report-section recommendations-section">
          <h4 className="section-title">Recommended Next Steps & Study Topics</h4>
          <ul className="recommendations-list">
            {summary.recommendations.map((rec, idx) => (
              <li key={idx}>
                <span className="rec-icon" aria-hidden="true">💡</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="report-actions">
        <button type="button" className="btn-primary-action" onClick={onStartNew}>
          🚀 Start Another Interview
        </button>
        <button type="button" className="btn-secondary-action" onClick={onViewHistory}>
          📋 View All Past Interviews
        </button>
      </div>
    </div>
  );
}
