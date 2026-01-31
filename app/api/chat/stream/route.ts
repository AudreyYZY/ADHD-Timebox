import { auth } from "@clerk/nextjs/server";

const RAW_BACKEND_URL =
  process.env.BACKEND_CHAT_URL ??
  process.env.BACKEND_BASE_URL ??
  process.env.NEXT_PUBLIC_BACKEND_URL ??
  "http://127.0.0.1:8000";
const BACKEND_BASE_URL = RAW_BACKEND_URL.replace(/\/api\/?$/, "");
const BACKEND_CHAT_URL = `${BACKEND_BASE_URL}/api/chat`;
const DEFAULT_FALLBACK =
  "Sorry, I couldn't reach the assistant. Please try again.";
const FAST_START_DELAY_MS = 20;
const STREAM_DELAY_MS = 60;
const SECTION_PAUSE_MS = 220;
const PARAGRAPH_PAUSE_MS = 360;
const FAST_START_TOKENS = 6;
const LONG_WORD_SPLIT = 8;

function splitLongToken(token: string): string[] {
  if (token.length <= LONG_WORD_SPLIT) return [token];
  const parts: string[] = [];
  let start = 0;
  while (start < token.length) {
    parts.push(token.slice(start, start + LONG_WORD_SPLIT));
    start += LONG_WORD_SPLIT;
  }
  return parts;
}

type ChatMessage = {
  role?: string;
  content?: unknown;
  parts?: Array<{ type?: string; text?: string }>;
};

function getMessageText(message: ChatMessage | undefined): string {
  if (!message) return "";

  if (typeof message.content === "string") {
    return message.content;
  }

  if (Array.isArray(message.content)) {
    return message.content
      .map((part) =>
        typeof part === "string"
          ? part
          : typeof part?.text === "string"
          ? part.text
          : ""
      )
      .join("");
  }

  if (Array.isArray(message.parts)) {
    return message.parts
      .filter((part) => part?.type === "text" && typeof part.text === "string")
      .map((part) => part.text ?? "")
      .join("");
  }

  return "";
}

function getLastUserMessageText(messages: ChatMessage[]): string {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i]?.role === "user") {
      return getMessageText(messages[i]);
    }
  }
  return "";
}

async function getBackendErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : typeof data?.message === "string"
        ? data.message
        : typeof data?.error === "string"
        ? data.error
        : "";
    if (detail) return detail;
  } catch {
    // Fall back to status text if body isn't JSON.
  }
  return response.statusText || `HTTP ${response.status}`;
}

function streamTextByWord(
  text: string,
  signal?: AbortSignal,
  delayMs = STREAM_DELAY_MS
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const rawTokens = text.match(/\S+|\s+/g) ?? [];
  const tokens = rawTokens.flatMap((token) => {
    if (/^\s+$/.test(token)) return [token];
    return splitLongToken(token);
  });
  let index = 0;

  return new ReadableStream({
    start(controller) {
      const push = () => {
        if (signal?.aborted) {
          controller.close();
          return;
        }

        if (index >= tokens.length) {
          controller.close();
          return;
        }

        controller.enqueue(encoder.encode(tokens[index]));
        index += 1;
        const currentChunk = tokens[index - 1] ?? "";
        const isParagraphBreak = currentChunk.includes("\n\n");
        const isSectionPause = /[.!?。！？]$/.test(currentChunk) || currentChunk.includes("\n");
        const baseDelay = index <= FAST_START_TOKENS ? FAST_START_DELAY_MS : delayMs;
        const extraDelay = isParagraphBreak
          ? PARAGRAPH_PAUSE_MS
          : isSectionPause
          ? SECTION_PAUSE_MS
          : 0;
        const nextDelay = baseDelay + extraDelay;
        setTimeout(push, nextDelay);
      };

      push();
    },
  });
}

export async function POST(req: Request) {
  const { userId } = auth();
  if (!userId) {
    const fallbackStream = streamTextByWord(
      "Please sign in to use the assistant.",
      req.signal
    );
    return new Response(fallbackStream, {
      status: 401,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  }
  let payload: { messages?: ChatMessage[] } | undefined;

  try {
    payload = await req.json();
  } catch {
    const fallbackStream = streamTextByWord(DEFAULT_FALLBACK, req.signal);
    return new Response(fallbackStream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  }

  const messages = Array.isArray(payload?.messages) ? payload?.messages : [];
  const userMessage = getLastUserMessageText(messages).trim();

  if (!userMessage) {
    const fallbackStream = streamTextByWord(
      "Please send a message so I can help.",
      req.signal
    );
    return new Response(fallbackStream, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  }

  let responseText = DEFAULT_FALLBACK;

  try {
    const backendResponse = await fetch(BACKEND_CHAT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Id": userId },
      body: JSON.stringify({ message: userMessage }),
    });

    if (backendResponse.ok) {
      const data = await backendResponse.json().catch(() => null);
      responseText =
        typeof data?.content === "string"
          ? data.content
          : typeof data?.response === "string"
          ? data.response
          : responseText;
    } else {
      const errorMessage = await getBackendErrorMessage(backendResponse);
      responseText = `Assistant server error: ${errorMessage}.`;
    }
  } catch {
    responseText = DEFAULT_FALLBACK;
  }

  const stream = streamTextByWord(responseText, req.signal);
  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
