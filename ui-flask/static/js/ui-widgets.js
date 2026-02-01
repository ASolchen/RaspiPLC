// ui-widgets.js

(() => {
  const widgets = {};
  const bindingsByTag = {};
  let socket = null;

  /* ---------------- Engine ---------------- */

  function init(bindings) {
    // Build tag → widget map
    for (const selector in bindings) {
      const cfg = bindings[selector];
      const el = document.querySelector(selector);
      if (!el) {
        console.warn("UI binding: element not found:", selector);
        continue;
      }

      const widget = widgets[cfg.widget];
      if (!widget) {
        console.error("Unknown widget:", cfg.widget);
        continue;
      }

      const instance = widget.init(el, cfg);

      // Register tag subscriptions
      if (cfg.tag) {
        if (!bindingsByTag[cfg.tag]) {
          bindingsByTag[cfg.tag] = [];
        }
        bindingsByTag[cfg.tag].push(instance);
      }
    }

    connectSocket();
  }

  function connectSocket() {
    socket = io();

    socket.on("tag_update", updates => {
      for (const tag in updates) {
        const value = updates[tag];
        const subs = bindingsByTag[tag];
        if (!subs) continue;

        subs.forEach(w => w.onTag(value));
      }
    });
  }

  function writeTag(tag, value) {
    if (!socket) return;
    socket.emit("write_tag", { tag, value });
  }

  /* ---------------- Widgets ---------------- */

  widgets.label = {
    init(el, cfg) {
      return {
        onTag(value) {
          let txt = value;

          if (cfg.format === "fixed") {
            const p = cfg.precision ?? 1;
            txt = Number(value).toFixed(p);
          }

          if (cfg.unit) {
            txt += " " + cfg.unit;
          }

          el.textContent = txt;
        }
      };
    }
  };

  widgets.button = {
    init(el, cfg) {
      el.addEventListener("click", () => {
        writeTag(cfg.tag, cfg.value ?? 1);
      });

      return {
        onTag() {
          /* buttons do not subscribe */
        }
      };
    }
  };

  /* ---------------- Public API ---------------- */

  window.UIWidgets = {
    init
  };
})();
