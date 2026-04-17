interface SummaryCardProps {
  label: string;
  value: string | number;
  tone?: "default" | "warning";
}

export function SummaryCard({ label, value, tone = "default" }: SummaryCardProps) {
  const toneClass =
    tone === "warning"
      ? "bg-red-50 border-red-200 text-red-900"
      : "bg-slate-50 border-slate-200 text-slate-900";
  return (
    <div className={`rounded-lg border p-4 ${toneClass}`}>
      <div className="text-sm font-medium opacity-70">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}
