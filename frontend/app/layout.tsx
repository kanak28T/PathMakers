import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PathMakers — AI Learning Roadmap",
  description:
    "Personalized ML-powered learning roadmap with prerequisite-aware DAG navigation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-50 antialiased">
        {children}
      </body>
    </html>
  );
}
