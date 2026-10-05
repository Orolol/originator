import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Let `next dev` hydrate when browsed at the loopback IP too (it only trusts `localhost` by default).
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
