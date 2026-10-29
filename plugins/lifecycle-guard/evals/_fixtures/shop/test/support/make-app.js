// Wires src/api/refunds.js to in-memory stores and recording fakes; app.as(user) sends authenticated requests.
const { createApp } = require("../../src/api/app");
const fakes = require("./fakes");
module.exports.makeApp = () => {
  const deps = { orders: fakes.store(), refunds: fakes.store(), events: fakes.onceSet(), gateway: fakes.gateway(),
                 notify: fakes.recorder(), alerts: fakes.recorder(), settings: { refundWindowDays: 30 }, clock: fakes.clock() };
  return { ...deps, app: createApp(deps), customer: fakes.user(), admin: fakes.user({ isAdmin: true }), stranger: fakes.user() };
};
