import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";

type Props = {
  onSubmit: (payload: { symbol: string; condition: "above" | "below"; threshold: number }) => void;
  pending?: boolean;
};

export default function AlertForm({ onSubmit, pending }: Props) {
  const [symbol, setSymbol] = useState("");
  const [condition, setCondition] = useState<"above" | "below">("above");
  const [threshold, setThreshold] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = symbol.trim().toUpperCase();
    const t = parseFloat(threshold);
    if (!trimmed || !Number.isFinite(t) || t <= 0) return;
    onSubmit({ symbol: trimmed, condition, threshold: t });
    setSymbol("");
    setThreshold("");
  };

  return (
    <form onSubmit={submit} className="flex flex-wrap items-center gap-2">
      <input
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        placeholder="Symbol"
        className="w-32 rounded border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm font-mono uppercase focus:border-emerald-500 focus:outline-none"
      />
      <select
        value={condition}
        onChange={(e) => setCondition(e.target.value as "above" | "below")}
        className="rounded border border-zinc-800 bg-zinc-900 px-2 py-2 text-sm focus:border-emerald-500 focus:outline-none"
      >
        <option value="above">above</option>
        <option value="below">below</option>
      </select>
      <input
        value={threshold}
        onChange={(e) => setThreshold(e.target.value)}
        placeholder="Threshold"
        inputMode="decimal"
        className="w-32 rounded border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm font-mono focus:border-emerald-500 focus:outline-none"
      />
      <button
        type="submit"
        disabled={pending}
        className="flex items-center gap-1 rounded bg-emerald-500 px-3 py-2 text-sm font-medium text-zinc-950 hover:bg-emerald-400 disabled:opacity-50"
      >
        <Plus className="h-4 w-4" />
        Add alert
      </button>
    </form>
  );
}
