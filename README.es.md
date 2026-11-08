# LabApp

Un ERP pequeño de pedido a cobro (clientes, pedidos, facturas, pagos) hecho para ser el blanco ideal de la automatización de pruebas: un `data-testid` estable en cada elemento interactivo, HTML accesible, datos deterministas y controles solo para pruebas que reinician datos, mueven el reloj e inyectan fallas.

> English version: [README.md](README.md)

**Estado:** en desarrollo activo, aún sin desplegar. Lo que existe hoy está en "Dónde va"; la especificación, la arquitectura y el contrato de testabilidad están escritos y se mantienen al día con el código.

## Capturas

Tomadas de una compilación de producción con los datos de ejemplo, en las dos versiones del diseño "Libro mayor" y en ancho de teléfono.

<p>
  <img src="docs/screenshots/login-light.png" alt="Login con los usuarios de la demo" width="48%">
  <img src="docs/screenshots/home-light.png" alt="Resumen de los datos" width="48%">
  <img src="docs/screenshots/customers-light.png" alt="Lista de clientes" width="48%">
  <img src="docs/screenshots/order-detail-light.png" alt="Un pedido confirmado con sus totales" width="48%">
  <img src="docs/screenshots/invoice-detail-dark.png" alt="Una factura pagada, tema oscuro" width="48%">
  <img src="docs/screenshots/products-dark.png" alt="Catálogo de productos, tema oscuro" width="48%">
</p>

<img src="docs/screenshots/orders-phone-light.png" alt="La lista de pedidos en un teléfono" width="260">

## Por qué

Las apps demo públicas para automatización suelen traer elementos sin localizadores fiables, lo que obliga a usar selectores frágiles. LabApp está pensada al revés: la testabilidad es un contrato (ver [docs/TESTABILITY.md](docs/TESTABILITY.md)), que se exige con tipos, reglas de lint y dos auditorías que corren en CI (una estática y otra en navegador con axe).

## Qué hace

Tres flujos principales, que se pulen antes de añadir módulos nuevos:

1. Crear un cliente.
2. Armar y confirmar un pedido.
3. Facturar el pedido y registrar el pago.

Roles: Admin, Ventas, Finanzas y Solo lectura. La pantalla está en español. Las reglas de negocio están en [docs/SPEC.md](docs/SPEC.md) (en inglés).

## Tecnologías

| Capa | Elección |
|---|---|
| Backend | FastAPI (Python), SQLAlchemy 2, Alembic, PostgreSQL |
| Frontend | Next.js, TypeScript, Tailwind, TanStack Query y Table |
| Contrato | OpenAPI generado por el backend y cliente tipado generado para el frontend |
| Local | Un script de arranque (`mise run dev`), datos en memoria o una base Neon de desarrollo, pasarela de pagos falsa; el correo falso solo se escribe en los logs |
| Demo en línea | Vercel (web y API en un solo proyecto), Neon (Postgres), todo en capas gratuitas |

## Dónde va

| Área | Estado |
|---|---|
| Login, sesiones y los cuatro roles | Hecho (en memoria y en PostgreSQL) |
| Clientes: API, pantallas, almacén en PostgreSQL | Hecho |
| Pedidos: API, pantallas, almacén en PostgreSQL con stock y numeración bajo concurrencia | Hecho |
| Configuración (impuesto, solo Admin) y resumen de inicio | Hecho |
| Diseño: tema "Libro mayor" en versión clara y oscura, selector que se recuerda por navegador | Hecho |
| Protecciones de petición: origen, JSON mal formado, tamaño, límites, tiempos de espera de bloqueos | Hecho |
| Auditorías de testabilidad en CI: auditoría estática de testid, auditoría en navegador (testid y axe) en los dos temas, pruebas de integración con PostgreSQL | Hecho |
| Facturas y pagos: API, pantallas, almacén en PostgreSQL con pagos idempotentes y pasarela falsa | Hecho |
| Controles solo para pruebas (reset, seed, reloj, inyección de fallas) con estado en PostgreSQL, protegidos por token | Hecho |
| Contrato de la API: `docs/openapi.json`, comprobado contra el código en CI | Hecho |
| Guía de automatización de la interfaz web, catálogo generado de test ids | Hecho; la guía de los controles y la API sigue |
| Primer despliegue en línea (Vercel y Neon) y reinicio nocturno de datos | Configurado, aún sin desplegar |

## Hoja de ruta

| Hito | Contenido |
|---|---|
| M0 | Arranque del repositorio, especificación, arquitectura, esqueleto de CI |
| M1 | Base compartida, login y roles, controles solo para pruebas, clientes, primer despliegue en línea |
| M2 | Pedidos |
| M3 | Facturas y pagos |
| M4 | Pulido: 100 % de testid, accesibilidad, endurecer la demo |

## Usuarios de la demo

La pantalla de login muestra las credenciales de cuatro usuarios de ejemplo, uno por rol: `admin@labapp.test`, `sales@labapp.test`, `finance@labapp.test` y `readonly@labapp.test`. En la demo en línea los datos serán compartidos y se reiniciarán cada noche.

## Estructura del repositorio

| Ruta | Propósito |
|---|---|
| `backend/` | Aplicación FastAPI y sus pruebas internas |
| `frontend/` | Aplicación Next.js y sus pruebas de componentes |
| `tools/audit/` | Auditorías de testid y accesibilidad que corren en CI |
| `tests/` | Reservada para la suite de automatización E2E y de API del dueño |
| `docs/` | Especificación, arquitectura, contrato de testabilidad, guías de despliegue y de desarrollo; las instrucciones de cada tarea y el registro de revisión de cada tarea mergeada |

## Cómo empezar

```bash
mise install    # una vez: Node, pnpm y uv en las versiones fijadas
mise run dev    # API en 127.0.0.1:8000, web en localhost:3000, datos en memoria
```

Abre <http://localhost:3000> e ingresa con uno de los usuarios de la demo. ¿Empiezas a automatizar aquí? [docs/AUTOMATION_GUIDE.md](docs/AUTOMATION_GUIDE.md) (en inglés) es una guía práctica para conducción de pruebas sobre la interfaz web. Mira [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) (en inglés) para la opción con base de datos y los demás comandos, y [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) para el despliegue en línea.

## Licencia

[MIT](LICENSE)
