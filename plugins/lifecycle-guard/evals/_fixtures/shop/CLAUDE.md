# Shop
Small storefront + admin. React UI (`src/admin`, `src/customer`), Express API (`src/api`).
Settings live on the existing admin pages listed in `src/admin/routes.js`.

This is a deliberately small eval fixture: the test harness wiring (`test/support/fakes.js`, `src/api/app.js`)
and framework helpers (`router`, `requireAdmin`, `useApi`, ...) are omitted on purpose.
