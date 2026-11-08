import { Link } from "@/components/ui";

/**
 * The 404 page of any unknown route (the root `not-found.tsx` is what
 * Next.js renders for every unmatched url). It is part of the root
 * layout, so the theme tokens of `globals.css` apply as on any screen:
 * readable in the light and the dark voice alike.
 */
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 py-10 text-center">
      <h1 data-testid="app-notfound-heading">Página no encontrada</h1>
      <p className="text-muted">
        La dirección que buscas no existe o fue movida.
      </p>
      <Link href="/" testId="app-notfound-home-link" variant="secondary">
        Ir al inicio
      </Link>
    </div>
  );
}
