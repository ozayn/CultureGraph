import type { NextConfig } from "next";

import { securityResponseHeaders } from "./src/lib/security-headers";

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
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [...securityResponseHeaders],
      },
    ];
  },
  images: {
    remotePatterns: [
      apiImageRemotePattern(),
      {
        protocol: "https",
        hostname: "api.nga.gov",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "www.nga.gov",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "ids.si.edu",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "**.si.edu",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
