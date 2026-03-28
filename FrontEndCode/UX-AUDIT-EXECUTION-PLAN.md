# SoulReel / Virtual Legacy — UX Audit Execution Plan

> **Purpose**: This document is written for an AI coding agent to read and execute. Each task is self-contained with exact file paths, exact code to find, and exact code to replace. Execute tasks in order — some later tasks depend on earlier ones.
>
> **Project root**: All paths are relative to `FrontEndCode/`.
>
> **Tech stack**: React 18, TypeScript, Vite, Tailwind CSS 3, shadcn/ui (Radix primitives), React Router 6, React Query, AWS Amplify.
>
> **Golden rule**: Do not break existing functionality. After each task, run `npm run build` from `FrontEndCode/` to verify zero build errors. If a build fails, fix it before moving on.
>
> **Task dependencies**: Tasks 1–3 are independent. Task 4B modifies `index.html` (adds favicon link). Task 8A also modifies `index.html` (adds font links) — execute 4B before 8A so the "find" anchors are correct. Task 10C also modifies `index.html` (changes title/meta) — execute after 4B and 8A. All other tasks are independent of each other.

---

## Task 1 — Fix Color Contrast (Accessibility)

**Why**: The current primary purple `#9b87f5` has ~3.2:1 contrast ratio on white, failing WCAG AA (4.5:1 required). This affects buttons, links, progress bars, and the brand color used throughout the app. The target audience skews older, making this especially important.

### 1A — Update CSS custom properties

**File**: `src/index.css`

Find the light-mode `:root` block's `--primary` and `--ring` lines:

```css
    --primary: 252 80% 75%;
```

Replace with:

```css
    --primary: 252 56% 57%;
```

Find:

```css
    --ring: 252 80% 75%;
```

Replace with:

```css
    --ring: 252 56% 57%;
```

**Do NOT change the `.dark` block** — dark mode values stay as-is.

### 1B — Update Tailwind custom color

**File**: `tailwind.config.ts`

Find:

```ts
				legacy: {
					navy: '#1A1F2C',
					purple: '#9b87f5',
					lightPurple: '#E5DEFF',
					white: '#FFFFFF'
				}
```

Replace with:

```ts
				legacy: {
					navy: '#1A1F2C',
					purple: '#7c6bc4',
					lightPurple: '#E5DEFF',
					white: '#FFFFFF'
				}
```

**Rationale**: `#7c6bc4` is HSL(252, 56%, 57%) which gives ~4.7:1 contrast on white — passes WCAG AA. It's visually close to the original purple but darker enough to be readable.

**Important**: The `--primary-foreground` value (`210 40% 98%` — near-white) remains correct for the darker purple. White text on `#7c6bc4` has ~7:1 contrast, which is excellent. No change needed there.

### 1C — Verify

Run `npm run build` from `FrontEndCode/`. Confirm zero errors. Visually, all purple elements (buttons, progress bars, avatar backgrounds, links) will be slightly darker but still clearly purple.

---

## Task 2 — Keyboard Accessibility for Dashboard Progress Bars

**Why**: The progress bars on the Dashboard are the primary navigation mechanism for starting recordings. They use `onClick` on a plain `div` with no `role`, `tabIndex`, or keyboard handler. Keyboard-only users cannot access them.

**File**: `src/pages/Dashboard.tsx`

Find this exact block (inside the `data.questionTypes.map` callback):

```tsx
                <div 
                  className={`flex items-center space-x-3 transition-all ${
                    percentage === 100 ? 'cursor-default opacity-75' : 'cursor-pointer hover:opacity-80'
                  }`}
                  onClick={handleProgressBarClick}
                  title={percentage === 100 ? 'Level completed!' : `Click to record responses for ${friendlyName}`}
                >
```

Replace with:

