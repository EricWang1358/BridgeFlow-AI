import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "BridgeFlow AI",
  description: "Align cross-department SME data into one Master Table.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>{children}</body>
    </html>
  );
}
