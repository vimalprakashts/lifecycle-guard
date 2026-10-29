// Every admin page. Add to an existing page before adding a new top-level one.
export const adminRoutes = [
  { path: "/admin/orders", page: "OrdersPage", nav: "Orders" },          // supports ?status=
  { path: "/admin/orders/:id", page: "OrderDetailPage" },
  { path: "/admin/customers/:id", page: "CustomerDetailPage" },
  { path: "/admin/refunds", page: "RefundsPage", nav: "Refunds" },       // supports ?status=
  { path: "/admin/settings/payments", page: "PaymentSettingsPage", nav: "Settings" }, // gateway keys, refund window
];
