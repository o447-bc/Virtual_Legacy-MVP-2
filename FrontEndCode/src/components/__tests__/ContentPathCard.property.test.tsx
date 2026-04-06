import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import * as fc from "fast-check";
import { ContentPathCard } from "../ContentPathCard";

/**
 * Property-Based Test: Content path card keyboard accessibility
 *
 * Feature: dashboard-content-hub, Property 4: Content path card keyboard accessibility
 *
 * **Validates: Requirements 5.5**
 *
 * For any ContentPathCard component that is not disabled, pressing the Enter key
 * or Space key while the card is focused should invoke the card's onClick callback
 * exactly once. Disabled cards should NOT trigger onClick on Enter/Space.
 */

// Generator for random card props (excluding onClick which is controlled per-test)
const cardPropsArb = fc.record({
  title: fc.string({ minLength: 1, maxLength: 30 }),
  subtitle: fc.string({ minLength: 1, maxLength: 30 }),
  progressLabel: fc.string({ minLength: 1, maxLength: 40 }),
  accentColor: fc.oneof(
    fc.constant("border-legacy-purple"),
    fc.constant("border-blue-500"),
    fc.constant("border-amber-500")
  ),
  levelLabel: fc.option(fc.string({ minLength: 1, maxLength: 10 }), { nil: undefined }),
  badge: fc.option(fc.string({ minLength: 1, maxLength: 15 }), { nil: undefined }),
});

// Generator for keyboard keys that should trigger onClick
const triggerKeyArb = fc.oneof(fc.constant("Enter"), fc.constant(" "));

describe("ContentPathCard - Property 4: Content path card keyboard accessibility", () => {
  it("should invoke onClick exactly once when Enter or Space is pressed on a non-disabled card", () => {
    fc.assert(
      fc.property(cardPropsArb, triggerKeyArb, (props, key) => {
        const onClick = vi.fn();

        const { unmount } = render(
          <ContentPathCard
            {...props}
            icon={<span>📖</span>}
            onClick={onClick}
          />
        );

        const card = screen.getByRole("button");
        fireEvent.keyDown(card, { key });

        expect(onClick).toHaveBeenCalledTimes(1);

        unmount();
        cleanup();
      }),
      { numRuns: 100, verbose: false }
    );
  });

  it("should NOT invoke onClick when Enter or Space is pressed on a disabled card", () => {
    fc.assert(
      fc.property(cardPropsArb, triggerKeyArb, (props, key) => {
        const onClick = vi.fn();

        const { unmount } = render(
          <ContentPathCard
            {...props}
            icon={<span>📖</span>}
            disabled={true}
            onClick={onClick}
          />
        );

        const card = screen.getByRole("button");
        fireEvent.keyDown(card, { key });

        expect(onClick).not.toHaveBeenCalled();

        unmount();
        cleanup();
      }),
      { numRuns: 100, verbose: false }
    );
  });
});
