# NotebookLM UI Clone - Detailed Specification

**Goal:** Pixel-perfect recreation of NotebookLM's interface using shadcn/ui components

**Reference:** NotebookLM (December 2024 - 2025 redesign)

---

## Core Layout Architecture

### Three-Panel System

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Header: Logo + Notebook Title + Share + User                               │
├──────────────────┬──────────────────────────────────┬──────────────────────┤
│                  │                                  │                      │
│  Sources         │  Chat                            │  Studio              │
│  (collapsible)   │  (primary)                       │  (collapsible)       │
│                  │                                  │                      │
│  280-400px       │  flexible                        │  320-400px           │
│  min: 240px      │  min: 480px                      │  min: 280px          │
│                  │                                  │                      │
└──────────────────┴──────────────────────────────────┴──────────────────────┘
```

### Responsive Breakpoints

**Desktop (≥1280px):**
- All three panels visible
- Sources: 320px default
- Chat: flexible center
- Studio: 360px default
- Panels resizable via drag handles

**Tablet (768-1279px):**
- Two panels visible
- Toggle between Sources/Chat or Chat/Studio
- Bottom tab navigation
- Active panel gets 60% width

**Mobile (<768px):**
- Single panel view
- Bottom tab bar (Sources | Chat | Studio)
- Full-width panels
- Slide transitions between views

---

## Design System

### Typography

**Font Family:** Inter (primary)
- Regular: 400
- Medium: 500
- Semibold: 600
- Bold: 700

**Font Scale:**

```css
--text-xs: 10px / 12px;    /* Metadata, badges */
--text-sm: 12px / 16px;    /* Secondary text */
--text-base: 14px / 20px;  /* Body text, list items */
--text-lg: 16px / 24px;    /* Panel headers */
--text-xl: 20px / 28px;    /* Section titles */
--text-2xl: 24px / 32px;   /* Page titles */
--text-3xl: 32px / 40px;   /* Hero text */
```

**Letter Spacing:**
- Tight: -0.02em (titles)
- Normal: 0 (body)
- Wide: 0.01em (uppercase labels)

### Color Palette

**Backgrounds:**

```css
--bg-primary: #FFFFFF;
--bg-secondary: #F6F6F8;
--bg-tertiary: #FAFAFA;
--bg-hover: #F1F3F4;
--bg-active: #E8EAED;
--bg-overlay: rgba(0, 0, 0, 0.6);
```

**Text:**

```css
--text-primary: #1F1F1F;
--text-secondary: #5F6368;
--text-tertiary: #9AA0A6;
--text-inverse: #FFFFFF;
```

**Borders:**

```css
--border-primary: #DADCE0;
--border-secondary: #E8EAED;
--border-focus: #1A73E8;
```

**Accent (Google Blue):**

```css
--accent-primary: #1A73E8;
--accent-hover: #1765CC;
--accent-active: #1557B0;
--accent-light: #E8F0FE;
```

**Status:**

```css
--status-success: #1E8E3E;
--status-warning: #F9AB00;
--status-error: #D93025;
--status-info: #1A73E8;
```

### Spacing System

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
```

**Common Patterns:**
- Panel padding: 24px
- Card padding: 16px
- List item padding: 12px 16px
- Button padding: 10px 24px
- Input padding: 8px 12px
- Section gaps: 16px

### Border Radius

```css
--radius-sm: 4px;   /* Badges, tags */
--radius-md: 8px;   /* Cards, buttons */
--radius-lg: 12px;  /* Panels, dialogs */
--radius-xl: 16px;  /* Images, media */
--radius-full: 9999px; /* Pills, avatars */
```

### Shadows

```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
--shadow-lg: 0 4px 6px rgba(0, 0, 0, 0.07), 0 2px 4px rgba(0, 0, 0, 0.05);
--shadow-xl: 0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05);
```

### Transitions

