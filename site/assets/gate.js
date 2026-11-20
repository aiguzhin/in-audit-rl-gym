/* FinSpector · вход на сайт: короткая регистрация в два шага (или вход), пока её нет — сайт закрыт.
   Всё проверяется прямо при вводе: свободен ли логин, надёжен ли пароль, что не так и как поправить. */
(function () {
  if (!window.AUTH) return;
  if (AUTH.user()) {                                   // проверяем, что сессия ещё действует (раз за визит)
    let checked = false; try { checked = sessionStorage.getItem("fs-ok") === AUTH.session().token.slice(-12); } catch (e) {}
    if (!checked) AUTH.api("/api/me", { timeout: 60000 }).then(() => { try { sessionStorage.setItem("fs-ok", AUTH.session().token.slice(-12)); } catch (e) {} })
      .catch(e => { if (e.status === 401) location.reload(); });
    return;
  }
  const { esc } = UI;
  const GOALS = { learn: ["lessons.html", "Начать с урока"], play: ["play.html?daily=1", "Пройти компанию дня"], code: ["python.html", "Открыть Python"] };
  const TR = { а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e", ж: "zh", з: "z", и: "i", й: "i", к: "k", л: "l", м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "h", ц: "ts", ч: "ch", ш: "sh", щ: "sch", ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya",
    ә: "a", ғ: "g", қ: "q", ң: "n", ө: "o", ұ: "u", ү: "u", һ: "h", і: "i" };
  const slug = s => s.toLowerCase().split("").map(c => TR[c] ?? c).join("").replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "").replace(/_+/g, "_").slice(0, 20);
  const LOGIN_RE = /^[a-z0-9][a-z0-9_.-]{2,23}$/;
  const lower = el => { const v = el.value, l = v.toLowerCase(); if (v !== l) { const a = el.selectionStart, b = el.selectionEnd; el.value = l; el.setSelectionRange(a, b); } return el.value; };

  document.body.classList.add("gated");
  const behind = [...document.body.children].filter(e => !e.matches("script"));
  behind.forEach(e => e.setAttribute("inert", ""));

  const g = document.createElement("div");
  g.className = "gate"; g.setAttribute("role", "dialog"); g.setAttribute("aria-modal", "true"); g.setAttribute("aria-labelledby", "gt-title");
  g.innerHTML = `<div class="gate-card">
    <aside class="gate-side">
      <div class="gate-brand"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M12 3v6M12 15v6M3 12h6M15 12h6"/></svg>FinSpector</div>
      <h2>Тренажёр финансового аудита</h2>
      <p>Находите ошибки в книгах вымышленных компаний и получайте честный балл. Аккаунт нужен, чтобы сохранять прогресс.</p>
      <ul class="gate-perks">
        <li><b>4 урока</b><span>с нуля: дубли, разнесение, курсы, период</span></li>
        <li><b>Песочница</b><span>настоящая компания с ошибками и подсказками</span></li>
        <li><b>Рейтинг</b><span>компания дня и общая таблица лидеров</span></li>
        <li><b>Профиль</b><span>история, график прогресса и 9 достижений</span></li>
      </ul>
      <p class="gate-fine">Бесплатно. Без почты и телефона — только логин и пароль.</p>
    </aside>
    <section class="gate-main">
      <div class="seg gate-tabs" role="tablist"><button type="button" role="tab" data-m="reg" aria-selected="true">Регистрация</button><button type="button" role="tab" data-m="in" aria-selected="false">У меня есть аккаунт</button></div>
      <div id="gt-body"></div>
    </section>
  </div>`;
  document.body.append(g);
  const body = g.querySelector("#gt-body");
  const st = { mode: "reg", step: 1, display: "", username: "", pass: "", goal: "learn", loginTouched: false, avail: null };

  // ---------------------------------------------------------------- проверка логина на сервере (с задержкой)
  let chkT = 0, chkSeq = 0;
  function checkLogin() {
    clearTimeout(chkT); const u = st.username, seq = ++chkSeq; st.avail = null; paintLogin();
    if (!LOGIN_RE.test(u)) return;
    st.avail = "wait"; paintLogin();
    chkT = setTimeout(async () => {
      try { const r = await AUTH.api("/api/check-username?u=" + encodeURIComponent(u), { auth: false, timeout: 60000 }); if (seq === chkSeq) { st.avail = r.available ? "ok" : "taken"; paintLogin(); } }
      catch (e) { if (seq === chkSeq) { st.avail = "unknown"; paintLogin(); } }
    }, 380);
  }
  function loginProblem(u) {                           // что именно не так — простыми словами
    if (!u) return "";
    if (/[а-яёәғқңөұүһі]/i.test(u)) return `Русские и казахские буквы в логине нельзя. Например: «${slug(u) || "aigerim"}»`;
    if (/\s/.test(u)) return "Пробелы нельзя — используйте _ или точку.";
    const bad = [...new Set(u.replace(/[a-z0-9_.-]/g, ""))].join(" ");
    if (bad) return `Нельзя использовать: ${bad}. Можно латинские буквы, цифры, точку, дефис и _.`;
    if (!/^[a-z0-9]/.test(u)) return "Логин должен начинаться с буквы или цифры.";
    if (u.length < 3) return `Ещё ${3 - u.length} ${3 - u.length === 1 ? "символ" : "символа"} — минимум 3.`;
    if (u.length > 24) return "Слишком длинный — максимум 24 символа.";
    return "";
  }
  function ideas() {                                   // варианты логина по имени — по нажатию
    const parts = st.display.trim().split(/\s+/).map(slug).filter(Boolean);
    if (!parts.length) return [];
    const y = String(new Date().getFullYear()).slice(2);
    return [...new Set([parts.join("_"), parts[0], parts[0] + (parts[1] ? "." + parts[1][0] : "_" + y), parts[0] + "_audit"])].filter(x => LOGIN_RE.test(x) && x !== st.username).slice(0, 3);
  }
  function paintLogin() {
    const box = body.querySelector("#gt-lstate"); if (!box) return;
    const u = st.username, prob = loginProblem(u), okRules = !!u && !prob;
    let msg = "", cls = "";
    if (!u) msg = "Придумайте логин сами: латиница, цифры, точка, дефис или _. Он нужен для входа.";
    else if (prob) { msg = prob; cls = "bad"; }
    else if (st.avail === "wait") msg = '<span class="spin"></span>Проверяем, свободен ли логин…';
    else if (st.avail === "ok") { msg = "✓ Логин свободен"; cls = "good"; }
    else if (st.avail === "taken") { cls = "bad"; msg = "Этот логин уже занят — попробуйте другой."; }
    else if (st.avail === "unknown") msg = "Не удалось проверить — сервер просыпается. Проверим при создании аккаунта.";
    box.className = "gt-state " + cls; box.innerHTML = msg;
    const sug = body.querySelector("#gt-ideas"), list = (!okRules || st.avail === "taken" || !u) ? ideas() : [];
    if (sug) sug.innerHTML = list.length ? `<span>${u ? "Или возьмите:" : "Идеи по вашему имени:"}</span>${list.map(a => `<button type="button" class="gt-alt" data-alt="${a}">${a}</button>`).join("")}` : "";
    body.querySelector("#gt-login")?.setAttribute("aria-invalid", cls === "bad");
    const next = body.querySelector("#gt-next"); if (next) next.disabled = !(st.display.trim().length >= 2 && okRules && st.avail !== "taken");
  }

  // ---------------------------------------------------------------- пароль
  function strength(p) {
    const checks = [[p.length >= 8, "не короче 8 символов"], [/[a-zа-яё]/i.test(p) && /\d/.test(p), "буквы и цифры"], [p.length >= 12 || /[^\w\s]/.test(p), "12+ символов или знак вроде ! ? #"], [!!p && p.toLowerCase() !== st.username && !/^(12345678|password|qwerty)/i.test(p), "не совпадает с логином и не «12345678»"]];
    return { checks, score: checks.filter(c => c[0]).length };
  }
  function genPass() {
    const w = ["audit", "ledger", "saldo", "kassa", "debet", "kredit", "balans", "schet", "kurs", "nalog"];
    const r = n => crypto.getRandomValues(new Uint32Array(1))[0] % n;
    return w[r(w.length)] + "-" + w[r(w.length)] + "-" + (100 + r(900)) + "!?#"[r(3)];
  }
  function paintPass() {
    const { checks, score } = strength(st.pass);
    const lvl = ["Слишком простой", "Слабый", "Нормальный", "Хороший", "Надёжный"][st.pass ? score : 0];
    body.querySelector("#gt-meter").dataset.s = st.pass ? score : 0;
    body.querySelector("#gt-mtxt").textContent = st.pass ? lvl : "Придумайте пароль или нажмите «Придумать за меня»";
    body.querySelector("#gt-checks").innerHTML = checks.map(c => `<li class="${c[0] ? "ok" : ""}">${c[0] ? "✓" : "○"} ${c[1]}</li>`).join("");
    body.querySelector("#gt-create").disabled = !(checks[0][0] && checks[3][0]);
  }

  // ---------------------------------------------------------------- экраны
  function steps() { return `<ol class="gt-steps" aria-label="Шаги регистрации">${["Имя и логин", "Пароль и цель"].map((s, i) => `<li class="${i + 1 < st.step ? "done" : i + 1 === st.step ? "on" : ""}"><span>${i + 1 < st.step ? "✓" : i + 1}</span>${s}</li>`).join("")}</ol>`; }
  function render() {
    g.querySelectorAll(".gate-tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.m === st.mode));
    if (st.mode === "in") return renderLogin();
    if (st.step === 1) {
      body.innerHTML = `${steps()}<h1 id="gt-title" class="gt-h">Давайте знакомиться</h1>
        <form id="gt-f1" novalidate>
          <label class="fld"><span>Как вас называть?</span><input id="gt-name" autocomplete="name" maxlength="32" placeholder="Например, Айгерим" value="${esc(st.display)}"></label>
          <p class="gt-hint">Это имя увидят другие в таблице лидеров. Можно по-русски или по-казахски.</p>
          <label class="fld"><span>Придумайте логин</span><span class="gt-pre"><i>@</i><input id="gt-login" autocomplete="username" autocapitalize="off" autocorrect="off" spellcheck="false" maxlength="30" placeholder="например, aigerim.s" value="${esc(st.username)}" aria-describedby="gt-lstate"></span></label>
          <p class="gt-state" id="gt-lstate" aria-live="polite"></p>
          <div class="gt-ideas" id="gt-ideas"></div>
          <button class="btn gt-wide" id="gt-next" type="submit" disabled>Дальше <span class="arr">→</span></button>
        </form>`;
      const n = body.querySelector("#gt-name"), l = body.querySelector("#gt-login");
      n.oninput = () => { st.display = n.value; paintLogin(); };
      l.oninput = () => { st.username = lower(l).trim(); checkLogin(); };
      body.querySelector("#gt-ideas").onclick = e => { const b = e.target.closest("[data-alt]"); if (b) { st.username = b.dataset.alt; l.value = st.username; checkLogin(); l.focus(); } };
      body.querySelector("#gt-f1").onsubmit = e => { e.preventDefault(); if (body.querySelector("#gt-next").disabled) return; st.step = 2; render(); };
      paintLogin(); if (st.username) checkLogin();
      (st.display ? l : n).focus();
    } else {
      body.innerHTML = `${steps()}<h1 id="gt-title" class="gt-h">Почти готово, ${esc(st.display.trim().split(" ")[0])}</h1>
        <form id="gt-f2" novalidate>
          <input type="text" autocomplete="username" value="${esc(st.username)}" hidden>
          <label class="fld"><span>Пароль</span><span class="gt-pw"><input id="gt-pass" type="password" autocomplete="new-password" maxlength="200" placeholder="Не короче 8 символов" value="${esc(st.pass)}" aria-describedby="gt-mtxt">
            <button type="button" class="gt-eye" id="gt-eye" aria-label="Показать пароль" aria-pressed="false">Показать</button></span></label>
          <div class="gt-meter" id="gt-meter" data-s="0" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
          <div class="gt-mrow"><span id="gt-mtxt" aria-live="polite"></span><button type="button" class="gt-link" id="gt-gen">Придумать за меня</button></div>
          <ul class="gt-checks" id="gt-checks"></ul>
          <fieldset class="gt-goal"><legend>С чего хотите начать?</legend>
            ${[["learn", "Я новичок", "4 коротких урока"], ["play", "Сразу в дело", "Компания дня и рейтинг"], ["code", "Пишу код", "Python прямо в браузере"]].map(([k, t, d]) =>
              `<label class="gt-opt"><input type="radio" name="goal" value="${k}"${st.goal === k ? " checked" : ""}><b>${t}</b><small>${d}</small></label>`).join("")}
          </fieldset>
          <p class="gt-err" id="gt-err" role="alert"></p>
          <div class="gt-actions"><button type="button" class="chip" id="gt-back">← Назад</button><button class="btn" id="gt-create" type="submit" disabled>Создать аккаунт <span class="arr">→</span></button></div>
          <p class="gt-fine">Запишите пароль: восстановить его без почты нельзя. Браузер может предложить сохранить его — соглашайтесь.</p>
        </form>`;
      const p = body.querySelector("#gt-pass"), eye = body.querySelector("#gt-eye");
      p.oninput = () => { st.pass = p.value; paintPass(); };
      eye.onclick = () => { const show = p.type === "password"; p.type = show ? "text" : "password"; eye.textContent = show ? "Скрыть" : "Показать"; eye.setAttribute("aria-pressed", show); eye.setAttribute("aria-label", show ? "Скрыть пароль" : "Показать пароль"); p.focus(); };
      body.querySelector("#gt-gen").onclick = () => { st.pass = genPass(); p.value = st.pass; p.type = "text"; eye.textContent = "Скрыть"; eye.setAttribute("aria-pressed", true); paintPass(); p.select(); };
      body.querySelectorAll("[name=goal]").forEach(r => r.onchange = () => st.goal = r.value);
      body.querySelector("#gt-back").onclick = () => { st.step = 1; render(); };
      body.querySelector("#gt-f2").onsubmit = async e => { e.preventDefault(); const btn = body.querySelector("#gt-create"); if (btn.disabled) return;
        await send(btn, "/api/register", { username: st.username.trim(), password: st.pass, display: st.display.trim() }, err => {
          if (/логин/i.test(err)) { st.step = 1; st.avail = /занят/.test(err) ? "taken" : null; render(); paintLogin(); } }); };
      paintPass(); p.focus();
    }
  }
  function renderLogin() {
    body.innerHTML = `<h1 id="gt-title" class="gt-h">С возвращением</h1>
      <form id="gt-fl" novalidate>
        <label class="fld"><span>Логин</span><span class="gt-pre"><i>@</i><input id="gt-lu" autocomplete="username" autocapitalize="off" spellcheck="false" maxlength="24" value="${esc(st.username)}"></span></label>
        <label class="fld"><span>Пароль</span><span class="gt-pw"><input id="gt-lp" type="password" autocomplete="current-password" maxlength="200"><button type="button" class="gt-eye" id="gt-leye" aria-label="Показать пароль" aria-pressed="false">Показать</button></span></label>
        <p class="gt-err" id="gt-err" role="alert"></p>
        <button class="btn gt-wide" id="gt-lgo" type="submit">Войти <span class="arr">→</span></button>
        <p class="gt-fine">Нет аккаунта? <button type="button" class="gt-link" id="gt-toreg">Зарегистрируйтесь за минуту</button></p>
      </form>`;
    const u = body.querySelector("#gt-lu"), p = body.querySelector("#gt-lp"), eye = body.querySelector("#gt-leye");
    u.oninput = () => { st.username = lower(u).trim(); };
    eye.onclick = () => { const show = p.type === "password"; p.type = show ? "text" : "password"; eye.textContent = show ? "Скрыть" : "Показать"; eye.setAttribute("aria-pressed", show); p.focus(); };
    body.querySelector("#gt-toreg").onclick = () => { st.mode = "reg"; st.step = 1; render(); };
    body.querySelector("#gt-fl").onsubmit = async e => { e.preventDefault();
      if (!u.value || !p.value) { body.querySelector("#gt-err").textContent = "Введите логин и пароль."; (u.value ? p : u).focus(); return; }
      await send(body.querySelector("#gt-lgo"), "/api/login", { username: u.value, password: p.value }); };
    (st.username ? p : u).focus();
  }

  async function send(btn, path, payload, onErr) {
    const err = body.querySelector("#gt-err"); err.textContent = ""; btn.disabled = true;
    const label = btn.innerHTML; btn.innerHTML = '<span class="spin"></span> Подождите…';
    const slow = setTimeout(() => { err.className = "gt-err info"; err.textContent = "Сервер просыпается после простоя — это бывает до минуты. Не закрывайте страницу."; }, 3500);
    try { const r = await AUTH.api(path, { method: "POST", body: payload, auth: false }); clearTimeout(slow); AUTH.login(r); dispatchEvent(new CustomEvent("fs:auth", { detail: r.user })); welcome(r.user, path === "/api/register"); }
    catch (e) { clearTimeout(slow); err.className = "gt-err"; err.textContent = e.message; btn.disabled = false; btn.innerHTML = label; if (onErr) onErr(e.message);
      if (!e.status) err.insertAdjacentHTML("beforeend", ` <button type="button" class="gt-link" id="gt-retry">Повторить</button>`), body.querySelector("#gt-retry").onclick = () => btn.click(); }
  }
  function welcome(user, isNew) {
    const [href, cta] = GOALS[st.goal];
    const here = document.body.dataset.page;
    body.innerHTML = `<div class="gt-welcome"><div class="gt-ava" aria-hidden="true">${esc(AUTH.initials(user.display))}</div>
      <h1 id="gt-title" class="gt-h">${isNew ? "Добро пожаловать" : "Рады видеть"}, ${esc(user.display)}!</h1>
      <p>${isNew ? "Аккаунт создан. Результаты, достижения и место в рейтинге теперь сохраняются в профиле." : "Вы вошли. Продолжайте с того места, где остановились."}</p>
      <div class="gt-actions center">${isNew && here !== href.split("?")[0].replace(".html", "") ? `<a class="btn" href="${href}">${cta} <span class="arr">→</span></a>` : ""}<button type="button" class="chip" id="gt-stay">${isNew ? "Осмотреться на этой странице" : "Продолжить"}</button></div></div>`;
    g.querySelector(".gate-tabs").hidden = true;
    body.querySelector("#gt-stay").onclick = close;
    (body.querySelector(".gt-welcome a") || body.querySelector("#gt-stay")).focus();
  }
  function close() { g.classList.add("out"); behind.forEach(e => e.removeAttribute("inert")); document.body.classList.remove("gated"); setTimeout(() => g.remove(), 350); }

  g.querySelectorAll(".gate-tabs button").forEach(b => b.onclick = () => { st.mode = b.dataset.m; if (st.mode === "reg") st.step = 1; render(); });
  render();
})();
