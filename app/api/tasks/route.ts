import { auth } from "@clerk/nextjs/server";

const RAW_BACKEND_URL =
  process.env.BACKEND_BASE_URL ??
  process.env.NEXT_PUBLIC_BACKEND_URL ??
  "http://127.0.0.1:8000";
const BACKEND_BASE_URL = RAW_BACKEND_URL.replace(/\/api\/?$/, "");
const TASKS_URL = `${BACKEND_BASE_URL}/api/tasks`;

export async function GET(req: Request) {
  const { userId } = auth();
  if (!userId) {
    return new Response("Unauthorized", { status: 401 });
  }

  const url = new URL(req.url);
  const backendUrl = `${TASKS_URL}${url.search}`;
  const backendResponse = await fetch(backendUrl, {
    headers: { "X-User-Id": userId },
    cache: "no-store",
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
