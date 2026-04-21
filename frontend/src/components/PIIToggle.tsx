interface Props {
  revealed: boolean;
  onToggle: () => void;
  /** Number of items affected by the toggle (optional label). */
  count?: number;
}

/**
 * Toggle + inline warning for revealing original submitter names.
 *
 * Default state shows anonymised handles (Submitter #xxxx). Clicking the
 * toggle reveals the raw names with a visible warning that the user is
 * viewing public-record data and accepts responsibility for its use.
 */
export function PIIToggle({ revealed, onToggle, count }: Props) {
  return (
    <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-xs text-stone-500">
        {revealed
          ? count !== undefined
            ? `Showing ${count} original submitter names (public record).`
            : "Showing original submitter names (public record)."
          : "Submitter names are anonymised by default."}
      </div>
      <button
        type="button"
        onClick={onToggle}
        className={`inline-flex shrink-0 items-center gap-2 self-start rounded-full border px-3 py-1 text-xs font-medium transition sm:self-auto ${
          revealed
            ? "border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100"
            : "border-stone-300 bg-white text-stone-700 hover:bg-stone-100"
        }`}
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            revealed ? "bg-amber-500" : "bg-stone-400"
          }`}
          aria-hidden
        />
        {revealed ? "Hide original names" : "Show original names"}
      </button>
    </div>
  );
}

/** Persistent banner that appears above revealed content. */
export function PIIRevealBanner() {
  return (
    <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-800">
      Original submitter names are public record from Regulations.gov. By
      viewing them you accept responsibility for how you use them.
    </div>
  );
}
