/**
 * Lightweight stub for react-force-graph-2d used in jsdom test environments.
 * The real package draws to canvas via d3-force which jsdom does not support.
 * Tests get a plain <div data-testid="force-graph-2d" />.
 */
export default function ForceGraph2D(props: Record<string, unknown>) {
  return (
    <div
      data-testid="force-graph-2d"
      data-nodes={String((props.graphData as { nodes?: unknown[] })?.nodes?.length ?? 0)}
    />
  );
}