```css
--transition-fast: 100ms ease-in-out;
--transition-base: 200ms ease-in-out;
--transition-slow: 300ms ease-in-out;
```

---

## Panel 1: Sources (Left)

### Header

```
┌─────────────────────────────┐
│ Sources              [+]    │ ← 16px padding, semibold, + button
└─────────────────────────────┘
```

**Structure:**
- Height: 56px
- Padding: 12px 16px
- Border bottom: 1px solid --border-primary
- Sticky header (stays at top during scroll)

**"Sources" Label:**
- Font: 16px / 24px semibold
- Color: --text-primary

**Add Button:**
- Size: 32px × 32px
- Border radius: --radius-full
- Background: transparent → --bg-hover (hover)
- Icon: Plus (20px)
- Tooltip: "Add source"

### Source List

**Empty State:**

```text
┌─────────────────────────────┐
│                             │
│         📄                  │ ← Icon 48px
│                             │
│   No sources yet            │ ← 14px medium
│   Add sources to get        │ ← 12px secondary
│   started                   │
│                             │
│   [+ Add source]            │ ← Primary button
│                             │
└─────────────────────────────┘
```

**Source Card:**

```text
┌─────────────────────────────┐
│ 📄 document-name.pdf    ⋮  │ ← Icon 20px, title 14px, menu
│ 125 pages • 45,231 words   │ ← Metadata 12px secondary
│ ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░  70%   │ ← Progress bar (processing)
└─────────────────────────────┘
```

**Card States:**

**Default (Ready):**
- Padding: 12px
- Background: transparent
- Border: 1px solid transparent
- Border radius: --radius-md
- Cursor: pointer

**Hover:**
- Background: --bg-hover
- Border: 1px solid --border-secondary

**Active/Selected:**
- Background: --accent-light
- Border: 1px solid --accent-primary
- Icon color: --accent-primary

**Processing:**
- Progress bar visible
- Animated pulse on icon
- Status text below metadata

**Error:**
- Red indicator icon
- Error message in red text
- Retry button

**Card Layout:**

```text
Row 1: [Icon 20px] [Title (truncate)] [Menu 16px]
Row 2:            [Metadata (gray, 12px)]
Row 3:            [Progress bar (if processing)]
```

**Source Type Icons:**
- PDF: 📄 (File icon)
- Web: 🌐 (Globe icon)
- YouTube: 🎥 (Video icon)
- Text: 📝 (Document icon)
- GitHub: <> (Code icon)
- Audio: 🎵 (Audio icon)

**Metadata Format:**
- `{page_count} pages • {word_count} words`
- `{duration}` (for video/audio)
- `Updated {relative_time}`

**Context Menu (⋮):**

```text
View
Copy link (if URL)
Download (if file)
───────────
Remove
```

### Source Details View

When source is clicked, expand inline or open in overlay:

```text
┌─────────────────────────────────────┐
│ ← Back         document-name.pdf    │
├─────────────────────────────────────┤
│                                     │
│ [Key Topics]                        │
│ • Topic 1                           │
│ • Topic 2                           │
│ • Topic 3                           │
│                                     │
│ [Summary]                           │
│ Auto-generated summary of the       │
│ document content...                 │
│                                     │
│ [Preview]                           │
│ First page or text preview...      │
│                                     │
└─────────────────────────────────────┘
```

### Add Source Dialog

**Tabs:**

```text
┌─────────────────────────────────────────┐
│ [Upload] [Website] [Paste] [Google]    │ ← Tab navigation
├─────────────────────────────────────────┤
│                                         │
│ [Upload Tab]                            │
│ ┌─────────────────────────────────────┐ │
│ │                                     │ │
│ │     Drop files here or click        │ │
│ │     to browse                       │ │
│ │                                     │ │
│ │     PDF, Text, Markdown, Audio      │ │
│ │     Max 200MB • 500K words          │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [Cancel]                    [Upload]    │
└─────────────────────────────────────────┘
```

**Tab Content:**

