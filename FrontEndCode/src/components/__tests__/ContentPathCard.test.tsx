import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ContentPathCard } from "../ContentPathCard";

const defaultProps = {
  title: "Life Story Reflections",
  subtitle: "General Questions",
  icon: <span data-testid="test-icon">📖</span>,
  progressLabel: "12 out of 45 questions",
  accentColor: "border-legacy-purple",
  onClick: vi.fn(),
};

const renderCard = (overrides: Partial<typeof defaultProps> = {}) =>
  render(<ContentPathCard {...defaultProps} {...overrides} />);

describe("ContentPathCard", () => {
  it("renders title, subtitle, and progress label", () => {
    renderCard();
    expect(screen.getByText("Life Story Reflections")).toBeInTheDocument();
    expect(screen.getByText("General Questions")).toBeInTheDocument();
    expect(screen.getByText("12 out of 45 questions")).toBeInTheDocument();
  });

  it("renders the icon", () => {
    renderCard();
    expect(screen.getByTestId("test-icon")).toBeInTheDocument();
  });

  it("renders with role=button and tabIndex=0", () => {
    renderCard();
    const card = screen.getByRole("button");
    expect(card).toBeInTheDocument();
    expect(card).toHaveAttribute("tabindex", "0");
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    renderCard({ onClick });
    fireEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("calls onClick on Enter key", () => {
    const onClick = vi.fn();
    renderCard({ onClick });
    fireEvent.keyDown(screen.getByRole("button"), { key: "Enter" });
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("calls onClick on Space key", () => {
    const onClick = vi.fn();
    renderCard({ onClick });
    fireEvent.keyDown(screen.getByRole("button"), { key: " " });
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not call onClick on other keys", () => {
    const onClick = vi.fn();
    renderCard({ onClick });
    fireEvent.keyDown(screen.getByRole("button"), { key: "Tab" });
    expect(onClick).not.toHaveBeenCalled();
  });

  it("renders levelLabel as a badge when provided", () => {
    renderCard({ levelLabel: "Level 3" });
    expect(screen.getByText("Level 3")).toBeInTheDocument();
  });

  it("renders badge when provided", () => {
    renderCard({ badge: "Coming Soon" });
    expect(screen.getByText("Coming Soon")).toBeInTheDocument();
  });

  it("applies disabled styling and prevents onClick", () => {
    const onClick = vi.fn();
    renderCard({ disabled: true, onClick });
    const card = screen.getByRole("button");
    expect(card.className).toContain("opacity-60");
    expect(card.className).toContain("cursor-default");
    expect(card).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(card);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("does not fire onClick on Enter/Space when disabled", () => {
    const onClick = vi.fn();
    renderCard({ disabled: true, onClick });
    const card = screen.getByRole("button");
    fireEvent.keyDown(card, { key: "Enter" });
    fireEvent.keyDown(card, { key: " " });
    expect(onClick).not.toHaveBeenCalled();
  });

  it("applies the accent color class", () => {
    renderCard({ accentColor: "border-blue-500" });
    const card = screen.getByRole("button");
    expect(card.className).toContain("border-blue-500");
  });

  it("has min-h-[120px] for mobile tap targets", () => {
    renderCard();
    const card = screen.getByRole("button");
    expect(card.className).toContain("min-h-[120px]");
  });

  it("has rounded-xl and p-6 styling", () => {
    renderCard();
    const card = screen.getByRole("button");
    expect(card.className).toContain("rounded-xl");
    expect(card.className).toContain("p-6");
  });

  it("has border-l-4 for left accent border", () => {
    renderCard();
    const card = screen.getByRole("button");
    expect(card.className).toContain("border-l-4");
  });

  it("has hover and active scale classes when not disabled", () => {
    renderCard();
    const card = screen.getByRole("button");
    expect(card.className).toContain("hover:scale-[1.01]");
    expect(card.className).toContain("active:scale-[0.99]");
    expect(card.className).toContain("hover:shadow-lg");
  });

  it("has focus-visible ring classes when not disabled", () => {
    renderCard();
    const card = screen.getByRole("button");
    expect(card.className).toContain("focus-visible:ring-2");
    expect(card.className).toContain("focus-visible:ring-legacy-purple");
    expect(card.className).toContain("focus-visible:ring-offset-2");
  });

  it("does not have hover/active/focus classes when disabled", () => {
    renderCard({ disabled: true });
    const card = screen.getByRole("button");
    expect(card.className).not.toContain("hover:scale-[1.01]");
    expect(card.className).not.toContain("active:scale-[0.99]");
    expect(card.className).not.toContain("hover:shadow-lg");
  });
});
