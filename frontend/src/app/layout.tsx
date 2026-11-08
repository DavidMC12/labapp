import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Serif } from "next/font/google";
import { Providers } from "@/components/Providers";
import { HydrationMarker } from "@/components/HydrationMarker";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import "./globals.css";

/**
 * The no-flash script, shipped inline in the <head> as a static string of
 * the server bundle: the stored choice lands on <html> before the first
 * paint, so the right voice of globals.css is active from the start. It
 * is built once at module scope from the exported storage key of
 * src/lib/theme.ts and nothing dynamic is interpolated. The whole
 * `window.localStorage` access sits inside the try, so blocked cookies
 * and storage leave the document on the system theme.
 */
export const THEME_NO_FLASH_SCRIPT =
  `try{var t=window.localStorage.getItem("${THEME_STORAGE_KEY}");`
  + 'if(t==="light"||t==="dark"){document.documentElement.setAttribute("data-theme",t)}}catch(e){}';

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
  title: {
    // The server render answers the plain "LabApp"; every screen sets
    // "{page} · LabApp" (the hook of src/lib/useDocumentTitle.ts on the
    // client pages, the template below on the ones that export metadata).
    default: "LabApp",
    template: "%s · LabApp",
  },
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
         * flash of the wrong theme).
         */}
        <script dangerouslySetInnerHTML={{ __html: THEME_NO_FLASH_SCRIPT }} />
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
