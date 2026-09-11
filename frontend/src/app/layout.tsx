import type { Metadata, Viewport } from "next";
import { Shell } from "@/components/shell";
import { PwaRegister } from "@/components/pwa-register";
import "./globals.css";

export const metadata: Metadata = {
  title: "NextOffer — Your job search assistant",
  description: "Chat with your job search assistant and keep your applications organized in Google Sheets.",
  manifest: "/manifest.webmanifest",
  applicationName: "NextOffer",
  appleWebApp: { capable: true, statusBarStyle: "default", title: "NextOffer" },
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
