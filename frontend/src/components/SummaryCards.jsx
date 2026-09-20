import React from "react";

export default function SummaryCards({ summary }) {
  if (!summary) return null;
  const topStation = summary.recommendation?.station;
  return (
    <div className="summary-cards">
      <div className="summary-card">
        <div className="value">{summary.total_jobs_completed}</div>
        <div className="label">Jobs completed</div>
      </div>
      <div className="summary-card">
        <div className="value">{summary.avg_cycle_time} min</div>
        <div className="label">Avg cycle time</div>
      </div>
      <div className="summary-card">
        <div className="value">{topStation}</div>
        <div className="label">Most frequent bottleneck</div>
      </div>
      <div className="summary-card">
        <div className="value">{summary.recommendation?.time_as_bottleneck_pct}%</div>
        <div className="label">Of shift as bottleneck</div>
      </div>
    </div>
  );
}