**Upload:**
- Drag-drop zone (full height)
- Dashed border on hover
- File type icons + supported formats
- Size/word count limits

**Website:**

```text
┌─────────────────────────────────────────┐
│ Website URL                              │
│ ┌─────────────────────────────────────┐ │
│ │ https://                            │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ □ Include subpages (max 10)            │
│                                         │
│ [Cancel]                      [Add]     │
└─────────────────────────────────────────┘
```

**Paste:**

```text
┌─────────────────────────────────────────┐
│ Paste text or markdown                   │
│ ┌─────────────────────────────────────┐ │
│ │                                     │ │
│ │                                     │ │
│ │                                     │ │
│ │                                     │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
│ 0 / 500,000 words                       │
│                                         │
│ [Cancel]                      [Add]     │
└─────────────────────────────────────────┘
```

**Google:**

```text
┌─────────────────────────────────────────┐
│ [Google Drive]  [Google Docs]           │
│                                         │
│ Recent files:                           │
│ □ Document 1.pdf                        │
│ □ Research Notes                        │
│ □ Project Plan.docx                     │
│                                         │
│ [Browse Drive...]                       │
│                                         │
│ [Cancel]                      [Add]     │
└─────────────────────────────────────────┘
```

---

## Panel 2: Chat (Center)

### Header

```text
┌─────────────────────────────────────────────┐
│  💬 Chat                    [⋮]             │ ← 16px padding
└─────────────────────────────────────────────┘
```

**Structure:**
- Height: 56px
- Padding: 12px 16px
- Border bottom: 1px solid --border-primary
- Sticky header

**Menu (⋮):**

```text
Clear conversation
Export chat
Pin important messages
───────────
Settings
```

### Message List

**Empty State:**

```text
┌─────────────────────────────────────────────┐
│                                             │
│                                             │
│              💬                             │ ← Icon 64px
│                                             │
│         Ask me anything                     │ ← 20px semibold
│                                             │
│    I can help you understand your           │ ← 14px secondary
│    sources, answer questions, and           │
│    generate insights                        │
│                                             │
│    Suggested questions:                     │
│    [What are the main themes?]              │ ← Chips/pills
│    [Summarize key findings]                 │
│    [Compare different sources]              │
│                                             │
└─────────────────────────────────────────────┘
```

**Message Bubbles:**

**User Message:**

```text
                           ┌──────────────────────┐
                           │ What are the key     │
                           │ findings in the      │
                           │ research?            │
                           └──────────────────────┘
                                          2:34 PM
```

**Styling:**
- Background: --accent-primary
- Color: --text-inverse
- Border radius: 16px 16px 4px 16px
- Padding: 12px 16px
- Max width: 70%
- Float right
- Margin: 8px 0

**Assistant Message:**

```text
┌────────────────────────────────────────────────┐
│ 🤖 Based on the sources, the key findings      │
│ are:                                           │
│                                                │
│ 1. Finding one from the research              │
│ 2. Finding two with important details         │
│ 3. Finding three that shows...                │
│                                                │
│ Sources: [1] [2] [3]                          │ ← Citation badges
└────────────────────────────────────────────────┘
2:34 PM
```

**Styling:**
- Background: --bg-secondary
- Color: --text-primary
- Border radius: 4px 16px 16px 16px
- Padding: 16px
- Max width: 85%
- Float left
- Margin: 8px 0
- Avatar: 32px circle (top left)

**Source Citations:**

**Citation Badge:**

```text
[1] [2] [3] [4]
```

**Styling:**
- Display: inline-flex
- Size: 24px × 24px
- Background: --accent-light
- Color: --accent-primary
- Border: 1px solid --accent-primary
- Border radius: --radius-sm
- Font: 12px semibold
- Margin: 0 4px
- Cursor: pointer

**Hover:**
- Background: --accent-primary
- Color: --text-inverse

**Tooltip on Hover:**

