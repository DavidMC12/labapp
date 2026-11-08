"use client";

import { Alert, Button, Input, TableScroll } from "@/components/ui";
import { SortableHeader, type SortableHeaderState } from "@/components/ui";
import {
  flipProductSortDirection,
  isDefaultProductSort,
  parseProductListParams,
  productSortDefaultDirection,
  productSortLabel,
  resolveProductSort,
  type ProductSort,
  type ProductSortField,
} from "@/features/products/params";
import { useProducts } from "@/features/products/hooks";
import { productMatchesSearch } from "@/features/products/search";
import { stockState } from "@/features/products/stock";
import type { Product } from "@/features/products/hooks";
import { ApiRequestError, INTERNAL_ERROR_DETAIL } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

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
 * The url of the catalog: the search term when set, and the sort when it
 * is not the one of the plain catalog. An empty term drops the q
 * parameter, so `/products` and `/products?q=` are one url; the default
 * order (`id` ascending) leaves both sort parameters out, so the clean
 * url is the plain catalog.
 */
function listUrl(q: string | null, sort: ProductSort): string {
  const parts: string[] = [];
  if (q) {
    parts.push(`q=${encodeURIComponent(q)}`);
  }
  if (!isDefaultProductSort(sort)) {
    // The sort values are literal field names and the two directions;
    // no url encoding is needed for them.
    parts.push(`sort=${sort.sort}`);
    parts.push(`direction=${sort.direction}`);
  }
  return parts.length === 0 ? "/products" : `/products?${parts.join("&")}`;
}

function ProductsListContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const params = parseProductListParams(searchParams);
  // The resolved sort is stable while the URL values are: the catalog
  // request below must not re-key itself for a new object of the same
  // pair.
  const sort = useMemo(
    () =>
      resolveProductSort({
        sort: params.sort,
        direction: params.direction,
      }),
    [params.sort, params.direction],
  );
  // The plain catalog order travels without parameters: the request
  // (and the cache entry of the draft editor) stays the same one.
  const catalog = useProducts(
    isDefaultProductSort(sort)
      ? {}
      : { sort: sort.sort, direction: sort.direction },
  );

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
    router.push(listUrl(term || null, sort));
  }

  /**
   * Sorting from a header: a new column sorts with its default direction
   * (ascending, the catalog has none of the created fields), the sorted
   * one flips; either way the search term stays.
   */
  function toggleSort(field: ProductSortField) {
    const next: ProductSort = field === sort.sort
      ? {
        sort: field,
        direction: flipProductSortDirection(sort.direction),
      }
      : { sort: field, direction: productSortDefaultDirection() };
    router.push(listUrl(params.q, next));
  }

  /** The header state of one sortable column, the `aria-sort` value. */
  function headerState(field: ProductSortField): SortableHeaderState {
    if (sort.sort !== field) {
      return "none";
    }
    return sort.direction === "asc" ? "ascending" : "descending";
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

      {/*
       * The live announcement of the order of the table (the same one the
       * other lists have), hidden from the visual layout.
       */}
      <p
        role="status"
        data-testid="products-list-sort-text"
        className="sr-only"
      >
        {`Ordenado por ${productSortLabel(sort.sort)}, ${
          sort.direction === "asc" ? "ascendente" : "descendente"
        }`}
      </p>

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
          <TableScroll testId="products-list-scroll-region" label="Tabla de productos" className="mt-6">
            <table
              data-testid="products-list-table"
              className="min-w-[32rem]"
            >
              <thead>
                <tr>
                  <SortableHeader
                    label="SKU"
                    testId="products-list-sort-sku-button"
                    state={headerState("sku")}
                    className={TABLE_HEAD_CLASSES}
                    onClick={() => toggleSort("sku")}
                  />
                  <SortableHeader
                    label="Producto"
                    testId="products-list-sort-name-button"
                    state={headerState("name")}
                    className={TABLE_HEAD_CLASSES}
                    onClick={() => toggleSort("name")}
                  />
                  <SortableHeader
                    label="Precio"
                    testId="products-list-sort-price-button"
                    state={headerState("price")}
                    className={TABLE_HEAD_RIGHT_CLASSES}
                    onClick={() => toggleSort("price")}
                  />
                  <SortableHeader
                    label="Stock"
                    testId="products-list-sort-stock-button"
                    state={headerState("stock")}
                    className={TABLE_HEAD_RIGHT_CLASSES}
                    onClick={() => toggleSort("stock")}
                  />
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
          </TableScroll>

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