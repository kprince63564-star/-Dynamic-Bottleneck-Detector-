import React from "react";

function utilColor(util) {
  if (util >= 0.8) return "var(--danger)";
  if (util >= 0.55) return "var(--warn)";
  return "var(--ok)";
}

export default function StationFlow({ stations, currentBottleneck }) {
  return (
    <div className="station-flow">
      {stations.map((s) => {
        const isBottleneck = s.name === currentBottleneck;
        return (
          <div
            key={s.name}
            className={`station-box ${isBottleneck ? "bottleneck" : ""}`}
          >
            <div className="station-name">
              {s.name}
              {isBottleneck && <span className="tag">BOTTLENECK</span>}
            </div>
            <div className="stat-row">
              <span>Utilization</span>
              <span>{Math.round(s.utilization * 100)}%</span>
            </div>
            <div className="util-bar-track">
              <div
                className="util-bar-fill"
                style={{
                  width: `${Math.round(s.utilization * 100)}%`,
                  background: utilColor(s.utilization),
                }}
              />
            </div>
            <div className="stat-row">
              <span>Queue</span>
              <span>{s.queue_length}</span>
            </div>
            <div className="stat-row">
              <span>Completed</span>
              <span>{s.jobs_completed}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
