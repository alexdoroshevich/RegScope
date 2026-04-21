import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DocketsPage } from "../src/pages/DocketsPage";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const twoItems = {
  items: [
    { docket_id: "EPA-HQ-OAR-2021-0317", comment_count: 3 },
    { docket_id: "OTHER-DOCKET", comment_count: 1 },
  ],
  total: 2,
  limit: 20,
  offset: 0,
};

const filteredItems = {
  items: [{ docket_id: "EPA-HQ-OAR-2021-0317", comment_count: 3 }],
  total: 1,
  limit: 20,
  offset: 0,
};

const emptyResp = { items: [], total: 0, limit: 20, offset: 0 };

function mockFetch(url: string): Promise<Response> {
  const params = new URL(url, "http://localhost").searchParams;
  const q = params.get("q");
  if (q === "EPA") {
    return Promise.resolve(
      new Response(JSON.stringify(filteredItems), { status: 200 }),
    );
  }
  if (q === "NOMATCH") {
    return Promise.resolve(new Response(JSON.stringify(emptyResp), { status: 200 }));
  }
  return Promise.resolve(new Response(JSON.stringify(twoItems), { status: 200 }));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("DocketsPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(mockFetch));
  });

  it("renders the page heading and search form", async () => {
    render(<MemoryRouter><DocketsPage /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Dockets" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Search by docket ID/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });

  it("loads and displays dockets on mount", async () => {
    render(<MemoryRouter><DocketsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText("EPA-HQ-OAR-2021-0317")).toBeInTheDocument();
    });
    expect(screen.getByText("OTHER-DOCKET")).toBeInTheDocument();
    expect(screen.getByText("3 comments")).toBeInTheDocument();
    expect(screen.getByText("1 comments")).toBeInTheDocument();
  });

  it("shows total docket count", async () => {
    render(<MemoryRouter><DocketsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText("2 total")).toBeInTheDocument();
    });
  });

  it("shows Clusters, Graph, and Ask links for each docket", async () => {
    render(<MemoryRouter><DocketsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText("EPA-HQ-OAR-2021-0317")).toBeInTheDocument();
    });
    const clusterLinks = screen.getAllByRole("link", { name: "Clusters" });
    const graphLinks = screen.getAllByRole("link", { name: "Graph" });
    const askLinks = screen.getAllByRole("link", { name: "Ask" });
    expect(clusterLinks).toHaveLength(2);
    expect(graphLinks).toHaveLength(2);
    expect(askLinks).toHaveLength(2);
  });

  it("Clusters link has correct href", async () => {
    render(<MemoryRouter><DocketsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText("EPA-HQ-OAR-2021-0317")).toBeInTheDocument();
    });
    const clustersLinks = screen.getAllByRole("link", { name: "Clusters" });
    expect(clustersLinks[0]).toHaveAttribute(
      "href",
      "/clusters?docket=EPA-HQ-OAR-2021-0317",
    );
  });

  it("filters dockets by search query", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><DocketsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText("EPA-HQ-OAR-2021-0317")).toBeInTheDocument();
    });

    await user.clear(screen.getByPlaceholderText(/Search by docket ID/));
    await user.type(screen.getByPlaceholderText(/Search by docket ID/), "EPA");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.queryByText("OTHER-DOCKET")).not.toBeInTheDocument();
    });
    expect(screen.getByText("EPA-HQ-OAR-2021-0317")).toBeInTheDocument();
  });

  it("shows empty state when no dockets match search", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><DocketsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText("EPA-HQ-OAR-2021-0317")).toBeInTheDocument();
    });

    await user.clear(screen.getByPlaceholderText(/Search by docket ID/));
    await user.type(screen.getByPlaceholderText(/Search by docket ID/), "NOMATCH");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText(/No dockets matching/)).toBeInTheDocument();
    });
  });

  it("shows error message when API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(new Response("boom", { status: 500, statusText: "Server Error" })),
      ),
    );
    render(<MemoryRouter><DocketsPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText(/API error 500/)).toBeInTheDocument();
    });
  });
});
