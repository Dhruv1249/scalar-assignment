import type { Metadata } from "next";
import { Nunito, Inter } from "next/font/google";
import "./globals.css";

const nunito = Nunito({
  subsets: ["latin"],
  weight: ["700", "800"],
  variable: "--font-nunito",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "PII Redaction Studio — Soft UI",
  description: "Tactile, privacy-first document sanitizer powered by Presidio & spaCy",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${nunito.variable} ${inter.variable} antialiased`}>
      <body className="min-h-screen flex flex-col items-center justify-center p-4 sm:p-8">
        {children}
      </body>
    </html>
  );
}
