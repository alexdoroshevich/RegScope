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
  });

  it("renders the top nav", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    const links = screen.getAllByRole("link");
    expect(links.map((l) => l.getAttribute("href"))).toContain("/astroturf");
  });
});
