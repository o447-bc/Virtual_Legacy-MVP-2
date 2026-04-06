import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LifeEventGroup } from "../LifeEventGroup";

const baseProps = {
  eventKey: "got_married",
  instanceName: "Sarah",
  instanceOrdinal: 1,
  questions: [
    { questionId: "q1", questionText: "How did you meet Sarah?", isAnswered: true },
    { questionId: "q2", questionText: "What was the wedding like?", isAnswered: false },
    { questionId: "q3", questionText: "What advice would you give?", isAnswered: false },
  ],
  totalQuestions: 3,
  completedQuestions: 1,
  onRecord: vi.fn(),
};

describe("LifeEventGroup", () => {
  it("renders the event label from the registry", () => {
    render(<LifeEventGroup {...baseProps} />);
    expect(
      screen.getByText(/Got married or entered a long-term partnership/i)
    ).toBeInTheDocument();
  });

  it("renders the instance name", () => {
    render(<LifeEventGroup {...baseProps} />);
    expect(screen.getByText(/Sarah/)).toBeInTheDocument();
  });

  it("displays progress as completed / total", () => {
    render(<LifeEventGroup {...baseProps} />);
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("renders a Record button when not all questions are answered", () => {
    render(<LifeEventGroup {...baseProps} />);
    expect(screen.getByRole("button", { name: /record/i })).toBeInTheDocument();
  });

  it("calls onRecord with unanswered question IDs and texts when Record is clicked", async () => {
    const onRecord = vi.fn();
    const user = userEvent.setup();
    render(<LifeEventGroup {...baseProps} onRecord={onRecord} />);

    await user.click(screen.getByRole("button", { name: /record/i }));

    expect(onRecord).toHaveBeenCalledWith(
      ["q2", "q3"],
      ["What was the wedding like?", "What advice would you give?"]
    );
  });


  it("expands question list when Show questions is clicked", async () => {
    const user = userEvent.setup();
    render(<LifeEventGroup {...baseProps} />);

    // Questions should not be in the DOM initially (Radix removes collapsed content)
    expect(screen.queryByText("How did you meet Sarah?")).not.toBeInTheDocument();

    await user.click(screen.getByText("Show questions"));

    expect(screen.getByText("How did you meet Sarah?")).toBeInTheDocument();
    expect(screen.getByText("What was the wedding like?")).toBeInTheDocument();
  });

  it("shows checkmark icon for answered questions and circle for unanswered", async () => {
    const user = userEvent.setup();
    render(<LifeEventGroup {...baseProps} />);
    await user.click(screen.getByText("Show questions"));

    const listItems = screen.getAllByRole("listitem");
    // First question is answered — should have line-through styling
    const answeredText = listItems[0].querySelector("span");
    expect(answeredText?.className).toContain("line-through");

    // Second question is unanswered — no line-through
    const unansweredText = listItems[1].querySelector("span");
    expect(unansweredText?.className).not.toContain("line-through");
  });

  it("shows completed state with muted styling when all questions answered", () => {
    const completedProps = {
      ...baseProps,
      questions: baseProps.questions.map((q) => ({ ...q, isAnswered: true })),
      completedQuestions: 3,
    };
    const { container } = render(<LifeEventGroup {...completedProps} />);

    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toContain("opacity-60");
  });

  it("hides Record button when all questions are answered", () => {
    const completedProps = {
      ...baseProps,
      questions: baseProps.questions.map((q) => ({ ...q, isAnswered: true })),
      completedQuestions: 3,
    };
    render(<LifeEventGroup {...completedProps} />);
    expect(screen.queryByRole("button", { name: /record/i })).not.toBeInTheDocument();
  });

  it("shows Complete label when all questions are answered", () => {
    const completedProps = {
      ...baseProps,
      questions: baseProps.questions.map((q) => ({ ...q, isAnswered: true })),
      completedQuestions: 3,
    };
    render(<LifeEventGroup {...completedProps} />);
    expect(screen.getByText("Complete")).toBeInTheDocument();
  });

  it("renders left accent border based on event category", () => {
    const { container } = render(<LifeEventGroup {...baseProps} />);
    const card = container.firstElementChild as HTMLElement;
    // got_married is "Core Relationship & Family" → border-rose-500
    expect(card.className).toContain("border-rose-500");
  });

  it("falls back to eventKey when registry entry is not found", () => {
    render(<LifeEventGroup {...baseProps} eventKey="unknown_event" />);
    expect(screen.getByText(/unknown_event/)).toBeInTheDocument();
  });
});
