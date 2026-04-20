import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryPage } from "../src/pages/QueryPage";

const queryResp = {
  answer: "Commenters raised concerns about air quality impacts on vulnerable populations.",
  sources: [
    {
      comment_id: "C-001",
      comment_text: "The proposed rule will worsen air quality for communities near industrial sites.",
      similarity: 0.87,
    },
    {
      comment_id: "C-002",
      comment_text: "Small businesses cannot afford the compliance costs outlined in the proposal.",
      similarity: 0.74,
    },
  ],
  model: "gpt-4o-mini",
  cost_usd: 0.00042,
  from_cache: false,
};

function mockFetch(url: string): Promise<Response> {
  if (url.includes("/dockets")) {
    return Promise.resolve(
      new Response(JSON.stringify({ items: [], total: 0, limit: 8, offset: 0 }), { status: 200 }),
    );
  }
  return Promise.resolve(new Response("not found", { status: 404 }));
}

function mockPost(url: string, init?: RequestInit): Promise<Response> {
  if (init?.method === "POST") {
    return Promise.resolve(new Response(JSON.stringify(queryResp), { status: 200 }));
  }
  return mockFetch(url);
}

describe("QueryPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => mockPost(url, init)));
  });

  it("renders the docket search and question input", () => {
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    expect(screen.getByPlaceholderText(/Docket ID/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/What concerns/)).toBeInTheDocument();
  });

  it("Ask button is disabled when both fields are empty", () => {
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("Ask button is disabled when only docket is filled", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Docket ID/), "EPA-HQ-OAR-2021-0317");
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("Ask button is disabled when only question is filled", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/What concerns/), "What about air quality?");
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("shows answer and sources after successful query", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Docket ID/), "EPA-HQ-OAR-2021-0317");
    await user.type(screen.getByPlaceholderText(/What concerns/), "What about air quality?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => {
      expect(screen.getByText(/Commenters raised concerns/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Source comments/)).toBeInTheDocument();
  });

  it("shows source comment IDs and similarity percentages", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Docket ID/), "EPA-HQ-OAR-2021-0317");
    await user.type(screen.getByPlaceholderText(/What concerns/), "air quality");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => {
      expect(screen.getByText(/C-001/)).toBeInTheDocument();
    });
    expect(screen.getByText(/C-002/)).toBeInTheDocument();
    expect(screen.getByText(/87.0%/)).toBeInTheDocument();
    expect(screen.getByText(/74.0%/)).toBeInTheDocument();
  });

  it("shows cost formatted to 5 decimal places", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Docket ID/), "EPA-HQ-OAR-2021-0317");
    await user.type(screen.getByPlaceholderText(/What concerns/), "air quality");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => {
      expect(screen.getByText("$0.00042")).toBeInTheDocument();
    });
  });

  it("shows cached badge when from_cache is true", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (init?.method === "POST") {
          return Promise.resolve(
            new Response(JSON.stringify({ ...queryResp, from_cache: true, cost_usd: 0 }), { status: 200 }),
          );
        }
        return Promise.resolve(
          new Response(JSON.stringify({ items: [], total: 0, limit: 8, offset: 0 }), { status: 200 }),
        );
      }),
    );
    const user = userEvent.setup();
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Docket ID/), "EPA-HQ-OAR-2021-0317");
    await user.type(screen.getByPlaceholderText(/What concerns/), "air quality");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => {
      expect(screen.getByText("cached")).toBeInTheDocument();
    });
  });

  it("expands and collapses long source text", async () => {
    const longText = "A".repeat(300);
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (init?.method === "POST") {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                ...queryResp,
                sources: [{ comment_id: "C-LONG", comment_text: longText, similarity: 0.9 }],
              }),
              { status: 200 },
            ),
          );
        }
        return Promise.resolve(
          new Response(JSON.stringify({ items: [], total: 0, limit: 8, offset: 0 }), { status: 200 }),
        );
      }),
    );
    const user = userEvent.setup();
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Docket ID/), "EPA-HQ-OAR-2021-0317");
    await user.type(screen.getByPlaceholderText(/What concerns/), "air quality");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => {
      expect(screen.getByText("Show more")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Show more"));
    expect(screen.getByText("Show less")).toBeInTheDocument();
    await user.click(screen.getByText("Show less"));
    expect(screen.getByText("Show more")).toBeInTheDocument();
  });

  it("shows error when API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (init?.method === "POST") {
          return Promise.resolve(new Response("boom", { status: 500, statusText: "Internal Server Error" }));
        }
        return Promise.resolve(
          new Response(JSON.stringify({ items: [], total: 0, limit: 8, offset: 0 }), { status: 200 }),
        );
      }),
    );
    const user = userEvent.setup();
    render(<MemoryRouter><QueryPage /></MemoryRouter>);
    await user.type(screen.getByPlaceholderText(/Docket ID/), "EPA-HQ-OAR-2021-0317");
    await user.type(screen.getByPlaceholderText(/What concerns/), "air quality");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });
  });

  it("pre-fills docket ID from ?docket= URL param", () => {
    render(
      <MemoryRouter initialEntries={["/query?docket=EPA-HQ-OAR-2021-0317"]}>
        <QueryPage />
      </MemoryRouter>,
    );
    expect(screen.getByPlaceholderText(/Docket ID/)).toHaveValue("EPA-HQ-OAR-2021-0317");
  });
});