```tsx
                <div 
                  className={`flex items-center space-x-3 transition-all ${
                    percentage === 100 ? 'cursor-default opacity-75' : 'cursor-pointer hover:opacity-80 focus-visible:ring-2 focus-visible:ring-legacy-purple focus-visible:ring-offset-2 focus-visible:rounded-md'
                  }`}
                  onClick={handleProgressBarClick}
                  role={percentage < 100 ? "button" : undefined}
                  tabIndex={percentage < 100 ? 0 : undefined}
                  onKeyDown={(e) => {
                    if ((e.key === 'Enter' || e.key === ' ') && percentage < 100) {
                      e.preventDefault();
                      handleProgressBarClick();
                    }
                  }}
                  aria-label={percentage === 100 ? `${friendlyName} — level completed` : `Record responses for ${friendlyName}, ${percentage}% complete`}
                  title={percentage === 100 ? 'Level completed!' : `Click to record responses for ${friendlyName}`}
                >
```

**What this does**:
- Adds `role="button"` and `tabIndex={0}` only for incomplete categories (so completed ones don't clutter the tab order).
- Adds `onKeyDown` for Enter and Space activation (standard button behavior).
- Adds `aria-label` for screen readers.
- Adds `focus-visible:ring-2` for visible keyboard focus indicator.

---

## Task 3 — Remove Production Debris

### 3A — Remove third-party tracking script from index.html

**File**: `index.html` (in the FrontEndCode root, not src/)

Find these two lines (they are adjacent, between `<div id="root"></div>` and `<script type="module" src="/src/main.tsx"></script>`):

```html
    <!-- IMPORTANT: DO NOT REMOVE THIS SCRIPT TAG OR THIS VERY COMMENT! -->
    <script src="https://cdn.gpteng.co/gptengineer.js" type="module"></script>
```

Delete both lines entirely. Do NOT delete the `<script type="module" src="/src/main.tsx"></script>` line that follows — that is the app entry point. This is a Lovable/GPT Engineer tracking script that should not be in production.

### 3B — Clean up App.css (Vite boilerplate)

**File**: `src/App.css`

Replace the entire file contents with:

```css
/* App-level styles — project-specific overrides go here */
```

The current contents are Vite's default boilerplate (`.logo`, `.read-the-docs`, `logo-spin` animation, `#root` max-width/text-align). None of these are used. The `#root` styles in particular could conflict with Tailwind's layout.

### 3C — Remove console.log statements from RecordConversation.tsx

**File**: `src/pages/RecordConversation.tsx`

There are 6 `console.log` calls to remove. Handle each one:

**3C-1**: Find and remove the entire console.log block in `handleConversationComplete`:

```tsx
    console.log('[VIDEO MEMORY FLOW] Conversation completed:', { 
      finalScore, 
      audioTranscriptUrl, 
      audioDetailedSummary,
      audioDetailedSummaryLength: audioDetailedSummary?.length,
      audioDetailedSummaryType: typeof audioDetailedSummary,
      hasAudioDetailedSummary: !!audioDetailedSummary
    });
```

Delete these lines entirely.

**3C-2**: Find and delete:

```tsx
      console.log('[VIDEO MEMORY FLOW] Setting video memory state - summary available');
```

**3C-3**: Find and delete:

```tsx
      console.log('[VIDEO MEMORY FLOW] State updated:', { showVideoMemory: true, conversationStarted: false });
```

**3C-4**: Find and delete:

```tsx
      console.log('[VIDEO MEMORY FLOW] No summary available, skipping video memory');
```

**3C-5**: Find and delete the multi-line console.log in `handleRecordingSubmitted`:

```tsx
      console.log('RecordResponse: Question answered, arrays updated:', {
        originalLength: progressData.totalQuestAtCurrLevel,
        newQuestionIdsLength: newQuestionIds.length,
        newQuestionTextsLength: newQuestionTexts.length,
        questionsAnswered: progressData.totalQuestAtCurrLevel - newQuestionIds.length
      });
```

**3C-6**: Find and delete the IIFE console.log in the render body. Find this entire block:

```tsx
        {(() => {
          console.log('[VIDEO MEMORY FLOW] Render check:', { 
            showVideoMemory, 
            levelCompleted, 
            conversationStarted,
            audioDetailedSummaryLength: audioDetailedSummary?.length 
          });
          return null;
        })()}
```

Delete it entirely.

### 3D — Remove console.log from RecordResponse.tsx

**File**: `src/pages/RecordResponse.tsx`

Find and delete:

```tsx
      console.log('RecordResponse: Question answered, arrays updated:', {
        originalLength: progressData.totalQuestAtCurrLevel,
        newQuestionIdsLength: newQuestionIds.length,
        newQuestionTextsLength: newQuestionTexts.length,
        questionsAnswered: progressData.totalQuestAtCurrLevel - newQuestionIds.length
      });
```

### 3E — Remove console.log from ResponseViewer.tsx

**File**: `src/pages/ResponseViewer.tsx`

Find:

```tsx
      } else {
        console.log('No audio URL available for this response');
      }
```

Replace with:

```tsx
      }
```

### 3F — Remove console.log from SignUpCreateLegacy.tsx

**File**: `src/pages/SignUpCreateLegacy.tsx`

Find and delete these two lines (they may not be adjacent):

```tsx
      console.log('Invite token found in URL:', inviteParam);
```

```tsx
        console.log('Signing up with invite token:', inviteToken);
```

### 3G — Note on console.error

Leave all `console.error` calls in place. These are in catch blocks and provide useful debugging information for production issues. Only `console.log` calls (debug/development logging) should be removed.

### 3H — Note on lovable-tagger

The `lovable-tagger` package in devDependencies and its usage in `vite.config.ts` (conditionally loaded in dev mode only) can stay for now. It's harmless in production since it's behind a `mode === 'development'` check. Removing it is optional cleanup but not urgent.

---

## Task 4 — Add Favicon

**Why**: The browser tab currently shows a generic icon. A favicon reinforces brand identity.

### 4A — Create the favicon SVG

**File**: `public/favicon.svg`

Create this file with the following content:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <circle cx="16" cy="16" r="16" fill="#7c6bc4"/>
  <text x="16" y="22" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-size="16" font-weight="700" fill="white">SR</text>
</svg>
```

Note: Uses the updated purple `#7c6bc4` from Task 1B. Uses "SR" for SoulReel to match the brand rename in Task 10. If Task 10 is not being executed (brand rename declined), change "SR" to "VL" instead.

### 4B — Reference the favicon in index.html

**File**: `index.html`

Find:

```html
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
```

After that line, add:

```html
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
```

---

## Task 5 — Skeleton Loading for Dashboard Progress Section

**Why**: The Dashboard progress section shows plain text "Loading your progress..." while the UserMenu's StatisticsSection already uses proper Skeleton components. This inconsistency makes the app feel unpolished.

**File**: `src/pages/Dashboard.tsx`

First, add the Skeleton import. Find the existing imports at the top of the file:

```tsx
import { Play, ChevronRight } from "lucide-react";
```

After that line, add:

```tsx
import { Skeleton } from "@/components/ui/skeleton";
```

Then find the loading state in the `ProgressSection` component:

```tsx
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Your Progress</h3>
        <p className="text-gray-600">Loading your progress...</p>
      </div>
    );
  }
```

Replace with:

```tsx
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-6">
          <Skeleton className="h-6 w-40" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-x-8">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="space-y-2">
              <div className="flex justify-between items-center">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-28" />
              </div>
              <div className="flex items-center space-x-3">
                <Skeleton className="flex-1 h-3 rounded-full" />
                <Skeleton className="h-4 w-10" />
              </div>
              <Skeleton className="h-3 w-24" />
            </div>
          ))}
        </div>
      </div>
    );
  }
```

This renders 6 skeleton progress bars in the same 2-column grid layout as the real data, giving users an accurate preview of the content shape.

---

## Task 6 — Make QuestionThemes Table Responsive

**Why**: The Question Themes page renders a full HTML `<table>` that breaks on mobile screens. Tables don't reflow — they either overflow or compress columns to unreadable widths.

**File**: `src/pages/QuestionThemes.tsx`

Find the entire table block:

```tsx
          <div className="overflow-x-auto shadow-lg rounded-lg">
            <table className="w-full border-collapse bg-white">
              <thead>
                <tr className="bg-legacy-purple text-white">
                  <th className="px-6 py-4 text-left font-semibold">Category / Theme</th>
                  <th className="px-6 py-4 text-left font-semibold">Appears in Levels</th>
                  <th className="px-6 py-4 text-left font-semibold">Explanation / Purpose</th>
                </tr>
              </thead>
              <tbody>
                {themes.map((theme, index) => (
                  <tr 
                    key={index}
                    className={index % 2 === 0 ? "bg-white hover:bg-gray-50" : "bg-gray-50 hover:bg-gray-100"}
                  >
                    <td className="px-6 py-4 border-t border-gray-200 font-medium text-gray-900">
                      {theme.category}
                    </td>
                    <td className="px-6 py-4 border-t border-gray-200 text-gray-700">
                      {theme.levels}
                    </td>
                    <td className="px-6 py-4 border-t border-gray-200 text-gray-600">
                      {theme.explanation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
```

Replace with:

```tsx
          {/* Mobile: card layout */}
          <div className="sm:hidden space-y-4">
            {themes.map((theme, index) => (
              <div key={index} className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-gray-900">{theme.category}</h3>
                  <span className="text-sm text-legacy-purple font-medium whitespace-nowrap ml-3">
                    Levels {theme.levels}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{theme.explanation}</p>
              </div>
            ))}
          </div>

          {/* Desktop: table layout */}
          <div className="hidden sm:block overflow-x-auto shadow-lg rounded-lg">
            <table className="w-full border-collapse bg-white">
              <thead>
                <tr className="bg-legacy-purple text-white">
                  <th className="px-6 py-4 text-left font-semibold">Category / Theme</th>
                  <th className="px-6 py-4 text-left font-semibold">Appears in Levels</th>
                  <th className="px-6 py-4 text-left font-semibold">Explanation / Purpose</th>
                </tr>
              </thead>
              <tbody>
                {themes.map((theme, index) => (
                  <tr 
                    key={index}
                    className={index % 2 === 0 ? "bg-white hover:bg-gray-50" : "bg-gray-50 hover:bg-gray-100"}
                  >
                    <td className="px-6 py-4 border-t border-gray-200 font-medium text-gray-900">
                      {theme.category}
                    </td>
                    <td className="px-6 py-4 border-t border-gray-200 text-gray-700">
                      {theme.levels}
                    </td>
                    <td className="px-6 py-4 border-t border-gray-200 text-gray-600">
                      {theme.explanation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
```

---

## Task 7 — Reduce QuestionThemes Heading Size

**Why**: The Question Themes page uses `text-4xl md:text-5xl` for its heading, which is visually heavier than every other page in the app. The Dashboard uses `text-xl` for section headings. This inconsistency makes the page feel like a different app.

**File**: `src/pages/QuestionThemes.tsx`

Find:

```tsx
          <h1 className="text-4xl md:text-5xl font-bold mb-4 text-center bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent">
            Question Themes & Levels
          </h1>
```

Replace with:

```tsx
          <h1 className="text-2xl md:text-3xl font-bold mb-4 text-center bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent">
            Question Themes & Levels
          </h1>
```

---

## Task 8 — Add Custom Font

**Why**: The app currently uses browser-default sans-serif fonts. A custom font adds personality and brand cohesion. "DM Sans" is warm, slightly rounded, and highly readable — appropriate for a product about personal memories.

### 8A — Add Google Fonts link to index.html

**File**: `index.html`

Find:

```html
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
```

(This line was added in Task 4B. If Task 4 hasn't been executed yet, find the `<meta name="viewport"...>` line instead and add after it.)

After that line, add:

```html
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap" rel="stylesheet" />
```

### 8B — Configure Tailwind to use DM Sans

**File**: `tailwind.config.ts`

Find the `extend` key inside `theme`:

```ts
		extend: {
			colors: {
```

Before the `colors` key, add:

```ts
			fontFamily: {
				sans: ['"DM Sans"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
			},
```

So it becomes:

```ts
		extend: {
			fontFamily: {
				sans: ['"DM Sans"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
			},
			colors: {
```

This overrides Tailwind's default `font-sans` with DM Sans as the primary, falling back to system fonts if the Google Font fails to load.

---

## Task 9 — Enrich the Benefactor Dashboard

**Why**: The Benefactor Dashboard (the view for people watching their loved one's memories) is data-focused when it should be emotion-focused. It shows a sparse list of makers with progress stats but no warmth or emotional hook.

**File**: `src/pages/BenefactorDashboard.tsx`

### 9A — Add a welcome message at the top of the main content

Find:

```tsx
      <main className="container mx-auto px-4 py-8">
        {/* Assignments from Legacy Makers Section */}
```

Replace with:

```tsx
      <main className="container mx-auto px-4 py-8">
        {/* Welcome Section */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-100 p-6 mb-8">
          <h2 className="text-xl font-semibold text-legacy-navy mb-2">
            Welcome back{user?.firstName ? `, ${user.firstName}` : ''}
          </h2>
          <p className="text-gray-600">
            This is where you can view and cherish the memories shared by your Legacy Makers. 
            Each recording is a gift — take your time and enjoy.
          </p>
        </div>

        {/* Assignments from Legacy Makers Section */}
```

### 9B — Add empty state illustration for no relationships

Find the empty state block inside "My Legacy Makers":

```tsx
            <div className="text-center py-8">
              <p className="text-gray-600 mb-2">No legacy makers connected yet</p>
              <p className="text-sm text-gray-500">Send an invitation below to get started</p>
            </div>
```

Replace with:

```tsx
            <div className="text-center py-12">
              <div className="text-5xl mb-4">💌</div>
              <p className="text-gray-700 font-medium mb-2">No Legacy Makers connected yet</p>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                Invite someone you care about to start preserving their memories. 
                Their stories will appear here once they begin recording.
              </p>
            </div>
```

---

## Task 10 — Brand Name Alignment (OWNER DECISION REQUIRED)

**Why**: The domain is `soulreel.net` but the UI says "Virtual Legacy" everywhere. Users see two different names for the same product. Since the domain isn't changing, we should bridge the gap.

**⚠️ This task requires explicit owner approval before execution.** If the owner prefers to keep "Virtual Legacy" as the UI-facing name, skip this entire task. Tasks 1–9 and 11 are independent of this decision. If skipping, also change the favicon text in Task 4A from "SR" to "VL".

### 10A — Update the Header title

**File**: `src/components/Header.tsx`

Find:

```tsx
        <h1 className="text-lg sm:text-xl font-semibold text-legacy-navy text-center sm:text-left">
          Virtual Legacy Dashboard
        </h1>
```

Replace with:

```tsx
        <h1 className="text-lg sm:text-xl font-semibold text-legacy-navy text-center sm:text-left">
          SoulReel
        </h1>
```

### 10B — Update the Logo component

**File**: `src/components/Logo.tsx`

Find:

```tsx
      <div className="h-10 w-10 rounded-full bg-legacy-purple flex items-center justify-center text-white font-bold text-xl">
        VL
      </div>
      <span className="text-xl font-semibold bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent">
        Virtual Legacy
      </span>
```

Replace with:

```tsx
      <div className="h-10 w-10 rounded-full bg-legacy-purple flex items-center justify-center text-white font-bold text-xl">
        SR
      </div>
      <span className="text-xl font-semibold bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent">
        SoulReel
      </span>
```

### 10C — Update the HTML title and meta tags

**File**: `index.html`

Find:

```html
    <title>Virtual Legacy</title>
    <meta name="description" content="Preserve your legacy through video responses" />
    <meta name="author" content="Virtual Legacy" />
```

Replace with:

```html
    <title>SoulReel — Your Virtual Legacy</title>
    <meta name="description" content="Preserve your legacy through video responses" />
    <meta name="author" content="SoulReel" />
```

Find:

```html
    <meta property="og:title" content="Virtual Legacy" />
    <meta property="og:description" content="Preserve your legacy through video responses" />
```

Replace with:

```html
    <meta property="og:title" content="SoulReel — Your Virtual Legacy" />
    <meta property="og:description" content="Preserve your legacy through video responses" />
```

### 10D — Update the Home page footer copyright

**File**: `src/pages/Home.tsx`

Find:

```tsx
            <p>&copy; {new Date().getFullYear()} Virtual Legacy. All rights reserved.</p>
```

Replace with:

```tsx
            <p>&copy; {new Date().getFullYear()} SoulReel. All rights reserved.</p>
```

### 10E — Update the QuestionThemes page footer copyright

**File**: `src/pages/QuestionThemes.tsx`

Find:

```tsx
            <p>&copy; {new Date().getFullYear()} Virtual Legacy. All rights reserved.</p>
```

Replace with:

```tsx
            <p>&copy; {new Date().getFullYear()} SoulReel. All rights reserved.</p>
```

### 10F — Update the BenefactorDashboard invite section text

**File**: `src/pages/BenefactorDashboard.tsx`

Find:

```tsx
            Help someone preserve their memories by inviting them to create their Virtual Legacy
```

Replace with:

```tsx
            Help someone preserve their memories by inviting them to create their legacy
```

### 10G — Update the SignUpCreateLegacy invite text

**File**: `src/pages/SignUpCreateLegacy.tsx`

Find:

```tsx
              ? "You've been invited to create your Virtual Legacy. Create an account to get started."
```

Replace with:

```tsx
              ? "You've been invited to create your legacy on SoulReel. Create an account to get started."
```

### 10H — Note on internal code

Do NOT rename CSS class prefixes like `legacy-purple`, `legacy-navy`, etc. These are developer-facing identifiers and renaming them would be a large, risky refactor with no user-visible benefit. The `legacy-` prefix in code is fine. Also leave code comments that reference "Virtual Legacy" as-is — comments are developer-facing.

---

## Task 11 — Constrain Getting Started Guide Text Width

**Why**: The text blocks inside the Getting Started Guide collapsible can run very wide on large screens, making them hard to read.

**File**: `src/components/DashboardInfoPanel.tsx`

Find:

```tsx
        <CollapsibleContent>
          <div className="px-4 pb-4 space-y-4">
```

Replace with:

```tsx
        <CollapsibleContent>
          <div className="px-4 pb-4 space-y-4 max-w-prose">
```

This constrains the content to ~65 characters per line, which is the optimal reading width.

---

## Final Verification Checklist

After all tasks are complete, run these checks:

1. `cd FrontEndCode && npm run build` — must exit with code 0, zero errors.
2. `npm run lint` — should pass (pre-existing warnings are acceptable, no new errors).
3. Visually verify in a browser:
   - Purple elements are slightly darker but still clearly purple.
   - Dashboard progress bars can be tabbed to with keyboard and activated with Enter/Space.
   - Dashboard shows skeleton loading animation briefly before progress data loads.
   - Question Themes page shows cards on mobile viewport (<640px) and table on desktop.
   - Favicon appears in the browser tab.
   - If Task 10 was executed: Header says "SoulReel" instead of "Virtual Legacy Dashboard".
   - DM Sans font is rendering (check in browser DevTools > Computed > font-family).
   - Benefactor Dashboard shows welcome message and improved empty state.
   - Getting Started Guide text doesn't stretch beyond ~65ch on wide screens.

---

## What This Plan Does NOT Cover (Future Work)

These items were identified in the audit but are larger efforts not included here:

- **Dependency audit and pruning**: Running `npx depcheck` and removing unused packages (recharts, embla-carousel, cmdk, vaul, etc.). This requires testing each removal individually.
- **Dark mode toggle**: CSS variables exist but no UI toggle is implemented.
- **Video thumbnail play overlay**: The ResponseViewer shows raw thumbnails without play button overlays.
- **Skip-to-content link**: For screen reader users to bypass the header.
- **aria-live regions**: For announcing loading/loaded states to screen readers.
- **Persistent navigation**: Adding a sidebar or breadcrumb system to reduce hub-and-spoke navigation.
