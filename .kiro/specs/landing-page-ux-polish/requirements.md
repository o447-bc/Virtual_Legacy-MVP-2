# Requirements Document

## Introduction

This specification covers a set of UX polish and conversion optimization enhancements to the SoulReel landing page and related public-facing pages. These changes build on the recently completed landing page redesign and address issues identified during a detailed UX and marketing review: sticky navigation, warmer copy, ease-of-use signals, modal signup flows, interactive How It Works cards, logo simplification, a new public Discover page, an improved legacy choice page, improved section subtitles, conversion micro-copy, email capture, authentic social proof, SEO optimization, and analytics tracking. The goal is to increase engagement, reduce friction, improve conversion rates, and better communicate the product's value to prospective users — many of whom may be older adults.

## Glossary

- **Landing_Page**: The public-facing home page of SoulReel, rendered by `FrontEndCode/src/pages/Home.tsx`. Contains the header, hero section, How It Works, sample questions, testimonials, closing CTA, trust strip, and footer.
- **Dashboard_Header**: The authenticated header component used on all post-login pages, rendered by `FrontEndCode/src/components/Header.tsx`.
- **Landing_Header**: The inline header section within `Home.tsx` that displays the Logo, Log In, and Sign Up buttons for unauthenticated visitors.
- **Hero_Section**: The primary above-the-fold section of the Landing_Page containing the headline, subtext, CTA buttons, and video embed, rendered by `FrontEndCode/src/components/landing/HeroSection.tsx`.
- **How_It_Works_Section**: The three-step explainer section on the Landing_Page, rendered by `FrontEndCode/src/components/landing/HowItWorksSection.tsx`.
- **How_It_Works_Card**: An individual step card within the How_It_Works_Section, rendered by `FrontEndCode/src/components/landing/HowItWorksCard.tsx`.
- **Sample_Questions_Section**: The section displaying example questions from each content path, rendered by `FrontEndCode/src/components/landing/SampleQuestionsSection.tsx`.
- **Trust_Strip**: The horizontal row of trust signals (encryption, data control, privacy) at the bottom of the Landing_Page, rendered by `FrontEndCode/src/components/landing/TrustStrip.tsx`.
- **Signup_Modal**: A dialog overlay that presents the signup form on top of the Landing_Page without navigating away, using the existing shadcn Dialog component at `FrontEndCode/src/components/ui/dialog.tsx`.
- **Create_Legacy_Form**: The signup form for users creating their own legacy, currently rendered as a full page by `FrontEndCode/src/pages/SignUpCreateLegacy.tsx`.
- **Start_Their_Legacy_Form**: The signup form for users setting up a legacy on behalf of someone else (the person signing up becomes the "benefactor" who manages the legacy; the person whose stories are preserved is the "legacy maker"). Currently rendered as a full page by `FrontEndCode/src/pages/SignUpStartTheirLegacy.tsx`.
- **Discover_Page**: A new public page at the `/discover` route that provides a deeper dive into SoulReel's content paths, conversation flow, and security information for prospective users.
- **Legacy_Choice_Page**: The existing page at `/legacy-create-choice` rendered by `FrontEndCode/src/pages/LegacyCreateChoice.tsx` that presents two signup options: "Create Your Legacy" and "Start Their Legacy".
- **Logo_Component**: The shared logo component used across the application, rendered by `FrontEndCode/src/components/Logo.tsx`.
- **Ease_Of_Use_Strip**: A new thin banner between the Hero_Section and How_It_Works_Section communicating ease of use (no typing required) and device compatibility.
- **Content_Path**: One of the three question categories in SoulReel: Life Story Reflections, Life Events, and Values & Emotions Deep Dive.
- **App_Router**: The application routing configuration in `FrontEndCode/src/App.tsx` using React Router.
- **Micro_Social_Proof**: A small, compact trust signal placed directly below or adjacent to a CTA button at the point of decision, such as "Join families already preserving their stories" or a row of avatar icons with a count.
- **Email_Capture**: A lightweight email collection form that allows non-converting visitors to subscribe for updates without creating a full account.
- **Founder_Story_Section**: A section on the Landing_Page replacing the current fabricated testimonials with an authentic founder story and mission statement, with placeholder text until the real content is provided.
- **Emotional_Urgency_Copy**: A brief, emotionally resonant line near the closing CTA that communicates the inherent time-sensitivity of preserving stories without using artificial scarcity tactics.

