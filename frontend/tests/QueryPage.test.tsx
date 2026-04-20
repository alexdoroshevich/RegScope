import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryPage } from "../src/pages/QueryPage";

const queryResp = {
  question: "What do commenters say?",
  answer: "Small businesses bear disproportionate costs.",
  sources: [
    {
      comment_id: "C-001",
      docket_id: "EPA-HQ-OAR-2021-0317",
      comment_text: "This regulation will harm small businesses.",
      similarity: 0.92,
    },
    {
      comment_id: "C-002",
      docket_id: "EPA-HQ-OAR-2021-0317",
      comment_text: "Compliance costs are too high.",
      similarity: 0.88,
    },
  ],
  model: "gpt-4o-mini",
  cost_usd: 0.00042,
  from_cache: false,
};

const cachedResp = { ...queryResp, from_cache: true, cost_usd: 0.0 };

function mockFetch(_url: string, init?: RequestInit): Promise<Response> {
  if (init?.method === "POST") {
    return Promise.resolve(
      new Response(JSON.stringify(queryResp), { status: 200 }),
    );
  }
  return Promise.resolve(new Response("not found", { status: 404 }));
}

describe("QueryPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(mockFetch));
  });

  it("renders the form with both inputs and the Ask button", () => {
    render(<QueryPage />);
    expect(screen.getByPlaceholderText(/Docket ID/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/What concerns/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask" })).toBeInTheDocument();
    expect(screen.getByText("Ask a Question")).toBeInTheDocument();
  });

  it("Ask button is disabled when both fields are empty", () => {
    render(<QueryPage />);
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("Ask button stays disabled when only the docket ID is filled", async () => {
    const user = userEvent.setup();
    render(<QueryPage />);

    await user.type(
      screen.getByPlaceholderText(/Docket ID/),
      "EPA-HQ-OAR-2021-0317",
    );
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("Ask button stays disabled when only the question is filled", async () => {
    const user = userEvent.setup();
    render(<QueryPage />);

    await user.type(
      screen.getByPlaceholderText(/What concerns/),
      "What do commenters say?",
    );
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("shows the answer panel and sources after a successful query", async () => {
    const user = userEvent.setup();
    render(<QueryPage />);

    await user.type(
      screen.getByPlaceholderText(/Docket ID/),
      "EPA-HQ-OAR-2021-0317",
    );
    await user.type(
      screen.getByPlaceholderText(/What concerns/),
      "What do commenters say?",
    );
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => {
      expect(
        screen.getByText("Small businesses bear disproportionate costs."),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Answer")).toBeInTheDocument();
    expect(screen.getByText("gpt-4o-mini")).toBeInTheDocument();
    expect(screen.getByText("Source comments (2)")).toBeInTheDocument();
  });

  it("shows source comment IDs and similarity percentages", async () => {
    const user = userEvent.setup();
    render(<QueryPage />);

    await user.type(
      screen.getByPlaceholderText(/Docket ID/),
      "EPA-HQ-OAR-2021-0317",
    );
    await user.type(
      screen.getByPlaceholderText(/What concerns/),
      "What do commenters say?",
    );
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => {
      expect(screen.getByText(/C-001/)).toBeInTheDocument();
    });
    expect(screen.getByText(/C-002/)).toBeInTheDocument();
    expect(screen.getByText("similarity 92.0%")).toBeInTheDocument();
    expect(screen.getByText("similarity 88.0%")).toBeInTheDocument();
  });

  it("displays cost when the response is not from cache", async () => {
    const user = userEvent.setup();
    render(<QueryPage />);

    await user.type(
      screen.getByPlaceholderText(/Docket ID/),
      "EPA-HQ-OAR-2021-0317",
    );
    await user.type(
      screen.getByPlaceholderText(/What concerns/),
      "What do commenters say?",
    );
    await user.click(screen.getByRole("button", { name: "Ask" }));

    // cost_usd 0.00042 → toFixed(5) → "0.00042" → rendered as "$0.00042"
    await waitFor(() => {
      expect(screen.getByText("$0.00042")).toBeInTheDocument();
    });
  });

  it("shows the cached badge when response comes from cache", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify(cachedResp), { status: 200 }),
        ),
      ),
    );
    const user = userEvent.setup();
    render(<QueryPage />);

    await user.type(
      screen.getByPlaceholderText(/Docket ID/),
      "EPA-HQ-OAR-2021-0317",
    );
    await user.type(screen.getByPlaceholderText(/What concerns/), "test");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => {
      expect(screen.getByText("cached")).toBeInTheDocument();
    });
  });

  it("expands and collapses a long source comment via Show more / Show less", async () => {
    const longText = "a".repeat(300);
    const longSourceResp = {
      ...queryResp,
      sources: [
        {
          comment_id: "C-001",
          docket_id: "EPA-HQ-OAR-2021-0317",
          comment_text: longText,
          similarity: 0.92,
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify(longSourceResp), { status: 200 }),
        ),
      ),
    );
    const user = userEvent.setup();
    render(<QueryPage />);

    await user.type(
      screen.getByPlaceholderText(/Docket ID/),
      "EPA-HQ-OAR-2021-0317",
    );
    await user.type(screen.getByPlaceholderText(/What concerns/), "test");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => {
      expect(screen.getByText("Show more")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Show more"));
    expect(screen.getByText("Show less")).toBeInTheDocument();

    await user.click(screen.getByText("Show less"));
    expect(screen.getByText("Show more")).toBeInTheDocument();
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
    render(<QueryPage />);

    await user.type(
      screen.getByPlaceholderText(/Docket ID/),
      "EPA-HQ-OAR-2021-0317",
    );
    await user.type(screen.getByPlaceholderText(/What concerns/), "test");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });
  });
});
