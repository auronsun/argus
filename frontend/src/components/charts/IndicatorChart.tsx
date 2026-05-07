import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, ReferenceLine } from "recharts";

export function RSIChart({ data, height = 140 }: { data: any[]; height?: number }) {
  const cleaned = data.filter((d) => d.rsi_14 !== null && d.rsi_14 !== undefined).slice(-180);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={cleaned}>
        <XAxis dataKey="time" hide />
        <YAxis domain={[0, 100]} stroke="#52525b" fontSize={10} width={28} />
        <Tooltip
          contentStyle={{ background: "#0e1018", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11 }}
          labelFormatter={(l) => String(l).slice(0, 10)}
        />
        <ReferenceLine y={70} stroke="#f43f5e" strokeDasharray="3 3" />
        <ReferenceLine y={30} stroke="#10b981" strokeDasharray="3 3" />
        <Line type="monotone" dataKey="rsi_14" stroke="#06b6d4" dot={false} strokeWidth={1.5} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function MACDChart({ data, height = 140 }: { data: any[]; height?: number }) {
  const cleaned = data.filter((d) => d.macd !== null && d.macd !== undefined).slice(-180);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={cleaned}>
        <XAxis dataKey="time" hide />
        <YAxis stroke="#52525b" fontSize={10} width={36} />
        <Tooltip
          contentStyle={{ background: "#0e1018", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11 }}
          labelFormatter={(l) => String(l).slice(0, 10)}
        />
        <ReferenceLine y={0} stroke="#3f3f46" />
        <Line type="monotone" dataKey="macd" stroke="#7c3aed" dot={false} strokeWidth={1.5} />
        <Line type="monotone" dataKey="macd_signal" stroke="#f59e0b" dot={false} strokeWidth={1.5} />
      </LineChart>
    </ResponsiveContainer>
  );
}
