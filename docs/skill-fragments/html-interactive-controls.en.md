## Interactive Controls (Try Values, Return the Result to the Session)

For documents where the reader decides by manipulating rather than only reading, write controls directly into an `html` block: sliders for trying values, toggles, reorderable cards.

Inline `<script>` and inline event handlers are allowed inside `html` blocks. Loading from an external host is rejected by `check-model` — both `<script src="…">` and `<link rel="stylesheet" href="https://…">` — so the bundle stays self-contained. Use the `diagram` block when you need diagram rendering.

To persist what the reader manipulated, use the bundled `RHWState`. With a preview server it saves through `PUT /annotations/state/<name>.json` so state is shared across devices; without one (published standalone, opened via `file://`) it falls back to localStorage, and to memory when neither is available. The interaction never breaks.

```html
<label>duration <input type="range" id="dur" min="0" max="2000" value="300"></label>
<output id="durOut">300</output>ms
<script>
  (async function () {
    var dur = document.getElementById("dur");
    var out = document.getElementById("durOut");
    var saved = await window.RHWState.load("tuning");
    if (saved && saved.duration) { dur.value = saved.duration; out.textContent = saved.duration; }
    dur.addEventListener("input", function () {
      out.textContent = dur.value;
      window.RHWState.save("tuning", { duration: dur.value }, { debounce: 300 });
    });
  })();
</script>
```

`<name>` accepts alphanumerics, hyphens, and underscores (64 chars max). Saved state is readable by the agent at `annotations/state/<name>.json` — that is the path by which a decision made in the browser returns to the session. Use distinct names per purpose (`tuning`, `priority-order`). For continuously moving controls (sliders, text inputs) pass `{ debounce: 300 }`: local storage is written on every call, while the server write is coalesced into one after input stops. Omit `debounce` for one-shot interactions (buttons, `dragend`, checkboxes). While a debounced write is waiting, `save()` resolves with `saved: "superseded"` — treat that as "saving" in any status display; only the final call reports the real result.

Add controls only when the reader needs to try values, decide an order, or narrow options; leave them out of read-only documents. If the agent must receive the outcome, `RHWState.save()` is required — otherwise the result stays on screen and disappears. Verify interactive documents through `preview` over the server, since opening via `file://` exercises the fallback path instead.
