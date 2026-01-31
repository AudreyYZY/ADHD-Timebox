# Frontend Streaming Chat Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stream assistant responses word-by-word in the planning + thought-parking chats with a GPT-like pending indicator.

**Architecture:** Add a Next.js API route that proxies the existing backend `/api/chat` and streams plain text chunks to the client. Switch the frontend chat transport to `TextStreamChatTransport`, then show a typing spinner while the response is pending/streaming.

**Tech Stack:** Next.js App Router, React, AI SDK (`@ai-sdk/react` + `TextStreamChatTransport`), Tailwind CSS.

---

### Task 1: Add streaming proxy route

**Files:**
- Create: `app/api/chat/stream/route.ts`

**Step 1: Write the failing test**

Manual test checklist (expected to fail before implementation):
1) Run `npm run dev`
2) Send a chat message in Planning mode
3) Observe: request to `/api/chat/stream` returns 404 and no streaming text appears

**Step 2: Run test to verify it fails**

Run: `npm run dev`  
Expected: 404 on `/api/chat/stream`, no streaming UI

**Step 3: Write minimal implementation**

Implement a route handler that:
- Accepts POST JSON from `useChat`
- Extracts the latest user message text (from `messages[].parts` or `messages[].content`)
- Calls the backend `http://localhost:8000/api/chat` with `{ message }`
- Streams the backend `content` back to the client **word-by-word** using a `TransformStream`

```ts
export async function POST(req: Request) {
  // parse body, extract last user text
  // fetch backend /api/chat
  // stream content word-by-word as text/plain
}
```

**Step 4: Run test to verify it passes**

Run: `npm run dev`  
Expected: `/api/chat/stream` responds with a streamed text body

**Step 5: Commit**

```bash
git add app/api/chat/stream/route.ts
git commit -m "feat: add streaming chat proxy route"
```

---

### Task 2: Stream Planning chat + pending indicator

**Files:**
- Modify: `components/planning-mode.tsx`

**Step 1: Write the failing test**

Manual test checklist:
1) Send a Planning message
2) Expect: GPT-like pending state (spinner + dots) immediately
3) Expect: assistant reply appears **word-by-word**

**Step 2: Run test to verify it fails**

Run: `npm run dev`  
Expected: no spinner + full response arrives all at once

**Step 3: Write minimal implementation**

- Replace `DefaultChatTransport` with `TextStreamChatTransport({ api: "/api/chat/stream" })`
- Add a “pending” bubble that shows when `status` is `submitted` or `streaming` and the last assistant message has no text yet
- Ensure pending indicator uses `role="status"` and `aria-live="polite"`

**Step 4: Run test to verify it passes**

Run: `npm run dev`  
Expected: spinner appears immediately; response streams word-by-word

**Step 5: Commit**

```bash
git add components/planning-mode.tsx
git commit -m "feat: stream planning chat with pending indicator"
```

---

### Task 3: Stream Thought Parking chat + pending indicator

**Files:**
- Modify: `components/thought-parking-sheet.tsx`

**Step 1: Write the failing test**

Manual test checklist:
1) Open Thought Parking
2) Send a message
3) Expect: spinner + word-by-word streaming response

**Step 2: Run test to verify it fails**

Run: `npm run dev`  
Expected: no spinner + response arrives all at once

**Step 3: Write minimal implementation**

- Replace `DefaultChatTransport` with `TextStreamChatTransport({ api: "/api/chat/stream" })`
- Add the same pending indicator as Planning mode

**Step 4: Run test to verify it passes**

Run: `npm run dev`  
Expected: pending indicator + streaming response

**Step 5: Commit**

```bash
git add components/thought-parking-sheet.tsx
git commit -m "feat: stream thought parking chat with pending indicator"
```

---

### Task 4: UX polish for loading state

**Files:**
- Modify: `components/planning-mode.tsx`
- Modify: `components/thought-parking-sheet.tsx`

**Step 1: Write the failing test**

Manual test checklist:
1) Send a message
2) Spinner should align with chat bubble and not shift layout

**Step 2: Run test to verify it fails**

Run: `npm run dev`  
Expected: no consistent layout for spinner or pending state

**Step 3: Write minimal implementation**

- Use a small inline spinner (`animate-spin`) + three dots
- Keep dimensions fixed to avoid layout shift

**Step 4: Run test to verify it passes**

Run: `npm run dev`  
Expected: stable pending indicator with no layout shift

**Step 5: Commit**

```bash
git add components/planning-mode.tsx components/thought-parking-sheet.tsx
git commit -m "chore: polish chat pending indicator layout"
```

