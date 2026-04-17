import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SummaryCard } from "../src/components/SummaryCard";

describe("SummaryCard", () => {
  it("renders label and value", () => {
    render(<SummaryCard label="Total" value={42} />);
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("applies warning tone styling", () => {
    const { container } = render(
      <SummaryCard label="Alerts" value={5} tone="warning" />,
    );
    expect(container.firstChild).toHaveClass("bg-red-50");
  });

  it("defaults to neutral tone", () => {
    const { container } = render(<SummaryCard label="Items" value="3" />);
    expect(container.firstChild).toHaveClass("bg-slate-50");
  });
});