```text
┌─────────────────────────────────────┐
│ research-paper.pdf (p. 12)          │
│ "...relevant excerpt from the       │
│ source that supports this claim..." │
└─────────────────────────────────────┘
```

**Click Action:**
- Highlights corresponding source in left panel
- Scrolls to source in list
- Opens source preview (optional)

### Streaming Response

**While generating:**

```text
┌────────────────────────────────────────────────┐
│ 🤖 Based on the sources, the key findings      │
│ are:                                           │
│                                                │
│ 1. Finding one from the research              │
│ 2. Finding two with important█                │ ← Cursor pulse
│                                                │
└────────────────────────────────────────────────┘
```

**Streaming Indicator:**
- Animated cursor pulse
- "Thinking..." text (brief)
- No stop button (fast enough)

### Chat Input

```text
┌─────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Ask anything...                                     │ │ ← Auto-resize textarea
│ └─────────────────────────────────────────────────────┘ │
│                                               [Send] ↑  │ ← Send button
└─────────────────────────────────────────────────────────┘
```

**Structure:**
- Position: sticky bottom
- Padding: 16px
- Background: --bg-primary
- Border top: 1px solid --border-primary
- Box shadow: --shadow-lg (on scroll)

**Textarea:**
- Min height: 44px
- Max height: 200px (scrollable)
- Padding: 12px 48px 12px 16px (room for button)
- Border: 1px solid --border-primary
- Border radius: --radius-lg
- Font: 14px
- Focus: border color → --border-focus

**Send Button:**
- Position: absolute right 12px bottom 12px
- Size: 32px × 32px
- Background: --accent-primary (enabled), --bg-secondary (disabled)
- Icon: Arrow up (20px)
- Border radius: --radius-full
- Disabled: no text in input

**Keyboard:**
- Enter: Send message
- Shift+Enter: New line
- Cmd+K: Focus input

---

## Panel 3: Studio (Right)

### Header

```text
┌─────────────────────────────┐
│ Studio                      │ ← 16px padding, semibold
└─────────────────────────────┘
```

**Structure:**
- Height: 56px
- Padding: 12px 16px
- Border bottom: 1px solid --border-primary
- Sticky header

### Content Types Grid

**Layout:**

```text
┌─────────────────────────────┐
│ [Audio Overview]            │ ← 2×2 grid
│ [Video Overview]            │
│                             │
│ [Mind Map]                  │
│ [Reports ▼]                 │ ← Expandable
└─────────────────────────────┘
```

**Tile Design:**

```text
┌─────────────────────────────┐
│                             │
│       🎵                    │ ← Icon 32px
│                             │
│   Audio Overview            │ ← 14px semibold
│   Generate a podcast-style  │ ← 12px secondary
│   discussion                │
│                             │
│   [Generate]                │ ← Button
│                             │
└─────────────────────────────┘
```

**Tile States:**

**Default:**
- Padding: 16px
- Background: --bg-secondary
- Border: 1px solid --border-secondary
- Border radius: --radius-lg
- Cursor: pointer

**Hover:**
- Background: --bg-hover
- Border: 1px solid --border-primary
- Scale: 1.02
- Transition: --transition-base

**Generating:**
- Spinner overlay
- "Generating..." text
- Progress percentage (if available)
- Cancel button

**Ready:**
- Badge: "Ready" (green)
- Preview content
- View button
- Regenerate button

### Studio Types

**1. Audio Overview**

```text
┌─────────────────────────────────────┐
│ 🎵 Audio Overview                   │
│                                     │
│ Generate a podcast-style discussion │
│ of your sources                     │
│                                     │
│ ○ Standard (5-10 min)               │ ← Radio options
│ ○ Deep Dive (10-20 min)             │
│                                     │
│ □ Focus on: ________________        │ ← Optional input
│                                     │
│ [Generate Audio Overview]           │
└─────────────────────────────────────┘
```

**Generated:**

