"""
bottleneck.py
Turns raw per-station snapshot data (queue length + utilization over time)
into a continuously-updated "which station is the bottleneck right now"
signal, plus a full timeline of how the bottleneck moved across the shift.

Approach (lightweight Theory-of-Constraints heuristic -- deliberately NOT
a black-box ML model, so behaviour is transparent and explainable in a
demo/pitch):

For each station, at each snapshot time t, compute a bottleneck score:

    score = w1 * utilization
          + w2 * normalized_queue_length
          + w3 * queue_growth_rate (over the last ROLLING_WINDOW snapshots)

The station with the highest score at time t is the current bottleneck.
We also smooth scores with a rolling average so the detector doesn't
flicker between stations on every single noisy snapshot.
"""

ROLLING_WINDOW = 5   # number of snapshots to look back for trend/smoothing
W_UTIL = 0.5
W_QUEUE = 0.3
W_GROWTH = 0.2


def _normalize(values):
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def compute_bottleneck_timeline(sim_data):
    snapshots = sim_data["snapshots"]
    station_names = sim_data["stations"]

    # Build per-station time series of utilization and queue length
    util_series = {name: [] for name in station_names}
    queue_series = {name: [] for name in station_names}
    times = []

    for snap in snapshots:
        times.append(snap["time"])
        by_name = {s["name"]: s for s in snap["stations"]}
        for name in station_names:
            util_series[name].append(by_name[name]["utilization"])
            queue_series[name].append(by_name[name]["queue_length"])

    n = len(times)
    timeline = []
    score_history = {name: [] for name in station_names}

    for i in range(n):
        window_start = max(0, i - ROLLING_WINDOW + 1)

        # Normalize queue lengths *across stations at this instant* so a
        # station with a naturally longer queue doesn't always win.
        instant_queues = [queue_series[name][i] for name in station_names]
        norm_queues = _normalize(instant_queues)

        scores = {}
        for idx, name in enumerate(station_names):
            util = util_series[name][i]

            # Rolling average utilization for smoothing
            util_window = util_series[name][window_start:i + 1]
            smooth_util = sum(util_window) / len(util_window)

            # Queue growth rate over the window (positive = building up)
            q_window = queue_series[name][window_start:i + 1]
            growth = (q_window[-1] - q_window[0]) / max(1, len(q_window) - 1) if len(q_window) > 1 else 0.0
            growth_norm = max(0.0, min(1.0, growth / 3.0))  # clamp/scale

            score = (W_UTIL * smooth_util) + (W_QUEUE * norm_queues[idx]) + (W_GROWTH * growth_norm)
            scores[name] = round(score, 4)
            score_history[name].append(score)

        bottleneck_station = max(scores, key=scores.get)
        timeline.append({
            "time": times[i],
            "bottleneck": bottleneck_station,
            "scores": scores,
        })

    # Summarize: how much total time (snapshots) each station spent as
    # the bottleneck, and the ordered list of bottleneck "shift events"
    shifts = []
    prev = None
    for point in timeline:
        if point["bottleneck"] != prev:
            shifts.append({"time": point["time"], "new_bottleneck": point["bottleneck"]})
            prev = point["bottleneck"]

    time_share = {name: 0 for name in station_names}
    for point in timeline:
        time_share[point["bottleneck"]] += 1
    total = len(timeline) or 1
    time_share_pct = {name: round(100 * c / total, 1) for name, c in time_share.items()}

    return {
        "timeline": timeline,
        "shift_events": shifts,
        "time_share_pct": time_share_pct,
    }


def recommend_action(bottleneck_summary, station_names):
    """Very simple heuristic recommendation: whichever station spent the
    most time as bottleneck is the best candidate for added capacity."""
    share = bottleneck_summary["time_share_pct"]
    top_station = max(share, key=share.get)
    return {
        "station": top_station,
        "time_as_bottleneck_pct": share[top_station],
        "recommendation": (
            f"{top_station} was the bottleneck {share[top_station]}% of the shift. "
            f"Adding capacity (an extra machine/shift/worker) here would likely "
            f"yield the largest throughput improvement."
        ),
    }