## Requirements

### Requirement 1: Sticky Header on Landing Page and Dashboard

**User Story:** As a visitor or authenticated user, I want the header to remain visible at the top of the screen as I scroll, so that I always have access to navigation and key actions without scrolling back up.

#### Acceptance Criteria

1. WHILE a visitor scrolls the Landing_Page, THE Landing_Header SHALL remain fixed at the top of the viewport using sticky positioning (`sticky top-0 z-50`).
2. WHILE a visitor scrolls the Landing_Page, THE Landing_Header SHALL display a semi-transparent white background (`bg-white/95`) with a backdrop blur effect (`backdrop-blur-sm`) to create a frosted glass appearance.
3. WHILE an authenticated user scrolls any dashboard page, THE Dashboard_Header SHALL remain fixed at the top of the viewport using sticky positioning (`sticky top-0 z-50`).
4. THE Dashboard_Header SHALL retain its existing `bg-white shadow-sm` styling alongside the new sticky positioning.
5. WHEN the Landing_Page first loads, THE Landing_Header SHALL render in its natural document flow position without causing any layout shift or content overlap.
6. WHEN the Dashboard page first loads, THE Dashboard_Header SHALL render in its natural document flow position without causing any layout shift or content overlap.
7. WHILE the Landing_Page is viewed on a mobile device, THE Landing_Header SHALL remain compact to preserve screen real estate.
8. WHILE the Dashboard is viewed on a mobile device, THE Dashboard_Header SHALL remain compact to preserve screen real estate.
9. WHEN the Signup_Modal (Requirement 4) is open, THE Signup_Modal SHALL render at a z-index higher than the sticky Landing_Header (e.g., `z-[60]` or higher) so the modal properly overlays the header.

---

### Requirement 2: Warmer Language for How It Works Step 2

**User Story:** As a prospective user, I want the How It Works section to use warm, human language, so that I feel emotionally connected to the product rather than intimidated by AI terminology.

#### Acceptance Criteria

1. THE How_It_Works_Section SHALL display the step 2 title as "Just Talk — We'll Listen" instead of "Have an AI-Guided Conversation".
2. THE How_It_Works_Section SHALL display the step 2 description as "Just talk naturally. We'll ask the right follow-up questions to help you uncover the moments that matter most." instead of "Our AI interviewer asks follow-up questions to draw out the deeper story behind your answer."
3. THE How_It_Works_Section SHALL continue to display the Mic icon for step 2.
4. THE How_It_Works_Section SHALL not change the title, description, or icon for step 1 or step 3.

---

### Requirement 3: Ease-of-Use and Device Compatibility Strip

**User Story:** As a prospective user who may not be comfortable with technology, I want to see clear messages that SoulReel requires no typing and works on any device, so that I feel confident I can use the product regardless of my technical ability or device.

#### Acceptance Criteria

1. THE Landing_Page SHALL display an Ease_Of_Use_Strip between the Hero_Section and the How_It_Works_Section.
2. THE Ease_Of_Use_Strip SHALL display two messages in a single horizontal row on desktop: (a) "No typing required — just press record and talk" accompanied by a Mic icon, and (b) "Works on computer, tablet, or phone" accompanied by Monitor, Smartphone, and Tablet icons from lucide-react.
3. THE Ease_Of_Use_Strip SHALL use a subtle, light background color that visually separates it from adjacent sections without dominating the page.
4. THE Ease_Of_Use_Strip SHALL center its content horizontally within the container.
5. THE Ease_Of_Use_Strip SHALL render as a thin banner strip, not a full-height section.
6. THE Ease_Of_Use_Strip SHALL use muted, understated styling consistent with the Trust_Strip (gray text, small icons).
7. WHILE the Landing_Page is viewed on a mobile device, THE Ease_Of_Use_Strip SHALL stack the two messages vertically and remain readable without breaking the layout.

