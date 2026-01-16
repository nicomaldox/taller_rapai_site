(function () {
  const search = document.querySelector("[data-search]");
  const form = document.querySelector("[data-form]");
  const status = document.querySelector("[data-status]");
  const catInput = document.querySelector("[data-categoria]");

  // When clicking an item: fill category + append item name into message + scroll to form
  document.addEventListener("click", (e) => {
    const card = e.target.closest(".itemCard");
    if (!card) return;

    const cat = card.getAttribute("data-cat") || "";
    const item = card.getAttribute("data-item") || "";

    const msg = document.querySelector("textarea[name='mensaje']");
    if (catInput) catInput.value = cat;

    if (msg) {
      // If empty, set a good default message. If not empty, append.
      const base = `Hola Rapai Quiindy Performance, quiero cotizar: ${item}.`;
      msg.value = msg.value.trim() ? (msg.value.trim() + "\n" + base) : base;
    }

    document.querySelector("#ubicacion").scrollIntoView({ behavior: "smooth" });
  });

  // Search filter (matches category + item + note)
// Search filter (for grid cards)
  if (search) {
    search.addEventListener("input", () => {
      const q = search.value.trim().toLowerCase();
      const cards = document.querySelectorAll(".itemCard");

      cards.forEach((c) => {
        const hay = c.getAttribute("data-search-text") || "";
        c.style.display = hay.includes(q) ? "" : "none";
      });
    });
  }


  // AJAX submit (fallback works without JS)
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (status) status.textContent = "Enviando...";

      try {
        const fd = new FormData(form);
        const res = await fetch("/lead", {
          method: "POST",
          headers: { "x-requested-with": "fetch" },
          body: fd
        });
        if (!res.ok) throw new Error("Request failed");
        if (status) status.textContent = "¡Enviado! Te responderemos pronto ✅";
        form.reset();
      } catch {
        if (status) status.textContent = "No se pudo enviar. Probá de nuevo o escribinos por WhatsApp.";
      }
    });
  }
})();
