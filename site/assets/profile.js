/* Профиль: вход и регистрация или статистика, график, достижения, история. */
(function () {
  const { $, $$, esc } = UI;
  const root = $("#profile");
  const PRESET_RU = { mixed: "обычная", inter: "взаимодействие", clean: "чистая", single: "по одной" };
  const fmt = v => (v > 0 ? "+" : "") + v.toFixed(3);
  const date = s => { const d = new Date(String(s).replace(" ", "T").replace(/(\+\d\d)$/, "$1:00"));
    return isNaN(d) ? String(s).slice(0, 16) : d.toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); };

  function authView(mode = "login") {
    const reg = mode === "register";
    root.innerHTML = `<div class="auth-wrap">
      <div class="auth-side"><p class="label">Аккаунт Fin-Audit</p><h2 class="h2">${reg ? "Создайте профиль" : "С возвращением"}</h2>
        <p class="intro">Профиль хранит все ваши прохождения, лучший балл, место в рейтинге и достижения. Результаты сохраняются в базе данных и пересчитываются сервером.</p>
        <ul class="perks"><li>История и график прогресса</li><li>8 достижений за честный аудит</li><li>Ваше имя в таблице лидеров</li></ul></div>
      <form class="glass auth-card" id="auth-form" novalidate>
        <div class="seg" role="tablist"><button type="button" role="tab" aria-selected="${!reg}" data-m="login">Вход</button><button type="button" role="tab" aria-selected="${reg}" data-m="register">Регистрация</button></div>
        <label class="fld"><span>Логин</span><input id="a-user" autocomplete="username" required minlength="3" maxlength="24" pattern="[a-zA-Z0-9_]{3,24}" placeholder="latin_letters_123"></label>
        ${reg ? `<label class="fld"><span>Имя в рейтинге</span><input id="a-disp" maxlength="32" autocomplete="nickname" placeholder="Например, Айгерим"></label>` : ""}
        <label class="fld"><span>Пароль${reg ? " · не короче 8 символов" : ""}</span><input id="a-pass" type="password" required minlength="8" autocomplete="${reg ? "new-password" : "current-password"}"></label>
        <p class="err" id="a-err" role="alert"></p>
        <button class="btn" type="submit">${reg ? "Создать профиль" : "Войти"} <span class="arr">→</span></button>
        <p class="label fine">${reg ? "Пароль хранится только в виде защищённого хеша." : "Нет аккаунта? Нажмите «Регистрация» сверху."}</p>
      </form></div>`;
    $$(".seg button").forEach(b => b.onclick = () => authView(b.dataset.m));
    $("#auth-form").onsubmit = async e => {
      e.preventDefault(); const err = $("#a-err"); err.textContent = "";
      const username = $("#a-user").value.trim(), password = $("#a-pass").value;
      if (!/^[a-zA-Z0-9_]{3,24}$/.test(username)) { err.textContent = "Логин: 3–24 символа, латинские буквы, цифры и _."; return; }
      if (password.length < 8) { err.textContent = "Пароль должен быть не короче 8 символов."; return; }
      const btn = e.target.querySelector("button[type=submit]"); btn.disabled = true; err.innerHTML = '<span class="spin"></span>Подключаемся к серверу…';
      try { const body = { username, password }; if (reg) body.display = ($("#a-disp").value || username).trim();
        const r = await AUTH.api(reg ? "/api/register" : "/api/login", { method: "POST", body, auth: false });
        AUTH.login(r); load(); }
      catch (x) { err.textContent = x.message; btn.disabled = false; }
    };
    $("#a-user").focus();
  }

  function chart(hist) {
    const pts = hist.slice().reverse().slice(-30); if (pts.length < 2) return `<p class="empty">График появится после двух прохождений.</p>`;
    const W = 600, H = 170, P = 14, n = pts.length;
    const x = i => P + i * (W - 2 * P) / (n - 1), y = v => H / 2 - v * (H / 2 - P);
    const d = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p.reward).toFixed(1)}`).join(" ");
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Награда за последние ${n} прохождений">
      <line x1="0" x2="${W}" y1="${H / 2}" y2="${H / 2}" class="zero"/><path d="${d} L${x(n - 1)} ${H / 2} L${x(0)} ${H / 2}Z" class="area"/><path d="${d}" class="ln"/>
      ${pts.map((p, i) => `<circle cx="${x(i)}" cy="${y(p.reward)}" r="3.5" class="${p.reward < 0 ? "neg" : "pos"}"><title>${fmt(p.reward)}</title></circle>`).join("")}</svg>`;
  }

  async function load() {
    if (!AUTH.user()) return authView();
    root.innerHTML = `<p class="empty"><span class="spin"></span> Загружаем профиль… Бесплатный сервер просыпается до минуты.</p>`;
    let d; try { d = await AUTH.api("/api/me"); } catch (e) {
      if (!AUTH.user()) return authView();
      root.innerHTML = `<p class="empty">${esc(e.message)} <button class="chip" id="p-retry">Повторить</button></p>`; $("#p-retry").onclick = load; return; }
    const s = d.stats, u = d.user, got = d.achievements.filter(a => a.done).length;
    root.innerHTML = `
      <div class="pf-head glass">
        <div class="pf-av">${AUTH.initials(u.display)}</div>
        <div class="pf-id"><h2>${esc(u.display)}</h2><p class="label">@${esc(u.username)} · в Fin-Audit с ${date(u.created_at)}</p></div>
        <div class="pf-actions"><a class="btn" href="play.html">Новый аудит <span class="arr">→</span></a><button class="chip" id="logout">Выйти</button></div>
      </div>
      <div class="pf-stats">${[["Прохождений", s.runs], ["Лучший балл", s.best == null ? "—" : fmt(s.best)], ["Средний балл", s.avg == null ? "—" : fmt(s.avg)],
        ["Средний F1", s.avg_f1 == null ? "—" : s.avg_f1.toFixed(2)], ["Найдено ошибок", s.found], ["Место в рейтинге", s.rank ? "#" + s.rank : "—"]]
        .map(([k, v]) => `<div class="glass"><span class="label">${k}</span><b>${v}</b></div>`).join("")}</div>
      <div class="pf-grid">
        <div class="glass pf-card"><div class="t">Прогресс</div><p class="label">Награда за последние прохождения</p>${chart(d.history)}</div>
        <div class="glass pf-card"><div class="t">Достижения <span class="label">${got} из ${d.achievements.length}</span></div>
          <div class="ach">${d.achievements.map(a => `<div class="a${a.done ? " done" : ""}"><span class="ai" aria-hidden="true">${a.done ? "✓" : "·"}</span><div><b>${a.title}</b><span>${a.hint}</span></div></div>`).join("")}</div></div>
      </div>
      <div class="glass pf-card"><div class="t">История</div>
        ${d.history.length ? `<div class="tbl-wrap"><table class="grid board"><thead><tr><th>Когда</th><th>Компания</th><th>Награда</th><th>F1</th><th>TP / FP / FN</th><th>Шаги</th></tr></thead><tbody>
        ${d.history.map((h, i) => `<tr style="--k:${Math.min(i, 20)}"><td>${date(h.created_at)}</td><td>№${h.seed} · ${PRESET_RU[h.preset] || h.preset}${h.day ? ' <span class="tag-day">день</span>' : ""}</td>
          <td class="num"><em class="${h.reward < 0 ? "neg" : "pos"}">${fmt(h.reward)}</em></td><td class="num">${(h.f1 || 0).toFixed(2)}</td><td>${h.tp} / ${h.fp} / ${h.fn}</td><td class="num">${h.steps}</td></tr>`).join("")}
        </tbody></table></div>` : `<p class="empty">Пока пусто. Пройдите аудит в песочнице и сохраните результат — он появится здесь.</p>`}</div>`;
    $("#logout").onclick = () => { AUTH.logout(); authView(); };
  }
  load();
})();