---

### Requirement 4: Modal Signup Overlay from Landing Page

**User Story:** As a prospective user clicking a signup CTA on the landing page, I want the signup form to appear as a modal overlay on top of the landing page, so that I maintain my mental context and can easily return to browsing if I change my mind.

#### Acceptance Criteria

1. WHEN an unauthenticated visitor clicks the "Start Free" button in the Hero_Section, THE Landing_Page SHALL open a Signup_Modal containing the Create_Legacy_Form.
2. WHEN an unauthenticated visitor clicks the "Start Their Legacy" button in the Hero_Section, THE Landing_Page SHALL open a Signup_Modal containing the Start_Their_Legacy_Form.
3. WHILE the Signup_Modal is open, THE Landing_Page SHALL remain visible but dimmed behind the modal with a backdrop overlay and blur effect.
4. THE Signup_Modal SHALL include a close button (X icon) that, when clicked, closes the modal and returns the user to the Landing_Page.
5. THE Signup_Modal SHALL use the existing shadcn Dialog component (`FrontEndCode/src/components/ui/dialog.tsx`) for the overlay implementation.
6. WHILE the Signup_Modal is viewed on a mobile device, THE Signup_Modal SHALL display as full-screen or near-full-screen for usability.
7. WHILE the Signup_Modal is viewed on a desktop device, THE Signup_Modal SHALL display as a centered overlay with appropriate max-width constraints.
8. THE signup form fields, validation logic, and submit handler for Create_Legacy_Form SHALL be extracted into a shared component that both the Signup_Modal and the standalone `SignUpCreateLegacy` page can render.
9. THE signup form fields, validation logic, and submit handler for Start_Their_Legacy_Form SHALL be extracted into a shared component that both the Signup_Modal and the standalone `SignUpStartTheirLegacy` page can render.
10. WHEN a user navigates directly to `/signup-create-legacy` via URL, THE App_Router SHALL render the full standalone `SignUpCreateLegacy` page as it does today.
11. WHEN a user navigates directly to `/signup-start-their-legacy` via URL, THE App_Router SHALL render the full standalone `SignUpStartTheirLegacy` page as it does today.
12. WHEN a user navigates to `/signup-create-legacy` with an `?invite=` query parameter, THE App_Router SHALL render the full standalone `SignUpCreateLegacy` page with invite token handling intact.
13. WHEN a user navigates from the Legacy_Choice_Page to a signup page, THE App_Router SHALL render the full standalone signup page (not the modal).
14. THE shared Create_Legacy_Form component SHALL preserve all existing form validation rules: required fields, email format, password strength (8+ characters, uppercase, lowercase, number), password confirmation match, and name format (2-50 characters, letters only).
15. THE shared Start_Their_Legacy_Form component SHALL preserve the same validation rules as criterion 14.
16. THE shared Create_Legacy_Form component SHALL preserve the existing `signupWithPersona` authentication call with persona parameters `create_legacy` / `legacy_maker`, and SHALL preserve the invite token flow: detecting the `?invite=` parameter, displaying the invite banner, and passing the invite token to `signupWithPersona` with the `create_legacy_invited` persona. Note: the invite token flow only applies to the Create_Legacy_Form, not the Start_Their_Legacy_Form.
17. THE shared Start_Their_Legacy_Form component SHALL preserve the existing `signupWithPersona` authentication call with persona parameters `setup_for_someone` / `legacy_benefactor`. Note: the person signing up via this form is the "benefactor" (the gift-giver who manages the legacy), not the person whose stories are preserved.
18. WHEN a user successfully completes signup via the Signup_Modal, THE Signup_Modal SHALL close and the application SHALL redirect the user to the confirmation/dashboard page using the same auth context redirect behavior as the standalone signup pages.

---

### Requirement 5: Expandable How It Works Cards with Screenshots

**User Story:** As a prospective user, I want to click on a How It Works card to see a screenshot or illustration of that step, so that I can better understand what the product experience looks like before signing up.

#### Acceptance Criteria

