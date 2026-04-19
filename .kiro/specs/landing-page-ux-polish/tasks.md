# Implementation Plan: Landing Page UX Polish

## Overview

This plan implements 16 UX polish and conversion optimization enhancements to the SoulReel landing page and related public pages. Tasks are ordered so dependencies are respected: the analytics utility comes first (used by many components), then simple copy/styling changes, then complex features (modal signup, Discover page). Each task builds on previous work and ends with wiring everything together.

## Tasks

- [x] 1. Create analytics utility and Logo simplification
  - [x] 1.1 Create `FrontEndCode/src/lib/analytics.ts` with the `trackEvent` utility function
    - Export `trackEvent(name: string, properties?: Record<string, string | number | boolean>): void`
    - Wrap body in try/catch so it never throws
    - Initial implementation logs to console via `console.debug('[analytics]', name, properties)`
    - Must be synchronous, fire-and-forget, non-blocking
    - _Requirements: 16.3, 16.4, 16.5_

  - [ ]* 1.2 Write property test for trackEvent safety (Property 8)
    - **Property 8: Analytics trackEvent is non-blocking and safe**
    - Generate random event names and property objects with fast-check, verify trackEvent never throws and returns undefined (not a Promise)
    - Test file: `FrontEndCode/src/__tests__/landing-page-ux-polish.property.test.ts`
    - **Validates: Requirements 16.3, 16.5**

  - [x] 1.3 Simplify `FrontEndCode/src/components/Logo.tsx` to wordmark only
    - Remove the purple circle `<div>` with "SR" initials
    - Render only the "SoulReel" `<span>` with `text-2xl font-extrabold`
    - Apply `bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent` by default
    - When `className` includes `text-white`, skip gradient classes and render solid white text
    - Changes propagate automatically to all existing usages (Home.tsx, SignUpCreateLegacy.tsx, SignUpStartTheirLegacy.tsx, LegacyCreateChoice.tsx, PricingPage.tsx)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 1.4 Write property test for Logo gradient conditional rendering (Property 4)
    - **Property 4: Logo gradient conditional rendering**
    - Generate random className strings (some containing "text-white"), verify gradient class presence/absence
    - **Validates: Requirements 6.5**

