import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DocketSearch } from "../src/components/DocketSearch";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const docketsResp = {
  items: [
    { docket_id: "EPA-HQ-OAR-2021-0317", comment_count: 3 },
    { docket_id: "EPA-HQ-OAR-2021-9999", comment_count: 1 },
  ],
  total: 2,
  limit: 8,
  offset: 0,
};

function mockFetch(url: string): Promise<Response> {
  if (url.includes("/dockets")) {
    return Promise.resolve(
      new Response(JSON.stringify(docketsResp), { status: 200 }),
    );
  }
  return Promise.resolve(new Response("not found", { status: 404 }));
}

/** Controlled wrapper so the value prop actually updates on user input. */
function Controlled({ initial = "" }: { initial?: string }) {
  const [v, setV] = useState(initial);
  return (
    <DocketSearch value={v} onChange={setV} placeholder="Search dockets" />
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("DocketSearch", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(mockFetch));
  });

  it("renders the input with the given placeholder", () => {
    render(<Controlled />);
    expect(screen.getByPlaceholderText("Search dockets")).toBeInTheDocument();
  });

  it("does not show a dropdown when fewer than 2 characters are typed", async () => {
    const user = userEvent.setup();
    render(<Controlled />);

    await user.type(screen.getByPlaceholderText("Search dockets"), "E");

    // No listbox should appear after a short wait
    await new Promise((r) => setTimeout(r, 100));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("shows a suggestion dropdown after typing 2+ characters", async () => {
    const user = userEvent.setup();
    render(<Controlled />);

    await user.type(screen.getByPlaceholderText("Search dockets"), "EP");

    await waitFor(
      () => expect(screen.getByRole("listbox")).toBeInTheDocument(),
      { timeout: 1500 },
    );
    expect(screen.getByText("EPA-HQ-OAR-2021-0317")).toBeInTheDocument();
    expect(screen.getByText("EPA-HQ-OAR-2021-9999")).toBeInTheDocument();
  });

  it("shows comment counts next to each suggestion", async () => {
    const user = userEvent.setup();
    render(<Controlled />);

    await user.type(screen.getByPlaceholderText("Search dockets"), "EP");

    await waitFor(
      () => expect(screen.getByRole("listbox")).toBeInTheDocument(),
      { timeout: 1500 },
    );
    expect(screen.getByText("3 comments")).toBeInTheDocument();
    expect(screen.getByText("1 comments")).toBeInTheDocument();
  });

  it("fills the input and closes the dropdown when a suggestion is clicked", async () => {
    const user = userEvent.setup();
    render(<Controlled />);

    await user.type(screen.getByPlaceholderText("Search dockets"), "EP");

    await waitFor(
      () => expect(screen.getByRole("listbox")).toBeInTheDocument(),
      { timeout: 1500 },
    );

    await user.click(screen.getByText("EPA-HQ-OAR-2021-0317"));

    expect(screen.getByPlaceholderText("Search dockets")).toHaveValue(
      "EPA-HQ-OAR-2021-0317",
    );
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("calls the onChange prop with the selected docket ID", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    // Use uncontrolled-ish wrapper that exposes onChange spy
    function SpyWrapper() {
      const [v, setV] = useState("");
      return (
        <DocketSearch
          value={v}
          onChange={(val) => {
            setV(val);
            onChange(val);
          }}
          placeholder="Search dockets"
        />
      );
    }

    render(<SpyWrapper />);
    await user.type(screen.getByPlaceholderText("Search dockets"), "EP");

    await waitFor(
      () => expect(screen.getByRole("listbox")).toBeInTheDocument(),
      { timeout: 1500 },
    );
    await user.click(screen.getByText("EPA-HQ-OAR-2021-0317"));

    expect(onChange).toHaveBeenCalledWith("EPA-HQ-OAR-2021-0317");
  });

  it("does not show a dropdown when the API returns an error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response("err", { status: 500, statusText: "Server Error" }),
        ),
      ),
    );
    const user = userEvent.setup();
    render(<Controlled />);

    await user.type(screen.getByPlaceholderText("Search dockets"), "EP");

    // Wait past debounce + fetch; wrap in act so React flushes state updates.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 500));
    });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("clears the dropdown when the input is cleared below 2 chars", async () => {
    const user = userEvent.setup();
    render(<Controlled />);

    await user.type(screen.getByPlaceholderText("Search dockets"), "EP");
    await waitFor(
      () => expect(screen.getByRole("listbox")).toBeInTheDocument(),
      { timeout: 1500 },
    );

    // Delete chars until back to 1
    await user.clear(screen.getByPlaceholderText("Search dockets"));
    await user.type(screen.getByPlaceholderText("Search dockets"), "E");

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
