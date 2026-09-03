import type { WSA } from "@/api/wsa";

const riskOrder: Record<WSA["risk_level"], number> = { high: 0, medium: 1, low: 2 };

// the default WSA shown on load should be the one most worth looking at,
// not just whichever name sorts first alphabetically (punctuation like "!"
// sorts before letters, so a name like "!Kai! Garib LM" would otherwise
// always win regardless of its actual risk)
export function pickDefaultWsa(wsas: WSA[]): WSA | null {
  return [...wsas].sort((a, b) => riskOrder[a.risk_level] - riskOrder[b.risk_level] || a.name.localeCompare(b.name))[0] ?? null;
}
