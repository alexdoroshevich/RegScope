/**
 * Lightweight stub for react-force-graph used in jsdom test environments.
 * The real package bundles three.js + WebGL which cannot run in jsdom.
 * Tests that import ForceGraph2D get a plain <div data-testid="force-graph-2d" />.
 */
export function ForceGraph2D(props: Record<string, unknown>) {
  return <div data-testid="force-graph-2d" data-nodes={String(props.graphData)} />;
}
