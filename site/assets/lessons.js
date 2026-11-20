/* FinSpector · Уроки: четыре короткие интерактивные задачи — по одной на каждый тип ошибки. */
(function () {
  const { $, $$, esc } = UI;
  const KEY = "fs-lessons";
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } };
  const save = s => { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} };
  let done = load();

  // Каждый урок: короткое объяснение → задача (найти строку или выбрать ответ) → ловушка (ошибка или нет?) → итог.
  const L = [
    { id: "dup", title: "Дубль счёта", short: "Один счёт выставлен дважды",
      teach: "Иногда бухгалтер вводит один и тот же счёт два раза. Клиенту кажется, что он должен вдвое больше, а выручка в отчёте раздута. Признаки дубля: тот же клиент, тот же заказ, та же сумма — и почти одно и то же время.",
      task: { kind: "row", q: "В таблице счетов за 3–4 мая есть дубль. Нажмите на лишний счёт.",
        cols: ["Счёт", "Клиент", "Выставлен", "Заказ", "Сумма"], num: [4],
        rows: [["INV-4K2P", "ТОО «Алма»", "3 мая, 09:14", "SO-7731", "1 250,00 €"], ["INV-9QX1", "ИП Борей", "3 мая, 11:02", "SO-7740", "480,00 €"],
               ["INV-7T3M", "ТОО «Алма»", "3 мая, 16:40", "SO-7731", "1 250,00 €"], ["INV-2LZ8", "АО «Каспий»", "4 мая, 10:20", "SO-7752", "990,00 €"]],
        answer: 2, mark: [0],
        near: { 0: "Почти! Это первый, настоящий счёт. Лишний — второй, выставленный позже по тому же заказу SO-7731." },
        ok: "INV-7T3M повторяет INV-4K2P: тот же клиент, заказ SO-7731 и сумма. В выводе укажите оба счёта, а сумма ошибки — 1 250,00 €." },
      trap: { q: "«Номад Медиа» каждый понедельник получает счёт на 99,00 € по подписке. В мае таких счетов четыре. Это дубли?",
        opts: ["Да, это дубли", "Нет, это подписка"], answer: 1,
        why: "Не дубли. У каждого счёта свой период услуги — неделя. Одинаковая сумма у подписки — это нормально." } },

    { id: "alloc", title: "Неполное разнесение", short: "Часть оплаты «зависла»",
      teach: "Клиент оплатил счёт, но в учёте на этот счёт записали только часть денег. Остаток попал на счёт 2900 — «невыясненные поступления». В итоге кажется, что клиент всё ещё должен, хотя он заплатил.",
      task: { kind: "pick", q: "Платёж PAY-5H1 на 2 000,00 € ссылается на счёт INV-4K2P. Вот как его провели. Сколько денег не дошло до счёта клиента?",
        cols: ["Строка", "Счёт учёта", "Дебет", "Кредит"], num: [2, 3],
        rows: [["L-81A", "1000 Касса", "2 000,00 €", "—"], ["L-81B", "1200 Долг клиента · INV-4K2P", "—", "1 400,00 €"], ["L-81C", "2900 Невыясненные поступления", "—", "600,00 €"]],
        hl: [2], opts: ["600,00 €", "1 400,00 €", "2 000,00 €"], answer: 0,
        ok: "Из 2 000 € на долг клиента записали только 1 400 €, а 600 € «зависли» на 2900. Сумма вывода — 600,00 €, доказательства — платёж и строки L-81B и L-81C." },
      trap: { q: "Пришёл платёж на 300,00 € без указания счёта, и его целиком записали на 2900. Это ошибка?",
        opts: ["Да, ошибка", "Нет, всё правильно"], answer: 1,
        why: "Правильно. Если в платеже не указан счёт, бухгалтер не знает, что гасить. Невыясненные деньги и должны лежать на 2900." } },

    { id: "fx", title: "Неверный курс", short: "Пересчёт не по той дате",
      teach: "Счёт в долларах нужно перевести в валюту учёта по курсу на дату счёта. Частая ошибка — взять курс другого дня или переставить цифры в курсе. Тогда сумма в журнале расходится с правильной.",
      task: { kind: "pick", q: "Счёт INV-U12 на 1 000,00 $ выставлен 12 мая. В журнал записали 934,50 €. Сколько должно было быть?",
        cols: ["Дата", "Курс $ → €"], num: [1],
        rows: [["12 мая", "0,9210"], ["21 мая", "0,9345"], ["28 мая", "0,9301"]],
        hl: [0], opts: ["921,00 €", "934,50 €", "930,10 €"], answer: 0,
        ok: "На 12 мая курс 0,9210, значит 1 000 $ = 921,00 €. В журнале взяли курс 21 мая. Ошибка — 13,50 € (934,50 − 921,00)." },
      trap: { q: "Клиент оплатил этот счёт 28 мая по курсу 0,9301. Появилась курсовая разница 9,10 €. Это ошибка?",
        opts: ["Да, ошибка", "Нет, это нормально"], answer: 1,
        why: "Нормально. Курс между датой счёта и датой оплаты меняется, и разница честно записывается в курсовые разницы." } },

    { id: "cut", title: "Не тот период", short: "Документ из чужого месяца",
      teach: "В отчёт за май должны попасть только майские документы. Подвох в часовых поясах: время в системе хранится по Гринвичу (UTC), а месяц считается по часам компании. Компания здесь живёт по UTC+5.",
      task: { kind: "row", q: "Все эти счета проведены в мае. Один из них — уже июньский. Нажмите на него.",
        cols: ["Счёт", "Время по UTC", "По часам компании"], num: [],
        rows: [["INV-A01", "31 мая, 17:30", "31 мая, 22:30"], ["INV-B02", "31 мая, 20:15", "1 июня, 01:15"], ["INV-C03", "1 мая, 03:00", "1 мая, 08:00"], ["INV-D04", "30 апр., 21:00", "1 мая, 02:00"]],
        answer: 1, mark: [],
        near: { 3: "Это ловушка! По UTC это апрель, но по часам компании уже 1 мая — счёт законно майский. Ищите обратный случай." },
        ok: "По UTC это ещё 31 мая, но у компании уже 01:15 1 июня. Счёт относится к июню, а проведён в мае." },
      trap: { q: "Счёт от 3 июня лежит в таблице, но в журнале за май его нет. Это ошибка?",
        opts: ["Да, ошибка", "Нет, всё правильно"], answer: 1,
        why: "Правильно. Документ следующего месяца может лежать в системе — ошибка только если его провели в текущем месяце." } },
  ];

  let cur = 0, step = 0;          // step: 0 — задача, 1 — ловушка, 2 — итог
  const total = L.length;

  function nav() {
    const n = L.filter(l => done[l.id]).length;
    $("#ls-prog-n").textContent = `${n} из ${total}`;
    $("#ls-prog i").style.width = (n / total * 100) + "%";
    $("#ls-nav").innerHTML = L.map((l, i) => `<button type="button" class="ls-item${i === cur ? " on" : ""}${done[l.id] ? " ok" : ""}" data-i="${i}" ${i === cur ? 'aria-current="step"' : ""}>
      <span class="ls-dot" aria-hidden="true">${done[l.id] ? "✓" : i + 1}</span><span><b>${l.title}</b><small>${l.short}</small></span></button>`).join("")
      + `<a class="ls-item final${n === total ? " ready" : ""}" href="play.html?preset=single"><span class="ls-dot" aria-hidden="true">★</span><span><b>Настоящая компания</b><small>${n === total ? "Все уроки пройдены — вперёд!" : "Можно и сразу, но лучше после уроков"}</small></span></a>`;
  }

  function table(t, clickable) {
    return `<div class="ls-tbl-wrap"><table class="ls-tbl"><thead><tr>${t.cols.map((c, i) => `<th${t.num.includes(i) ? ' class="r"' : ""}>${c}</th>`).join("")}</tr></thead><tbody>
      ${t.rows.map((r, ri) => `<tr${(t.hl || []).includes(ri) ? ' class="hl"' : ""}${clickable ? ` tabindex="0" role="button" data-row="${ri}" aria-label="Выбрать строку ${esc(r[0])}"` : ""}>${r.map((c, i) => `<td${t.num.includes(i) ? ' class="r"' : ""}>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }

  function render() {
    const l = L[cur];
    nav();
    const head = `<div class="ls-head"><span class="ls-k">Урок ${cur + 1} из ${total}</span><h2>${l.title}</h2></div>`;
    const pips = `<ol class="ls-pips" aria-label="Шаги урока">${["Задача", "Ловушка", "Итог"].map((s, i) => `<li class="${i < step ? "done" : i === step ? "on" : ""}">${s}</li>`).join("")}</ol>`;
    let body = "";
    if (step === 0) {
      const t = l.task;
      body = `<p class="ls-teach">${l.teach}</p><div class="ls-q"><b>Задача.</b> ${t.q}</div>${table(t, t.kind === "row")}
        ${t.kind === "pick" ? `<div class="ls-opts" role="group" aria-label="Варианты ответа">${t.opts.map((o, i) => `<button type="button" class="ls-opt" data-o="${i}">${o}</button>`).join("")}</div>` : ""}
        <div class="ls-fb" id="ls-fb" role="status" aria-live="polite"></div>`;
    } else if (step === 1) {
      const t = l.trap;
      body = `<div class="ls-trap"><span class="ls-badge">Ловушка</span><p>${t.q}</p></div>
        <div class="ls-opts" role="group" aria-label="Варианты ответа">${t.opts.map((o, i) => `<button type="button" class="ls-opt" data-t="${i}">${o}</button>`).join("")}</div>
        <div class="ls-fb" id="ls-fb" role="status" aria-live="polite"></div>`;
    } else {
      const last = cur === total - 1 || L.every(x => done[x.id]);
      body = `<div class="ls-done"><div class="ls-check" aria-hidden="true">✓</div><h3>Урок пройден</h3>
        <p>Теперь вы знаете, как выглядит «${l.title.toLowerCase()}» и чем она отличается от похожей законной ситуации.</p>
        <div class="ls-actions">${last && L.every(x => done[x.id])
          ? `<a class="btn" href="play.html?preset=single">Проверить настоящую компанию <span class="arr">→</span></a>`
          : `<button type="button" class="btn" id="ls-next">Следующий урок <span class="arr">→</span></button><a class="btn ghost" href="play.html?preset=single"><span class="dot"></span>Сразу в песочницу</a>`}</div></div>`;
    }
    $("#ls-main").innerHTML = head + pips + body;
    const nx = $("#ls-next"); if (nx) nx.onclick = () => { cur = L.findIndex(x => !done[x.id]); if (cur < 0) cur = 0; step = 0; render(); focusMain(); };
  }
  function focusMain() { const h = $("#ls-main h2"); if (h) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); } $("#ls-main").scrollIntoView({ behavior: UI.reduce ? "auto" : "smooth", block: "nearest" }); }

  function feedback(ok, text, nextLabel) {
    const fb = $("#ls-fb");
    fb.className = "ls-fb " + (ok ? "good" : "bad");
    fb.innerHTML = `<b>${ok ? "Верно" : "Не совсем"}</b> ${text}${ok ? `<button type="button" class="btn plain" id="ls-go">${nextLabel}</button>` : ""}`;
    if (ok) { const g = $("#ls-go"); g.onclick = () => { step++; if (step === 2) { done[L[cur].id] = Date.now(); save(done); } render(); focusMain(); }; g.focus({ preventScroll: true }); }
  }

  $("#ls-main").addEventListener("click", e => {
    const l = L[cur];
    const row = e.target.closest("tr[data-row]");
    if (row && step === 0 && l.task.kind === "row" && !row.closest("table").classList.contains("solved")) {
      const i = +row.dataset.row, t = l.task;
      $$("#ls-main tr[data-row]").forEach(r => r.classList.remove("wrong"));
      if (i === t.answer) { row.classList.add("right"); row.closest("table").classList.add("solved"); (t.mark || []).forEach(m => $(`#ls-main tr[data-row="${m}"]`).classList.add("pair")); feedback(true, t.ok, "К ловушке →"); }
      else { row.classList.add("wrong"); feedback(false, (t.near && t.near[i]) || "Эта строка в порядке. Сравните клиента, заказ, сумму и время ещё раз."); }
      return;
    }
    const o = e.target.closest("[data-o]");
    if (o && step === 0 && !o.disabled) { const t = l.task, i = +o.dataset.o;
      if (i === t.answer) { $$("#ls-main [data-o]").forEach(b => b.disabled = true); o.classList.add("right"); feedback(true, t.ok, "К ловушке →"); }
      else { o.classList.add("wrong"); o.disabled = true; feedback(false, "Посмотрите ещё раз на подсвеченную строку и пересчитайте."); }
      return; }
    const tr = e.target.closest("[data-t]");
    if (tr && step === 1 && !tr.disabled) { const t = l.trap, i = +tr.dataset.t;
      $$("#ls-main [data-t]").forEach(b => b.disabled = true);
      tr.classList.add(i === t.answer ? "right" : "wrong");
      if (i !== t.answer) $(`#ls-main [data-t="${t.answer}"]`).classList.add("right");
      const fb = $("#ls-fb"); fb.className = "ls-fb " + (i === t.answer ? "good" : "bad");
      fb.innerHTML = `<b>${i === t.answer ? "Верно" : "Это ловушка"}</b> ${t.why}<button type="button" class="btn plain" id="ls-go">Завершить урок</button>`;
      $("#ls-go").onclick = () => { step = 2; done[l.id] = Date.now(); save(done); render(); focusMain(); };
      $("#ls-go").focus({ preventScroll: true }); }
  });
  $("#ls-main").addEventListener("keydown", e => { if ((e.key === "Enter" || e.key === " ") && e.target.matches("tr[data-row]")) { e.preventDefault(); e.target.click(); } });
  $("#ls-nav").addEventListener("click", e => { const b = e.target.closest("button[data-i]"); if (!b) return; cur = +b.dataset.i; step = done[L[cur].id] ? 0 : 0; render(); focusMain(); });
  $("#ls-reset").onclick = () => { done = {}; save(done); cur = 0; step = 0; render(); };

  cur = Math.max(0, L.findIndex(l => !done[l.id])); if (L.every(l => done[l.id])) cur = 0;
  render();
})();
