import type { Metadata } from "next";
import { Inter, Newsreader, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { RESULTS_LIVE } from "@/lib/config";
// Once results are live, DataProvider fetches published runs from Supabase for
// the results components (see components/results/README.md). While the site is
// a proposal it is skipped entirely so the page makes no network calls.
import { DataProvider } from "@/components/results/DataProvider";

// Three faces, each with a job: Inter carries the UI and every heading,
// Newsreader is kept for long-form prose only (the site is a paper, and that
// is the one thing a serif does better), JetBrains Mono carries the data —
// scenario IDs, rates, and every table. Subset to latin and to the weights
// actually used, since three families is a real budget.
const sans = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  display: "swap",
});

const serif = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  display: "swap",
  style: ["normal", "italic"],
});

const mono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://paybench.org"),
  title: {
    default:
      "PayBench: A Benchmark for Unsafe Commercial Autonomy in AI Agents with Delegated Payment Authority",
    template: "%s · PayBench",
  },
  description:
    "When AI agents hold delegated payment authority, how often do they violate user intent, spend limits, merchant rules, approval boundaries, or privacy during realistic commercial tasks, and which control layers fix it without making the agent inert?",
  alternates: { canonical: "/" },
  openGraph: {
    title: "PayBench: Unsafe Commercial Autonomy benchmark",
    description:
      "A benchmark measuring whether AI agents with delegated payment authority preserve user intent across realistic commercial tasks.",
    url: "https://paybench.org",
    siteName: "PayBench",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "PayBench: Unsafe Commercial Autonomy benchmark",
    description:
      "A benchmark measuring whether AI agents with delegated payment authority preserve user intent across realistic commercial tasks.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${sans.variable} ${serif.variable} ${mono.variable} h-full`}
    >
      <body className="min-h-full">
        {RESULTS_LIVE ? <DataProvider>{children}</DataProvider> : children}
      </body>
    </html>
  );
}