1. WHEN a visitor clicks or taps a How_It_Works_Card, THE How_It_Works_Card SHALL expand inline (accordion-style) to reveal additional content including a screenshot area and an extended description.
2. WHEN a visitor clicks or taps an expanded How_It_Works_Card, THE How_It_Works_Card SHALL collapse back to its default state.
3. THE expanded How_It_Works_Card SHALL display a placeholder image area with a gradient background and the text "Screenshot coming soon" that can be replaced with real product screenshots in the future.
4. THE expanded How_It_Works_Card SHALL display a brief additional description providing more detail about that step of the product experience.
5. THE expanded How_It_Works_Card SHALL display a mini call-to-action (e.g., "Try it now") that links to the signup flow.
6. THE How_It_Works_Card expansion SHALL use accordion-style inline expansion on all viewport sizes (mobile and desktop). This provides a consistent, non-jarring experience without the context switch of a lightbox.
7. THE How_It_Works_Card expand and collapse transitions SHALL use smooth animation (e.g., height transition with `transition-all duration-300`).
8. THE How_It_Works_Card SHALL display a visual affordance (e.g., "Learn more" text or a chevron icon) in its default collapsed state to indicate that the card is interactive.
9. WHEN one How_It_Works_Card is expanded and the visitor clicks a different How_It_Works_Card, THE previously expanded card SHALL collapse and the newly clicked card SHALL expand.

---

### Requirement 6: Logo Simplification to Wordmark

**User Story:** As a visitor, I want the SoulReel logo to look polished and intentional, so that the brand feels trustworthy and crafted rather than template-generated.

#### Acceptance Criteria

1. THE Logo_Component SHALL render only the "SoulReel" wordmark text, without the purple circle containing "SR" initials.
2. THE Logo_Component SHALL apply the existing gradient (`from-legacy-navy to-legacy-purple`) to the "SoulReel" wordmark text using `bg-gradient-to-r` and `bg-clip-text text-transparent` by default.
3. THE Logo_Component SHALL use `text-2xl font-extrabold` to give the wordmark a crafted appearance and compensate for the visual weight lost by removing the circle.
4. THE Logo_Component SHALL continue to accept a `className` prop that allows overriding styles.
5. WHEN the `className` prop includes `text-white`, THE Logo_Component SHALL conditionally NOT apply the gradient classes (`bg-gradient-to-r`, `bg-clip-text`, `text-transparent`) and instead render the wordmark in solid white. This is necessary because `bg-clip-text text-transparent` makes the text transparent to show the gradient, and `text-white` cannot override `text-transparent` via CSS specificity alone.
6. THE Logo_Component changes SHALL automatically propagate to all existing usages: Landing_Page header (`Home.tsx`), Landing_Page footer (`Home.tsx`), `SignUpCreateLegacy.tsx`, `SignUpStartTheirLegacy.tsx`, `LegacyCreateChoice.tsx`, and `PricingPage.tsx`.

---

### Requirement 7: "Discover" Deep-Dive Public Page

**User Story:** As a prospective user who wants to learn more before signing up, I want a dedicated page that explains SoulReel's content paths, conversation flow, and security practices in detail, so that I can make an informed decision.

#### Acceptance Criteria

1. THE App_Router SHALL register a public route at `/discover` that does not require authentication.
2. THE Discover_Page SHALL be accessible to unauthenticated visitors without redirect or login prompt.
3. THE Discover_Page SHALL display the same Landing_Header and footer used on the Landing_Page for visual consistency, including a link back to the Landing_Page (via the Logo in the header).
4. THE Discover_Page SHALL include a "Content Paths" section with expanded explanations of each Content_Path:
   - Life Story Reflections: description of the path, sample questions, and what users gain from it.
   - Life Events: description of the path, sample questions, and what users gain from it.
   - Values & Emotions Deep Dive: description of the path, sample questions, and what users gain from it.
5. THE Discover_Page SHALL include a "How the Conversation Works" section explaining the natural conversation flow, emphasizing ease of use, no typing requirement, and the AI follow-up question experience.
6. THE Discover_Page SHALL include a "Security & Privacy" section addressing:
   - Data protection and encryption practices.
   - User ownership of their data.
   - Deletion rights and data control.
   - A statement that data is never shared with third parties.
