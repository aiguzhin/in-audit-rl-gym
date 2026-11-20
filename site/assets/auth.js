/* Аккаунт: токен, запросы к API, значок профиля в шапке. Подключается до остальных скриптов страницы. */
(function () {
  const API = window.FA_API;
  const KEY = "fa-auth";
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { return null; } };
  const write = v => { try { v ? localStorage.setItem(KEY, JSON.stringify(v)) : localStorage.removeItem(KEY); } catch (e) {} };

  async function api(path, { method = "GET", body, auth = true, timeout = 70000 } = {}) {
    const c = new AbortController(); const t = setTimeout(() => c.abort(), timeout);
    const headers = {}; if (body) headers["Content-Type"] = "application/json";
    const s = read(); if (auth && s && s.token) headers.Authorization = "Bearer " + s.token;
    try {
      const r = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined, signal: c.signal });
      const data = await r.json().catch(() => ({}));
      if (r.status === 401 && s) { write(null); renderChip(); }
      if (!r.ok) { const e = new Error(data.error || "Сервер ответил ошибкой."); e.status = r.status; throw e; }
      return data;
    } catch (e) {
      if (e.name === "AbortError") throw new Error("Сервер не ответил. Бесплатный сервер просыпается до минуты — попробуйте ещё раз.");
      if (e instanceof TypeError) throw new Error("Нет связи с сервером. Проверьте интернет и повторите.");
      throw e;
    } finally { clearTimeout(t); }
  }

  const initials = n => (n || "?").trim().split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase();
  function renderChip() {
    const bar = document.querySelector("header.top .bar"); if (!bar) return;
    let chip = document.getElementById("acct");
    if (!chip) { chip = document.createElement("a"); chip.id = "acct"; chip.className = "acct"; chip.href = "profile.html"; bar.insertBefore(chip, bar.querySelector(".burger")); }
    const s = read();
    chip.classList.toggle("in", !!(s && s.user));
    chip.innerHTML = s && s.user ? `<span class="av">${initials(s.user.display)}</span><span class="nm">${UI.esc(s.user.display)}</span>` : `<span class="av">→</span><span class="nm">Войти</span>`;
    chip.setAttribute("aria-label", s && s.user ? `Профиль: ${s.user.display}` : "Войти или зарегистрироваться");
    if (document.body.dataset.page === "profile") chip.setAttribute("aria-current", "page");
  }

  window.AUTH = {
    api, session: read, user: () => (read() || {}).user || null,
    login(data) { write({ token: data.token, user: data.user }); renderChip(); },
    logout() { write(null); try { sessionStorage.removeItem("fs-ok"); } catch (e) {} renderChip(); },
    setUser(user) { const s = read(); if (s) { s.user = user; write(s); renderChip(); } },
    initials,
  };
  renderChip();
})();
