"use client";

import { Button, Input } from "@/components/ui";
import { Alert } from "@/components/ui";
import { useProducts } from "@/features/products/hooks";
import { parseProductListParams } from "@/features/products/params";
import { productMatchesSearch } from "@/features/products/search";
import { stockState } from "@/features/products/stock";
import type { Product } from "@/features/products/hooks";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

/** The classes of a ledger header cell and a ledger body cell. */
const TABLE_HEAD_CLASSES = [
  "border-b-2 border-ink px-[10px] py-[9px] text-left",
  "text-xs font-medium uppercase tracking-[0.07em] text-muted",
].join(" ");

const TABLE_CELL_CLASSES =
  "border-b border-line px-[10px] py-[9px] text-ink tabular-nums";

/** The money and stock columns are numbers: right aligned. */
const TABLE_HEAD_RIGHT_CLASSES =
  `${TABLE_HEAD_CLASSES} text-right`;

const TABLE_CELL_RIGHT_CLASSES =
  `${TABLE_CELL_CLASSES} text-right`;

/** The styles of the stock badge, the pattern of the list state badges. */
const BADGE_CLASSES =
  "inline-flex whitespace-nowrap rounded-sm px-2 py-0.5 text-xs font-semibold";

type StockBadge = {
  label: string;
  classes: string;
};

function stockBadge(stock: number): StockBadge | null {
  const state = stockState(stock);
  if (state === "agotado") {
    return {
      label: "Agotado",
      classes: `${BADGE_CLASSES} bg-danger-bg text-danger`,
    };
  }
  if (state === "poco") {
    return {
      label: "Poco stock",
      classes: `${BADGE_CLASSES} bg-off-bg text-muted`,
    };
  }
  return null;
}

/**
 * The url of the search: the only state the catalog has. An empty term
 * drops the parameter, so `/products` and `/products?q=` are one url.
 */
function listUrl(q: string | null): string {
  return q ? `/products?q=${encodeURIComponent(q)}` : "/products";
}

function ProductsListContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const params = parseProductListParams(searchParams);
  const catalog = useProducts();

  // The field of the search form is local; submitting it writes the url,
  // which is what the client-side filter reads.
  const [qInput, setQInput] = useState(params.q ?? "");

  // The url is the state: arriving from a link resets the field during
  // render — the "adjust state when its dependencies change" pattern the
  // other lists use — instead of watching the url in an effect.
  const [lastUrlQ, setLastUrlQ] = useState(params.q);
  if (lastUrlQ !== params.q) {
    setLastUrlQ(params.q);
    setQInput(params.q ?? "");
  }

  function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const term = qInput.trim();
    router.push(listUrl(term || null));
  }

  function problemDetail(): string {
    if (catalog.error instanceof ApiRequestError) {
      return catalog.error.problem.detail;
    }
    return INTERNAL_ERROR_DETAIL;
  }

  const data = catalog.isSuccess && catalog.data !== undefined
    ? catalog.data
    : null;
  // The filter runs in the browser: the loaded rows never require a
  // second request.
  const items: Product[] = data === null
    ? []
    : data.items.filter((product) =>
      productMatchesSearch(product, params.q ?? "")
    );

  return (
    <div>
      <h1 data-testid="products-list-heading">Productos</h1>

      <form
        data-testid="products-list-search-form"
        onSubmit={handleSearch}
        className="mt-4 grid items-end gap-3 md:grid-cols-[minmax(0,1fr)_auto]"
      >
        <Input
          id="products-list-search"
          testId="products-list-search-input"
          label="Buscar por SKU o nombre"
          value={qInput}
          onChange={(event) => setQInput(event.target.value)}
        />
        <Button
          testId="products-list-search-button"
          type="submit"
          variant="secondary"
        >
          Buscar
        </Button>
      </form>

      {catalog.isPending ? (
        <p
          role="status"
          data-testid="products-list-loading-status"
          aria-busy="true"
          className="mt-6 text-muted"
        >
          Cargando…
        </p>
      ) : catalog.isError ? (
        <div className="mt-6">
          <Alert testId="products-list-error-alert">
            {problemDetail()}
          </Alert>
          <div className="mt-3">
            <Button
              testId="products-list-retry-button"
              onClick={() => void catalog.refetch()}
            >
              Reintentar
            </Button>
          </div>
        </div>
      ) : data !== null && items.length === 0 ? (
        <p
          role="status"
          data-testid="products-list-empty-status"
          className="mt-6 text-muted"
        >
          No hay productos que coincidan.
        </p>
      ) : data !== null ? (
        <>
          {/*
           * The wide content scrolls inside this wrapper, never the page:
           * the padding keeps the 3px focus ring visible around the
           * scrollbar edges.
           */}
          <div className="mt-6 overflow-x-auto p-1.5">
            <table
              data-testid="products-list-table"
              className="min-w-[32rem]"
            >
              <thead>
                <tr>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>SKU</th>
                  <th scope="col" className={TABLE_HEAD_CLASSES}>Producto</th>
                  <th scope="col" className={TABLE_HEAD_RIGHT_CLASSES}>
                    Precio
                  </th>
                  <th scope="col" className={TABLE_HEAD_RIGHT_CLASSES}>
                    Stock
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((product) => {
                  const badge = stockBadge(product.stock);
                  return (
                    <tr
                      key={product.id}
                      data-testid={`products-list-row-${product.id}`}
                      className="ledger-row"
                    >
                      <td
                        data-testid={`products-list-sku-cell-${product.id}`}
                        className={TABLE_CELL_CLASSES}
                      >
                        {product.sku}
                      </td>
                      <td
                        data-testid={`products-list-name-cell-${product.id}`}
                        className={TABLE_CELL_CLASSES}
                      >
                        {product.name}
                      </td>
                      <td
                        data-testid={`products-list-price-cell-${product.id}`}
                        className={TABLE_CELL_RIGHT_CLASSES}
                      >
                        {formatMoney(product.price)}
                      </td>
                      <td
                        data-testid={`products-list-stock-cell-${product.id}`}
                        className={TABLE_CELL_RIGHT_CLASSES}
                      >
                        <span className="inline-flex items-center gap-2">
                          {product.stock}
                          {badge ? (
                            <span
                              data-testid={`products-list-stockstate-status-${product.id}`}
                              className={badge.classes}
                            >
                              {badge.label}
                            </span>
                          ) : null}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/*
           * The ledger footer: a 4px double rule of ink above it and the
           * count of the rows on screen — the count of the **filtered**
           * rows, because the table shows the filtered search. It answers
           * "1 producto" for one row.
           */}
          <p
            data-testid="products-list-footer-item"
            className="mt-6 border-t-4 border-double border-ink pt-3 font-semibold tabular-nums"
          >
            {items.length === 1 ? "1 producto" : `${items.length} productos`}
          </p>
        </>
      ) : null}
    </div>
  );
}

/**
 * The url can only be read inside a Suspense boundary, so the content
 * lives here and the default export wraps it (the pattern of the other
 * list screens).
 */
export default function ProductsPage() {
  useDocumentTitle("Productos");

  return (
    <Suspense
      fallback={
        <p
          role="status"
          data-testid="products-list-loading-status"
          aria-busy="true"
        >
          Cargando…
        </p>
      }
    >
      <ProductsListContent />
    </Suspense>
  );
}