```text
┌─────────────────────────────────────┐
│ 🎵 Audio Overview • 12:34           │
│                                     │
│ ▶️ [Progress Bar ────●──────] 5:21 │ ← Audio player
│                                     │
│ 🎙️ Deep dive discussion covering    │
│ key themes and insights from        │
│ your sources                        │
│                                     │
│ [Download] [Share] [Regenerate]     │
└─────────────────────────────────────┘
```

**2. Video Overview**
- Similar to audio but with video thumbnail
- Slide preview
- Visual indicators

**3. Mind Map**

```text
┌─────────────────────────────────────┐
│ 🗺️ Mind Map                         │
│                                     │
│ Visualize connections between       │
│ topics and concepts                 │
│                                     │
│ [Generate Mind Map]                 │
└─────────────────────────────────────┘
```

**4. Reports (Expandable)**

**Collapsed:**

```text
┌─────────────────────────────┐
│ 📊 Reports              ▼   │ ← Expand arrow
└─────────────────────────────┘
```

**Expanded:**

```text
┌─────────────────────────────┐
│ 📊 Reports              ▲   │
├─────────────────────────────┤
│ • Briefing doc              │ ← List items
│ • Study guide               │
│ • FAQ                       │
│ • Timeline                  │
└─────────────────────────────┘
```

**Generate Dialog:**

```text
┌─────────────────────────────────────┐
│ Generate Briefing Doc                │
│                                     │
│ Focus (optional):                   │
│ ┌─────────────────────────────────┐ │
│ │ E.g., "Executive summary for    │ │
│ │ stakeholders"                   │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Cancel]           [Generate]       │
└─────────────────────────────────────┘
```

### Document Viewer

When document is ready:

```text
┌─────────────────────────────────────────┐
│ ← Back to Studio    Briefing Doc       │
├─────────────────────────────────────────┤
│                                         │
│ # Executive Briefing                    │ ← Markdown content
│                                         │
│ ## Key Findings                         │
│                                         │
│ Lorem ipsum dolor sit amet...          │
│                                         │
│ ## Recommendations                      │
│                                         │
│ 1. First recommendation                 │
│ 2. Second recommendation                │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ [Copy] [Download] [Share] [Regenerate] │ ← Action bar
└─────────────────────────────────────────┘
```

**Markdown Styling:**
- H1: 24px bold
- H2: 20px semibold
- H3: 16px semibold
- Body: 14px regular
- Lists: 14px with proper indentation
- Code: monospace, gray background
- Links: blue, underline on hover

---

## Header (Top)

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [☰] Taboot    [Notebook Name]    [↗ Share] [Settings ⚙] [User 👤]    │
└────────────────────────────────────────────────────────────────────────┘
```

**Structure:**
- Height: 64px
- Padding: 12px 24px
- Border bottom: 1px solid --border-primary
- Background: --bg-primary
- Position: sticky top

**Left Section:**
- Hamburger menu (mobile only): 32px button
- Logo: Taboot wordmark or icon (32px)
- Notebook name: Editable inline (click to edit)

**Right Section:**
- Share button: Ghost button with icon
- Settings: Icon button (28px)
- User menu: Avatar (32px) + dropdown

**Notebook Name:**
- Font: 16px semibold
- Color: --text-primary
- Hover: background --bg-hover
- Click: Inline edit (input field)
- Max width: 300px (truncate with ellipsis)

**Share Button:**

```text
┌──────────────┐
│ ↗ Share      │
└──────────────┘
```

- Padding: 8px 16px
- Border: 1px solid --border-primary
- Border radius: --radius-md
- Hover: background --bg-hover

**User Dropdown:**

```text
┌─────────────────────────┐
│ User Name               │
│ [user email]            │
├─────────────────────────┤
│ My notebooks            │
│ Settings                │
│ Help                    │
├─────────────────────────┤
│ Sign out                │
└─────────────────────────┘
```

---

## Notebooks Home View

### Layout

```text
┌────────────────────────────────────────────────────────────────┐
│ Header (Logo + [+ New notebook] + User)                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Notebooks                          [⊞ Grid] [≡ List]         │ ← View toggle
│                                                                │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                │
│  │ 📒         │ │ 📗         │ │ 📘         │                │
│  │            │ │            │ │            │                │
│  │ Research   │ │ Meeting    │ │ Project    │                │
│  │            │ │ Notes      │ │ Docs       │                │
│  │ 8 sources  │ │ 3 sources  │ │ 15 sources │                │
│  │ 2 days ago │ │ 5 days ago │ │ 1 week ago │                │
│  └────────────┘ └────────────┘ └────────────┘                │
│                                                                │
│  Example Notebooks                                             │
│                                                                │
│  ┌────────────┐ ┌────────────┐                                │
│  │ 📙 Getting │ │ 📕 Sample  │                                │
│  │ Started    │ │ Research   │                                │
│  └────────────┘ └────────────┘                                │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Notebook Card (Grid View)