- [x] 2. Sticky headers and simple copy changes
  - [x] 2.1 Add sticky positioning to Landing Header in `FrontEndCode/src/pages/Home.tsx`
    - Add `sticky top-0 z-50 bg-white/95 backdrop-blur-sm` to the `<header>` element
    - Ensure no layout shift — `sticky` keeps element in document flow
    - _Requirements: 1.1, 1.2, 1.5, 1.7_

  - [x] 2.2 Add sticky positioning to Dashboard Header in `FrontEndCode/src/components/Header.tsx`
    - Add `sticky top-0 z-50` to the existing `<header>` element
    - Keep existing `bg-white shadow-sm` styling
    - _Requirements: 1.3, 1.4, 1.6, 1.8_

  - [x] 2.3 Update How It Works step 2 copy in `FrontEndCode/src/components/landing/HowItWorksSection.tsx`
    - Change step 2 title to "Just Talk — We'll Listen"
    - Change step 2 description to "Just talk naturally. We'll ask the right follow-up questions to help you uncover the moments that matter most."
    - Keep Mic icon for step 2; do not change steps 1 or 3
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.4 Update Sample Questions subtitle in `FrontEndCode/src/components/landing/SampleQuestionsSection.tsx`
    - Replace "Here are a few of the questions waiting for you" with "Three paths to explore: your life story, the events that shaped you, and the values you hold dear."
    - Maintain existing styling: `text-lg text-gray-600 text-center max-w-2xl mx-auto mb-12`
    - Do NOT change the "Explore more questions →" link target yet — it will be updated to `/discover` in task 9.5 after the Discover page exists
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 2.5 Update "No credit card" micro-copy in `FrontEndCode/src/components/landing/HeroSection.tsx`
    - Replace "Preserve your own stories and memories" under "Start Free" with "Free forever. No credit card required." in `text-sm text-gray-500`
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 2.6 Add "No credit card" and emotional urgency copy to `FrontEndCode/src/components/landing/ClosingCTASection.tsx`
    - Add "No credit card required" below the primary CTA button in `text-sm text-gray-500`
    - Add "Every day holds stories worth preserving. Don't wait for someday." above or below the headline in `text-base italic text-gray-500`
    - Add `trackEvent('closing_cta_click', { button: 'primary' | 'secondary' })` on CTA clicks
    - _Requirements: 10.4, 13.1, 13.2, 13.3, 13.4, 16.1e_

  - [x] 2.7 Add descriptions to `FrontEndCode/src/pages/LegacyCreateChoice.tsx`
    - Add "Preserve your own stories, memories, and wisdom for the people who matter most." under "Create Your Legacy"
    - Add "Set it up for a parent, grandparent, or loved one — you'll manage the account and they'll record their stories." under "Start Their Legacy"
    - Add a "Learn more" link to `/discover`
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 3. Checkpoint — Verify sticky headers, copy changes, and Logo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. New landing page components (EaseOfUseStrip, MicroSocialProof, FounderStory, EmailCapture)
  - [x] 4.1 Create `FrontEndCode/src/components/landing/EaseOfUseStrip.tsx`
    - Thin banner with two messages: "No typing required — just press record and talk" (Mic icon) and "Works on computer, tablet, or phone" (Monitor, Smartphone, Tablet icons from lucide-react)
    - Desktop: horizontal row. Mobile: vertical stack
    - Styling: `bg-gray-50 py-4 text-sm text-gray-500`, centered content, muted icons
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 4.2 Create `FrontEndCode/src/components/landing/MicroSocialProof.tsx`
    - Render "Join families already preserving their stories" in `text-sm text-gray-400`
    - Centered horizontally, visually subtle
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 4.3 Create `FrontEndCode/src/components/landing/FounderStorySection.tsx`
    - Heading: "My Story — Why I Built SoulReel"
    - Body: the full founder story text from Requirement 12.3, rendered as paragraphs (not all italic)
    - End on "then you already understand why this exists." — omit the CTA-style ending lines
    - Background: `bg-legacy-lightPurple`, centered block, readable body text, founder attribution at bottom
    - Responsive padding and text sizing for mobile
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_

  - [x] 4.4 Create `FrontEndCode/src/components/landing/EmailCaptureSection.tsx`
    - Prompt: "Not ready yet? Get a free sample question delivered to your inbox."
    - Single email input + submit button, inline section (not modal/popup)
    - Validate email format before submission
    - On success: show "You're on the list!" and clear input
    - Storage: initially log via `trackEvent('email_capture_submit')`, future: POST to API
    - Subtle styling: `bg-gray-50`, non-intrusive, does not compete with primary CTAs
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 16.1f_

  - [ ]* 4.5 Write property test for email capture validation (Property 6)
    - **Property 6: Email capture validation**
    - Generate random strings and valid email addresses, verify validation correctly accepts/rejects
    - **Validates: Requirements 14.4**

  - [x] 4.6 Wire new components into `FrontEndCode/src/pages/Home.tsx`
    - Import and add `EaseOfUseStrip` between `HeroSection` and `HowItWorksSection`
    - Replace `TestimonialSection` import/usage with `FounderStorySection` (remove the TestimonialSection import)
    - Import and add `EmailCaptureSection` between `ClosingCTASection` and `TrustStrip`
    - Note: MicroSocialProof is NOT added here — it will be integrated into HeroSection in task 7.7
    - Section order: Header → HeroSection → EaseOfUseStrip → HowItWorksSection → SampleQuestionsSection → FounderStorySection → ClosingCTASection → EmailCaptureSection → TrustStrip → Footer
    - _Requirements: 3.1, 12.1, 12.5, 14.1_

- [x] 5. Checkpoint — Verify new landing page components render correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Expandable How It Works cards
  - [x] 6.1 Modify `HowItWorksCard.tsx` and `HowItWorksSection.tsx` together for accordion expansion
    - **HowItWorksCard.tsx**: Add new props: `expandedDescription: string`, `isExpanded: boolean`, `onToggle: () => void`
    - Collapsed state: show step number, icon, title, description, and "Learn more" text with chevron affordance
    - Expanded state: reveal placeholder screenshot area (gradient bg + "Screenshot coming soon"), extended description, and "Try it now →" mini-CTA linking to signup
    - Smooth animation: `transition-all duration-300 ease-in-out`
    - Call `trackEvent('how_it_works_expand', { step })` / `trackEvent('how_it_works_collapse', { step })` on toggle
    - **HowItWorksSection.tsx**: Add `expandedStep` state (`number | null`), default `null`
    - Toggle logic: clicking an expanded card collapses it, clicking a different card collapses the previous and expands the new one
    - Pass `expandedDescription`, `isExpanded`, and `onToggle` props to each `HowItWorksCard`
    - Define expanded descriptions for each step
    - IMPORTANT: Both files must be modified in the same task because the new required props on HowItWorksCard will cause TypeScript errors if the section isn't updated simultaneously
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 16.1c_

  - [ ]* 6.2 Write property tests for accordion behavior (Properties 2 & 3)
    - **Property 2: Accordion toggle round-trip** — expand then collapse returns to null state
    - **Property 3: Accordion mutual exclusion** — at most one card expanded at any time after any sequence of clicks
    - **Validates: Requirements 5.2, 5.9**

