# FRONTEND ARCHITECTURE ANALYSIS
## Virtual Legacy - React 18 + TypeScript + Vite

**Document Version:** 1.0  
**Last Updated:** February 14, 2026  
**Analysis Scope:** Complete frontend architecture, component structure, state management, and integration patterns

---

## TABLE OF CONTENTS

1. [Technology Stack](#technology-stack)
2. [Project Structure](#project-structure)
3. [Routing Architecture](#routing-architecture)
4. [State Management](#state-management)
5. [Component Architecture](#component-architecture)
6. [Service Layer](#service-layer)
7. [Authentication Flow](#authentication-flow)
8. [Design System](#design-system)
9. [Build Configuration](#build-configuration)
10. [Best Practices & Patterns](#best-practices--patterns)
11. [Areas for Improvement](#areas-for-improvement)

---

## 1. TECHNOLOGY STACK

### Core Framework
- **React:** 18.3.1 (latest stable)
- **TypeScript:** 5.5.3
- **Build Tool:** Vite 5.4.1 with SWC plugin
- **Router:** React Router DOM 6.26.2

### State Management
- **TanStack Query (React Query):** 5.56.2 - Server state management
- **React Context API:** Authentication and global state
- **Local Storage:** Caching (streak data)

### UI Framework
- **Radix UI:** Comprehensive primitive components (20+ packages)
- **Tailwind CSS:** 3.4.11 with custom design tokens
- **shadcn/ui:** Component library built on Radix + Tailwind
- **Lucide React:** 0.462.0 - Icon library

### AWS Integration
- **AWS Amplify:** 6.15.1 - Authentication and Storage
- **Cognito:** User authentication
- **S3:** File storage (via Amplify Storage)

### Form Management
- **React Hook Form:** 7.53.0
- **Zod:** 3.23.8 - Schema validation
- **@hookform/resolvers:** 3.9.0

### Additional Libraries
- **date-fns:** 3.6.0 - Date manipulation
- **Recharts:** 2.12.7 - Data visualization
- **Sonner:** 1.5.0 - Toast notifications
- **class-variance-authority:** 0.7.1 - Component variants
- **tailwind-merge:** 2.5.2 - Tailwind class merging

---

## 2. PROJECT STRUCTURE

```
FrontEndCode/
├── src/
│   ├── components/          # Reusable components
│   │   ├── ui/             # shadcn/ui components (50+ files)
│   │   ├── AudioVisualizer.tsx
│   │   ├── ConversationInterface.tsx
│   │   ├── ErrorBoundary.tsx
│   │   ├── FileUpload.tsx
│   │   ├── Logo.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── StreakCounter.tsx
│   │   ├── VideoMemoryRecorder.tsx
│   │   └── VideoRecorder.tsx
│   ├── pages/              # Route components (21 files)
│   ├── contexts/           # React Context providers
│   │   └── AuthContext.tsx
│   ├── services/           # API integration layer (6 files)
│   ├── hooks/              # Custom React hooks
│   │   ├── use-mobile.tsx
│   │   └── use-toast.ts
│   ├── config/             # Configuration files
│   │   └── api.ts
│   ├── lib/                # Utility functions
│   ├── App.tsx             # Main application component
│   ├── main.tsx            # Application entry point
│   ├── aws-config.ts       # AWS Amplify configuration
│   └── index.css           # Global styles
├── public/                 # Static assets
├── amplify/                # AWS Amplify backend config
├── dist/                   # Build output
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── components.json         # shadcn/ui configuration
```

### Key Directories

**`src/components/`** - 9 custom components + 50+ shadcn/ui primitives
**`src/pages/`** - 21 page components (14 active routes)
**`src/services/`** - 6 service modules for API integration
**`src/contexts/`** - AuthContext for global authentication state
**`src/hooks/`** - 2 custom hooks (mobile detection, toast)
**`src/config/`** - API endpoint configuration

---

## 3. ROUTING ARCHITECTURE

### Route Configuration (App.tsx)

```typescript
<BrowserRouter>
  <AuthProvider>
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/confirm-signup" element={<ConfirmSignup />} />
      
      {/* Onboarding Flow */}
      <Route path="/legacy-create-choice" element={<LegacyCreateChoice />} />
      <Route path="/signup-create-legacy" element={<SignUpCreateLegacy />} />
      <Route path="/signup-start-their-legacy" element={<SignUpStartTheirLegacy />} />
      
      {/* Protected Routes */}
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/benefactor-dashboard" element={<BenefactorDashboard />} />
      <Route path="/response-viewer/:makerId" element={<ResponseViewer />} />
      <Route path="/record" element={<RecordResponse />} />
      <Route path="/record-conversation" element={<RecordConversation />} />
      
      {/* Utility Routes */}
      <Route path="/test-s3" element={<TestS3 />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  </AuthProvider>
</BrowserRouter>
```

### Route Categories

#### 1. Public Routes (3)
- `/` - Landing page
- `/login` - Authentication
- `/signup` - Basic registration

#### 2. Onboarding Flow (3)
- `/legacy-create-choice` - Choose persona type
- `/signup-create-legacy` - Legacy Maker registration
- `/signup-start-their-legacy` - Benefactor registration

#### 3. Protected Routes (5)
- `/dashboard` - Legacy Maker dashboard
- `/benefactor-dashboard` - Benefactor dashboard
- `/response-viewer/:makerId` - View maker's videos
- `/record` - Record video responses
- `/record-conversation` - Conversation mode

#### 4. Utility Routes (2)
- `/test-s3` - S3 testing page
- `*` - 404 Not Found

### Navigation Patterns

**No Route Guards:** Routes don't enforce authentication at router level
**Context-Based Protection:** Components check `useAuth()` hook
**Redirect on Login:** AuthContext navigates to `/dashboard` after login
**Persona-Based Routing:** Different dashboards for Legacy Makers vs Benefactors

---

## 4. STATE MANAGEMENT

### Architecture Overview

```
┌─────────────────────────────────────────┐
│         TanStack Query Client           │
│    (Server State & Cache Management)    │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│          AuthContext Provider           │
│   (User State, Auth Methods, Loading)   │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         Component Local State           │
│      (useState, useRef, useEffect)      │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│          Local Storage Cache            │
│         (Streak Data, Tokens)           │
└─────────────────────────────────────────┘
```

### 1. AuthContext (Global Authentication State)

**Location:** `src/contexts/AuthContext.tsx`

**State:**
```typescript
interface User {
  email: string;
  id: string;
  personaType: string;  // 'legacy_maker' | 'benefactor'
  firstName?: string;
  lastName?: string;
}

const [user, setUser] = useState<User | null>(null);
const [isLoading, setIsLoading] = useState<boolean>(true);
```

**Methods:**
- `login(email, password)` - Authenticate user
- `signup(email, password, firstName, lastName)` - Basic registration
- `signupWithPersona(...)` - Registration with persona selection
- `confirmSignup(email, code)` - Email verification
- `resendConfirmationCode(email)` - Resend verification
- `logout()` - Sign out user

**Key Features:**
- Automatic auth state check on mount
- JWT token extraction from Cognito
- Persona type parsing from user attributes
- Progress initialization for Legacy Makers
- Toast notifications for all auth actions

### 2. TanStack Query (Server State)

**Configuration:**
```typescript
const queryClient = new QueryClient();

<QueryClientProvider client={queryClient}>
  <App />
</QueryClientProvider>
```

**Usage:** Currently minimal - opportunity for expansion
**Potential Use Cases:**
- Question fetching with caching
- Video list management
- Progress data synchronization
- Relationship data

### 3. Local Storage Caching

**Streak Service Cache:**
```typescript
const CACHE_KEY_PREFIX = 'streak_';
const CACHE_DURATION = 3600000; // 1 hour

interface CachedStreak {
  data: StreakData;
  timestamp: number;
}
```

**Cache Methods:**
- `getCachedStreak(userId)` - Get with cache fallback
- `invalidateCache(userId)` - Clear cache
- `updateCache(userId, data)` - Update cache

**Benefits:**
- Reduces API calls
- Improves UI responsiveness
- Automatic expiration (1 hour)

### 4. Component Local State

**Common Patterns:**
```typescript
// Form state
const [email, setEmail] = useState("");
const [errors, setErrors] = useState({});

// UI state
const [isRecording, setIsRecording] = useState(false);
const [isUploading, setIsUploading] = useState(false);

// Media refs
const videoRef = useRef<HTMLVideoElement>(null);
const mediaRecorderRef = useRef<MediaRecorder | null>(null);
```

---

## 5. COMPONENT ARCHITECTURE

### Component Categories

#### A. Page Components (21 files)

**Authentication Pages:**
- `Home.tsx` - Landing page with hero section
- `Login.tsx` - Email/password authentication
- `Signup.tsx` - Basic registration form
- `ConfirmSignup.tsx` - Email verification
- `ForgotPassword.tsx` - Password reset
- `ResetPassword.tsx` - New password entry

**Onboarding Pages:**
- `LegacyCreateChoice.tsx` - Persona selection
- `SignUpCreateLegacy.tsx` - Legacy Maker registration
- `SignUpStartTheirLegacy.tsx` - Benefactor registration

**Dashboard Pages:**
- `Dashboard.tsx` - Legacy Maker main interface
- `BenefactorDashboard.tsx` - Benefactor main interface

**Recording Pages:**
- `RecordResponse.tsx` - Video recording interface
- `RecordConversation.tsx` - Conversation mode

**Viewing Pages:**
- `ResponseViewer.tsx` - View maker's video responses

**Utility Pages:**
- `TestS3.tsx` - S3 upload testing
- `NotFound.tsx` - 404 error page

#### B. Feature Components (9 custom)

**1. VideoRecorder.tsx**

**Purpose:** Video capture and upload
**Key Features:**
- Camera/microphone permission handling
- MediaRecorder API integration
- Recording state management (start/stop/retry)
- Preview playback
- S3 upload via service layer
- Camera cleanup on unmount
- Flipped video preview (mirror effect)

**Props:**
```typescript
interface VideoRecorderProps {
  onSkipQuestion?: () => void;
  canSkip?: boolean;
  currentQuestionId?: string;
  currentQuestionType?: string;
  currentQuestionText?: string;
  onRecordingSubmitted?: () => void;
}
```

**State Management:**
- `isRecording` - Recording status
- `stream` - MediaStream object
- `recordedBlob` - Captured video blob
- `isUploading` - Upload status
- `permissionDenied` - Permission error state

**Critical Pattern - Camera Cleanup:**
```typescript
const cleanupCamera = () => {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
  }
  if (videoRef.current) {
    videoRef.current.srcObject = null;
    videoRef.current.pause();
  }
  setStream(null);
};

useEffect(() => {
  return () => cleanupCamera(); // Cleanup on unmount
}, []);
```

**2. AudioVisualizer.tsx**

**Purpose:** Real-time audio waveform visualization
**Key Features:**
- Web Audio API integration
- Frequency data analysis
- Responsive bar count (20 mobile, 30 desktop)
- Mirrored visualization (top/bottom)
- Smooth animations
- Cross-origin audio support

**Props:**
```typescript
interface AudioVisualizerProps {
  audioUrl: string | null;
  isPlaying: boolean;
  onAudioEnd?: () => void;
  className?: string;
  showBackground?: boolean;
}
```

**Technical Implementation:**
```typescript
// Audio context setup
const audioContext = new AudioContext();
const analyser = audioContext.createAnalyser();
analyser.fftSize = 2048;
analyser.smoothingTimeConstant = 0.8;

// Connect audio source
const source = audioContext.createMediaElementSource(audioRef.current);
source.connect(analyser);
analyser.connect(audioContext.destination);

// Animate bars
const dataArray = new Uint8Array(barCount);
analyser.getByteFrequencyData(dataArray);
barHeightsRef.current[i] = 2 + (value / 255) * 38;
```

**3. ConversationInterface.tsx**

**Purpose:** WebSocket-based conversation mode
**Key Features:**
- Real-time bidirectional communication
- Audio playback with visualization
- Message history display
- Connection state management
- Error handling

**4. VideoMemoryRecorder.tsx**

**Purpose:** Specialized recorder for video memories
**Similar to VideoRecorder but:**
- Different upload flag (`isVideoMemory: true`)
- Potentially different UI/UX
- Separate question flow

**5. StreakCounter.tsx**

**Purpose:** Display user's daily streak
**Features:**
- Streak count display
- Freeze availability indicator
- Visual feedback
- Real-time updates

**6. ProgressBar.tsx**

**Purpose:** Visual progress indicator
**Features:**
- Percentage-based progress
- Smooth animations
- Customizable styling

**7. FileUpload.tsx**

**Purpose:** Generic file upload component
**Features:**
- Drag-and-drop support
- File type validation
- Upload progress
- Error handling

**8. Logo.tsx**

**Purpose:** Brand logo component
**Features:**
- Consistent branding
- Customizable size/color
- Link to home page

**9. ErrorBoundary.tsx**

**Purpose:** React error boundary
**Features:**
- Catch component errors
- Fallback UI
- Error logging
- Graceful degradation

#### C. UI Components (50+ shadcn/ui)

**Location:** `src/components/ui/`

**Categories:**
1. **Form Components:** Input, Label, Textarea, Select, Checkbox, Radio, Switch
2. **Layout Components:** Card, Sheet, Dialog, Drawer, Tabs, Accordion
3. **Navigation:** Button, Dropdown Menu, Navigation Menu, Breadcrumb
4. **Feedback:** Alert, Toast, Progress, Skeleton, Badge
5. **Data Display:** Table, Avatar, Calendar, Chart
6. **Overlay:** Popover, Tooltip, Hover Card, Context Menu
7. **Advanced:** Command, Carousel, Resizable, Sidebar

**Design Philosophy:**
- Built on Radix UI primitives
- Fully accessible (ARIA compliant)
- Customizable via Tailwind
- Type-safe with TypeScript
- Composable and reusable

---

## 6. SERVICE LAYER

### Architecture Pattern

```
┌─────────────────────────────────────────┐
│         React Components                │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         Service Layer                   │
│  (API calls, auth, error handling)      │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         AWS Services                    │
│  (API Gateway, Lambda, S3, Cognito)     │
└─────────────────────────────────────────┘
```

### Service Modules

#### 1. videoService.ts

**Purpose:** Video upload and retrieval

**Key Functions:**
```typescript
// Get audio summary for a video
getAudioSummaryForVideo(questionId: string): Promise<string>

// Store video with 3-step process
storeVideo(videoData: VideoData, isVideoMemory: boolean): Promise<VideoUploadResponse>
  // Step 1: Get pre-signed URL
  // Step 2: Upload to S3
  // Step 3: Process video (Lambda)

// Get all videos for a maker
getMakerVideos(makerId: string): Promise<VideosByType>
```

**Interfaces:**
```typescript
interface Video {
  questionId: string;
  questionType: string;
  questionText: string;
  responseType: 'video' | 'audio' | 'video_memory';
  videoUrl: string | null;
  thumbnailUrl: string | null;
  audioUrl: string | null;
  oneSentence?: string | null;
  timestamp: string;
  filename: string;
}

interface VideoUploadResponse {
  message: string;
  filename: string;
  s3Key: string;
  thumbnailFilename?: string;
  streakData?: {
    streakCount: number;
    streakFreezeAvailable: boolean;
    freezeUsed?: boolean;
  };
}
```

**Upload Flow:**
```
1. Component calls storeVideo()
2. Service gets pre-signed URL from Lambda
3. Service uploads directly to S3 (no Lambda proxy)
4. Service calls process-video Lambda
5. Lambda extracts audio, generates thumbnail, updates DB
6. Service returns response with streak data
```

#### 2. progressService.ts

**Purpose:** User progress tracking

**Key Functions:**
```typescript
getTotalValidQuestions(): Promise<number>
getUserCompletedCount(userId: string): Promise<number>
getUserProgress(userId: string): Promise<ProgressData>
```

**Interface:**
```typescript
interface ProgressData {
  completed: number;
  total: number;
  percentage: number;
}
```

**Pattern:**
- Parallel fetching with `Promise.all()`
- Automatic percentage calculation
- Error handling with fallback to 0

#### 3. streakService.ts

**Purpose:** Daily streak management with caching

**Key Functions:**
```typescript
getStreak(): Promise<StreakData>                    // Simple, fast
checkStreak(): Promise<StreakData>                  // Detailed with status
getCachedStreak(userId: string): Promise<StreakData> // With 1-hour cache
invalidateCache(userId: string): void               // Clear cache
updateCache(userId: string, data: StreakData): void // Update cache
```

**Interface:**
```typescript
interface StreakData {
  streakCount: number;
  streakFreezeAvailable: boolean;
  lastVideoDate?: string;
  streakStatus?: 'active' | 'at_risk' | 'broken';
  daysSinceLastVideo?: number;
  freezeUsed?: boolean;
}
```

**Caching Strategy:**
```typescript
const CACHE_DURATION = 3600000; // 1 hour

// Check cache first
const cached = localStorage.getItem(cacheKey);
if (cached && (Date.now() - cachedData.timestamp < CACHE_DURATION)) {
  return cachedData.data;
}

// Cache miss - fetch fresh
const streakData = await this.getStreak();
localStorage.setItem(cacheKey, JSON.stringify({ data, timestamp }));
```

#### 4. relationshipService.ts

**Purpose:** Manage Legacy Maker <-> Benefactor relationships

**Key Functions:**
```typescript
getRelationships(userId: string): Promise<GetRelationshipsResponse>
```

**Interface:**
```typescript
interface Relationship {
  initiator_id: string;
  related_user_id: string;
  related_user_email?: string;
  related_user_first_name?: string;
  related_user_last_name?: string;
  relationship_type: string;
  status: string;
  created_at: string;
  created_via: string;
}
```

#### 5. inviteService.ts

**Purpose:** Send invitations to benefactors

**Key Functions:**
```typescript
sendInvite(request: SendInviteRequest): Promise<SendInviteResponse>
```

**Interface:**
```typescript
interface SendInviteRequest {
  benefactor_email: string;
  invitee_email: string;
}

interface SendInviteResponse {
  message: string;
  invite_token: string;
  sent_to: string;
}
```

#### 6. s3Service.ts

**Purpose:** Direct S3 operations via Amplify Storage

**Key Functions:**
```typescript
uploadFile(file: File, fileName: string): Promise<string>
downloadFile(fileName: string): Promise<Blob>
listUserFiles(): Promise<string[]>
deleteFile(fileName: string): Promise<void>
```

**Pattern:**
- Uses Amplify Storage API
- Automatic user prefix (`users/${userId}/`)
- Private access level
- Type-safe with TypeScript

### Common Service Patterns

**1. Authentication Header:**
```typescript
const authSession = await fetchAuthSession();
const idToken = authSession.tokens?.idToken?.toString();

if (!idToken) throw new Error('No authentication token');

fetch(url, {
  headers: { 'Authorization': `Bearer ${idToken}` }
});
```

**2. Error Handling:**
```typescript
try {
  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }
  return await response.json();
} catch (error) {
  console.error('Error:', error);
  throw error;
}
```

**3. API URL Building:**
```typescript
import { API_CONFIG, buildApiUrl } from '@/config/api';

const url = buildApiUrl(API_CONFIG.ENDPOINTS.UPLOAD_VIDEO, { userId });
```

---

## 7. AUTHENTICATION FLOW

### Registration Flow

```
1. User visits /signup or /legacy-create-choice
2. Selects persona type (Legacy Maker or Benefactor)
3. Fills registration form (email, password, first/last name)
4. Frontend calls signupWithPersona()
5. Cognito creates user (unconfirmed)
6. PreSignUp Lambda trigger:
   - Validates persona choice
   - Stores persona in custom:profile attribute
   - Stores first/last name in given_name/family_name
   - Processes invite token if present
7. User receives verification email
8. User enters code on /confirm-signup
9. PostConfirmation Lambda trigger:
   - Creates userDB record
   - Creates progressDB record (for Legacy Makers)
   - Creates streakDB record (for Legacy Makers)
   - Creates relationship (if invite token present)
10. User redirected to /login
```

### Login Flow

```
1. User enters email/password on /login
2. Frontend calls login()
3. Cognito validates credentials
4. Frontend receives JWT tokens (ID, Access, Refresh)
5. Frontend fetches user attributes
6. Frontend parses persona_type from custom:profile
7. Frontend initializes progress (for Legacy Makers)
8. User redirected to /dashboard or /benefactor-dashboard
```

### Session Management

**Token Storage:** Handled by AWS Amplify (secure storage)
**Token Refresh:** Automatic via Amplify
**Session Check:** On app mount via `checkAuthState()`
**Logout:** Clears tokens and redirects to home

### Persona Type Handling

**Storage Location:** Cognito custom attribute `custom:profile`
**Format:** JSON string `{"persona_type": "legacy_maker"}`
**Parsing:**
```typescript
const userAttributes = await fetchUserAttributes({ forceRefresh: true });
if (userAttributes.profile) {
  const profileJson = JSON.parse(userAttributes.profile);
  personaType = profileJson.persona_type || 'legacy_maker';
}
```

**Usage:**
- Determines dashboard route
- Controls feature access
- Filters available questions
- Manages relationships

---

## 8. DESIGN SYSTEM

### Color Palette

**Brand Colors:**
```typescript
legacy: {
  navy: '#1A1F2C',        // Primary dark
  purple: '#9b87f5',      // Primary accent
  lightPurple: '#E5DEFF', // Light accent
  white: '#FFFFFF'        // Base white
}
```

**Semantic Colors (HSL):**
```css
--primary: 252 80% 75%;           /* Purple */
--secondary: 210 40% 96.1%;       /* Light gray */
--destructive: 0 84.2% 60.2%;     /* Red */
--muted: 210 40% 96.1%;           /* Muted gray */
--accent: 210 40% 96.1%;          /* Accent gray */
```

### Typography

**Font Stack:** System fonts (via Tailwind defaults)
**Sizes:** Tailwind scale (text-xs to text-6xl)
**Weights:** 400 (normal), 500 (medium), 600 (semibold), 700 (bold)

### Spacing

**Scale:** Tailwind default (0.25rem increments)
**Common Values:**
- `gap-4` (1rem) - Component spacing
- `p-6` (1.5rem) - Card padding
- `py-20` (5rem) - Section padding

### Border Radius

**Values:**
```css
--radius: 0.5rem;
border-radius: {
  lg: var(--radius),
  md: calc(var(--radius) - 2px),
  sm: calc(var(--radius) - 4px)
}
```

### Animations

**Custom Animations:**
```css
@keyframes breathe {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.3); }
}

@keyframes accordion-down {
  from { height: 0 }
  to { height: var(--radix-accordion-content-height) }
}
```

### Responsive Breakpoints

**Tailwind Defaults:**
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1400px (custom)

### Component Styling Patterns

**1. Card Pattern:**
```tsx
<Card className="w-full max-w-md">
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>Content</CardContent>
  <CardFooter>Footer</CardFooter>
</Card>
```

**2. Button Variants:**
```tsx
<Button className="bg-legacy-purple hover:bg-legacy-navy">
<Button variant="outline">
<Button variant="destructive">
<Button variant="ghost">
```

**3. Form Pattern:**
```tsx
<div className="space-y-2">
  <Label htmlFor="field">Label</Label>
  <Input id="field" type="text" />
  {error && <p className="text-sm text-red-500">{error}</p>}
</div>
```

---

## 9. BUILD CONFIGURATION

### Vite Configuration

**File:** `vite.config.ts`

```typescript
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",      // IPv6 support
    port: 8080,
  },
  plugins: [
    react(),         // React with SWC
    mode === 'development' && componentTagger(), // Dev tools
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"), // Path alias
    },
  },
}));
```

### Build Scripts

```json
{
  "dev": "vite",                              // Dev server
  "build": "vite build",                      // Production build
  "build:dev": "vite build --mode development", // Dev build
  "lint": "eslint .",                         // Linting
  "preview": "vite preview"                   // Preview build
}
```

### TypeScript Configuration

**Compiler Options:**
- Target: ES2020
- Module: ESNext
- JSX: react-jsx
- Strict mode enabled
- Path aliases configured

### Environment Variables

**Pattern:** Vite uses `import.meta.env`
**Files:** `.env`, `.env.local`, `.env.production`
**Prefix:** `VITE_` for client-side variables

**Current Configuration:**
- API URL hardcoded in `src/config/api.ts`
- AWS config hardcoded in `src/aws-config.ts`
- **Recommendation:** Move to environment variables

---

## 10. BEST PRACTICES & PATTERNS

### 1. Component Composition

**Good Example:**
```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
  </CardHeader>
  <CardContent>
    <VideoRecorder onRecordingSubmitted={handleSubmit} />
  </CardContent>
</Card>
```

**Pattern:** Compose small, focused components

### 2. Custom Hooks

**use-toast.ts:**
```typescript
export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  
  const toast = useCallback((props: Toast) => {
    setToasts((prev) => [...prev, { ...props, id: generateId() }]);
  }, []);
  
  return { toast, toasts, dismiss };
}
```

**Pattern:** Extract reusable logic into hooks

### 3. Service Layer Abstraction

**Good:**
```typescript
// Component
const videos = await getMakerVideos(makerId);

// Service
export const getMakerVideos = async (makerId: string) => {
  const token = await getAuthToken();
  return fetch(url, { headers: { Authorization: token } });
};
```

**Pattern:** Keep API logic out of components

### 4. Error Boundaries

```tsx
<ErrorBoundary>
  <VideoRecorder />
</ErrorBoundary>
```

**Pattern:** Wrap error-prone components

### 5. TypeScript Interfaces

```typescript
interface VideoRecorderProps {
  onSkipQuestion?: () => void;
  canSkip?: boolean;
  currentQuestionId?: string;
}
```

**Pattern:** Define clear prop interfaces

### 6. Async/Await Error Handling

```typescript
try {
  setIsLoading(true);
  await videoService.storeVideo(data);
  toast.success("Video uploaded!");
} catch (error) {
  console.error("Upload failed:", error);
  toast.error("Upload failed. Please try again.");
} finally {
  setIsLoading(false);
}
```

**Pattern:** Consistent error handling with user feedback

### 7. Cleanup Effects

```typescript
useEffect(() => {
  const stream = await navigator.mediaDevices.getUserMedia({ video: true });
  
  return () => {
    stream.getTracks().forEach(track => track.stop());
  };
}, []);
```

**Pattern:** Always cleanup resources

### 8. Conditional Rendering

```typescript
{isLoading ? (
  <Skeleton className="h-20 w-full" />
) : error ? (
  <Alert variant="destructive">{error}</Alert>
) : (
  <VideoList videos={videos} />
)}
```

**Pattern:** Handle loading, error, and success states

---

## 11. AREAS FOR IMPROVEMENT

### 1. Route Protection

**Current:** No route guards, components check auth manually
**Recommendation:** Implement ProtectedRoute wrapper
```typescript
<Route path="/dashboard" element={
  <ProtectedRoute>
    <Dashboard />
  </ProtectedRoute>
} />
```

### 2. Environment Variables

**Current:** Hardcoded API URLs and AWS config
**Recommendation:** Use environment variables
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const USER_POOL_ID = import.meta.env.VITE_USER_POOL_ID;
```

### 3. TanStack Query Adoption

**Current:** Minimal usage, mostly manual fetch calls
**Recommendation:** Migrate to React Query for:
- Automatic caching
- Background refetching
- Optimistic updates
- Pagination support

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['videos', makerId],
  queryFn: () => getMakerVideos(makerId),
  staleTime: 5 * 60 * 1000, // 5 minutes
});
```

### 4. Error Boundary Coverage

**Current:** ErrorBoundary component exists but not widely used
**Recommendation:** Wrap major sections
```tsx
<ErrorBoundary fallback={<ErrorPage />}>
  <Routes />
</ErrorBoundary>
```

### 5. Loading States

**Current:** Inconsistent loading indicators
**Recommendation:** Standardize with Skeleton components
```tsx
{isLoading ? <Skeleton className="h-40 w-full" /> : <Content />}
```

### 6. Form Validation

**Current:** Manual validation in some forms
**Recommendation:** Consistent use of React Hook Form + Zod
```typescript
const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

const form = useForm({ resolver: zodResolver(schema) });
```

### 7. Code Splitting

**Current:** Single bundle
**Recommendation:** Lazy load routes
```typescript
const Dashboard = lazy(() => import('./pages/Dashboard'));

<Suspense fallback={<Loading />}>
  <Dashboard />
</Suspense>
```

### 8. Accessibility Improvements

**Current:** Good foundation with Radix UI
**Recommendations:**
- Add skip navigation links
- Improve focus management
- Add ARIA live regions for dynamic content
- Test with screen readers

### 9. Performance Optimization

**Recommendations:**
- Memoize expensive computations with `useMemo`
- Memoize callbacks with `useCallback`
- Virtualize long lists (react-window)
- Optimize images (WebP, lazy loading)

### 10. Testing

**Current:** No test files present
**Recommendations:**
- Unit tests (Vitest)
- Component tests (React Testing Library)
- E2E tests (Playwright)
- Visual regression tests (Chromatic)

### 11. Documentation

**Current:** Minimal inline comments
**Recommendations:**
- JSDoc comments for complex functions
- Component usage examples
- Storybook for component library
- Architecture decision records (ADRs)

### 12. State Management Evolution

**Current:** Context + local state works for current scale
**Future Consideration:** If app grows significantly:
- Zustand for global state
- Redux Toolkit for complex state
- Jotai for atomic state

---

## SUMMARY

The Virtual Legacy frontend is a well-structured React 18 application built with modern best practices:

**Strengths:**
- Modern tech stack (React 18, TypeScript, Vite)
- Excellent UI foundation (shadcn/ui + Radix)
- Clean service layer abstraction
- Good component composition
- Proper authentication flow
- Responsive design system

**Architecture Highlights:**
- 14 active routes with clear separation
- 9 custom feature components
- 6 service modules for API integration
- Context-based authentication
- Local storage caching for performance

**Key Patterns:**
- Service layer for API calls
- Custom hooks for reusable logic
- Composition over inheritance
- TypeScript for type safety
- Tailwind for styling

**Next Steps:**
- Implement route protection
- Expand TanStack Query usage
- Add comprehensive testing
- Improve error handling
- Optimize performance

The frontend provides a solid foundation for the Virtual Legacy platform with room for growth and optimization as the application scales.

---

**Document Complete**  
**Total Components Analyzed:** 80+  
**Total Service Modules:** 6  
**Total Routes:** 14  
**Lines of Analysis:** 1000+
