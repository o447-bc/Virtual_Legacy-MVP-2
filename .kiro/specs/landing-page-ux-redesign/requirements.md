# Requirements Document

## Introduction

The SoulReel landing page (Home.tsx) needs a UX redesign to improve visual hierarchy, emotional engagement, and conversion. The current page is text-heavy with a flat, monotone purple palette, no video or animation despite being a video recording product, and several structural issues that weaken trust and mobile usability. This spec covers redesigning the hero section with a video embed, introducing an optional warm accent color for primary CTAs, improving section structure, strengthening social proof, adding trust signals, and fixing mobile spacing.

## Glossary

- **Landing_Page**: The public-facing Home component at route `/` rendered by `FrontEndCode/src/pages/Home.tsx`
- **Hero_Section**: The top section of the Landing_Page containing the headline, subheadline, and call-to-action buttons
- **Video_Embed**: A placeholder-ready component that renders an iframe or HTML5 video element in 16:9 aspect ratio, with a poster/thumbnail state before the real HeyGen avatar video is provided
- **Accent_Color**: A warm secondary color (amber-700 `#B45309`) used on primary CTAs and step numbers to contrast with the existing purple palette. Controlled by a single config constant so it can be reverted to legacy-purple in one line.
- **How_It_Works_Section**: The three-card section explaining the SoulReel flow (Choose a Question, Have a Conversation, Share)
- **Testimonial_Section**: The social proof section currently showing a single anonymous quote
- **Trust_Strip**: A horizontal strip near the bottom of the Landing_Page displaying privacy and security signals with icons
- **Closing_CTA_Section**: A warm call-to-action section replacing the inline pricing section, driving users to `/pricing` or signup
- **Sample_Questions_Section**: The "Questions That Spark Your Story" section displaying example prompts
- **Footer**: The bottom navigation area of the Landing_Page containing links and copyright

## Requirements

### Requirement 1: Two-Column Hero Layout with Video Embed

**User Story:** As a visitor, I want to see a compelling hero section with a video demo alongside the headline, so that I immediately understand what SoulReel does and feel emotionally engaged.

#### Acceptance Criteria

1. THE Hero_Section SHALL render a two-column layout with headline, subheadline, and CTA buttons on the left column and the Video_Embed on the right column on viewports 768px and wider
2. WHEN the viewport width is below 768px, THE Hero_Section SHALL stack the text content above the Video_Embed in a single column
3. THE Video_Embed SHALL maintain a 16:9 aspect ratio at all viewport sizes
4. THE Video_Embed SHALL display a poster/thumbnail state with a centered play icon when no video source URL is provided
5. WHEN a video source URL is provided via props, THE Video_Embed SHALL render the video content in place of the poster state
6. THE Hero_Section SHALL use vertical padding of py-12 on mobile viewports (below 768px) to keep CTA buttons above the fold on standard mobile screens

### Requirement 2: Warm Accent Color for Primary CTAs (Revertible)

**User Story:** As a visitor, I want primary action buttons to stand out visually from the purple background, so that I can quickly identify the next step to take.

#### Acceptance Criteria