- [x] 7. Modal signup flow (extract shared forms, create SignupModal, integrate into HeroSection)
  - [x] 7.1 Extract `FrontEndCode/src/components/signup/CreateLegacyFormFields.tsx`
    - Move form state, validation logic, and submit handler from `SignUpCreateLegacy.tsx` into this shared component
    - Props: `onSuccess?: () => void`, `inviteToken?: string | null`, `showInviteBanner?: boolean`
    - Preserve all validation rules: required fields, email format, password strength (8+ chars, uppercase, lowercase, number), password confirmation, name format (2-50 chars, letters only)
    - Preserve `signupWithPersona` call with persona params `create_legacy` / `legacy_maker` (or `create_legacy_invited` with invite token)
    - Preserve invite token detection and banner display
    - Uses `useAuth()` internally
    - _Requirements: 4.8, 4.14, 4.16_

  - [x] 7.2 Extract `FrontEndCode/src/components/signup/StartTheirLegacyFormFields.tsx`
    - Move form state, validation logic, and submit handler from `SignUpStartTheirLegacy.tsx` into this shared component
    - Props: `onSuccess?: () => void`
    - Preserve `signupWithPersona` call with persona params `setup_for_someone` / `legacy_benefactor`
    - No invite token handling
    - _Requirements: 4.9, 4.15, 4.17_

  - [x] 7.3 Refactor `FrontEndCode/src/pages/SignUpCreateLegacy.tsx` to use shared form
    - Become a thin wrapper: reads `?invite=` from URL, renders Card layout with Logo, renders `<CreateLegacyFormFields>`
    - Standalone page behavior preserved for direct URL navigation and invite token flow
    - _Requirements: 4.10, 4.12_

  - [x] 7.4 Refactor `FrontEndCode/src/pages/SignUpStartTheirLegacy.tsx` to use shared form
    - Become a thin wrapper: renders Card layout with Logo, renders `<StartTheirLegacyFormFields>`
    - Standalone page behavior preserved for direct URL navigation
    - _Requirements: 4.11_

  - [ ]* 7.5 Write property test for signup form validation (Property 1)
    - **Property 1: Signup form validation correctness**
    - Generate random string inputs for all fields, verify validation accepts/rejects correctly per the rules
    - **Validates: Requirements 4.14, 4.15**

  - [x] 7.6 Create `FrontEndCode/src/components/landing/SignupModal.tsx`
    - Use shadcn `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`
    - Props: `open: boolean`, `onOpenChange: (open: boolean) => void`, `variant: 'create-legacy' | 'start-their-legacy'`
    - Render `CreateLegacyFormFields` or `StartTheirLegacyFormFields` based on variant
    - Mobile: `max-h-[90vh] overflow-y-auto w-[95vw]` for near-full-screen
    - Desktop: centered overlay with `max-w-lg`
    - Z-index: `z-[60]` on overlay and content to sit above sticky header
    - `onSuccess` callback closes the modal; auth context handles redirect
    - Fire `trackEvent('signup_modal_open', { variant })` and `trackEvent('signup_modal_close', { variant })`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.18, 1.9, 16.1b_

  - [x] 7.7 Integrate SignupModal into `FrontEndCode/src/components/landing/HeroSection.tsx`
    - Add modal state: `modalOpen`, `modalVariant`
    - Change "Start Free" and "Start Their Legacy" from `<Link>` to `<button>` elements that open the modal with the appropriate variant (for unauthenticated users only)
    - Preserve the "Free forever. No credit card required." micro-copy under "Start Free" (from task 2.5)
    - Preserve the "Set it up for a parent, grandparent, or loved one" subtitle under "Start Their Legacy"
    - Add `MicroSocialProof` component below the CTA buttons area
    - Fire `trackEvent('hero_cta_click', { variant })` on button clicks
    - _Requirements: 4.1, 4.2, 11.1, 10.3, 16.1a_

