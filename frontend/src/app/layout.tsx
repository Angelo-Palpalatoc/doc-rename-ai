import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocRename AI — Document OCR & Auto-Renaming",
  description:
    "Deterministic local OCR, corporate registry matching, and optional structured-output LLM fallback.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0054A4",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-[100dvh] bg-[#F3F6FA] text-[#162B43] antialiased selection:bg-[#0054A4]/15 selection:text-[#162B43]">
        {children}
      </body>
    </html>
  );
}
