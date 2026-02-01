// index.bindings.js

document.addEventListener("DOMContentLoaded", () => {
  UIWidgets.init({
    "#smoker-temp": {
      widget: "label",
      tag: "smoker.temp",
      format: "fixed",
      precision: 1,
      unit: "°F"
    },

    "#meat-temp": {
      widget: "label",
      tag: "meat.temp",
      format: "fixed",
      precision: 1,
      unit: "°F"
    },

    "#heater-pct": {
      widget: "label",
      tag: "heater.1.pct",
      format: "fixed",
      precision: 0,
      unit: "%"
    },

    "#start-btn": {
      widget: "button",
      tag: "smoker.start",
      value: 1
    }
  });
});
