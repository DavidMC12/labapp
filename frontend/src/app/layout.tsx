import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Serif } from "next/font/google";
import { Providers } from "@/components/Providers";
import { HydrationMarker } from "@/components/HydrationMarker";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import "./globals.css";

/*
 * "Libro mayor" typography: IBM Plex Sans for the body, IBM Plex Serif for
 * the headings and the brand, exposed as CSS variables that globals.css
 * maps into the `--font-sans`/`--font-serif` theme tokens.
 */
const plexSans = IBM_Plex_Sans({
  weight: ["400", "500", "600"],
  style: ["normal"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-plex-sans",
});

const plexSerif = IBM_Plex_Serif({
  weight: ["600"],
  style: ["normal"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-plex-serif",
});

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
    <html
      lang="es"
      className={`${plexSans.variable} ${plexSerif.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/*
         * The stored theme has to land on <html> before the first paint,
         * so the correct tokens of globals.css are already active (no
         * flash of the wrong theme). See src/lib/theme.ts.
         */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>
        <Providers>
          <HydrationMarker />
          {children}
        </Providers>
      </body>
    </html>
  );
}
