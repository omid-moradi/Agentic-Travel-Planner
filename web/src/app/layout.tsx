import type { Metadata } from "next";
import "./globals.css";
import { LangProvider } from "@/lib/lang-context";

export const metadata: Metadata = {
  title: "Agentic Travel Planner",
  description:
    "Plan an entire trip - domestic Iran and international - in Persian and English, with sourced facts and deterministic optimization.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fa" dir="rtl" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900">
        <LangProvider>{children}</LangProvider>
      </body>
    </html>
  );
}

