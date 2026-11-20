/* FinSpector · обучение: состав курса, прогресс (в браузере и в аккаунте), план и график занятий. */
(function () {
  const COURSE = [
    { id: "m1", title: "Основы", desc: "Как устроены книги компании", items: [
      ["books", "Три книги компании", "Счета, платежи и журнал", 2], ["dr", "Дебет и кредит", "Как записывается каждая операция", 2],
      ["minor", "Суммы в «копейках»", "Как читать суммы в данных", 1], ["tz", "Часы компании", "UTC и местное время", 2]] },
    { id: "m2", title: "Четыре ошибки", desc: "То, что ищет аудитор", items: [
      ["dup", "Дубль счёта", "Один счёт выставлен дважды", 2], ["alloc", "Неполное разнесение", "Часть оплаты «зависла»", 2],
      ["fx", "Неверный курс", "Пересчёт не по той дате", 2], ["cut", "Не тот период", "Документ из чужого месяца", 2]] },
    { id: "m3", title: "Сложные случаи", desc: "Ловушки и как не ошибиться", items: [
      ["subs", "Подписка или дубль", "Одинаковые суммы — не всегда ошибка", 2], ["combo", "Две ошибки в одном платеже", "Когда нужно два вывода", 2],
      ["clean", "Чистая компания", "Когда лучший ответ — ничего", 1], ["evidence", "Доказательства", "Что приложить к выводу", 2]] },
    { id: "m4", title: "Практика", desc: "Настоящие компании в песочнице", practice: true, items: [
      ["p_single", "Учебная компания", "По одной ошибке каждого типа", 10, "play.html?preset=single"],
      ["p_clean", "Чистая компания", "Не обвинить никого зря", 8, "play.html?preset=clean"],
      ["p_mixed", "Обычная компания", "Наберите балл выше нуля", 12, "play.html?preset=mixed"],
      ["p_inter", "Сложная компания", "Ошибки прячут друг друга", 15, "play.html?preset=inter"],
      ["p_daily", "Компания дня", "Сравните себя с другими", 12, "play.html?daily=1"]] },
  ];
  const ITEMS = COURSE.flatMap(m => m.items.map(([id, title, short, min, href]) => ({ id, title, short, min, href, module: m.id, practice: !!m.practice })));
  const BY = Object.fromEntries(ITEMS.map(x => [x.id, x]));
  const PACES = {
    fast: { name: "Интенсив", sessions: 3, note: "3 занятия по ~35 минут", days: [1, 2, 3, 4, 5, 6, 7] },
    normal: { name: "Обычный", sessions: 6, note: "6 занятий по ~15 минут", days: [1, 3, 5] },
    calm: { name: "Спокойный", sessions: 10, note: "10 занятий по ~10 минут", days: [2, 4, 6] },
  };
  const TIMES = { morning: ["Утром", "09:00"], day: ["Днём", "13:00"], evening: ["Вечером", "19:00"] };
  const DOW = ["", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

  const ls = { get: k => { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
  const uid = () => (window.AUTH && AUTH.user() ? AUTH.user().id || AUTH.user().username : "anon");
  const PK = () => "fs-progress-" + uid(), PLK = () => "fs-plan-" + uid();
  // перенос старого прогресса уроков (до аккаунтов) в новый ключ
  (function migrate() { const old = ls.get("fs-lessons"); if (old && window.AUTH && AUTH.user()) { ls.set(PK(), Object.assign({}, old, ls.get(PK()) || {})); try { localStorage.removeItem("fs-lessons"); } catch (e) {} } })();

  const progress = () => ls.get(PK()) || {};
  const isDone = id => !!progress()[id];
  function markDone(id) {
    if (!BY[id]) return; const p = progress(); if (p[id]) return; p[id] = Date.now(); ls.set(PK(), p);
    if (window.AUTH && AUTH.user()) AUTH.api("/api/progress", { method: "POST", body: { done: { [id]: p[id] } } }).catch(() => {});
    dispatchEvent(new CustomEvent("fs:progress", { detail: id }));
  }
  const plan = () => ls.get(PLK());
  async function savePlan(p) {
    const r = await AUTH.api("/api/plan", { method: "POST", body: p });
    ls.set(PLK(), r.plan); dispatchEvent(new CustomEvent("fs:plan")); return r.plan;
  }
  let synced = null;
  function sync() {                                     // подтягиваем план и прогресс из аккаунта и сливаем с браузером
    if (!window.AUTH || !AUTH.user()) return Promise.resolve();
    if (synced) return synced;
    synced = AUTH.api("/api/me", { timeout: 70000 }).then(d => {
      const local = progress(), remote = d.progress || {}, merged = Object.assign({}, remote);
      let push = {};
      for (const [k, v] of Object.entries(local)) if (!remote[k]) { merged[k] = v; push[k] = v; }
      ls.set(PK(), merged);
      if (Object.keys(push).length) AUTH.api("/api/progress", { method: "POST", body: { done: push } }).catch(() => {});
      if (d.plan) ls.set(PLK(), d.plan);
      dispatchEvent(new CustomEvent("fs:plan"));
      return d;
    }).catch(() => null);
    return synced;
  }

  // ---------- график: даты занятий и что в каждом ----------
  const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const todayIso = () => iso(new Date());
  function schedule(p) {
    if (!p) return [];
    const P = PACES[p.pace], n = P.sessions, per = Math.ceil(ITEMS.length / n), dates = [];
    const d = new Date(p.start + "T12:00:00");
    for (let guard = 0; dates.length < n && guard < 400; guard++) { const w = d.getDay() || 7; if (p.days.includes(w)) dates.push(iso(d)); d.setDate(d.getDate() + 1); }
    return dates.map((date, i) => ({ date, n: i + 1, items: ITEMS.slice(i * per, (i + 1) * per).map(x => x.id) })).filter(s => s.items.length);
  }
  function status(p) {                                  // что сделать сегодня, что просрочено, что дальше
    const S = schedule(p), t = todayIso(), done = progress();
    const due = S.filter(s => s.date <= t).flatMap(s => s.items).filter(id => !done[id]);
    const next = S.find(s => s.date > t && s.items.some(id => !done[id]));
    const nDone = ITEMS.filter(x => done[x.id]).length;
    return { sessions: S, due, next, nDone, total: ITEMS.length, finished: nDone === ITEMS.length, nextItem: ITEMS.find(x => !done[x.id]) };
  }
  function ics(p) {                                     // файл для календаря: каждое занятие — событие с напоминанием
    const S = schedule(p), [, hhmm] = TIMES[p.time], P = PACES[p.pace];
    const mins = Math.round(ITEMS.reduce((a, x) => a + x.min, 0) / P.sessions / 5) * 5 || 15;
    const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
    const ev = S.map(s => { const [h, m] = hhmm.split(":").map(Number), st = s.date.replace(/-/g, "") + "T" + hhmm.replace(":", "") + "00";
      const e = new Date(s.date + "T" + hhmm + ":00"); e.setMinutes(e.getMinutes() + mins);
      const en = iso(e).replace(/-/g, "") + "T" + String(e.getHours()).padStart(2, "0") + String(e.getMinutes()).padStart(2, "0") + "00";
      const what = s.items.map(id => BY[id].title).join(", ");
      return ["BEGIN:VEVENT", `UID:finspector-${s.date}-${s.n}@fin-audit-rl-gym`, `DTSTAMP:${stamp}`, `DTSTART:${st}`, `DTEND:${en}`,
        `SUMMARY:FinSpector · занятие ${s.n} из ${S.length}`, `DESCRIPTION:${what.replace(/,/g, "\\,")}\\nhttps://fin-audit-rl-gym.onrender.com/lessons.html`,
        "URL:https://fin-audit-rl-gym.onrender.com/lessons.html", "BEGIN:VALARM", "TRIGGER:-PT10M", "ACTION:DISPLAY", "DESCRIPTION:Скоро занятие FinSpector", "END:VALARM", "END:VEVENT"].join("\r\n"); });
    return ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//FinSpector//План учёбы//RU", "CALSCALE:GREGORIAN", ...ev, "END:VCALENDAR"].join("\r\n");
  }
  function downloadIcs(p) { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([ics(p)], { type: "text/calendar" })); a.download = "finspector-plan.ics"; document.body.append(a); a.click(); a.remove(); }

  // ---------- выбор плана (используется при регистрации и на странице обучения) ----------
  function picker(root, { initial, submitLabel = "Сохранить план", onSaved, onCancel } = {}) {
    const esc = UI.esc;
    const st = Object.assign({ pace: "normal", time: "evening", days: PACES.normal.days.slice(), start: todayIso() }, initial || {});
    function preview() {
      const S = schedule(st), last = S[S.length - 1];
      const fmt = s => new Date(s + "T12:00:00").toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
      return S.length ? `${S.length} ${plural(S.length, "занятие", "занятия", "занятий")} · с ${fmt(S[0].date)} по ${fmt(last.date)} · ${TIMES[st.time][0].toLowerCase()} в ${TIMES[st.time][1]}` : "Выберите хотя бы один день недели.";
    }
    function draw() {
      root.innerHTML = `<div class="pk">
        <fieldset class="pk-row"><legend>Темп</legend><div class="pk-paces">${Object.entries(PACES).map(([k, P]) => `<label class="pk-pace"><input type="radio" name="pk-pace" value="${k}"${st.pace === k ? " checked" : ""}><b>${P.name}</b><small>${P.note}</small></label>`).join("")}</div></fieldset>
        <fieldset class="pk-row"><legend>Дни занятий</legend><div class="pk-days">${[1, 2, 3, 4, 5, 6, 7].map(d => `<label class="pk-day"><input type="checkbox" value="${d}"${st.days.includes(d) ? " checked" : ""}><span>${DOW[d]}</span></label>`).join("")}</div></fieldset>
        <fieldset class="pk-row"><legend>Время</legend><div class="pk-times">${Object.entries(TIMES).map(([k, [t, h]]) => `<label class="pk-time"><input type="radio" name="pk-time" value="${k}"${st.time === k ? " checked" : ""}><span>${t} <small>${h}</small></span></label>`).join("")}</div></fieldset>
        <label class="pk-row pk-start"><span>Начать</span><input type="date" id="pk-start" value="${esc(st.start)}" min="${todayIso()}"></label>
        <p class="pk-prev" id="pk-prev" aria-live="polite">${preview()}</p>
        <p class="pk-err" id="pk-err" role="alert"></p>
        <div class="pk-actions">${onCancel ? `<button type="button" class="chip" id="pk-cancel">Отмена</button>` : "<span></span>"}<button type="button" class="btn" id="pk-save">${submitLabel} <span class="arr">→</span></button></div></div>`;
      root.querySelectorAll("[name=pk-pace]").forEach(r => r.onchange = () => { st.pace = r.value; st.days = PACES[r.value].days.slice(); draw(); });
      root.querySelectorAll(".pk-day input").forEach(c => c.onchange = () => { st.days = [...root.querySelectorAll(".pk-day input:checked")].map(x => +x.value); upd(); });
      root.querySelectorAll("[name=pk-time]").forEach(r => r.onchange = () => { st.time = r.value; upd(); });
      root.querySelector("#pk-start").onchange = e => { if (e.target.value) st.start = e.target.value; upd(); };
      if (onCancel) root.querySelector("#pk-cancel").onclick = onCancel;
      root.querySelector("#pk-save").onclick = async e => { const b = e.currentTarget, err = root.querySelector("#pk-err");
        if (!st.days.length) { err.textContent = "Выберите хотя бы один день недели."; return; }
        b.disabled = true; err.textContent = ""; try { const saved = await savePlan({ pace: st.pace, days: st.days, time: st.time, start: st.start }); onSaved && onSaved(saved); }
        catch (x) { err.textContent = x.message; b.disabled = false; } };
    }
    function upd() { root.querySelector("#pk-prev").textContent = preview(); root.querySelector("#pk-save").disabled = !st.days.length; }
    draw();
  }
  function plural(n, a, b, c) { n = Math.abs(n) % 100; const d = n % 10; return n > 10 && n < 20 ? c : d === 1 ? a : d > 1 && d < 5 ? b : c; }
  const daysText = ds => { const k = ds.slice().sort().join(""); return k === "1234567" ? "каждый день" : k === "12345" ? "по будням" : k === "67" ? "по выходным" : ds.map(d => DOW[d]).join(", "); };
  const describe = p => p ? `${PACES[p.pace].name} · ${daysText(p.days)} · ${TIMES[p.time][0].toLowerCase()}` : "";

  window.LEARN = { COURSE, ITEMS, BY, PACES, TIMES, DOW, progress, isDone, markDone, plan, savePlan, sync, schedule, status, downloadIcs, picker, describe, plural, todayIso };
})();
