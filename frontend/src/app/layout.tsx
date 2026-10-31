import type { Metadata } from "next";
import { Providers } from "@/components/Providers";
import { HydrationMarker } from "@/components/HydrationMarker";
import "./globals.css";

export const metadata: Metadata = {
  title: "LabApp",
  description: "LabApp web",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        <Providers>
          <HydrationMarker />
          {children}
        </Providers>
      </body>
    </html>
  );
}
