import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GraphPage } from "../src/pages/GraphPage";

const graphResp = {
  nodes: [
    { id: "docket-1", label: "EPA-HQ-OAR-2021-0317", type: "docket", count: 3 },
    { id: "reg-1", label: "40 CFR 50.6", type: "regulation", count: 2 },
    { id: "reg-2", label: "42 U.S.C. 7408", type: "regulation", count: 1 },
  ],
  links: [
    { source: "docket-1", target: "reg-1", value: 2 },
    { source: "docket-1", target: "reg-2", value: 1 },
  ],
};

function mockFetch(url: string): Promise<Response> {
  if (url.includes("/graph/")) {
    return Promise.resolve(
      new Response(JSON.stringify(graphResp), { status: 200 }),
    );
  }
  if (url.includes("/dockets")) {
    return Promise.resolve(
      new Response(JSON.stringify({ items: [], total: 0, limit: 8, offset: 0 }), { status: 200 }),
    );
  }
  return Promise.resolve(new Response("not found", { status: 404 }));
}

describe("GraphPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(mockFetch));
  });

  it("renders the search form", () => {
    render(<MemoryRouter><GraphPage /></MemoryRouter>);
    expect(screen.getByPlaceholderText(/Enter docket ID/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });

  it("Search button is disabled when input is empty", () => {
    render(<MemoryRouter><GraphPage /></MemoryRouter>);
    expect(screen.getByRole("button", { name: "Search" })).toBeDisabled();
  });

  it("renders ForceGraph2D after a successful search", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><GraphPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "EPA-HQ-OAR-2021-0317");
    await user.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      expect(screen.getByTestId("force-graph-2d")).toBeInTheDocument();
    });
  });

  it("shows the top cited regulations list", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><GraphPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "EPA-HQ-OAR-2021-0317");
    await user.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      expect(screen.getByText("40 CFR 50.6")).toBeInTheDocument();
    });
    expect(screen.getByText("42 U.S.C. 7408")).toBeInTheDocument();
    expect(screen.getByText("2 comments")).toBeInTheDocument();
    expect(screen.getByText("1 comments")).toBeInTheDocument();
  });

  it("shows unique regulation count in legend", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><GraphPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "EPA-HQ-OAR-2021-0317");
    await user.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      expect(screen.getByText(/2 unique/)).toBeInTheDocument();
    });
  });

  it("shows empty state when no citations found", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(new Response(JSON.stringify({ nodes: [], links: [] }), { status: 200 })),
      ),
    );
    const user = userEvent.setup();
    render(<MemoryRouter><GraphPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "EMPTY");
    await user.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      expect(screen.getByText(/No citations found/)).toBeInTheDocument();
    });
  });

  it("shows error when API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(new Response("boom", { status: 500, statusText: "err" })),
      ),
    );
    const user = userEvent.setup();
    render(<MemoryRouter><GraphPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "BAD");
    await user.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => {
      expect(screen.getByText(/API error 500/)).toBeInTheDocument();
    });
  });

  it("pre-fills docket ID from ?docket= URL param", () => {
    render(
      <MemoryRouter initialEntries={["/graph?docket=EPA-HQ-OAR-2021-0317"]}>
        <GraphPage />
      </MemoryRouter>,
    );
    expect(screen.getByPlaceholderText(/Enter docket ID/)).toHaveValue("EPA-HQ-OAR-2021-0317");
  });
});
