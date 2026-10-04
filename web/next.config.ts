import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required by the Docker runtime stage: emits .next/standalone so the
  // production image only needs the server files and node.
  output: "standalone",
};

export default nextConfig;

