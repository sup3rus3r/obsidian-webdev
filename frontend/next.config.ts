import type { NextConfig } from "next";


const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:7412";

const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    return [
      {
        source      : "/api/auth/:path*",
        destination : "/api/auth/:path*",
      },
      {
        source      : "/api/:path*",
        destination : `${BACKEND_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