7. THE Discover_Page SHALL include a "Device Compatibility" section communicating that users can record from any device with a camera (computer, phone, tablet).
8. THE Discover_Page SHALL include a closing call-to-action section with primary and secondary signup buttons. If Requirement 4 (Signup_Modal) is implemented, the primary CTA should trigger the modal. Otherwise, it should link to `/legacy-create-choice`. The secondary CTA should offer "See a sample conversation" or "Try a question" linking to a relevant section or future interactive demo.
9. WHEN a visitor clicks the "Explore more questions →" link in the Sample_Questions_Section, THE Landing_Page SHALL navigate to `/discover` instead of `/legacy-create-choice`.
10. THE Discover_Page SHALL be added to the App_Router in `FrontEndCode/src/App.tsx` as a public route alongside existing public routes.
11. THE Discover_Page SHALL use responsive layout that adapts gracefully to mobile, tablet, and desktop viewports.
12. WHEN a visitor scrolls past the first section of the Discover_Page, THE Discover_Page SHALL display a sticky floating "Sign Up" CTA button (e.g., fixed to the bottom-right on desktop or as a bottom bar on mobile) that remains visible as the user reads the page. THE floating CTA SHALL hide when the closing CTA section scrolls into view, to avoid two competing CTAs on screen simultaneously. This is a proven conversion pattern for longer-form consideration pages.
13. THE Discover_Page SHALL include a "Who is SoulReel for?" section with two persona descriptions: (a) "For you" — addressing people who want to preserve their own stories, and (b) "For someone you love" — addressing people setting it up for a parent, grandparent, or loved one. Each persona should have a brief description and a relevant CTA.

---

### Requirement 8: Enhanced Sample Questions Section Subtitle

**User Story:** As a prospective user, I want to understand that SoulReel offers three distinct content paths to explore, so that I appreciate the breadth and depth of the experience before signing up.

#### Acceptance Criteria

1. THE Sample_Questions_Section SHALL display a subtitle under the "Questions That Spark Your Story" heading that explicitly mentions all three Content_Paths.
2. THE Sample_Questions_Section subtitle SHALL read: "Three paths to explore: your life story, the events that shaped you, and the values you hold dear." (or equivalent copy that names all three paths).
3. THE Sample_Questions_Section subtitle SHALL replace the existing subtitle text "Here are a few of the questions waiting for you".
4. THE Sample_Questions_Section subtitle SHALL maintain the existing styling: `text-lg text-gray-600 text-center max-w-2xl mx-auto mb-12`.

---

### Requirement 9: Enhanced Legacy Choice Page

**User Story:** As a prospective user arriving at the legacy choice page, I want to see clear explanations of the two signup options, so that I understand the difference and can choose confidently.

#### Acceptance Criteria

1. THE Legacy_Choice_Page SHALL display a brief description under each signup option explaining what it means:
   - Under "Create Your Legacy": a short explanation such as "Preserve your own stories, memories, and wisdom for the people who matter most."
   - Under "Start Their Legacy": a short explanation such as "Set it up for a parent, grandparent, or loved one — you'll manage the account and they'll record their stories."
2. THE Legacy_Choice_Page SHALL maintain its existing layout structure (centered card with two buttons) but add the descriptive text between each button and the next.
3. THE Legacy_Choice_Page SHALL use the same visual styling as the Landing_Page for consistency (legacy-purple buttons, gray descriptive text).
4. THE Legacy_Choice_Page SHALL include a link back to the Landing_Page or Discover_Page for users who want to learn more before choosing.

---

### Requirement 10: "No Credit Card Required" Micro-Copy on Hero CTAs

**User Story:** As a prospective user considering signing up, I want to see that no credit card is required for the free plan, so that I feel safe clicking the signup button without financial commitment.

#### Acceptance Criteria