- [x] 8. Checkpoint — Verify modal signup, shared forms, and expandable cards
  - Ensure all tests pass
  - Manually verify standalone signup pages still work via direct URL: `/signup-create-legacy`, `/signup-start-their-legacy`, `/signup-create-legacy?invite=TOKEN`
  - Verify navigation from `LegacyCreateChoice` renders standalone pages (not modal)
  - _Requirements: 4.10, 4.11, 4.12, 4.13_
  - Ask the user if questions arise.

- [x] 9. Discover page and SEO
  - [x] 9.1 Create `FrontEndCode/src/pages/Discover.tsx` with all required sections
    - Reuse Landing Header and Footer pattern from `Home.tsx` (including sticky header with `sticky top-0 z-50 bg-white/95 backdrop-blur-sm`)
    - Sections: Hero/Intro (`<h1>`), Content Paths (3 paths with descriptions, sample questions, benefits), How the Conversation Works, Who is SoulReel For? (two persona cards with CTAs), Security & Privacy, Device Compatibility, Closing CTA
    - Use semantic heading hierarchy: one `<h1>`, `<h2>` for sections, `<h3>` for subsections
    - All images/placeholders must have descriptive `alt` text
    - Naturally incorporate SEO terms: "preserve family stories," "record memories," "legacy video recording," "grandparent stories," "family history"
    - Responsive layout for mobile, tablet, desktop
    - Primary CTA triggers SignupModal (if available), secondary CTA "See a sample conversation" links to the "How the Conversation Works" section on the same page via anchor scroll (e.g., `#how-it-works`)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.11, 7.13, 15.3, 15.4, 15.5_

  - [x] 9.2 Implement floating CTA on Discover page
    - Fixed-position "Sign Up" button that appears after scrolling past the first section
    - Uses `IntersectionObserver` on first section and closing CTA section
    - Shows when first section exits viewport, hides when closing CTA enters viewport
    - Desktop: fixed bottom-right. Mobile: fixed bottom bar
    - Graceful degradation if `IntersectionObserver` unavailable (always show CTA)
    - Fire `trackEvent('discover_floating_cta_click')` on click
    - _Requirements: 7.12, 16.2c_

  - [ ]* 9.3 Write property test for floating CTA visibility logic (Property 5)
    - **Property 5: Floating CTA visibility logic**
    - For all combinations of `(scrolledPastFirstSection, closingCTAInView)`, verify visibility equals `scrolledPast && !closingInView`
    - **Validates: Requirements 7.12**

  - [x] 9.4 Add SEO meta tags to Discover page via `useEffect`
    - Set `document.title` to "Preserve Family Stories | Record Memories with SoulReel"
    - Create/update `<meta name="description">` with compelling summary under 160 characters
    - Clean up meta tag on unmount
    - _Requirements: 15.1, 15.2_

  - [x] 9.5 Add `/discover` route to `FrontEndCode/src/App.tsx` and update "Explore more questions" link
    - Import `Discover` page component
    - Add `<Route path="/discover" element={<Discover />} />` in the public routes section
    - Update `SampleQuestionsSection.tsx`: change "Explore more questions →" link target from `/legacy-create-choice` to `/discover`
    - Add `trackEvent('explore_questions_click')` on the "Explore more questions" link click
    - _Requirements: 7.1, 7.9, 7.10, 16.1d_

  - [x] 9.6 Integrate analytics events into Discover page
    - Fire `trackEvent('discover_page_view')` on mount
    - Fire `trackEvent('discover_section_view', { section })` when each section scrolls into view (via IntersectionObserver)
    - Fire `trackEvent('discover_closing_cta_click')` and `trackEvent('discover_persona_cta_click', { persona })` on CTA clicks
    - _Requirements: 16.2a, 16.2b, 16.2d, 16.2e_

- [x] 10. Final analytics wiring and footer tracking
  - [x] 10.1 Add `trackEvent('footer_privacy_click')` to the "Privacy & Your Data" link in the `Home.tsx` footer
    - _Requirements: 16.1g_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after major milestones
- Property tests validate universal correctness properties from the design document
- The analytics utility is created first because many subsequent components depend on it
- The modal signup flow (task 7) is the most architecturally complex change — shared form extraction must happen before the modal can be built
- The Discover page (task 9) is the largest single feature but has few dependencies on other tasks beyond analytics and the SignupModal
