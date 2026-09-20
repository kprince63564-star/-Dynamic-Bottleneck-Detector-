"""
main.py
FastAPI backend for the Dynamic Bottleneck Detector.

Design choice for a hackathon-friendly, reliable demo:
We run the full shift simulation ONCE at startup (and on-demand for the
what-if endpoint), then serve the complete precomputed timeline to the
frontend. The frontend replays it on a timer (setInterval) to create a
"live" feel, without needing WebSockets or real-time streaming -- this
is far more robust for a live demo (no dropped connections, fully
reproducible, works offline).

Endpoints:
    GET  /api/simulation      -> full snapshot + bottleneck timeline
    GET  /api/summary         -> time-share % per station + recommendation
    POST /api/whatif          -> rerun sim with a capacity override, return
                                  the new time-share summary for comparison
    GET  /api/health          -> simple healthcheck
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict

from simulation import run_simulation, STATIONS
from bottleneck import compute_bottleneck_timeline, recommend_action

app = FastAPI(title="Dynamic Bottleneck Detector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon demo: keep it open; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Run the baseline simulation once at startup and cache the result.
# ---------------------------------------------------------------------------
_baseline_sim = run_simulation()
_baseline_bottleneck = compute_bottleneck_timeline(_baseline_sim)
_baseline_recommendation = recommend_action(_baseline_bottleneck, STATIONS)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/simulation")
def get_simulation():
    """Full dataset the frontend needs to animate the shift:
    per-snapshot station stats + the bottleneck at each point in time."""
    return {
        "stations": _baseline_sim["stations"],
        "shift_length": _baseline_sim["shift_length"],
        "snapshot_interval": _baseline_sim["snapshot_interval"],
        "snapshots": _baseline_sim["snapshots"],
        "bottleneck_timeline": _baseline_bottleneck["timeline"],
        "shift_events": _baseline_bottleneck["shift_events"],
    }


@app.get("/api/summary")
def get_summary():
    return {
        "time_share_pct": _baseline_bottleneck["time_share_pct"],
        "recommendation": _baseline_recommendation,
        "total_jobs_completed": len(_baseline_sim["completed_jobs"]),
        "avg_cycle_time": round(
            sum(j["cycle_time"] for j in _baseline_sim["completed_jobs"])
            / max(1, len(_baseline_sim["completed_jobs"])), 2
        ),
    }


class WhatIfRequest(BaseModel):
    station: str
    extra_capacity: int = 1  # additional parallel capacity to add


@app.post("/api/whatif")
def whatif(req: WhatIfRequest):
    """Rerun the simulation with extra capacity at one station and return
    a comparison against the baseline -- powers the 'what if we add a
    machine/worker here?' slider in the dashboard."""
    if req.station not in STATIONS:
        return {"error": f"Unknown station '{req.station}'. Valid: {STATIONS}"}

    overrides = {req.station: 1 + max(0, req.extra_capacity)}
    sim = run_simulation(capacity_overrides=overrides)
    bottleneck = compute_bottleneck_timeline(sim)
    recommendation = recommend_action(bottleneck, STATIONS)

    avg_cycle_baseline = round(
        sum(j["cycle_time"] for j in _baseline_sim["completed_jobs"])
        / max(1, len(_baseline_sim["completed_jobs"])), 2
    )
    avg_cycle_new = round(
        sum(j["cycle_time"] for j in sim["completed_jobs"])
        / max(1, len(sim["completed_jobs"])), 2
    )

    return {
        "station": req.station,
        "extra_capacity": req.extra_capacity,
        "baseline": {
            "time_share_pct": _baseline_bottleneck["time_share_pct"],
            "avg_cycle_time": avg_cycle_baseline,
            "jobs_completed": len(_baseline_sim["completed_jobs"]),
        },
        "with_change": {
            "time_share_pct": bottleneck["time_share_pct"],
            "avg_cycle_time": avg_cycle_new,
            "jobs_completed": len(sim["completed_jobs"]),
        },
        "cycle_time_improvement_pct": round(
            100 * (avg_cycle_baseline - avg_cycle_new) / avg_cycle_baseline, 1
        ) if avg_cycle_baseline > 0 else 0,
        "new_recommendation": recommendation,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