1. THE Hero_Section SHALL display the text "Free forever. No credit card required." directly below the "Start Free" CTA button, in small muted text (`text-sm text-gray-500`).
2. THE "Start Free" CTA button label SHALL remain "Start Free" (do not change the button text itself).
3. THE micro-copy SHALL replace the existing subtitle "Preserve your own stories and memories" under the "Start Free" button.
4. THE ClosingCTASection SHALL also display "No credit card required" below its primary CTA button for consistency.

---

### Requirement 11: Micro Social Proof Adjacent to Hero CTAs

**User Story:** As a prospective user at the point of deciding whether to sign up, I want to see that other families are already using SoulReel, so that I feel confident I'm not the first person trying this.

#### Acceptance Criteria

1. THE Hero_Section SHALL display a Micro_Social_Proof element directly below the CTA buttons (below both the "Start Free" and "Start Their Legacy" buttons and their subtitles).
2. THE Micro_Social_Proof element SHALL display the text "Join families already preserving their stories" in small muted text (`text-sm text-gray-400`).
3. THE Micro_Social_Proof element SHALL be centered horizontally within the CTA area.
4. THE Micro_Social_Proof element SHALL be visually subtle — it should not compete with the CTA buttons for attention but should be readable at the point of decision.

---

### Requirement 12: Founder Story Replacing Fabricated Testimonials

**User Story:** As a prospective user, I want to see an authentic story about why SoulReel was created, so that I trust the product is built by real people with genuine motivation rather than seeing obviously fabricated testimonials.

#### Acceptance Criteria

1. THE Landing_Page SHALL replace the current TestimonialSection (containing fabricated quotes from "Margaret T." and "David R.") with a Founder_Story_Section.
2. THE Founder_Story_Section SHALL display the heading "My Story — Why I Built SoulReel".
3. THE Founder_Story_Section SHALL display the following founder story text:

> At my father's 80th birthday weekend, we went bourbon tasting together and spent a lot of time reflecting on his life.
>
> As he shared stories from his childhood, his early career choices, and the challenges he faced as a young adult, it hit me: these experiences shaped who he is — and they shaped the start of my own life. Yet one day they could simply be gone.
>
> Home movies capture celebrations and big events, but they don't capture the quieter, deeper parts — the memories, the decisions, the values, and the lessons that actually define a person.
>
> What was it really like growing up in a working-class family? Why did he choose the path he did? What were the turning points that mattered most to him?
>
> All of that risks being lost forever.
>
> That weekend I started building what became SoulReel — originally just for him.
>
> SoulReel lets you sit down and record honest video responses to thoughtful, guided questions about your life, your experiences, and the values that matter most. It's not about polished performances — it's about preserving your real voice and your real wisdom so your family can hear it long after you're gone.
>
> Because the stories that matter most are usually the ones no one thinks to write down… until it's too late.
>
> If you've ever wished you knew more about where your parents or grandparents came from — the real stories behind the person — then you already understand why this exists.

4. THE Founder_Story_Section SHALL use a visually distinct layout that feels personal and authentic — e.g., a single centered block with a warm background, the story in readable body text (not all italic — use italic sparingly for emphasis), and a founder attribution line at the bottom.
5. THE Founder_Story_Section SHALL maintain the same position in the page flow as the current TestimonialSection (between the Sample_Questions_Section and the ClosingCTASection).
6. THE Founder_Story_Section SHALL use the `bg-legacy-lightPurple` background to maintain visual consistency with the existing section.
7. THE Founder_Story_Section SHALL NOT display the final three lines of the original text ("Don't let those answers disappear. Start capturing yours now. Welcome to SoulReel. Let's make sure your legacy is never lost.") — these are CTA-style lines that belong in the ClosingCTASection, not the story section. The story should end on the emotional hook: "then you already understand why this exists."
8. THE Founder_Story_Section SHALL be responsive and readable on mobile viewports with appropriate text sizing and padding.

---

### Requirement 13: Emotional Urgency Copy Near Closing CTA

**User Story:** As a prospective user browsing the landing page, I want to feel a genuine emotional motivation to act now rather than later, so that I don't postpone preserving stories that matter.

#### Acceptance Criteria

