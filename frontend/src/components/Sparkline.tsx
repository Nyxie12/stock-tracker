import { Line, LineChart, ResponsiveContainer } from "recharts";

type Props = {
  data: number[];
  changePct: number | null | undefined;
  width?: number;
  height?: number;
};

export default function Sparkline({ data, changePct, width = 120, height = 32 }: Props) {
  if (data.length < 2) {
    return <div style={{ width, height }} className="opacity-30" />;
  }
  const color = (changePct ?? 0) >= 0 ? "#34d399" : "#fb7185";
  const points = data.map((value, index) => ({ index, value }));
  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points}>
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
