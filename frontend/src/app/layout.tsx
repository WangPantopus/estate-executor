import type { Metadata } from "next";
import { Auth0Provider } from "@auth0/nextjs-auth0";
import { QueryProvider } from "@/components/providers/QueryProvider";
import "./globals.css";

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
    <html lang="en" className="h-full antialiased">
      <head>
        {/* Inter (sans) and Crimson Pro (serif) — premium typography */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500;600&family=Inter:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full flex flex-col font-sans">
        <Auth0Provider>
          <QueryProvider>{children}</QueryProvider>
        </Auth0Provider>
      </body>
    </html>
  );
}
