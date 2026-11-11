import type { NextConfig } from "next";

// NEXT_PUBLIC_API_URL is inlined at build time. On Vercel, a missing value would
// silently ship a bundle that calls http://localhost:8000, so fail the build.
if (process.env.VERCEL && !process.env.NEXT_PUBLIC_API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL must be set in the Vercel project settings");
}

const nextConfig: NextConfig = {};

export default nextConfig;
