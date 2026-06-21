import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Dev only: Next 16 blocks cross-origin requests to dev assets (HMR, chunks,
  // RSC) by default, so opening the dev server from a phone on the LAN fails to
  // hydrate. These are the host's LAN and Tailscale addresses used for on-device
  // testing. No effect on the production build. Hostnames only, no scheme/port.
  // Adjust if the LAN IP changes.
  allowedDevOrigins: ["192.168.178.76", "192.168.178.111", "100.64.0.83"],
};

export default nextConfig;