```text
┌──────────────────────┐
│ 📒                   │ ← Emoji/icon (32px)
│                      │
│ Research Project     │ ← Title 16px semibold
│                      │
│ 8 sources            │ ← Metadata 12px secondary
│ Updated 2 days ago   │
│                      │
│ [⋮]                  │ ← Context menu (bottom right)
└──────────────────────┘
```

**Card Styling:**
- Size: 200px × 160px
- Padding: 16px
- Background: --bg-secondary
- Border: 1px solid --border-secondary
- Border radius: --radius-lg
- Cursor: pointer

**Hover:**
- Background: --bg-hover
- Border: 1px solid --border-primary
- Scale: 1.02
- Shadow: --shadow-md

**Context Menu:**

```text
Open
Rename
Duplicate
───────────
Delete
```

### List View

```text
┌────────────────────────────────────────────────────────┐
│ 📒 Research Project      8 sources    2 days ago  [⋮] │
│ 📗 Meeting Notes         3 sources    5 days ago  [⋮] │
│ 📘 Project Docs         15 sources    1 week ago  [⋮] │
└────────────────────────────────────────────────────────┘
```

**Row Styling:**
- Height: 56px
- Padding: 12px 16px
- Background: transparent
- Border bottom: 1px solid --border-secondary

**Hover:**
- Background: --bg-hover

---

## Mobile Adaptations

### Bottom Tab Navigation

```text
┌─────────────────────────────────────────────┐
│                                             │
│                                             │
│           [Active Panel Content]            │
│                                             │
│                                             │
├─────────────────────────────────────────────┤
│  Sources     Chat        Studio             │ ← Tabs
│    📚         💬           ⭐               │ ← Icons
│    ●         ○            ○                 │ ← Indicators
└─────────────────────────────────────────────┘
```

**Tab Styling:**
- Height: 64px
- Background: --bg-primary
- Border top: 1px solid --border-primary
- Shadow: --shadow-xl (above content)

**Tab Item:**
- Width: 33.33%
- Padding: 8px
- Text align: center
- Icon: 24px
- Label: 12px
- Color: --text-secondary (inactive), --accent-primary (active)

**Active State:**
- Indicator dot below icon
- Bold label
- Icon color: --accent-primary

### Slide Transitions

**Swipe Gestures:**
- Swipe left: Next panel
- Swipe right: Previous panel
- Animation: 300ms ease-out
- Elastic bounce on edges

### Mobile Chat Input

```text
┌─────────────────────────────────────────────┐
│ [Attach] [Ask anything...]        [Send] ↑ │
└─────────────────────────────────────────────┘
```

**Fixed to Bottom:**
- Above tab navigation
- Padding: 12px
- Safe area insets
- Keyboard pushes up (no overlap)

---

## Interactions & Microanimations

### Panel Resize

**Drag Handle:**
- Width: 4px
- Height: 100%
- Background: transparent
- Hover: background --border-primary
- Active: background --accent-primary
- Cursor: col-resize

