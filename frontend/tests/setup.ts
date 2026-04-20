// Stub AFRAME global required by aframe-extras, a transitive dep of react-force-graph.
// aframe-extras reads AFRAME at module-load time; jsdom doesn't provide it.
// This assignment must appear in a setupFile so it runs before test module imports.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).AFRAME = {
  registerComponent: () => {},
  registerGeometry: () => {},
  registerPrimitive: () => {},
  registerShader: () => {},
  registerSystem: () => {},
  utils: { coordinates: {}, entity: {} },
  THREE: {},
};

import "@testing-library/jest-dom/vitest";
