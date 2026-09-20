# Dynamic Bottleneck Detector (DBD)

**Most factories treat the production bottleneck as fixed. It isn't.**
As product mix, staffing, and machine health shift over a shift, the
station that's actually limiting throughput moves too — but most
scheduling and OEE tools are built around a static assumption. DBD
continuously detects *which station is the current bottleneck*, in
real time, using a transparent Theory-of-Constraints-style algorithm
(not a black-box model), and visualizes exactly when and why it shifts.

Built for [hackathon name] — B.Tech level software project.

---

## What it does

1. **Simulates** an 8-hour shift on a 5-station production line
   (Cutting → Assembly → Painting → QC → Packaging) using discrete-event
   simulation (SimPy). Two product types stress different stations
   differently, and their mix changes over the shift — so the true
   bottleneck genuinely moves, not just synthetically flickers.
2. **Detects** the current bottleneck every 2 simulated minutes using a
   rolling-window score combining utilization, relative queue length,
   and queue-growth rate — explainable, not a black box.
3. **Visualizes** the live production line, a full-shift bottleneck
   timeline (showing exactly when the bottleneck handed off from one
   station to another), and shift-level summary stats.
4. **Answers "what if?"** — pick a station, add capacity, and see the
   predicted effect on cycle time and which station becomes the new
   bottleneck.

## Architecture

```
dbd-project/
├── backend/              FastAPI + SimPy
│   ├── simulation.py      Discrete-event line simulation
│   ├── bottleneck.py      Rolling-window bottleneck-detection algorithm
│   ├── main.py             API endpoints (/api/simulation, /api/summary, /api/whatif)
│   └── requirements.txt
└── frontend/              React + Vite + Recharts
    └── src/
        ├── App.jsx                   Playback loop + layout
        └── components/
            ├── StationFlow.jsx         Live station boxes, bottleneck highlight
            ├── BottleneckTimeline.jsx  Full-shift bottleneck scatter/timeline
            ├── SummaryCards.jsx        Shift stats
            └── WhatIfPanel.jsx         Capacity what-if control
```

**Why precomputed-and-replayed instead of live streaming?** For a demo,
reliability beats real-time purity. The backend runs the full shift
simulation once at startup, computes the entire bottleneck timeline, and
serves it as one payload. The frontend replays it on a timer to *look*
live. This avoids WebSocket flakiness during a live pitch and makes the
demo perfectly reproducible.

## Running it locally

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Backend runs at `http://localhost:8000`. Check `http://localhost:8000/api/health`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173` and proxies `/api/*` calls to the
backend (configured in `vite.config.js`) — no extra setup needed.

Open `http://localhost:5173` and the shift simulation will start
replaying automatically.

## The algorithm (bottleneck.py)

For each station, at each point in time:

```
score = 0.5 × smoothed_utilization
      + 0.3 × normalized_queue_length (relative to other stations right now)
      + 0.2 × queue_growth_rate (rolling window)
```

The station with the highest score is the current bottleneck. Weights
and window size are constants at the top of `bottleneck.py` — deliberately
simple and tunable rather than a trained model, so its behavior is fully
explainable in a demo or to a judge asking "why did it pick that station?"

## What-if endpoint

`POST /api/whatif {"station": "Painting", "extra_capacity": 1}` reruns
the simulation with an extra parallel server at that station and returns
a before/after comparison — average cycle time, jobs completed, and the
new bottleneck distribution. This is what powers the "add a machine
here" slider in the dashboard.

## Possible extensions (mentioned in pitch, not required for demo)

- Swap the SimPy feed for a real MES/SCADA/sensor data stream — the
  detection algorithm is data-source agnostic.
- Add a recommendation ranking across *multiple* what-if scenarios at once.
- Persist shift history to compare bottleneck patterns day-over-day.

## Tech stack

- **Simulation:** Python, SimPy (discrete-event simulation)
- **Backend:** FastAPI, Pydantic, Uvicorn
- **Frontend:** React 18, Vite, Recharts
- **Algorithm:** Rolling-window heuristic scoring (Theory of Constraints)

## License

MIT — see `LICENSE`.
