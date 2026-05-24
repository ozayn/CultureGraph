import type { NextConfig } from "next";

function apiImageRemotePattern() {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    const url = new URL(raw);
    return {
      protocol: url.protocol.replace(":", "") as "http" | "https",
      hostname: url.hostname,
      ...(url.port ? { port: url.port } : {}),
      pathname: "/uploads/**",
    };
  } catch {
    return {
      protocol: "http" as const,
      hostname: "localhost",
      port: "8000",
      pathname: "/uploads/**",
    };
  }
}

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [apiImageRemotePattern()],
  },
};

export default nextConfig;
