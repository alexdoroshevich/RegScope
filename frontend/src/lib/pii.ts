/**
 * PII redaction helpers.
 *
 * Regulations.gov exposes submitter names on every public comment. The names
 * are technically public record, but re-publishing them on a third-party site
 * creates GDPR / CCPA / reputation / defamation exposure. Default-hide turns
 * the display into a stable pseudonym derived from the comment_id; users who
 * need the real names must opt in via a per-page toggle.
 */

/** Deterministic FNV-1a → 4-hex-char short id. Collisions are OK — this
 * is for display, not uniqueness guarantees. */
function hash4(input: string): string {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(16).padStart(8, "0").slice(0, 4);
}

/** Stable opaque handle for a comment — "Submitter #a3f2". */
export function anonymizeSubmitter(commentId: string): string {
  return `Submitter #${hash4(commentId)}`;
}

/**
 * Resolve the display name for a submitter given the current reveal state.
 *
 * Returns the real name only when `reveal` is true AND a real name exists.
 * Otherwise returns the deterministic anonymised handle.
 */
export function formatSubmitter(
  name: string | null | undefined,
  commentId: string,
  reveal: boolean,
): string {
  if (reveal && name && name.trim() !== "") return name;
  return anonymizeSubmitter(commentId);
}
