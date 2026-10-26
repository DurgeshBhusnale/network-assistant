import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, Instrument_Sans } from "next/font/google";

import { copy } from "@/lib/copy/en";

import "./globals.css";
import { Providers } from "./providers";

const display = Bricolage_Grotesque({
  variable: "--font-bricolage",
  weight: ["600", "700"],
  subsets: ["latin"],
  display: "swap",
});

const body = Instrument_Sans({
  variable: "--font-instrument",
  weight: ["400", "500", "600"],
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
  // Matches --color-bg in design/tokens.css (the browser chrome can't read CSS variables).
  themeColor: "#F3F5F7",
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
