import type { Metadata } from "next";

/**
 * The title of the login page, answered by the server so that it is right from the first byte. The
 * client hook of the page used to be the only source, and the framework put the default title back
 * when the page below its Suspense boundary resolved.
 */
export const metadata: Metadata = {
  title: "Iniciar sesión",
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
