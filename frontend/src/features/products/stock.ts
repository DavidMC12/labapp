/**
 * The stock cue of the catalog screen: a stock of 0 is "Agotado" and a
 * stock of 1 to 5 is "Poco stock"; above 5 there is no badge. The thre-
 * sholds live here alone so a review of the rule reads one place and the
 * tests keep it honest.
 */

/**
 * A stock at or below this number (0, the only value that can be lower)
 * is out of stock.
 */
export const OUT_OF_STOCK_MAX = 0;

/** A stock in `1 … LOW_STOCK_MAX` is low stock. */
export const LOW_STOCK_MAX = 5;

/** The stock cue of one product, or `null` when the catalog shows none. */
export type StockState = "agotado" | "poco" | null;

/**
 * The badge of one stock value: `"agotado"` at or below
 * `OUT_OF_STOCK_MAX`, `"poco"` through `LOW_STOCK_MAX`, and `null` above
 * it — the plain number carries the rest.
 */
export function stockState(stock: number): StockState {
  if (stock <= OUT_OF_STOCK_MAX) {
    return "agotado";
  }
  if (stock <= LOW_STOCK_MAX) {
    return "poco";
  }
  return null;
}
