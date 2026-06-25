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
  metadataBase: new URL("https://paybench.org"),
  title: {
    default:
      "PayBench — A Benchmark for Unsafe Commercial Autonomy in AI Agents with Delegated Payment Authority",
    template: "%s · PayBench",
  },
  description:
    "When AI agents hold delegated payment authority, how often do they violate user intent, spend limits, merchant rules, approval boundaries, or privacy during realistic commercial tasks — and which control layers fix it without making the agent inert?",
  alternates: { canonical: "/" },
  openGraph: {
    title: "PayBench — Unsafe Commercial Autonomy benchmark",
    description:
      "A benchmark measuring whether AI agents with delegated payment authority preserve user intent across realistic commercial tasks.",
    url: "https://paybench.org",
    siteName: "PayBench",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "PayBench — Unsafe Commercial Autonomy benchmark",
    description:
      "A benchmark measuring whether AI agents with delegated payment authority preserve user intent across realistic commercial tasks.",
  },
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
