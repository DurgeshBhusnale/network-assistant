import type { MetadataRoute } from "next";

import { copy } from "@/lib/copy/en";

// Colours mirror design/tokens.css (--color-bg, --color-canvas-top); manifests can't read CSS vars.
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: copy.appName,
    short_name: copy.appName,
    description: copy.appDescription,
    start_url: "/today",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#F4F5FD",
    theme_color: "#FFFFFF",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
