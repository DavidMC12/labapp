# LabApp

Un ERP pequeño de pedido a cobro (clientes, pedidos, facturas, pagos) hecho para ser el blanco ideal de la automatización de pruebas: un `data-testid` estable en cada elemento interactivo, HTML accesible, datos deterministas y controles solo para pruebas que reinician datos, mueven el reloj e inyectan fallas.

> English version: [README.md](README.md)

**Estado:** en arranque. La especificación y la arquitectura están escritas; el código de la aplicación llega hito por hito (ver la hoja de ruta).

## Por qué

Las apps demo públicas para automatización suelen traer elementos sin localizadores fiables, lo que obliga a usar selectores frágiles. LabApp está pensada al revés: la testabilidad es un contrato (ver [docs/TESTABILITY.md](docs/TESTABILITY.md)), que se exigirá con tipos, reglas de lint y una auditoría en CI (previsto para M1).

## Qué hace

Tres flujos principales, que se pulen antes de añadir módulos nuevos:

1. Crear un cliente.
2. Armar y confirmar un pedido.
3. Facturar el pedido y registrar el pago.

Roles: Admin, Ventas, Finanzas y Solo lectura. La pantalla está en español. Las reglas de negocio están en [docs/SPEC.md](docs/SPEC.md) (en inglés).

## Tecnologías previstas

| Capa | Elección |
|---|---|
| Backend | FastAPI (Python), SQLAlchemy 2, Alembic, PostgreSQL |
| Frontend | Next.js, TypeScript, Tailwind, TanStack Query y Table |
| Contrato | OpenAPI generado por el backend y cliente tipado generado para el frontend |
| Local | Docker Compose, pasarela de pagos falsa, Mailpit para correo falso |
| Demo en línea | Vercel (web), Render (API), Neon (Postgres), todo en capas gratuitas |

## Hoja de ruta

| Hito | Contenido |
|---|---|
| M0 | Arranque del repositorio, especificación, arquitectura, esqueleto de CI |
| M1 | Base compartida, login y roles, controles solo para pruebas, clientes, primer despliegue en línea |
| M2 | Pedidos |
| M3 | Facturas y pagos |
| M4 | Pulido: 100 % de testid, accesibilidad, endurecer la demo |

## Usuarios de la demo

Desde M1, la pantalla de login de la demo en línea mostrará las credenciales de cuatro usuarios de ejemplo, uno por rol: `admin@labapp.test`, `sales@labapp.test`, `finance@labapp.test` y `readonly@labapp.test`. Los datos serán compartidos y se reiniciarán cada noche.

## Estructura del repositorio

| Ruta | Propósito |
|---|---|
| `backend/` | Aplicación FastAPI y sus pruebas internas (desde M1) |
| `frontend/` | Aplicación Next.js y sus pruebas de componentes (desde M1) |
| `tools/audit/` | Auditorías de testid y accesibilidad que corren en CI (desde M1) |
| `tests/` | Reservada para la suite de automatización E2E y de API del dueño |
| `docs/` | Especificación, arquitectura y contrato de testabilidad; las instrucciones de tareas y los registros de revisión se añaden al empezar el trabajo |

## Cómo empezar

Disponible desde M1. Las versiones de las herramientas (Node, uv, pnpm) están fijadas en `mise.toml`; todo arranca con un solo `docker compose up`.

## Licencia

[MIT](LICENSE)