**Resize Constraints:**
- Min width: as defined per panel
- Snap to collapsed (< 200px drag)
- Smooth animation: --transition-base

### Collapse/Expand Panels

**Collapse Button:**
- Position: top of drag handle
- Size: 24px × 24px
- Icon: Chevron left/right
- Tooltip: "Collapse panel"

**Animation:**
- Duration: 200ms
- Easing: ease-in-out
- Content fades out first
- Width animates to 48px (collapsed)
- Icon rotates 180deg

**Collapsed State:**
- Width: 48px
- Vertical text label (optional)
- Icon buttons for quick actions

### Scroll Behaviors

**Panel Scroll:**
- Independent scrolling per panel
- Sticky headers
- Shadow appears on scroll (indicates more content)
- Smooth scroll to element (citations)

**Chat Auto-scroll:**
- New message: scroll to bottom (animated)
- User scrolls up: disable auto-scroll
- "Scroll to bottom" button appears (floating)

### Loading States

**Skeleton Screens:**
- Use for initial load
- Gray animated gradient (shimmer)
- Match actual content layout

**Source Card Skeleton:**

```text
┌─────────────────────────────┐
│ ▓  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓         │ ← Icon + title
│    ▓▓▓▓▓▓  ▓▓▓▓▓▓           │ ← Metadata
└─────────────────────────────┘
```

**Progress Indicators:**
- Linear progress bar (determinate)
- Spinner (indeterminate)
- Percentage text (if available)

### Toasts/Notifications

**Position:** Top right (desktop), top center (mobile)

**Toast Design:**

```text
┌─────────────────────────────────────┐
│ ✓ Source added successfully         │ ← Success
│   document-name.pdf                 │
└─────────────────────────────────────┘
```

**Types:**
- Success: Green icon + border
- Error: Red icon + border
- Info: Blue icon + border
- Warning: Yellow icon + border

**Behavior:**
- Slide in from right (desktop)
- Auto-dismiss: 3s (success), 5s (error)
- Stack multiple toasts
- Swipe to dismiss (mobile)

---

## Accessibility

### Keyboard Navigation

**Focus Order:**
1. Header (skip link, logo, notebook name, share, settings, user)
2. Left panel (sources list, add button)
3. Center panel (messages, input)
4. Right panel (studio tiles)

**Focus Indicators:**
- Outline: 2px solid --border-focus
- Offset: 2px
- Border radius: --radius-sm

**Keyboard Shortcuts:**
- `Tab`: Next element
- `Shift+Tab`: Previous element
- `Enter/Space`: Activate button/link
- `Escape`: Close dialog/menu
- `Cmd+K`: Focus chat input
- `Cmd+N`: New notebook
- `Cmd+/`: Show shortcuts

### Screen Reader Support

**ARIA Labels:**
- Landmark regions: `main`, `navigation`, `complementary`
- Button labels: All icon buttons
- Live regions: Chat messages, notifications
- Status updates: Processing, generating

**Alt Text:**
- Source type icons
- User avatars
- Generated images (mind map, etc.)

**Semantic HTML:**
- `<header>`, `<nav>`, `<main>`, `<aside>`
- `<article>` for messages
- `<button>` for actions
- `<input>` with `<label>`

---

## Performance Considerations

### Virtual Scrolling

**Source List:**
- Render only visible items + buffer
- Recycle DOM nodes
- Threshold: > 50 sources

**Chat Messages:**
- Render last 50 messages
- Load more on scroll up
- Intersection observer

### Image Optimization

**Source Thumbnails:**
- Lazy loading
- Responsive images (srcset)
- WebP format with fallback
- Blur placeholder

### Code Splitting

**Routes:**
- Home: Notebook list
- Notebook: Three-panel view
- Settings: User settings

**Components:**
- Studio document viewer (lazy)
- Add source dialog (lazy)
- Audio/video players (lazy)

