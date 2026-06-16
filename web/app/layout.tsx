import type { Metadata } from "next";
import { Newsreader, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { DataProvider } from "@/components/DataProvider";

const serif = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  display: "swap",
  style: ["normal", "italic"],
});

const mono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title:
    "Unsafe Commercial Autonomy — a benchmark for agents spending human money",
  description:
    "When AI agents hold delegated payment authority, how often do they violate user intent, spend limits, merchant rules, approval boundaries, or privacy during realistic commercial tasks?",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${serif.variable} ${mono.variable} h-full`}>
      <body className="min-h-full">
        <DataProvider>{children}</DataProvider>
      </body>
    </html>
  );
}
