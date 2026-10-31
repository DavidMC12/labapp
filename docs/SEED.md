# Seed data

The exact data loaded on first start and restored by `POST /__test__/reset`. Values here are the contract: tests may rely on them. Business rules are in [SPEC.md](SPEC.md).

## Users

All four users share the demo password `Demo-LabApp-2026!`, which the login screen of the demo displays.

| Email | Name | Role |
|---|---|---|
| `admin@labapp.test` | Admin Demo | Admin |
| `sales@labapp.test` | Ventas Demo | Sales |
| `finance@labapp.test` | Finanzas Demo | Finance |
| `readonly@labapp.test` | Solo Lectura Demo | Read-only |

All four users were created on `2026-01-01` at 08:00 UTC.

## Customers

| Id | Name | Email | Tax ID | Status | Why it exists |
|---|---|---|---|---|---|
| 1 | Acme Industrial S.A. | `acme@example.test` | `ACME-900123` | active | Baseline customer. |
| 2 | Beta Comercial Ltda. | `beta@example.test` | `BETA-800456` | active | Baseline customer. |
| 3 | Cafetería La Esquina | `cafe@example.test` | none | active | Active but cannot be invoiced (no tax ID). |
| 4 | Distribuidora Delta | `delta@example.test` | `DELT-700789` | active | Has an issued invoice with a declined payment. |
| 5 | Estudio Épsilon | `epsilon@example.test` | `EPSI-600321` | inactive | Cannot receive new orders. |
| 6 | Ferretería Fénix | `fenix@example.test` | `FENI-500654` | active | Has a paid order. |
| 7 | Grupo Gamma Servicios Profesionales y Consultoría Internacional de Latinoamérica Sociedad por Acciones Simplificada | `gamma@example.test` | `GAMM-400111` | active | Long name (115 of 120 characters). |
| 8 | Hotel Horizonte | `hotel@example.test` | none | inactive | Inactive and without tax ID. |
| 9 | Ibérica Importaciones | `iberica@example.test` | `IBER-400987` | active | Has a shipped order. |
| 10 | Joyería Júpiter | `joyeria@example.test` | `JUPI-300210` | active | Has a cancelled order. |

Phone and address are empty except for customer 1 (`+1 555 010 0001`, `Av. Principal 100`). Customer `n` was created on `2026-01-01` at 09:00 UTC plus `n` minutes, so customer 10 is the newest. Every seeded record has `version` 1.

## Products

The stock column is the stock after the seeded orders below are applied. All products were created on `2026-01-01` at 08:30 UTC.

| Id | SKU | Name | Price (USD) | Stock | Why it exists |
|---|---|---|---|---|---|
| 1 | `KB-100` | Teclado USB | 19.90 | 120 | |
| 2 | `MS-200` | Mouse óptico | 9.50 | 195 | |
| 3 | `MN-240` | Monitor 24" | 149.00 | 33 | |
| 4 | `LP-300` | Laptop 14" | 699.00 | 11 | |
| 5 | `HD-500` | Disco externo 1 TB | 59.99 | 57 | |
| 6 | `CB-010` | Cable HDMI 2 m | 6.25 | 489 | |
| 7 | `WC-720` | Cámara web HD | 34.50 | 3 | Low stock. |
| 8 | `HS-110` | Audífonos con micrófono | 22.00 | 78 | |
| 9 | `PR-400` | Impresora láser | 189.90 | 0 | Out of stock. |
| 10 | `UP-650` | UPS 650 VA | 79.00 | 18 | |
| 11 | `RT-AC1` | Router doble banda | 44.75 | 40 | |
| 12 | `SW-8P` | Switch 8 puertos | 27.40 | 25 | The cancelled order does not consume stock. |
| 13 | `DK-USB` | Hub USB-C 7 en 1 | 31.20 | 70 | |
| 14 | `SD-128` | Tarjeta SD 128 GB | 14.99 | 300 | |
| 15 | `CH-ERG` | Silla ergonómica | 215.00 | 8 | |

## Orders, invoices and payments

Tax rate 10.00% (the default of `DEFAULT_TAX_RATE`). Draft orders do not reserve stock.

| Order | Customer | Status | Lines | Subtotal | Tax | Total | Invoice | Payments |
|---|---|---|---|---|---|---|---|---|
| `PED-0001` | 1 | draft | `KB-100` x 2 | 39.80 | 3.98 | 43.78 | none | none |
| `PED-0002` | 2 | confirmed | `MS-200` x 5, `CB-010` x 10 | 110.00 | 11.00 | 121.00 | none | none |
| `PED-0003` | 4 | confirmed | `MN-240` x 2 | 298.00 | 29.80 | 327.80 | `FAC-0001` issued | #1 card ending 0002, declined; #2 card ending 0003, failed (gateway unavailable) |
| `PED-0004` | 6 | paid | `HD-500` x 3 | 179.97 | 18.00 | 197.97 | `FAC-0002` paid | #3 transfer (reference `TRF-2026-0001`), approved |
| `PED-0005` | 9 | shipped | `LP-300` x 1 | 699.00 | 69.90 | 768.90 | `FAC-0003` paid | #4 cash, approved |
| `PED-0006` | 10 | cancelled | `SW-8P` x 4 | 109.60 | 10.96 | 120.56 | none | none |
| `PED-0007` | 3 | confirmed | `HS-110` x 2, `CB-010` x 1 | 50.25 | 5.03 | 55.28 | none | none |

Notes:
- `PED-0004`: 179.97 x 10% = 17.997, rounded half-up to 18.00.
- `PED-0007`: 50.25 x 10% = 5.025, a tie that half-up rounds to 5.03 (half-even would give 5.02).
- `PED-0007` belongs to a customer without tax ID, so invoicing it fails with `CUSTOMER_TAX_ID_REQUIRED`.
- Timestamps are fixed: order `PED-000n` is created on `2026-01-0n` at 10:00 UTC; invoices are issued the same day as their order at 14:00 UTC; payments are made at 15:00 UTC on that day.

## Numbering and reset

- Numbers are zero-padded to at least 4 digits and grow beyond that (`PED-10000`). After the seed, the next order is `PED-0008`, the next invoice `FAC-0004` and the next payment id 5. Seeded numbers have no gaps; later numbers can skip one, because a rolled-back transaction still consumes a number. Ids of invoices, order lines and payments are assigned in the order they appear in the tables above.
- `POST /__test__/reset` restores the data above and everything else listed in [SPEC.md](SPEC.md) section 9. `POST /__test__/seed` with the `default` dataset loads the same data without touching the number sequences' definition; with `empty` it keeps only the four users and the settings.
