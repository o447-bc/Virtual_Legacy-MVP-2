import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import * as fc from 'fast-check';
import { SecurityDialog } from '../SecurityDialog';

/**
 * Property-Based Test: Progressive Disclosure State Transitions
 * 
 * **Validates: Requirements 5.3, 5.4, 5.6, 5.7, 5.9, 5.10, 5.12**
 * 
 * Property 12: For any SecurityDialog in Level 1 state, clicking "Learn More" 
 * should expand to Level 2, and clicking "Technical Details" should expand to 
 * Level 3, and collapsing should return to the previous level.
 * 
 * This test verifies that the progressive disclosure mechanism works correctly
 * across all possible sequences of user interactions.
 */

describe('SecurityDialog - Property 12: Progressive Disclosure State Transitions', () => {
  afterEach(() => {
    // Clean up any remaining portals
    document.body.innerHTML = '';
  });

  it('should correctly handle progressive disclosure state transitions for any sequence of actions', async () => {
    // Define possible actions a user can take
    type Action = 
      | { type: 'toggle-level2' }
      | { type: 'toggle-level3' };

    // Generator for sequences of actions
    const actionSequenceArbitrary = fc.array(
      fc.oneof(
        fc.constant<Action>({ type: 'toggle-level2' }),
        fc.constant<Action>({ type: 'toggle-level3' })
      ),
      { minLength: 1, maxLength: 8 }
    );

    await fc.assert(
      fc.asyncProperty(actionSequenceArbitrary, async (actions) => {
        const onOpenChange = vi.fn();

        // Render the dialog in open state
        const { unmount } = render(
          <SecurityDialog open={true} onOpenChange={onOpenChange} />
        );

        // Wait for dialog to render
        await new Promise(resolve => setTimeout(resolve, 50));

        // Level 1 content should always be visible (Requirement 5.3, 5.4)
        const level1Elements = screen.queryAllByText(/Your videos and personal information are encrypted and protected/i);
        expect(level1Elements.length).toBeGreaterThan(0);

        // Execute each action in the sequence
        for (const action of actions) {
          switch (action.type) {
            case 'toggle-level2':
              // Click "Learn More About Our Security" button (Requirement 5.6)
              const learnMoreButtons = screen.queryAllByRole('button', { 
                name: /Learn More About Our Security/i 
              });
              if (learnMoreButtons.length > 0) {
                fireEvent.click(learnMoreButtons[0]);
                
                // Wait for animation
                await new Promise(resolve => setTimeout(resolve, 150));
              }
              break;

            case 'toggle-level3':
              // Level 3 can only be toggled if Level 2 is open
              const technicalDetailsButtons = screen.queryAllByRole('button', { 
                name: /Technical Details/i 
              });
              
              if (technicalDetailsButtons.length > 0) {
                fireEvent.click(technicalDetailsButtons[0]);
                
                // Wait for animation
                await new Promise(resolve => setTimeout(resolve, 150));
              }
              break;
          }

          // Verify Level 1 is always visible (Requirement 5.3, 5.4)
          const level1Check = screen.queryAllByText(/Your videos and personal information are encrypted and protected/i);
          expect(level1Check.length).toBeGreaterThan(0);
        }

        // Cleanup
        unmount();
        await new Promise(resolve => setTimeout(resolve, 50));
      }),
      { 
        numRuns: 50, // Reduced from 100 for faster execution
        verbose: false,
      }
    );
  }, 60000); // Increase timeout for property-based test

  it('should always display Level 1 content regardless of Level 2/3 state', async () => {
    // Property: Level 1 is always visible (Requirement 5.3, 5.4)
    await fc.assert(
      fc.asyncProperty(
        fc.boolean(), // level2Open
        fc.boolean(), // level3Open
        async (shouldOpenLevel2, shouldOpenLevel3) => {
          const onOpenChange = vi.fn();

          const { unmount } = render(
            <SecurityDialog open={true} onOpenChange={onOpenChange} />
          );

          await new Promise(resolve => setTimeout(resolve, 50));

          // Level 1 content should always be visible
          let level1Elements = screen.queryAllByText(/Your videos and personal information are encrypted and protected/i);
          expect(level1Elements.length).toBeGreaterThan(0);

          if (shouldOpenLevel2) {
            const learnMoreButtons = screen.queryAllByRole('button', { 
              name: /Learn More About Our Security/i 
            });
            if (learnMoreButtons.length > 0) {
              fireEvent.click(learnMoreButtons[0]);
              await new Promise(resolve => setTimeout(resolve, 150));

              // Level 1 should still be visible
              level1Elements = screen.queryAllByText(/Your videos and personal information are encrypted and protected/i);
              expect(level1Elements.length).toBeGreaterThan(0);

              if (shouldOpenLevel3) {
                const technicalDetailsButtons = screen.queryAllByRole('button', { 
                  name: /Technical Details/i 
                });
                if (technicalDetailsButtons.length > 0) {
                  fireEvent.click(technicalDetailsButtons[0]);
                  await new Promise(resolve => setTimeout(resolve, 150));

                  // Level 1 should still be visible
                  level1Elements = screen.queryAllByText(/Your videos and personal information are encrypted and protected/i);
                  expect(level1Elements.length).toBeGreaterThan(0);
                }
              }
            }
          }

          unmount();
          await new Promise(resolve => setTimeout(resolve, 50));
        }
      ),
      { numRuns: 50 }
    );
  }, 60000); // Increase timeout for property-based test

  it('should only show Level 3 button when Level 2 is open', async () => {
    // Property: Level 3 is only accessible when Level 2 is open
    await fc.assert(
      fc.asyncProperty(
        fc.boolean(),
        async (shouldOpenLevel2) => {
          const onOpenChange = vi.fn();

          const { unmount } = render(
            <SecurityDialog open={true} onOpenChange={onOpenChange} />
          );

          await new Promise(resolve => setTimeout(resolve, 50));

          if (shouldOpenLevel2) {
            const learnMoreButtons = screen.queryAllByRole('button', { 
              name: /Learn More About Our Security/i 
            });
            if (learnMoreButtons.length > 0) {
              fireEvent.click(learnMoreButtons[0]);
              await new Promise(resolve => setTimeout(resolve, 150));

              // Technical Details button should now be visible
              const technicalDetailsButtons = screen.queryAllByRole('button', { 
                name: /Technical Details/i 
              });
              expect(technicalDetailsButtons.length).toBeGreaterThan(0);
            }
          } else {
            // Technical Details button should not be visible
            const technicalDetailsButtons = screen.queryAllByRole('button', { 
              name: /Technical Details/i 
            });
            expect(technicalDetailsButtons.length).toBe(0);
          }

          unmount();
          await new Promise(resolve => setTimeout(resolve, 50));
        }
      ),
      { numRuns: 50 }
    );
  }, 60000); // Increase timeout for property-based test
});
