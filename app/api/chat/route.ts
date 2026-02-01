import { auth } from "@clerk/nextjs/server";

const RAW_BACKEND_URL =
  process.env.BACKEND_BASE_URL ??
  process.env.NEXT_PUBLIC_BACKEND_URL ??
  "http://127.0.0.1:8000";
const BACKEND_BASE_URL = RAW_BACKEND_URL.replace(/\/api\/?$/, "");
const CHAT_URL = `${BACKEND_BASE_URL}/api/chat`;

export async function POST(req: Request) {
  const { userId } = auth();
  const headerUserId = req.headers.get("x-user-id");
  const resolvedUserId =
    userId ??
    (process.env.NODE_ENV === "development" ? headerUserId : null);

  if (!resolvedUserId) {
    return new Response("Unauthorized", { status: 401 });
  }

  const payload = await req.text();

  const backendResponse = await fetch(CHAT_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": resolvedUserId,
    },
    body: payload,
  });

  const body = await backendResponse.text();
  return new Response(body, {
    status: backendResponse.status,
    headers: {
      "Content-Type": backendResponse.headers.get("Content-Type") ?? "application/json",
      "Cache-Control": "no-store",
    },
  });
}