1. THE Landing_Page SHALL define `legacy.warmAccent` (#B45309) and `legacy.warmAccentHover` (#92400E) in the Tailwind configuration under the `legacy` color namespace
2. THE Landing_Page SHALL centralize the primary CTA color choice in a single constant (`PRIMARY_CTA_CLASSES`) in a shared config file (`colorConfig.ts`), so reverting to legacy-purple requires changing only one boolean
3. THE Landing_Page SHALL apply the Accent_Color as the background color on all primary CTA buttons ("Start Free", "Start Their Legacy", "Start Recording", closing CTA primary button)
4. THE Landing_Page SHALL retain the existing legacy-purple color for secondary and outline-style buttons
5. WHEN a user hovers over a primary CTA button, THE Landing_Page SHALL use the warmAccentHover color to provide hover feedback

### Requirement 3: Step Numbers on How It Works Cards

**User Story:** As a visitor, I want to see numbered steps in the How It Works section, so that I understand the sequential flow of using SoulReel.

#### Acceptance Criteria

1. THE How_It_Works_Section SHALL display a visible step number ("1", "2", "3") on each card
2. THE How_It_Works_Section SHALL render the step number in the top-left area of each card, visually distinct from the icon and card title
3. THE How_It_Works_Section SHALL use the Accent_Color for the step number text to create visual consistency with the primary CTAs

### Requirement 4: Strengthened Testimonial Section

**User Story:** As a visitor, I want to see credible-looking testimonials with names and photos, so that I trust that real people use and value SoulReel.

#### Acceptance Criteria

1. THE Testimonial_Section SHALL display at least two testimonial cards in a horizontal layout on desktop viewports
2. WHEN the viewport width is below 768px, THE Testimonial_Section SHALL stack testimonial cards vertically
3. THE Testimonial_Section SHALL display each testimonial with an avatar placeholder image, a display name, a relationship descriptor (e.g., "Grandmother, age 74"), and a quote
4. THE Testimonial_Section SHALL use a card-based layout with visible borders or shadows to distinguish each testimonial

### Requirement 5: Replace Inline Pricing with Closing CTA Section

**User Story:** As a visitor, I want to see an inviting closing call-to-action instead of pricing details on the landing page, so that I feel encouraged to take the next step without feeling pressured by cost.

#### Acceptance Criteria

1. THE Landing_Page SHALL NOT render the inline pricing section with monthly price and billing details
2. THE Closing_CTA_Section SHALL display a warm headline (e.g., "Ready to preserve your story?") and a brief supporting sentence
3. THE Closing_CTA_Section SHALL include a primary CTA button linking to `/pricing` and a secondary CTA button linking to the signup flow
4. THE Closing_CTA_Section SHALL use a visually distinct background (gradient or light warm tone) to separate it from adjacent sections

### Requirement 6: Trust and Privacy Signal Strip

**User Story:** As a visitor, I want to see clear privacy and security signals, so that I feel confident my personal stories will be protected.

#### Acceptance Criteria

1. THE Trust_Strip SHALL appear between the Closing_CTA_Section and the Footer
2. THE Trust_Strip SHALL display at least three trust signals with accompanying icons (e.g., encryption, data ownership, no third-party sharing)
3. THE Trust_Strip SHALL render signals in a horizontal row on desktop and wrap gracefully on mobile viewports
4. THE Trust_Strip SHALL use muted, understated styling that does not compete with the Closing_CTA_Section above it

### Requirement 7: Mobile Spacing and Padding Fixes

**User Story:** As a mobile visitor, I want the landing page to feel well-spaced and readable on my device, so that I can comfortably browse and take action.

#### Acceptance Criteria

1. THE Landing_Page SHALL use reduced horizontal container padding (1rem instead of 2rem) on viewports below 640px
2. THE Hero_Section SHALL use py-12 on viewports below 768px instead of py-20 to keep CTAs visible above the fold
3. THE Landing_Page SHALL apply consistent vertical section spacing that avoids excessive whitespace on mobile viewports

### Requirement 8: Enhanced Sample Questions Section

**User Story:** As a visitor, I want the sample questions section to feel more engaging and interactive, so that I am drawn to explore what SoulReel offers.

#### Acceptance Criteria

1. THE Sample_Questions_Section SHALL display question cards with a subtle hover animation (e.g., slight lift or shadow increase) on desktop viewports
2. THE Sample_Questions_Section SHALL use the theme category color (legacy-purple) as a left border or top accent on each card to create visual interest
3. THE Sample_Questions_Section SHALL include a CTA link or button below the cards encouraging visitors to explore more questions

### Requirement 9: Footer Privacy Link

**User Story:** As a visitor, I want to see a Privacy / Your Data link in the footer, so that I can learn how my data is handled before signing up.

#### Acceptance Criteria

1. THE Footer SHALL include a "Privacy & Your Data" link in the Quick Links list
2. WHEN a user clicks the "Privacy & Your Data" link, THE Footer SHALL navigate to the `/your-data` route
3. THE Footer SHALL render the "Privacy & Your Data" link with the same styling as other footer links
