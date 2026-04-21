import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";

describe("App", () => {
  beforeEach(() => {
    // HomePage fetches top dockets on mount; return empty list to keep tests simple.
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({ items: [], total: 0, limit: 5, offset: 0 }),
            { status: 200 },
          ),
        ),
      ),
    );
  });
  it("renders the home page at /", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: /Regulatory intelligence/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/FedComment/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Astroturf Detector/)).toBeInTheDocument();
    expect(screen.getByText(/Comment Clusters/)).toBeInTheDocument();
  });

  it("renders the top nav with all feature links", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    const links = screen.getAllByRole("link");
    const hrefs = links.map((l) => l.getAttribute("href"));
    expect(hrefs).toContain("/astroturf");
    expect(hrefs).toContain("/clusters");
    expect(hrefs).toContain("/graph");
  });
});
