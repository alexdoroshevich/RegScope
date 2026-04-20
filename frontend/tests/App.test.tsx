import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "../src/App";

describe("App", () => {
  it("renders the home page at /", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "RegScope" })).toBeInTheDocument();
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
