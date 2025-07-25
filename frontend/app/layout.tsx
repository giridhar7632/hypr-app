import type { Metadata } from "next";
import { Host_Grotesk } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";
import { ViewTransitions } from "next-view-transitions";
import Providers from "./provider";


const grotesk = Host_Grotesk({
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Market Sentiment Dashboard",
  description: "Market Sentiment Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ViewTransitions>
    <html lang="en">
      <body
        className={`${grotesk.className} antialiased`}
      >
        <Nav />
        <Providers>
        {children}
        </Providers>
      </body>
    </html>
    </ViewTransitions>
  );
}
