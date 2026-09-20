import React, { useState } from "react";
import { apiUrl } from "../api.js";

export default function WhatIfPanel({ stations }) {
  const [station, setStation] = useState(stations[0] || "");
  const [extraCapacity, setExtraCapacity] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runWhatIf = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(apiUrl("/api/whatif"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ station, extra_capacity: Number(extraCapacity) }),
      });
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e.message || "Failed to run what-if simulation");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2>What-if: add capacity</h2>
      <div className="whatif-row">
        <select value={station} onChange={(e) => setStation(e.target.value)}>
          {stations.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          type="number"
          min="1"
          max="3"
          value={extraCapacity}
          onChange={(e) => setExtraCapacity(e.target.value)}
          style={{ width: 70 }}
        />
        <span style={{ color: "var(--text-dim)", fontSize: 13 }}>extra parallel capacity</span>
        <button className="btn" onClick={runWhatIf} disabled={loading}>
          {loading ? "Simulating..." : "Run what-if"}
        </button>
      </div>

      {error && <div className="error" style={{ padding: "10px 0" }}>{error}</div>}

      {result && !error && (
        <div className="result-box">
          Adding <strong>{result.extra_capacity}</strong> extra capacity to{" "}
          <strong>{result.station}</strong> changes average cycle time from{" "}
          <strong>{result.baseline.avg_cycle_time} min</strong> to{" "}
          <strong>{result.with_change.avg_cycle_time} min</strong>
          {" "}({result.cycle_time_improvement_pct > 0 ? "-" : "+"}
          {Math.abs(result.cycle_time_improvement_pct)}%).
          <br />
          New most-frequent bottleneck:{" "}
          <strong>{result.new_recommendation.station}</strong> (
          {result.new_recommendation.time_as_bottleneck_pct}% of shift).
        </div>
      )}
    </div>
  );
}
