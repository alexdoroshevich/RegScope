import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AstroturfPage } from "../src/pages/AstroturfPage";

const summary = {
  total_groups: 10,
  astroturf_groups: 3,
  total_flagged_comments: 45,
  max_campaign_likelihood: 7.5,
};

const groupsResp = {
  items: [
    {
      group_id: 1,
      comment_ids: ["C-1", "C-2", "C-3"],
      group_size: 3,
      unique_submitters: 1,
      campaign_likelihood: 3.0,
      is_astroturf: true,
      template_text: "Repeat this comment exactly",
    },
  ],
  limit: 20,
  offset: 0,
};

function mockFetch(url: string): Promise<Response> {
  if (url.includes("/astroturf/summary")) {
    return Promise.resolve(
      new Response(JSON.stringify(summary), { status: 200 }),
    );
  }
  if (url.includes("/astroturf/groups")) {
    return Promise.resolve(
      new Response(JSON.stringify(groupsResp), { status: 200 }),
    );
  }
  return Promise.resolve(new Response("not found", { status: 404 }));
}

describe("AstroturfPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(mockFetch));
  });

  it("renders summary cards after loading", async () => {
    render(<AstroturfPage />);
    await waitFor(() => {
      expect(screen.getByText("Astroturf Detection")).toBeInTheDocument();
    });
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText("7.50")).toBeInTheDocument();
  });

  it("renders the list of suspected groups", async () => {
    render(<AstroturfPage />);
    await waitFor(() => {
      expect(
        screen.getByText("Repeat this comment exactly"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/#1/)).toBeInTheDocument();
    expect(screen.getByText(/3 comments · 1 submitters/)).toBeInTheDocument();
  });

  it("shows an error when the API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(new Response("boom", { status: 500, statusText: "err" })),
      ),
    );
    render(<AstroturfPage />);
    await waitFor(() => {
      expect(screen.getByText(/API error 500/)).toBeInTheDocument();
    });
  });
});
