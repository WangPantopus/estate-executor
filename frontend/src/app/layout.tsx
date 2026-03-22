import type { Metadata } from "next";
import { Auth0Provider } from "@auth0/nextjs-auth0";
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
      <body className="min-h-full flex flex-col">
        <Auth0Provider>{children}</Auth0Provider>
      </body>
    </html>
  );
}
