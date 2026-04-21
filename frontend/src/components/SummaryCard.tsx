interface SummaryCardProps {
  label: string;
  value: string | number;
  tone?: "default" | "warning";
}

export function SummaryCard({ label, value, tone = "default" }: SummaryCardProps) {
  const toneClass =
    tone === "warning"
      ? "border-rose-200 bg-rose-50/70"
      : "border-stone-200 bg-white";
  const valueClass =
    tone === "warning" ? "text-rose-600" : "text-stone-800";
  const labelClass =
    tone === "warning" ? "text-rose-500/80" : "text-stone-500";

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${toneClass}`}>
      <div className={`text-xs font-medium uppercase tracking-wide ${labelClass}`}>
        {label}
      </div>
      <div className={`mt-2 text-3xl font-bold tabular-nums ${valueClass}`}>
        {value}
      </div>
    </div>
  );
}