### Caching Strategy

**React Query:**
- Notebooks list: 5-minute stale time
- Sources: 1-minute stale time
- Chat history: Session cache
- Studio documents: 30-minute stale time

---

## Component Mapping to shadcn/ui

### Layout Components

| Custom Component | shadcn/ui Base | Notes |
|-----------------|---------------|-------|
| `NotebookLayout` | `ResizablePanelGroup` | Three-panel system |
| `SourcePanel` | `ResizablePanel` | Left panel |
| `ChatPanel` | `ResizablePanel` | Center panel |
| `StudioPanel` | `ResizablePanel` | Right panel |
| `PanelResizer` | `ResizableHandle` | Drag handles |

### UI Components

| Custom Component | shadcn/ui Base | Notes |
|-----------------|---------------|-------|
| `NotebookCard` | `Card` | Grid/list item |
| `SourceCard` | `Card` + `Badge` | Source list item |
| `AddSourceDialog` | `Dialog` + `Tabs` | Upload modal |
| `ChatMessage` | `Card` (variant) | Message bubble |
| `ChatInput` | `Textarea` + `Button` | Input with send |
| `SourceCitationBadge` | `Badge` (variant) | Citation numbers |
| `StudioTile` | `Card` (interactive) | Generation type |
| `StudioDocument` | `ScrollArea` | Markdown viewer |
| `UploadZone` | Custom + `Card` | Drag-drop area |
| `ProgressBar` | `Progress` | Processing indicator |
| `ContextMenu` | `DropdownMenu` | Right-click menu |
| `Toast` | `Sonner` (toast library) | Notifications |
| `EmptyState` | Custom | No sources/messages |
| `LoadingSkeleton` | `Skeleton` | Loading states |

### shadcn/ui Components Used

- ✅ `Button` - Actions, CTAs
- ✅ `Card` - Containers
- ✅ `Dialog` - Modals
- ✅ `Tabs` - Navigation (add source)
- ✅ `Badge` - Status, citations
- ✅ `Separator` - Dividers
- ✅ `Textarea` - Chat input
- ✅ `ScrollArea` - Scrollable regions
- ✅ `DropdownMenu` - Context menus
- ✅ `Progress` - Loading bars
- ✅ `Skeleton` - Loading states
- ✅ `Sheet` - Mobile panels
- ✅ `Tooltip` - Hints
- ✅ `Avatar` - User images
- ✅ `Input` - Form fields
- ✅ `Label` - Form labels
- ✅ `ResizablePanel` - Panel system
- ✅ `Sonner` - Toast notifications

---

## Implementation Priority

### Phase 1: Layout Shell (Week 1)
1. Three-panel responsive layout
2. Header with notebook name
3. Empty states for all panels
4. Mobile tab navigation

### Phase 2: Sources (Week 2)
1. Source list with cards
2. Add source dialog (all tabs)
3. Processing indicators
4. Context menu

### Phase 3: Chat (Week 3)
1. Message bubbles (user/assistant)
2. Chat input with auto-resize
3. Streaming response
4. Citation badges
5. Suggested questions

### Phase 4: Studio (Week 4)
1. Studio type tiles
2. Generation dialogs
3. Document viewer
4. Export functionality

### Phase 5: Polish (Week 5)
1. Animations and transitions
2. Loading states everywhere
3. Error boundaries
4. Keyboard shortcuts
5. Mobile optimizations

---

## Next Steps

1. **Create design tokens** - CSS variables in globals.css
2. **Build layout shell** - ResizablePanel structure
3. **Implement empty states** - Visual placeholders
4. **Build component library** - Storybook (optional)
5. **Wire up backend** - API integration
6. **Test responsive** - All breakpoints
7. **Accessibility audit** - WCAG compliance
8. **Performance test** - Lighthouse scores

**Target:** Pixel-perfect NotebookLM clone with shadcn/ui DNA
