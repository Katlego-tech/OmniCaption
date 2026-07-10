import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OmniCaption — AI Video Captioning on AMD",
  description:
    "Dual-model hybrid video captioning: local Whisper STT + Fireworks VLM on AMD MI300X. Four styles per clip, grounded in the actual audio and frames.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="antialiased">
      <body>{children}</body>
    </html>
  );
}
