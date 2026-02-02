// index.bindings.js

document.addEventListener("DOMContentLoaded", () => {
  UIWidgets.init({
    "#pid-pv": {
      widget: "label",
      tag: "tic1.pid.pv",
      format: "fixed",
      precision: 1,
      unit: "°F"
    },

    "#tc-ctrlmode": {
      widget: "label",
      tag: "tic1.tc.ctrlmode",
      format: "fixed",
      precision: 1,
      unit: "°F"
    },

    "#pid-cv": {
      widget: "label",
      tag: "tic1.pid.cv",
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
