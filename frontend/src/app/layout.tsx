import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Disclaimer } from "@/components/Disclaimer";
import { NavBar } from "@/components/NavBar";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Wealth-Lens",
  description: "SG Personal Finance Optimizer — educational simulation, not advice.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <NavBar />
        <main className="flex-1">{children}</main>
        <Disclaimer />
      </body>
    </html>
  );
}