1. THE ClosingCTASection SHALL display an Emotional_Urgency_Copy line above or below the headline "Ready to preserve your story?"
2. THE Emotional_Urgency_Copy SHALL read: "Every day holds stories worth preserving. Don't wait for someday." (or equivalent copy that communicates the inherent time-sensitivity of preserving stories without using artificial scarcity).
3. THE Emotional_Urgency_Copy SHALL use a slightly smaller, italic or lighter-weight font style to differentiate it from the headline while remaining readable.
4. THE Emotional_Urgency_Copy SHALL NOT use fake countdown timers, limited-time offers, or artificial scarcity language.

---

### Requirement 14: Lightweight Email Capture for Non-Converting Visitors

**User Story:** As a visitor who is interested but not ready to sign up today, I want to leave my email to stay informed, so that I can come back when I'm ready without losing track of SoulReel.

#### Acceptance Criteria

1. THE Landing_Page SHALL display an Email_Capture section between the ClosingCTASection and the Trust_Strip (or integrated into the ClosingCTASection as a secondary action).
2. THE Email_Capture SHALL display a brief prompt such as "Not ready yet? Get a free sample question delivered to your inbox." or "Stay in the loop — we'll let you know when new question paths launch."
3. THE Email_Capture SHALL include a single email input field and a submit button.
4. THE Email_Capture SHALL validate the email format before submission.
5. WHEN a visitor submits a valid email, THE Email_Capture SHALL display a success confirmation message (e.g., "You're on the list!") and clear the input field.
6. THE Email_Capture SHALL store the submitted email for future use. The storage mechanism (e.g., API endpoint, third-party service) will be determined in the design phase.
7. THE Email_Capture SHALL use subtle, non-intrusive styling that does not compete with the primary signup CTAs.
8. THE Email_Capture SHALL NOT be a popup or modal — it should be an inline section on the page.

---

### Requirement 15: SEO Optimization for Discover Page

**User Story:** As a potential user searching for ways to preserve family stories, I want the Discover page to appear in search results, so that I can find SoulReel organically.

#### Acceptance Criteria

1. THE Discover_Page SHALL include a descriptive `<title>` tag optimized for target search terms (e.g., "Preserve Family Stories | Record Memories with SoulReel").
2. THE Discover_Page SHALL include a `<meta name="description">` tag with a compelling summary of the page content, under 160 characters, optimized for search click-through.
3. THE Discover_Page SHALL use semantic heading hierarchy: one `<h1>` for the page title, `<h2>` for each major section, and `<h3>` for subsections.
4. THE Discover_Page SHALL include descriptive `alt` text on all images and placeholder images.
5. THE Discover_Page content SHALL naturally incorporate target search terms such as "preserve family stories," "record memories," "legacy video recording," "grandparent stories," and "family history" without keyword stuffing.

---

### Requirement 16: Analytics Event Tracking for Key Interactions

**User Story:** As the product owner, I want to track how visitors interact with key elements on the landing page and Discover page, so that I can measure conversion rates and optimize the funnel.

#### Acceptance Criteria

1. THE Landing_Page SHALL emit analytics events for the following interactions: (a) Hero CTA clicks ("Start Free", "Start Their Legacy"), (b) Signup_Modal open and close, (c) How_It_Works_Card expand/collapse, (d) "Explore more questions" link click, (e) Closing CTA clicks, (f) Email_Capture submission, (g) Footer "Privacy & Your Data" link click.
2. THE Discover_Page SHALL emit analytics events for: (a) page view, (b) section scroll-into-view for each major section, (c) floating CTA click, (d) closing CTA click, (e) "Who is SoulReel for?" persona CTA clicks.
3. THE analytics events SHALL include a descriptive event name and relevant metadata (e.g., which CTA was clicked, which card was expanded).
4. THE analytics implementation SHALL use a lightweight approach (e.g., a simple `trackEvent` utility function) that can be connected to any analytics provider (Google Analytics, Mixpanel, Amplitude, etc.) in the future. The initial implementation may log events to the console if no provider is configured.
5. THE analytics tracking SHALL NOT block or delay user interactions — all event tracking SHALL be non-blocking (fire-and-forget).
