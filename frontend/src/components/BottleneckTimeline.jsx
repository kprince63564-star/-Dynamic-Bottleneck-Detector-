import React, { useMemo } from "react";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

const STATION_COLORS = {
  Cutting: "#4f8cff",
  Assembly: "#a06dff",
  Painting: "#ff8f4f",
  QC: "#ff5c5c",
  Packaging: "#4fd18a",
};

// Renders each snapshot's "current bottleneck station" as a point on a
// timeline -- visually, this produces a step pattern showing exactly when
// the bottleneck moved from one station to another across the shift.
export default function BottleneckTimeline({ timeline, stationNames, currentTime }) {
  const data = useMemo(
    () =>
      timeline.map((point) => ({
        time: point.time,
        station: point.bottleneck,
        y: stationNames.indexOf(point.bottleneck),
      })),
    [timeline, stationNames]
  );

  return (
    <div>
      <ResponsiveContainer width="100%" height={220}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#232c42" />
          <XAxis
            type="number"
            dataKey="time"
            domain={[0, "dataMax"]}
            tick={{ fill: "#8f9bb8", fontSize: 11 }}
            label={{ value: "Shift time (min)", position: "insideBottom", offset: -5, fill: "#8f9bb8", fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[-0.5, stationNames.length - 0.5]}
            ticks={stationNames.map((_, i) => i)}
            tickFormatter={(v) => stationNames[v] || ""}
            tick={{ fill: "#8f9bb8", fontSize: 11 }}
            width={80}
          />
          <Tooltip
            contentStyle={{ background: "#161d2e", border: "1px solid #232c42", fontSize: 12 }}
            formatter={(value, name, props) => [props.payload.station, "Bottleneck"]}
            labelFormatter={(t) => `t = ${t} min`}
          />
          {currentTime != null && (
            <ReferenceLine x={currentTime} stroke="#e8ecf5" strokeDasharray="4 4" />
          )}
          <Scatter data={data}>
            {data.map((entry, i) => (
              <Cell key={`cell-${i}`} fill={STATION_COLORS[entry.station] || "#4f8cff"} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="timeline-legend">
        {stationNames.map((name) => (
          <span key={name}>
            <span className="legend-dot" style={{ background: STATION_COLORS[name] }} />
            {name}
          </span>
        ))}
      </div>
    </div>
  );
}
