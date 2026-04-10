import { useMemo } from "react";
import { hierarchy, treemap } from "d3-hierarchy";
import { interpolateRdYlGn } from "d3-scale-chromatic";
import type { HeatmapRow } from "../api/heatmap";

type Props = {
  rows: HeatmapRow[];
  width: number;
  height: number;
};

// Clamp change percent to ±5% for the color scale. 0.5 is the neutral midpoint
// of interpolateRdYlGn (red → yellow → green).
function colorFor(changePct: number): string {
  const clamped = Math.max(-5, Math.min(5, changePct));
  return interpolateRdYlGn(0.5 + clamped / 10);
}

type Leaf = HeatmapRow & { value: number };
type TreeRoot = { name: "root"; children: Leaf[] };

export default function Heatmap({ rows, width, height }: Props) {
  const layout = useMemo(() => {
    if (rows.length === 0 || width <= 0 || height <= 0) return [];
    const data: TreeRoot = {
      name: "root",
      children: rows.map((r) => ({ ...r, value: r.marketCap })),
    };
    const root = hierarchy<TreeRoot | Leaf>(data, (d) =>
      "children" in d ? (d.children as Leaf[]) : undefined,
    )
      .sum((d) => ("children" in d ? 0 : (d as Leaf).value))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    treemap<TreeRoot | Leaf>().size([width, height]).padding(2).round(true)(root);
    return root.leaves() as unknown as Array<
      Leaf & { x0: number; y0: number; x1: number; y1: number }
    >;
  }, [rows, width, height]);

  return (
    <div className="relative" style={{ width, height }}>
      {layout.map((leaf) => {
        const w = leaf.x1 - leaf.x0;
        const h = leaf.y1 - leaf.y0;
        const bg = colorFor(leaf.changePct);
        const showLabel = w > 40 && h > 28;
        return (
          <div
            key={leaf.symbol}
            className="absolute flex flex-col items-center justify-center overflow-hidden text-center font-mono"
            style={{
              left: leaf.x0,
              top: leaf.y0,
              width: w,
              height: h,
              background: bg,
              color: "#0a0a0a",
            }}
            title={`${leaf.symbol}  ${leaf.changePct.toFixed(2)}%`}
          >
            {showLabel && (
              <>
                <div className="text-xs font-bold leading-tight">{leaf.symbol}</div>
                <div className="text-[10px] leading-tight">
                  {leaf.changePct > 0 ? "+" : ""}
                  {leaf.changePct.toFixed(2)}%
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
