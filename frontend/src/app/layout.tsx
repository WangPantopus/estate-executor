import type { Metadata } from "next";
import { Inter, Crimson_Pro } from "next/font/google";
import { Auth0Provider } from "@auth0/nextjs-auth0";
import { QueryProvider } from "@/components/providers/QueryProvider";
import "./globals.css";

// Self-hosted via next/font — eliminates external network request to
// Google Fonts, enables font-display:swap by default, and allows the
// fonts to be cached with the rest of the static assets on the CDN.
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const crimsonPro = Crimson_Pro({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600"],
  variable: "--font-serif",
});

export const metadata: Metadata = {
  title: "Estate Executor OS",
  description: "Coordination Operating System for Estate Administration",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`h-full antialiased ${inter.variable} ${crimsonPro.variable}`}
    >
      <body className="min-h-full flex flex-col font-sans">
        <Auth0Provider>
          <QueryProvider>{children}</QueryProvider>
        </Auth0Provider>
      </body>
    </html>
  );
}
