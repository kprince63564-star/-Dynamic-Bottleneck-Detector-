import React, { useEffect, useMemo, useRef, useState } from "react";
import StationFlow from "./components/StationFlow.jsx";
import BottleneckTimeline from "./components/BottleneckTimeline.jsx";
import SummaryCards from "./components/SummaryCards.jsx";
import WhatIfPanel from "./components/WhatIfPanel.jsx";
import { apiUrl } from "./api.js";

const PLAYBACK_MS_PER_STEP = 120; // how fast the replay steps through snapshots

export default function App() {
  const [sim, setSim] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const intervalRef = useRef(null);

  useEffect(() => {
    Promise.all([
      fetch(apiUrl("/api/simulation")).then((r) => {
        if (!r.ok) throw new Error("Could not reach backend at /api/simulation");
        return r.json();
      }),
      fetch(apiUrl("/api/summary")).then((r) => r.json()),
    ])
      .then(([simData, summaryData]) => {
        setSim(simData);
        setSummary(summaryData);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!sim || !playing) return;
    intervalRef.current = setInterval(() => {
      setStepIndex((i) => {
        if (i >= sim.snapshots.length - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, PLAYBACK_MS_PER_STEP);
    return () => clearInterval(intervalRef.current);
  }, [sim, playing]);

  const currentSnapshot = useMemo(() => {
    if (!sim) return null;
    return sim.snapshots[stepIndex];
  }, [sim, stepIndex]);

  const currentBottleneckPoint = useMemo(() => {
    if (!sim) return null;
    return sim.bottleneck_timeline[stepIndex];
  }, [sim, stepIndex]);

  if (error) {
    return (
      <div className="app">
        <div className="error">
          <strong>Couldn't load simulation data.</strong>
          <br />
          {error}
          <br />
          <br />
          Make sure the backend is running: <code>cd backend && uvicorn main:app --reload</code>
        </div>
      </div>
    );
  }

  if (!sim || !currentSnapshot) {
    return (
      <div className="app">
        <div className="loading">Loading shift simulation…</div>
      </div>
    );
  }

  const progressPct = Math.round((stepIndex / (sim.snapshots.length - 1)) * 100);

  return (
    <div className="app">
      <div className="header">
        <div>
          <h1>Dynamic Bottleneck Detector</h1>
          <p>
            Live view of an 8-hour shift · t = {currentSnapshot.time} min ·{" "}
            {progressPct}% through shift
          </p>
        </div>
        <div className="controls">
          <button className="btn secondary" onClick={() => setStepIndex(0)}>
            Restart
          </button>
          <button className="btn" onClick={() => setPlaying((p) => !p)}>
            {playing ? "Pause" : "Play"}
          </button>
        </div>
      </div>

      <div className="panel">
        <h2>Production line — current state</h2>
        <StationFlow
          stations={currentSnapshot.stations}
          currentBottleneck={currentBottleneckPoint?.bottleneck}
        />
      </div>

      <div className="grid-2">
        <div className="panel">
          <h2>Bottleneck shift timeline (whole shift)</h2>
          <BottleneckTimeline
            timeline={sim.bottleneck_timeline}
            stationNames={sim.stations}
            currentTime={currentSnapshot.time}
          />
        </div>
        <div className="panel">
          <h2>Shift summary</h2>
          <SummaryCards summary={summary} />
        </div>
      </div>

      <WhatIfPanel stations={sim.stations} />
    </div>
  );
}
