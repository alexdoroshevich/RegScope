import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GraphPage } from "../src/pages/GraphPage";

const graphResp = {
  nodes: [
    { id: "DEMO-2024-0001", label: "DEMO-2024-0001", type: "docket", count: 5 },
    { id: "40 CFR 50", label: "40 CFR 50", type: "regulation", count: 4 },
    { id: "42 U.S.C. 7409", label: "42 U.S.C. 7409", type: "regulation", count: 2 },
  ],
  links: [
    { source: "DEMO-2024-0001", target: "40 CFR 50", value: 4 },
    { source: "DEMO-2024-0001", target: "42 U.S.C. 7409", value: 2 },
  ],
};

const emptyGraphResp = { nodes: [], links: [] };

function mockFetch(url: string): Promise<Response> {
  if (url.includes("/graph/DEMO-2024-0001")) {
    return Promise.resolve(
      new Response(JSON.stringify(graphResp), { status: 200 }),
    );
  }
  if (url.includes("/graph/EMPTY")) {
    return Promise.resolve(
      new Response(JSON.stringify(emptyGraphResp), { status: 200 }),
    );
  }
  return Promise.resolve(new Response("not found", { status: 404 }));
}

describe("GraphPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(mockFetch));
  });

  it("renders the search form", () => {
    render(<GraphPage />);
    expect(screen.getByPlaceholderText(/Enter docket ID/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
    expect(screen.getByText("Citation Graph")).toBeInTheDocument();
  });

  it("Search button is disabled when input is empty", () => {
    render(<GraphPage />);
    expect(screen.getByRole("button", { name: "Search" })).toBeDisabled();
  });

  it("shows the force graph canvas and top-citations list after searching", async () => {
    const user = userEvent.setup();
    render(<GraphPage />);

    await user.type(
      screen.getByPlaceholderText(/Enter docket ID/),
      "DEMO-2024-0001",
    );
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByTestId("force-graph-2d")).toBeInTheDocument();
    });
    expect(screen.getByText("Top cited regulations")).toBeInTheDocument();
  });

  it("lists regulation nodes with label and comment count", async () => {
    const user = userEvent.setup();
    render(<GraphPage />);

    await user.type(
      screen.getByPlaceholderText(/Enter docket ID/),
      "DEMO-2024-0001",
    );
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("40 CFR 50")).toBeInTheDocument();
    });
    expect(screen.getByText("42 U.S.C. 7409")).toBeInTheDocument();
    expect(screen.getByText("4 comments")).toBeInTheDocument();
    expect(screen.getByText("2 comments")).toBeInTheDocument();
  });

  it("shows the unique regulation count in the legend", async () => {
    const user = userEvent.setup();
    render(<GraphPage />);

    await user.type(
      screen.getByPlaceholderText(/Enter docket ID/),
      "DEMO-2024-0001",
    );
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      // Legend reads "Regulation (2 unique)"
      expect(screen.getByText(/2 unique/)).toBeInTheDocument();
    });
  });

  it("shows empty state when the docket has no citations", async () => {
    const user = userEvent.setup();
    render(<GraphPage />);

    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "EMPTY");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText(/No citations found/)).toBeInTheDocument();
    });
  });

  it("shows an error message when the API returns an error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response("boom", { status: 500, statusText: "Internal Server Error" }),
        ),
      ),
    );
    const user = userEvent.setup();
    render(<GraphPage />);

    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "DOC-001");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });
  });
});
