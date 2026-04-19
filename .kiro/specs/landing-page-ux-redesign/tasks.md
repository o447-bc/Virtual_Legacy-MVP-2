# Implementation Plan: Landing Page UX Redesign

## Overview

Incrementally extract the monolithic Home.tsx into composable landing page components, introduce a revertible warm accent color system, replace inline pricing with a closing CTA, add trust signals, strengthen testimonials, and fix mobile spacing. Each task builds on the previous — no orphaned code.

## Tasks

- [x] 1. Set up color config and Tailwind extensions
  - [x] 1.1 Add `legacy.warmAccent` (#B45309) and `legacy.warmAccentHover` (#92400E) to the `legacy` color namespace in `FrontEndCode/tailwind.config.ts`
    - _Requirements: 2.1_
  - [x] 1.2 Create `FrontEndCode/src/components/landing/colorConfig.ts` with `USE_WARM_ACCENT` toggle, exporting `PRIMARY_CTA_CLASSES`, `STEP_NUMBER_CLASSES`, and `CLOSING_CTA_GRADIENT`
    - When `USE_WARM_ACCENT` is `true`, primary CTAs use `bg-legacy-warmAccent hover:bg-legacy-warmAccentHover text-white`
    - When `false`, fall back to `bg-legacy-purple hover:bg-legacy-navy text-white`
    - _Requirements: 2.2_

- [x] 2. Create VideoEmbed component
  - [x] 2.1 Create `FrontEndCode/src/components/landing/VideoEmbed.tsx`
    - Accept optional `src`, `posterUrl`, and `title` props
    - Use Tailwind `aspect-video` class for 16:9 ratio
    - Render placeholder state (gradient bg, centered Play icon, "Watch how it works" label) when `src` is falsy
    - Render `<iframe>` or `<video>` when `src` is provided
    - Add `data-state="placeholder"` or `data-state="video"` attribute on root element
    - _Requirements: 1.3, 1.4, 1.5_
  - [ ]* 2.2 Write property test: VideoEmbed renders correct state based on src prop
    - **Property 3: VideoEmbed renders correct state based on src prop**
    - **Validates: Requirements 1.4, 1.5**

- [x] 3. Create HeroSection component
  - [x] 3.1 Create `FrontEndCode/src/components/landing/HeroSection.tsx`
    - Two-column grid (`md:grid-cols-2`): text left, VideoEmbed right
    - Single column stacked on mobile (text above video)
    - `py-12` on mobile, `md:py-20` on desktop
    - Primary CTAs ("Start Free", "Start Their Legacy", "Start Recording") use `PRIMARY_CTA_CLASSES` from colorConfig
    - Secondary CTAs retain `border-legacy-purple text-legacy-purple`
    - Accept `user` and optional `videoSrc` props
    - _Requirements: 1.1, 1.2, 1.6, 2.3, 2.4, 2.5_

- [x] 4. Create HowItWorksCard, HowItWorksSection, and refactor How It Works section
  - [x] 4.1 Create `FrontEndCode/src/components/landing/HowItWorksCard.tsx`
    - Accept `stepNumber`, `icon`, `title`, `description` props
    - Render step number in top-left using `STEP_NUMBER_CLASSES` from colorConfig
    - Keep icon circle as `bg-legacy-purple`
    - White bg, rounded-lg, shadow-md card
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 4.2 Create `FrontEndCode/src/components/landing/HowItWorksSection.tsx` wrapper that renders heading and 3 HowItWorksCards with MessageSquare, Mic, Heart icons
    - _Requirements: 3.1_
  - [ ]* 4.3 Write property test: Step number visibility in How It Works cards
    - **Property 1: Step number visibility in How It Works cards**
    - **Validates: Requirements 3.1**

- [x] 5. Create TestimonialCard and refactor Testimonial section
  - [x] 5.1 Create `FrontEndCode/src/components/landing/TestimonialCard.tsx`
    - Accept `quote`, `name`, `relationship`, optional `avatarUrl` props
    - Use shadcn `Avatar` with `AvatarFallback` for initials when no avatarUrl
    - Card layout with border/shadow
    - _Requirements: 4.3, 4.4_
  - [x] 5.2 Create `FrontEndCode/src/components/landing/TestimonialSection.tsx` wrapper that renders at least two TestimonialCards in horizontal layout on desktop (`md:grid-cols-2`), stacked vertically on mobile
    - Define static `TESTIMONIALS` array with at least two entries inside this component
    - _Requirements: 4.1, 4.2_
  - [ ]* 5.3 Write property test: Testimonial card content completeness
    - **Property 2: Testimonial card content completeness**
    - **Validates: Requirements 4.3**

- [x] 6. Checkpoint - Verify core components
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create SampleQuestionCard and enhance Sample Questions section
  - [x] 7.1 Create `FrontEndCode/src/components/landing/SampleQuestionCard.tsx`
    - Accept `category` and `question` props
    - Left border accent: `border-l-4 border-legacy-purple`
    - Hover animation: `transition-all hover:-translate-y-1 hover:shadow-lg`
    - Category label in `text-legacy-purple`
    - _Requirements: 8.1, 8.2_
  - [x] 7.2 Create `FrontEndCode/src/components/landing/SampleQuestionsSection.tsx` wrapper that renders SampleQuestionCards from a static data array and includes a CTA link below the cards encouraging visitors to sign up to explore more questions (link to `/legacy-create-choice`)
    - _Requirements: 8.3_

- [x] 8. Create ClosingCTASection and remove inline pricing
  - [x] 8.1 Create `FrontEndCode/src/components/landing/ClosingCTASection.tsx`
    - Accept `user` prop
    - Warm gradient background using `CLOSING_CTA_GRADIENT` from colorConfig
    - Headline: "Ready to preserve your story?" with supporting sentence
    - Primary CTA button → `/pricing` using `PRIMARY_CTA_CLASSES`
    - Secondary CTA link → `/legacy-create-choice`
    - _Requirements: 5.2, 5.3, 5.4_
  - [x] 8.2 Remove the inline pricing section (monthly price, billing details, `getPublicPlans` call) from Home.tsx and replace with ClosingCTASection
    - Remove `premiumPlan` state and `useEffect` for `getPublicPlans`
    - Remove `getPublicPlans` and `PlanDefinition` imports
    - _Requirements: 5.1_

- [x] 9. Create TrustStrip component
  - [x] 9.1 Create `FrontEndCode/src/components/landing/TrustStrip.tsx`
    - Display at least 3 trust signals with lucide-react icons (Shield, Lock, EyeOff)
    - Horizontal row on desktop, flex-wrap on mobile
    - Muted styling: `text-gray-500`, small text, `py-8`
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 10. Update Footer with Privacy link and fix mobile spacing
  - [x] 10.1 Add "Privacy & Your Data" link to the footer Quick Links list, navigating to `/your-data`, with same styling as other footer links
    - _Requirements: 9.1, 9.2, 9.3_
  - [x] 10.2 Apply mobile spacing fixes across the landing page
    - Add responsive padding overrides on each section's container: `px-4 sm:px-8` (1rem on mobile, 2rem on sm+) — do NOT modify the global Tailwind container config
    - Consistent vertical section spacing on mobile (reduce py values on mobile breakpoints)
    - _Requirements: 7.1, 7.2, 7.3_

- [ ] 11. Wire all components into Home.tsx
  - [x] 11.1 Refactor Home.tsx to import and compose all new landing components in order: Header → HeroSection → HowItWorksSection → SampleQuestionsSection → TestimonialSection → ClosingCTASection → TrustStrip → Footer
    - Remove all inline section JSX from Home.tsx — each section is now its own component
    - Ensure section order matches design: TrustStrip between ClosingCTA and Footer
    - Pass `user` from `useAuth()` to HeroSection and ClosingCTASection
    - Remove `premiumPlan` state, `getPublicPlans` useEffect, and related imports (moved to task 8.2)
    - _Requirements: 1.1, 5.1, 6.1_
  - [ ] 11.2 Write property test: CTA button color matches accent config
    - **Property 4: CTA button color matches accent config**
    - **Validates: Requirements 2.3, 2.4**

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- All components go under `FrontEndCode/src/components/landing/`
- The `/your-data` route protection issue (ProtectedRoute) is noted in the design as a separate fix — not part of this task list
