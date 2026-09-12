import type { Metadata, Viewport } from "next";
import { Shell } from "@/components/shell";
import { PwaRegister } from "@/components/pwa-register";
import "./globals.css";

export const metadata: Metadata = {
  title: "NextOffer — Your job search assistant",
  description: "Chat with your job search assistant and keep your applications organized in Google Sheets.",
  manifest: "/manifest.webmanifest",
  applicationName: "NextOffer",
  // black-translucent lets the page's own background extend behind the
  // notch/Dynamic Island (instead of iOS reserving an opaque status bar) —
  // it also forces the status bar icons to always render white, regardless
  // of light/dark mode, which is why globals.css keeps a small always-dark
  // strip behind them for legibility (see body::before).
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "NextOffer" },
  icons: {
    icon: "/icon.svg",
    apple: "/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2f2f7" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
        <PwaRegister />
      </body>
    </html>
  );
}
