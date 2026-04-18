import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ClustersPage } from "../src/pages/ClustersPage";

const clustersResp = [
  {
    cluster_id: 0,
    comment_count: 15,
    label: "Air Quality",
    summary: "Comments discuss pollution standards.",
  },
  {
    cluster_id: 1,
    comment_count: 8,
    label: null,
    summary: null,
  },
];

const commentsResp = [
  {
    comment_id: "C-1",
    comment_text: "We need cleaner air.",
    submitter_name: "Alice",
  },
  {
    comment_id: "C-2",
    comment_text: "Pollution is bad.",
    submitter_name: null,
  },
];

function mockFetch(url: string): Promise<Response> {
  if (url.includes("/clusters/") && !url.includes("/0")) {
    return Promise.resolve(
      new Response(JSON.stringify(clustersResp), { status: 200 }),
    );
  }
  if (url.includes("/0")) {
    return Promise.resolve(
      new Response(JSON.stringify(commentsResp), { status: 200 }),
    );
  }
  return Promise.resolve(new Response("not found", { status: 404 }));
}

describe("ClustersPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(mockFetch));
  });

  it("renders the search form", () => {
    render(<ClustersPage />);
    expect(screen.getByPlaceholderText(/Enter docket ID/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });

  it("shows clusters after searching", async () => {
    const user = userEvent.setup();
    render(<ClustersPage />);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "DOC-001");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("Air Quality")).toBeInTheDocument();
    });
    expect(screen.getByText("(15 comments)")).toBeInTheDocument();
    expect(screen.getByText("Cluster #1")).toBeInTheDocument();
    expect(screen.getByText("(8 comments)")).toBeInTheDocument();
  });

  it("shows summary cards with cluster stats", async () => {
    const user = userEvent.setup();
    render(<ClustersPage />);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "DOC-001");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("Total comments")).toBeInTheDocument();
    });
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("23")).toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
  });

  it("expands a cluster to show comments", async () => {
    const user = userEvent.setup();
    render(<ClustersPage />);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "DOC-001");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText("Air Quality")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Air Quality"));

    await waitFor(() => {
      expect(screen.getByText("We need cleaner air.")).toBeInTheDocument();
    });
    expect(screen.getByText("Pollution is bad.")).toBeInTheDocument();
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
    expect(screen.getByText(/Anonymous/)).toBeInTheDocument();
  });

  it("shows empty state when no clusters found", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      ),
    );
    const user = userEvent.setup();
    render(<ClustersPage />);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "EMPTY");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(
        screen.getByText("No clusters found for this docket."),
      ).toBeInTheDocument();
    });
  });

  it("shows error when API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response("boom", { status: 500, statusText: "err" }),
        ),
      ),
    );
    const user = userEvent.setup();
    render(<ClustersPage />);
    await user.type(screen.getByPlaceholderText(/Enter docket ID/), "DOC-001");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });
  });
});
