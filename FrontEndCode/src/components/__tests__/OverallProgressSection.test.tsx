import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OverallProgressSection } from "../OverallProgressSection";
import { TooltipProvider } from "@/components/ui/tooltip";

// Wrap component with TooltipProvider since InfoTooltip uses Radix Tooltip
const renderWithProviders = (completed: number, total: number) =>
  render(
    <TooltipProvider>
      <OverallProgressSection completed={completed} total={total} />
    </TooltipProvider>
  );

describe("OverallProgressSection", () => {
  it("renders the heading text", () => {
    renderWithProviders(5, 20);
    expect(screen.getByText("Your Overall Progress")).toBeInTheDocument();
  });

  it("renders the ProgressBar with correct completed/total text", () => {
    renderWithProviders(12, 45);
    expect(screen.getByText("12 of 45 questions answered")).toBeInTheDocument();
  });

  it("renders the percentage", () => {
    renderWithProviders(12, 45);
    expect(screen.getByText("27%")).toBeInTheDocument();
  });

  it("renders 0% when total is 0", () => {
    renderWithProviders(0, 0);
    expect(screen.getByText("0 of 0 questions answered")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("renders 100% when all questions are completed", () => {
    renderWithProviders(10, 10);
    expect(screen.getByText("10 of 10 questions answered")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("renders the InfoTooltip trigger icon", () => {
    renderWithProviders(5, 20);
    expect(screen.getByLabelText("More information")).toBeInTheDocument();
  });

  it("renders inside a white card container", () => {
    const { container } = renderWithProviders(5, 20);
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toContain("bg-white");
    expect(card.className).toContain("rounded-lg");
    expect(card.className).toContain("shadow");
  });
});
