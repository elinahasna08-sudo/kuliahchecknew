(function () {
  "use strict";

  var hero = document.getElementById("hero");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function api(method, url, body) {
    return fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) { throw new Error(data.error || "Terjadi kesalahan."); }
        return data;
      });
    });
  }

  function confetti() {
    if (reduceMotion) { return; }
    var icons = ["🎒", "✨", "📚", "🎓", "⭐"];
    for (var i = 0; i < 22; i++) {
      var el = document.createElement("span");
      el.className = "confetti";
      el.textContent = icons[i % icons.length];
      el.style.left = Math.round(Math.random() * 100) + "vw";
      el.style.animationDelay = (Math.random() * 0.5).toFixed(2) + "s";
      el.style.animationDuration = (1.6 + Math.random() * 1.2).toFixed(2) + "s";
      el.setAttribute("aria-hidden", "true");
      document.body.appendChild(el);
      setTimeout(function (n) { n.remove(); }, 3500, el);
    }
  }

  function render(status) {
    var before = parseInt(document.getElementById("pct").textContent, 10);
    document.getElementById("pct").textContent = status.percent;
    document.getElementById("msg").textContent = status.message;
    hero.dataset.level = status.level;
    document.getElementById("bag-fill").style.transform = "translateY(" + (100 - status.percent) + "px)";
    status.rows.forEach(function (it) {
      var btn = document.querySelector('.item[data-id="' + it.id + '"]');
      if (!btn) { return; }
      btn.classList.toggle("is-on", it.checked);
      btn.setAttribute("aria-pressed", it.checked ? "true" : "false");
    });
    if (status.percent === 100 && before < 100 && status.total > 0) { confetti(); }
  }

  var list = document.getElementById("items");
  if (list) {
    list.addEventListener("click", function (e) {
      var btn = e.target.closest(".item");
      if (!btn) { return; }
      api("POST", "/api/toggle/" + encodeURIComponent(btn.dataset.id)).then(render).catch(function (err) {
        alert(err.message);
      });
    });
  }

  var reset = document.getElementById("reset");
  if (reset) {
    reset.addEventListener("click", function () {
      api("POST", "/api/reset").then(render).catch(function (err) { alert(err.message); });
    });
  }

  var form = document.getElementById("add-form");
  if (form) {
    var errBox = document.getElementById("form-error");
    form.addEventListener("input", function () { errBox.textContent = ""; });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var days = Array.prototype.map.call(form.querySelectorAll('input[name="days"]:checked'), function (c) {
        return parseInt(c.value, 10);
      });
      api("POST", "/api/items", {
        name: form.elements.name.value,
        emoji: form.elements.emoji.value,
        days: days
      }).then(function () {
        location.reload();
      }).catch(function (err) { errBox.textContent = err.message; });
    });
  }

  document.addEventListener("click", function (e) {
    var del = e.target.closest("[data-delete]");
    if (!del) { return; }
    if (!window.confirm("Hapus barang ini dari daftar?")) { return; }
    api("DELETE", "/api/items/" + encodeURIComponent(del.dataset.delete)).then(function () {
      location.reload();
    }).catch(function (err) { alert(err.message); });
  });
})();
