import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, Figtree } from "next/font/google";

import { copy } from "@/lib/copy/en";

import "./globals.css";
import { Providers } from "./providers";

const display = Bricolage_Grotesque({
  variable: "--font-bricolage",
  weight: ["500", "600", "700"],
  subsets: ["latin"],
  display: "swap",
});

const body = Figtree({
  variable: "--font-figtree",
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: copy.appName,
  description: copy.appDescription,
  applicationName: copy.appName,
  appleWebApp: { capable: true, title: copy.appName, statusBarStyle: "default" },
  icons: { icon: "/icons/icon-192.png", apple: "/icons/icon-192.png" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  // Matches --color-canvas-top in design/tokens.css (the browser chrome can't read CSS vars).
  themeColor: "#FFFFFF",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} antialiased`}>
      <body className="min-h-dvh">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
