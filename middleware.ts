import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher(["/"]);

export default clerkMiddleware((auth, req) => {
  if (!isPublicRoute(req)) {
    const devBypass =
      process.env.NODE_ENV === "development" &&
      req.headers.get("x-user-id");
    if (devBypass) {
      return;
    }
    auth.protect();
  }
});

export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
};
