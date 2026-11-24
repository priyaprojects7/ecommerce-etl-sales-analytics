import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PULSE | Company Intelligence",
  description: "An interactive workspace for understanding company performance.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
