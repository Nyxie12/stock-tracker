import type { Timeframe } from "../api/candles";

const OPTIONS: Timeframe[] = ["1D", "1W", "1M", "1Y"];

type Props = {
  value: Timeframe;
  onChange: (tf: Timeframe) => void;
};

export default function TimeframeToggle({ value, onChange }: Props) {
  return (
    <div className="inline-flex overflow-hidden rounded border border-zinc-800 bg-zinc-900">
      {OPTIONS.map((tf) => (
        <button
          key={tf}
          onClick={() => onChange(tf)}
          className={`px-3 py-1 text-xs font-medium transition-colors ${
            value === tf ? "bg-emerald-500 text-zinc-950" : "text-zinc-400 hover:bg-zinc-800"
          }`}
        >
          {tf}
        </button>
      ))}
    </div>
  );
}
