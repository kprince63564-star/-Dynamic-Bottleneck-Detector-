"""
simulation.py
Discrete-event simulation of a multi-station production line using SimPy.

Design goals:
- Multiple sequential stations (a simple flow line).
- Each station has a base processing time that varies stochastically.
- Product mix changes over the shift (Product A vs Product B), and each
  product stresses different stations differently -- this is what makes
  the real bottleneck MOVE over time instead of staying fixed.
- Random slowdown events (simulating minor stoppages / degraded performance)
  are injected at random stations at random times.
- Every SNAPSHOT_INTERVAL minutes, we record per-station queue length,
  utilization, and cumulative throughput. This snapshot log is the raw
  data the bottleneck-detection algorithm (bottleneck.py) consumes.

Run standalone with `python simulation.py` to generate simulation_data.json.
"""

import json
import random
import simpy

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STATIONS = ["Cutting", "Assembly", "Painting", "QC", "Packaging"]

# Base processing time (minutes) per station, per product type.
# Product B deliberately stresses Painting + QC harder than Product A,
# and Product A stresses Cutting + Assembly harder -- this asymmetry is
# what causes the bottleneck to shift as product mix changes over the shift.
BASE_TIMES = {
    "A": {"Cutting": 3.2, "Assembly": 4.0, "Painting": 2.5, "QC": 2.0, "Packaging": 1.8},
    "B": {"Cutting": 2.0, "Assembly": 2.5, "Painting": 4.5, "QC": 4.2, "Packaging": 1.8},
}

SHIFT_LENGTH_MIN = 480          # 8-hour shift, simulated in minutes
SNAPSHOT_INTERVAL = 2           # record stats every 2 sim-minutes
ARRIVAL_INTERVAL_MEAN = 3.0     # mean minutes between new jobs entering the line

# Product mix schedule: which product is dominant during which portion
# of the shift. (start_min, end_min, probability_of_product_B)
MIX_SCHEDULE = [
    (0, 150, 0.2),     # early shift: mostly Product A
    (150, 300, 0.8),   # mid shift: mostly Product B  -> stresses Painting/QC
    (300, 480, 0.5),   # late shift: mixed
]

random.seed(42)  # reproducible demo run


def product_mix_prob(t):
    for start, end, prob_b in MIX_SCHEDULE:
        if start <= t < end:
            return prob_b
    return 0.5


class Station:
    """A single station in the line: a SimPy resource plus running stats."""

    def __init__(self, env, name, capacity=1):
        self.env = env
        self.name = name
        self.resource = simpy.Resource(env, capacity=capacity)
        self.busy_time = 0.0
        self.jobs_completed = 0
        self.total_wait_time = 0.0
        self.queue_len_samples = []
        self.slowdown_factor = 1.0   # >1 means running slower than normal
        self.slowdown_until = 0.0

    def maybe_apply_slowdown(self):
        """Randomly degrade this station's speed for a period (simulates
        minor mechanical issues, material feed problems, etc.)."""
        if self.env.now >= self.slowdown_until and random.random() < 0.004:
            self.slowdown_factor = random.uniform(1.4, 2.2)
            duration = random.uniform(8, 25)
            self.slowdown_until = self.env.now + duration
        elif self.env.now >= self.slowdown_until:
            self.slowdown_factor = 1.0


def job_process(env, job_id, product, stations, stats):
    """A single job's journey through every station in sequence."""
    arrival_time = env.now
    for station in stations:
        queue_join_time = env.now
        with station.resource.request() as req:
            station.queue_len_samples.append((env.now, len(station.resource.queue)))
            yield req
            wait = env.now - queue_join_time
            station.total_wait_time += wait

            station.maybe_apply_slowdown()
            base = BASE_TIMES[product][station.name]
            proc_time = max(0.2, random.gauss(base, base * 0.15)) * station.slowdown_factor

            start = env.now
            yield env.timeout(proc_time)
            station.busy_time += env.now - start
            station.jobs_completed += 1

    stats["completed_jobs"].append({
        "job_id": job_id,
        "product": product,
        "arrival": round(arrival_time, 2),
        "completion": round(env.now, 2),
        "cycle_time": round(env.now - arrival_time, 2),
    })


def job_generator(env, stations, stats):
    job_id = 0
    while True:
        yield env.timeout(random.expovariate(1.0 / ARRIVAL_INTERVAL_MEAN))
        if env.now > SHIFT_LENGTH_MIN:
            break
        product = "B" if random.random() < product_mix_prob(env.now) else "A"
        env.process(job_process(env, job_id, product, stations, stats))
        job_id += 1


def snapshot_recorder(env, stations, snapshots):
    """Every SNAPSHOT_INTERVAL minutes, record each station's queue length
    and utilization *since the previous snapshot* (windowed utilization,
    not cumulative -- this is what lets the bottleneck move over time)."""
    prev_busy = {s.name: 0.0 for s in stations}
    prev_t = 0.0
    while True:
        yield env.timeout(SNAPSHOT_INTERVAL)
        t = env.now
        window = t - prev_t
        station_snap = []
        for s in stations:
            busy_delta = s.busy_time - prev_busy[s.name]
            capacity = s.resource.capacity
            util = min(1.0, busy_delta / (window * capacity)) if window > 0 else 0.0
            queue_len = len(s.resource.queue)
            station_snap.append({
                "name": s.name,
                "utilization": round(util, 3),
                "queue_length": queue_len,
                "jobs_completed": s.jobs_completed,
            })
            prev_busy[s.name] = s.busy_time
        snapshots.append({"time": round(t, 1), "stations": station_snap})
        prev_t = t


def run_simulation(capacity_overrides=None):
    """Run the full shift simulation.

    capacity_overrides: optional dict like {"Painting": 2} to give a
    station extra parallel capacity -- used by the /api/whatif endpoint
    to answer "what if we added a machine/worker to station X?".
    """
    env = simpy.Environment()
    stations = []
    for name in STATIONS:
        cap = 1
        if capacity_overrides and name in capacity_overrides:
            cap = capacity_overrides[name]
        stations.append(Station(env, name, capacity=cap))

    stats = {"completed_jobs": []}
    snapshots = []

    env.process(job_generator(env, stations, stats))
    env.process(snapshot_recorder(env, stations, snapshots))
    env.run(until=SHIFT_LENGTH_MIN)

    return {
        "stations": STATIONS,
        "snapshots": snapshots,
        "completed_jobs": stats["completed_jobs"],
        "shift_length": SHIFT_LENGTH_MIN,
        "snapshot_interval": SNAPSHOT_INTERVAL,
    }


if __name__ == "__main__":
    data = run_simulation()
    with open("simulation_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Simulated {len(data['completed_jobs'])} jobs across "
          f"{len(data['snapshots'])} snapshots. Saved simulation_data.json")
