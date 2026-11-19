/* Песочница FinSpector: настоящая среда auditenv (Python в браузере через Pyodide) + удобные инструменты аудитора. */
(function () {
  const { $, $$, esc, typeRu } = UI;
  const PYODIDE = "py/pyodide/";
  const FILES = ["__init__", "money", "config", "generator", "policy", "reference", "matcher", "calculator", "env", "policies"];
  const PRESETS = {
    mixed: {},
    inter: { clean: false, interactions: { partial_payment_wrong_fx: [1, 1], cutoff_partial_payment_fx: [1, 1] } },
    clean: { clean: true },
    single: { clean: false, interactions: { partial_payment_wrong_fx: [0, 0], cutoff_partial_payment_fx: [0, 0] },
      errors: { duplicate_invoice: [1, 1], missing_or_partial_allocation: [1, 1], fx_conversion_error: [1, 1], period_cutoff_error: [1, 1] } },
  };
  const EXP = { USD: 2, EUR: 2, GBP: 2, KZT: 2, CNY: 2, JPY: 0, KWD: 3 };
  const BRIDGE = `
import json
from auditenv.env import AuditEnv
from auditenv.generator import generate_episode
from auditenv.policies import make_policy
_S = {}
def new_episode(seed, cfg_json):
    cfg = json.loads(cfg_json)
    ep = generate_episode(int(seed), cfg)
    env = AuditEnv(mode="train", time_limit_s=10**9)
    obs, info = env.reset(episode=ep)
    _S.update(env=env, ep=ep, seed=int(seed), cfg=cfg)
    return json.dumps({"obs": obs, "info": info}, ensure_ascii=False)
def step(action_json):
    obs, r, term, trunc, info = _S["env"].step(json.loads(action_json))
    return json.dumps({"obs": obs, "reward": r, "terminated": term, "truncated": trunc, "info": info}, ensure_ascii=False)
def result():
    return json.dumps({"grader": _S["env"].grader_result(), "truth": _S["ep"].truth}, ensure_ascii=False)
def baseline(name):
    ep = generate_episode(_S["seed"], _S["cfg"])
    env = AuditEnv(mode="train", time_limit_s=10**9)
    obs, info = env.reset(episode=ep)
    pol = make_policy(name, truth=ep.truth, seed=0)
    pol.begin(obs, info)
    while True:
        obs, r, term, trunc, inf = env.step(pol.act(obs))
        if term or trunc:
            break
    g = env.grader_result()["result"]
    return json.dumps({k: g[k] for k in ("reward", "precision", "recall", "f1", "tp", "fp", "fn", "inspection_steps")})
`;
  let py = null, S = null;

  // ================================================================ утилиты
  const status = (html, busy) => { $("#pl-status").innerHTML = (busy ? '<span class="spin"></span>' : "") + html; };
  const exp = c => EXP[c] ?? ((S && S.m.currency_exponents[c]) ?? 2);
  const money = (minor, cur) => (minor / 10 ** exp(cur)).toLocaleString("ru-RU", { minimumFractionDigits: exp(cur), maximumFractionDigits: exp(cur) }) + " " + cur;
  const toMinor = (str, cur) => { const s = String(str).replace(/\s/g, "").replace(",", "."); if (!/^\d+(\.\d+)?$/.test(s)) return null;
    const [i, f = ""] = s.split("."); const e = exp(cur); if (f.length > e) return null; return parseInt(i + f.padEnd(e, "0"), 10); };
  const convert = (minor, src, rate, dst) => Math.round((minor / 10 ** exp(src)) * rate * 10 ** exp(dst));
  function tzOff(tz) { const m = /([+-])(\d\d):(\d\d)/.exec(tz); return m ? (m[1] === "-" ? -1 : 1) * (+m[2] * 60 + +m[3]) : 0; }
  function local(ts) { const ms = Date.parse(ts); if (isNaN(ms)) return { date: "", time: "" }; const d = new Date(ms + tzOff(S.m.timezone) * 60000).toISOString(); return { date: d.slice(0, 10), time: d.slice(11, 16) }; }
  const inPeriod = d => d >= S.m.period_start && d <= S.m.period_end;
  const ruDate = d => d ? new Date(d + "T00:00:00Z").toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }) : "—";
  const call = (fn, ...a) => JSON.parse(py.globals.get(fn)(...a));
  function act(name, args) { const r = call("step", JSON.stringify({ name, args })); steps(r.obs.remaining_steps); if (r.truncated) finish(r); return r; }
  const curStage = () => [...$$(".pl-steps li")].findIndex(l => l.classList.contains("on")) + 1;
  function stage(n) { $$(".pl-steps li").forEach((li, i) => { li.classList.toggle("done", i < n - 1); li.classList.toggle("on", i === n - 1); }); }

  // ================================================================ загрузка Python
  async function boot() {
    try {
      await new Promise((res, rej) => { const s = document.createElement("script"); s.src = PYODIDE + "pyodide.js"; s.onload = res; s.onerror = () => rej(new Error("pyodide.js")); document.head.append(s); });
      status("Запускаем Python в браузере… Это происходит один раз, около 10 секунд.", true);
      py = await loadPyodide({ indexURL: new URL(PYODIDE, location.href).href });
      py.FS.mkdirTree("/home/pyodide/auditenv");
      await Promise.all(FILES.map(async f => { const r = await fetch(`py/auditenv/${f}.py`); if (!r.ok) throw new Error(f);
        py.FS.writeFile(`/home/pyodide/auditenv/${f}.py`, await r.text()); }));
      py.runPython(`import sys; sys.path.insert(0, "/home/pyodide")\n` + BRIDGE);
      status("Готово. Выберите компанию и нажмите «Сгенерировать» — или возьмите компанию дня.");
      $("#pl-gen").disabled = false; $("#pl-daily").disabled = false; stage(1);
      if (new URLSearchParams(location.search).get("daily")) daily();
    } catch (e) { status(`Не удалось загрузить Python (${esc(e.message || e)}). Обновите страницу.`); }
  }

  // ================================================================ генерация
  function generate() {
    if (!py) return;
    const seed = Math.max(0, Math.min(999999, parseInt($("#pl-seed").value || "0", 10)));
    $("#pl-seed").value = seed; status("Строим компанию и прячем ошибки…", true);
    setTimeout(() => {
      const r = call("new_episode", seed, JSON.stringify(PRESETS[$("#pl-preset").value]));
      const m = r.obs.manifest;
      S = { m, seed, preset: $("#pl-preset").value, steps: 100, done: false, tab: "ledger", query: "", findings: [], aff: [], ev: [],
            t: { ledger: null, invoices: null, payments: null, fx: null }, fx: {}, sel: null };
      const foreign = m.currencies.filter(c => c !== m.base_currency);
      $("#pl-company").innerHTML = `
        <div class="cc"><span class="label">Компания</span><b>№${seed}</b><small>${esc(m.episode_id)}</small></div>
        <div class="cc"><span class="label">Отчётный период</span><b>${ruDate(m.period_start)} — ${ruDate(m.period_end)}</b><small>Документы вне этих дат проводить нельзя</small></div>
        <div class="cc"><span class="label">Часовой пояс</span><b>UTC${m.timezone}</b><small>Все даты в таблицах уже переведены в него</small></div>
        <div class="cc"><span class="label">Валюта учёта</span><b>${m.base_currency}</b><small>${foreign.length ? "Другие валюты: " + foreign.join(", ") : "Без других валют"}</small></div>
        <div class="cc steps-cc"><span class="label">Осталось шагов</span><b id="pl-steps-n">100</b><div class="meter"><i id="pl-meter"></i></div><small>Каждый запрос к книгам — 1 шаг</small></div>`;
      $("#f-cur").innerHTML = m.currencies.map(c => `<option${c === m.base_currency ? " selected" : ""}>${c}</option>`).join("");
      $("#cv-from").innerHTML = (foreign.length ? foreign : [m.base_currency]).map(c => `<option>${c}</option>`).join("");
      $("#cv-date").value = m.period_start;
      $("#pl-work").hidden = false; $("#pl-result").hidden = true; $("#pl-base-out").innerHTML = "";
      $$("#pl-work input, #pl-work select, #pl-work button").forEach(x => x.disabled = false);
      $("#pl-search").value = "";
      renderChips(); renderFindings(); inspect(null); setTab("ledger"); stage(2);
      status(`Компания №${seed} готова: ${m.counts.ledger} проводок и ${m.counts.documents} документов. Нажмите на строку, чтобы открыть её в инспекторе.`);
      $("#pl-work").scrollIntoView({ behavior: UI.reduce ? "auto" : "smooth", block: "start" });
    }, 30);
  }
  $("#pl-gen").onclick = generate;
  function steps(n) { if (!S) return; S.steps = n; const el = $("#pl-steps-n"); if (!el) return; el.textContent = n;
    $("#pl-meter").style.width = n + "%"; $("#pl-company .steps-cc").classList.toggle("low", n <= 15); }

  // ================================================================ таблицы
  const COLS = {
    ledger: [["row_id", "Строка", "id"], ["timestamp", "Дата (местн.)", "time"], ["account", "Счёт учёта"], ["debit_minor", "Дебет", "money"], ["credit_minor", "Кредит", "money"], ["invoice_id", "Счёт-фактура", "id"], ["payment_id", "Платёж", "id"]],
    invoices: [["invoice_id", "Счёт-фактура", "id"], ["issued_at", "Выставлен (местн.)", "time"], ["entity_id", "Контрагент"], ["total_minor", "Сумма", "money"], ["line_items", "Позиции", "lines"]],
    payments: [["payment_id", "Платёж", "id"], ["timestamp", "Поступил (местн.)", "time"], ["entity_id", "Плательщик"], ["amount_minor", "Сумма", "money"], ["invoice_refs", "Оплачивает счета", "refs"]],
    fx: [["date", "Дата", "date"], ["source_currency", "Валюта"], ["rate", "Курс к валюте учёта", "rate"]],
  };
  function load(table, everything = false) {
    if (!S || S.done) return;
    let t = S.t[table];
    do {
      if (t && !t.next) break;
      const r = act("list_records", { table, cursor: t ? t.next : null, limit: 50 });
      if (S.done) return;
      if (r.obs.error) { status(esc(r.obs.error.message)); return; }
      const res = r.obs.result;
      t = S.t[table] = { rows: (t ? t.rows : []).concat(res.records), next: res.next_cursor, total: res.total };
      if (table === "fx") res.records.forEach(x => { S.fx[x.source_currency + "|" + x.date] = +x.rate; });
    } while (everything && S.steps > 1);
    if (curStage() < 3) stage(3);
  }
  function setTab(table) { S.tab = table; $$("#pl-tabs .tab").forEach(b => b.setAttribute("aria-pressed", b.dataset.t === table)); if (!S.t[table]) load(table); renderTable(); }
  function cell(r, [k, , kind]) { const v = r[k];
    if (v === null || v === undefined) return '<td class="null">—</td>';
    if (kind === "id") return `<td><button type="button" class="idc" data-id="${esc(v)}">${esc(v)}</button></td>`;
    if (kind === "money") return v === 0 ? '<td class="num null">—</td>' : `<td class="num">${money(v, r.currency)}</td>`;
    if (kind === "time") { const l = local(v); const out = !inPeriod(l.date);
      return `<td title="Как записано в документе: ${esc(v)}"><span>${ruDate(l.date)}, ${l.time}</span>${out ? '<span class="badge-out">вне периода</span>' : ""}</td>`; }
    if (kind === "date") return `<td>${ruDate(v)}</td>`;
    if (kind === "refs") return `<td>${v.length ? v.map(x => `<button type="button" class="idc" data-id="${esc(x.invoice_id)}">${esc(x.invoice_id)}</button> <span class="null">${money(x.amount_minor, r.currency)}</span>`).join("<br>") : '<span class="null">не указаны</span>'}</td>`;
    if (kind === "lines") return `<td class="li">${v.map(l => esc(`${l.description}${l.service_period ? " · " + l.service_period : ""} ×${l.qty}`)).join("<br>")}</td>`;
    if (kind === "rate") return `<td class="num">1 ${esc(r.source_currency)} = ${esc(v)} ${esc(r.target_currency)}</td>`;
    return `<td>${esc(v)}</td>`; }
  function rowKey(r, table) { return table === "fx" ? `fx:${r.date}:${r.source_currency}:${r.target_currency}` : r.row_id || r.invoice_id || r.payment_id; }
  function renderTable() {
    const table = S.tab, t = S.t[table], c = COLS[table], q = S.query.trim().toLowerCase();
    let rows = t ? t.rows : [];
    if (q) { const qd = q.replace(/[\s,.]/g, ""); rows = rows.filter(r => JSON.stringify(r).toLowerCase().includes(q) || (qd && /^\d+$/.test(qd) && JSON.stringify(r).includes(qd))); }
    $("#pl-tbl").innerHTML = `<thead><tr>${c.map(x => `<th>${x[1]}</th>`).join("")}</tr></thead><tbody>${rows.map((r, i) =>
      `<tr data-k="${esc(rowKey(r, table))}" class="${S.sel && S.sel.key === rowKey(r, table) ? "sel" : ""}" style="--k:${Math.min(i, 25)}">${c.map(x => cell(r, x)).join("")}</tr>`).join("")}</tbody>`;
    if (!rows.length) $("#pl-tbl").insertAdjacentHTML("beforeend", `<tbody><tr><td colspan="${c.length}" class="empty">${q ? "Ничего не найдено среди загруженных строк." : "Нет строк."}</td></tr></tbody>`);
    const left = t ? t.total - t.rows.length : 0;
    $("#pl-count").textContent = t ? `Загружено ${t.rows.length} из ${t.total}${q ? ` · найдено ${rows.length}` : ""}` : "";
    const can = !!(t && t.next) && !S.done;
    $("#pl-more").disabled = !can; $("#pl-all").disabled = !can;
    $("#pl-all").textContent = can ? `Загрузить всё · ${Math.ceil(left / 50)} шаг.` : "Всё загружено";
  }
  $$("#pl-tabs .tab").forEach(b => b.onclick = () => setTab(b.dataset.t));
  $("#pl-more").onclick = () => { load(S.tab); renderTable(); };
  $("#pl-all").onclick = () => { load(S.tab, true); renderTable(); };
  $("#pl-search").oninput = e => { S.query = e.target.value; renderTable(); };
  $("#pl-tbl").addEventListener("click", e => {
    const b = e.target.closest(".idc"); if (b) { openId(b.dataset.id); return; }
    const tr = e.target.closest("tr[data-k]"); if (tr) openId(tr.dataset.k);
  });

  // ================================================================ инспектор
  const all = t => (S.t[t] ? S.t[t].rows : []);
  function find(id) {
    if (id.startsWith("fx:")) { const [, d, c, base] = id.split(":"); return { kind: "fx", r: { date: d, source_currency: c, target_currency: base, rate: S.fx[c + "|" + d] } }; }
    let r = all("ledger").find(x => x.row_id === id); if (r) return { kind: "row", r };
    r = all("invoices").find(x => x.invoice_id === id || x.doc_id === id); if (r) return { kind: "inv", r };
    r = all("payments").find(x => x.payment_id === id || x.doc_id === id); if (r) return { kind: "pay", r };
    return null;
  }
  function fetchRecord(id) {   // запрос одной записи — 1 шаг
    const table = id.startsWith("L-") ? "ledger" : id.startsWith("INV-") ? "invoices" : id.startsWith("PAY-") ? "payments" : id.startsWith("fx:") ? "fx" : null;
    const r = table ? act("get_record", { table, id }) : act("get_document", { doc_id: id });
    if (S.done) return;
    if (r.obs.error) { status(id.startsWith("fx:") ? "Курса на эту дату нет в таблице курсов." : esc(r.obs.error.message)); return; }
    const rec = r.obs.result.record || r.obs.result.document;
    const tt = table || (r.obs.result.doc_type === "invoice" ? "invoices" : "payments");
    if (tt === "fx") S.fx[rec.source_currency + "|" + rec.date] = +rec.rate;
    else { const t = S.t[tt] || (S.t[tt] = { rows: [], next: null, total: S.m.counts[tt], partial: true }); const key = rowKey(rec, tt); if (!t.rows.some(x => rowKey(x, tt) === key)) t.rows.push(rec); }
    openId(id);
  }
  const rateFor = (cur, date) => cur === S.m.base_currency ? 1 : S.fx[cur + "|" + date];
  function rateLine(cur, date, minor) {
    if (cur === S.m.base_currency) return "";
    const r = rateFor(cur, date), id = `fx:${date}:${cur}:${S.m.base_currency}`;
    return r ? `<div class="kv"><span>Курс ${cur} на ${ruDate(date)}</span><b>${r}</b></div><div class="kv"><span>В ${S.m.base_currency} по курсу этой даты</span><b class="hl">${money(convert(minor, cur, r, S.m.base_currency), S.m.base_currency)}</b></div>${addBtns(id, "курс этой даты")}`
      : `<div class="kv"><span>Курс ${cur} на ${ruDate(date)}</span><button type="button" class="chip sm" data-fetch="${id}">Узнать · 1 шаг</button></div>`;
  }
  const addBtns = (id, what = "") => `<div class="add-row">${what ? `<span class="label">${what}</span>` : ""}<button type="button" class="chip sm" data-add="aff" data-id="${esc(id)}">+ затронутые</button><button type="button" class="chip sm" data-add="ev" data-id="${esc(id)}">+ доказательства</button></div>`;
  const rowsHtml = rows => rows.length ? `<div class="mini-rows">${rows.map(x => `<button type="button" class="mr" data-open="${x.row_id}"><span>${esc(x.account)}<small>${esc(x.row_id)}</small></span><b class="${x.debit_minor ? "dr" : "cr"}">${x.debit_minor ? "Дт " + money(x.debit_minor, x.currency) : "Кт " + money(x.credit_minor, x.currency)}</b></button>`).join("")}</div>` : `<p class="empty">В загруженной части журнала проводок нет.</p>`;
  const ledgerNote = () => S.t.ledger && !S.t.ledger.next && !S.t.ledger.partial ? "" : `<p class="note">Журнал загружен не полностью — часть проводок может быть не видна. <button type="button" class="chip sm" data-loadall="ledger">Загрузить журнал</button></p>`;
  const periodBadge = d => inPeriod(d) ? `<span class="ok-b">в периоде</span>` : `<span class="bad-b">вне периода</span>`;

  function inspect(item) {
    const box = $("#sp-inspect");
    if (!item) { box.innerHTML = `<div class="insp-empty"><b>Нажмите на строку таблицы</b><p>Здесь появятся местная дата, пересчёт по курсу, связанные проводки и платежи. Считать вручную ничего не нужно.</p></div>`; return; }
    const { kind, r } = item; let h = "";
    if (kind === "inv") {
      const l = local(r.issued_at), rows = all("ledger").filter(x => x.invoice_id === r.invoice_id && !x.payment_id);
      const paid = all("payments").flatMap(p => p.invoice_refs.filter(x => x.invoice_id === r.invoice_id).map(x => ({ p, a: x.amount_minor })));
      const same = all("invoices").filter(x => x.entity_id === r.entity_id && x.invoice_id !== r.invoice_id);
      h = `<div class="ih"><span class="label">Счёт-фактура</span><b>${esc(r.invoice_id)}</b><small>документ ${esc(r.doc_id)} · контрагент ${esc(r.entity_id)}</small></div>
        ${addBtns(r.invoice_id, "этот счёт")}${addBtns(r.doc_id, "его документ")}
        <div class="kv"><span>Сумма</span><b>${money(r.total_minor, r.currency)}</b></div>
        <div class="kv"><span>Выставлен (местное время)</span><b>${ruDate(l.date)}, ${l.time} ${periodBadge(l.date)}</b></div>
        <div class="kv"><span>Как записано</span><small>${esc(r.issued_at)}</small></div>
        ${rateLine(r.currency, l.date, r.total_minor)}
        <div class="sub">Позиции</div><div class="lines">${r.line_items.map(x => `<div><span>${esc(x.description)}${x.service_period ? ` <small>${esc(x.service_period)}</small>` : ""} ×${x.qty}</span><b>${money(x.amount_minor, r.currency)}</b></div>`).join("")}</div>
        <div class="sub">Проводки по счёту</div>${rowsHtml(rows)}${ledgerNote()}
        <div class="sub">Оплаты по счёту</div>${paid.length ? `<div class="mini-rows">${paid.map(x => `<button type="button" class="mr" data-open="${x.p.payment_id}"><span>${esc(x.p.payment_id)}</span><b>${money(x.a, x.p.currency)}</b></button>`).join("")}</div>` : `<p class="empty">В загруженных платежах оплат нет.</p>`}
        ${same.length ? `<div class="sub">Другие счета этого контрагента</div><div class="mini-rows">${same.slice(0, 8).map(x => `<button type="button" class="mr" data-open="${x.invoice_id}"><span>${esc(x.invoice_id)}<small>${ruDate(local(x.issued_at).date)}</small></span><b>${money(x.total_minor, x.currency)}</b></button>`).join("")}</div>` : ""}`;
    } else if (kind === "pay") {
      const l = local(r.timestamp), rows = all("ledger").filter(x => x.payment_id === r.payment_id);
      const refs = r.invoice_refs.map(x => {
        const ar = rows.filter(y => y.invoice_id === x.invoice_id && y.account.startsWith("1200")).reduce((s, y) => s + y.credit_minor - y.debit_minor, 0);
        const inv = all("invoices").find(i => i.invoice_id === x.invoice_id); const ir = inv ? rateFor(r.currency, local(inv.issued_at).date) : null;
        const expect = ir ? convert(x.amount_minor, r.currency, ir, S.m.base_currency) : null;
        return `<div class="ref"><div class="kv"><span>Счёт <button type="button" class="idc" data-open="${esc(x.invoice_id)}">${esc(x.invoice_id)}</button> — по документу</span><b>${money(x.amount_minor, r.currency)}</b></div>
          <div class="kv"><span>Разнесено в 1200 по журналу</span><b>${money(ar, S.m.base_currency)}</b></div>
          ${expect !== null ? `<div class="kv"><span>Должно быть (курс даты счёта)</span><b class="hl">${money(expect, S.m.base_currency)}</b></div><div class="kv"><span>Разница</span><b class="${Math.abs(expect - ar) > 1 ? "warn" : ""}">${money(expect - ar, S.m.base_currency)}</b></div>`
            : `<p class="note">${inv ? `Нужен курс ${r.currency} на дату счёта — откройте счёт и узнайте курс.` : `Откройте счёт ${esc(x.invoice_id)}, чтобы сравнить с журналом.`}</p>`}</div>`; }).join("");
      h = `<div class="ih"><span class="label">Платёж</span><b>${esc(r.payment_id)}</b><small>документ ${esc(r.doc_id)} · плательщик ${esc(r.entity_id || "неизвестен")}</small></div>
        ${addBtns(r.payment_id, "этот платёж")}${addBtns(r.doc_id, "его документ")}
        <div class="kv"><span>Сумма</span><b>${money(r.amount_minor, r.currency)}</b></div>
        <div class="kv"><span>Поступил (местное время)</span><b>${ruDate(l.date)}, ${l.time} ${periodBadge(l.date)}</b></div>
        <div class="kv"><span>Как записано</span><small>${esc(r.timestamp)}</small></div>
        ${rateLine(r.currency, l.date, r.amount_minor)}
        <div class="sub">Разнесение по счетам</div>${refs || `<p class="empty">Счета не указаны — это законное «невыясненное» поступление в 2900.</p>`}
        <div class="sub">Проводки платежа</div>${rowsHtml(rows)}${ledgerNote()}`;
    } else if (kind === "row") {
      const l = local(r.timestamp);
      h = `<div class="ih"><span class="label">Строка журнала</span><b>${esc(r.row_id)}</b><small>${esc(r.account)}</small></div>${addBtns(r.row_id, "эту строку")}
        <div class="kv"><span>${r.debit_minor ? "Дебет" : "Кредит"}</span><b>${money(r.debit_minor || r.credit_minor, r.currency)}</b></div>
        <div class="kv"><span>Дата проводки (местн.)</span><b>${ruDate(l.date)}, ${l.time}</b></div>
        ${r.invoice_id ? `<div class="kv"><span>Счёт-фактура</span><button type="button" class="idc" data-open="${esc(r.invoice_id)}">${esc(r.invoice_id)} →</button></div>` : ""}
        ${r.payment_id ? `<div class="kv"><span>Платёж</span><button type="button" class="idc" data-open="${esc(r.payment_id)}">${esc(r.payment_id)} →</button></div>` : ""}
        ${!r.invoice_id && !r.payment_id ? `<p class="note">Строка не связана с документами — например, расход поставщику.</p>` : ""}`;
    } else if (kind === "fx") {
      h = `<div class="ih"><span class="label">Курс валюты</span><b>${r.source_currency} → ${r.target_currency}</b><small>${ruDate(r.date)}</small></div>
        ${r.rate ? `<div class="kv"><span>1 ${r.source_currency} =</span><b>${r.rate} ${r.target_currency}</b></div>${addBtns(`fx:${r.date}:${r.source_currency}:${r.target_currency}`, "этот курс")}` : `<button type="button" class="chip" data-fetch="fx:${r.date}:${r.source_currency}:${r.target_currency}">Узнать курс · 1 шаг</button>`}`;
    } else {
      h = `<div class="ih"><span class="label">Запись не загружена</span><b>${esc(item.id)}</b></div><p class="note">Этой записи нет среди загруженных строк.</p>
        <button type="button" class="chip" data-fetch="${esc(item.id)}">Запросить запись · 1 шаг</button>${addBtns(item.id)}`;
    }
    box.innerHTML = h; setSide("inspect");
  }
  function openId(id) { if (!S) return; S.sel = { key: id }; inspect(find(id) || { kind: "missing", id }); renderTable(); }
  $("#sp-inspect").addEventListener("click", e => {
    if (S && S.done) return;
    const o = e.target.closest("[data-open]"); if (o) return openId(o.dataset.open);
    const a = e.target.closest("[data-add]"); if (a) { addId(a.dataset.add, a.dataset.id); a.classList.add("added"); a.textContent = "✓ добавлено"; const c = $("#form-cnt"); c.classList.remove("pop"); void c.offsetWidth; c.classList.add("pop"); return; }
    const f = e.target.closest("[data-fetch]"); if (f) return fetchRecord(f.dataset.fetch);
    const la = e.target.closest("[data-loadall]"); if (la) { load(la.dataset.loadall, true); if (S.tab === la.dataset.loadall) renderTable(); openId(S.sel.key); }
  });

  // ================================================================ боковые вкладки
  function setSide(name) { $$("#side-tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.s === name)); $$(".sp").forEach(p => { p.hidden = p.id !== "sp-" + name; }); }
  $$("#side-tabs button").forEach(b => b.onclick = () => setSide(b.dataset.s));

  // калькулятор: свой разбор выражения (без eval), шаги не тратит
  function calcEval(src) {
    const s = src.replace(/,/g, ".").replace(/×/g, "*").replace(/÷/g, "/").replace(/−/g, "-").replace(/\s/g, "");
    if (!/^[\d.+\-*/()]+$/.test(s)) throw new Error("Только цифры и + − × ÷ ( )");
    let i = 0;
    const num = () => { const m = /^\d+(\.\d+)?/.exec(s.slice(i)); if (!m) throw new Error("Проверьте выражение"); i += m[0].length; return parseFloat(m[0]); };
    const fac = () => { if (s[i] === "-") { i++; return -fac(); } if (s[i] === "(") { i++; const v = add(); if (s[i] !== ")") throw new Error("Не хватает «)»"); i++; return v; } return num(); };
    const mul = () => { let v = fac(); while (s[i] === "*" || s[i] === "/") { const op = s[i++]; const r = fac(); if (op === "/" && r === 0) throw new Error("Деление на ноль"); v = op === "*" ? v * r : v / r; } return v; };
    const add = () => { let v = mul(); while (s[i] === "+" || s[i] === "-") { const op = s[i++]; const r = mul(); v = op === "+" ? v + r : v - r; } return v; };
    const v = add(); if (i !== s.length) throw new Error("Проверьте выражение"); return v;
  }
  $("#calc-in").oninput = () => { const s = $("#calc-in").value.trim();
    try { $("#calc-out").textContent = s ? "= " + calcEval(s).toLocaleString("ru-RU", { maximumFractionDigits: 6 }) : ""; } catch (e) { $("#calc-out").textContent = e.message; } };
  $("#cv-btn").onclick = () => { if (!S || S.done) return; const cur = $("#cv-from").value, d = $("#cv-date").value, amt = toMinor($("#cv-amt").value || "", cur);
    if (amt === null) { $("#cv-out").textContent = "Введите сумму числом, например 1250,50"; return; }
    let r = rateFor(cur, d);
    if (!r) { const res = act("get_record", { table: "fx", id: `fx:${d}:${cur}:${S.m.base_currency}` }); if (S.done) return;
      if (res.obs.error) { $("#cv-out").textContent = "Курса на эту дату нет в таблице курсов."; return; } r = +res.obs.result.record.rate; S.fx[cur + "|" + d] = r; }
    $("#cv-out").innerHTML = `${money(amt, cur)} × ${r} = <b>${money(convert(amt, cur, r, S.m.base_currency), S.m.base_currency)}</b>`; };

  // ================================================================ форма вывода
  const HINTS = {
    duplicate_invoice: ["Затронутые: <b>оба счёта</b> — оригинал и дубль.", "Сумма: итог дубля в <b>валюте счёта</b>.", "Доказательства: документы обоих счетов + строка журнала дубля (1200 или 4000)."],
    missing_or_partial_allocation: ["Затронутые: <b>платёж и счёт</b>.", "Сумма: сколько <b>не разнесено</b>, в валюте платежа.", "Доказательства: документ платежа + строка 2900. Если часть разнесена — ещё документ счёта и строка 1200."],
    fx_conversion_error: ["Затронутые: <b>счёт или платёж</b> с неверным курсом.", "Сумма: разница в <b>валюте учёта</b>.", "Доказательства: документ + строка журнала (1200/4000 или 1000) + курс нужной даты."],
    period_cutoff_error: ["Затронутые: <b>счёт или платёж</b> не из этого месяца.", "Сумма: сумма документа в <b>его валюте</b>.", "Доказательства: документ + строка журнала (1200/4000 или 1000)."],
  };
  const renderHint = () => { $("#f-hint").innerHTML = HINTS[$("#f-type").value].map(x => `<li>${x}</li>`).join(""); };
  $("#f-type").onchange = renderHint;
  function addId(where, id) { if (!S || S.done) return; const arr = S[where];
    if (!arr.includes(id)) { if (where === "ev" && arr.length >= 10) { $("#f-err").textContent = "Доказательств может быть не больше 10."; return; } arr.push(id); } renderChips(); }
  function renderChips() { if (!S) return; const n = S.aff.length + S.ev.length; const c = $("#form-cnt"); c.hidden = !n; c.textContent = n;
    ["aff", "ev"].forEach(w => { $("#f-" + w + "-list").innerHTML = S[w].map((id, i) => `<span class="idchip">${esc(id)}<button type="button" aria-label="Убрать ${esc(id)}" data-rm="${w}" data-i="${i}">×</button></span>`).join("")
    || `<span class="null">${w === "aff" ? "Добавьте через «+ затронутые» в инспекторе" : "Добавьте через «+ доказательства» в инспекторе"}</span>`; }); }
  $("#pl-form").addEventListener("click", e => { const b = e.target.closest("[data-rm]"); if (b && S && !S.done) { S[b.dataset.rm].splice(+b.dataset.i, 1); renderChips(); } });
  ["aff", "ev"].forEach(w => $("#f-" + w + "-in").addEventListener("keydown", e => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); const v = e.target.value.trim(); if (v) addId(w, v); e.target.value = ""; } }));
  $("#pl-form").onsubmit = e => { e.preventDefault(); if (!S || S.done) return; const err = $("#f-err"); err.textContent = "";
    if (!S.aff.length) { err.textContent = "Добавьте хотя бы один затронутый ID: откройте запись в инспекторе и нажмите «+ затронутые»."; return; }
    const cur = $("#f-cur").value, amt = toMinor($("#f-amt").value, cur);
    if (amt === null) { err.textContent = `Сумма — число, например 1250,50. Для ${cur} не больше ${exp(cur)} знаков после запятой.`; return; }
    if (S.findings.length >= 30) { err.textContent = "Выводов может быть не больше 30."; return; }
    S.findings.push({ type: $("#f-type").value, affected_ids: [...S.aff], claimed_amount_minor: amt, currency: cur, evidence_ids: [...S.ev], explanation: $("#f-exp").value.slice(0, 1000) });
    S.aff = []; S.ev = []; $("#f-amt").value = ""; $("#f-exp").value = ""; renderChips(); renderFindings(); stage(4);
    $$("#sp-inspect .added").forEach(b => { b.classList.remove("added"); b.textContent = b.dataset.add === "aff" ? "+ затронутые" : "+ доказательства"; });
    status(`Вывод добавлен. Всего выводов: ${S.findings.length}. Когда закончите, нажмите «Отправить оценщику».`); };
  function renderFindings() { const f = S ? S.findings : [];
    $("#pl-n").textContent = f.length ? `· ${f.length}` : "";
    $("#pl-findings").innerHTML = f.length ? f.map((x, i) => `<div class="fd"><div><b>${typeRu[x.type]}</b><span>${esc(x.affected_ids.join(", "))} · ${money(x.claimed_amount_minor, x.currency)} · доказательств ${x.evidence_ids.length}</span></div>
      ${S.done ? "" : `<button type="button" class="x" data-i="${i}" aria-label="Удалить вывод">×</button>`}</div>`).join("")
      : `<p class="empty">Пока пусто. Если ошибок нет, отправьте пустой список: на чистой компании это лучший ответ.</p>`;
    $$("#pl-findings .x").forEach(b => b.onclick = () => { S.findings.splice(+b.dataset.i, 1); renderFindings(); }); }
  $("#pl-submit").onclick = () => { if (!S || S.done) return;
    const b = $("#pl-submit");
    if (!S.findings.length && !b.dataset.sure) { b.dataset.sure = "1"; b.innerHTML = 'Отправить пустой ответ? Нажмите ещё раз <span class="arr">→</span>';
      setTimeout(() => { delete b.dataset.sure; b.innerHTML = 'Отправить оценщику <span class="arr">→</span>'; }, 4000); return; }
    const r = act("submit", { findings: { episode_id: S.m.episode_id, findings: S.findings } }); finish(r); };

  // ================================================================ итог
  const WHY = { type: "не тот тип ошибки", affected_ids: "не те затронутые ID", currency: "не та валюта", amount: "сумма вне допуска", evidence: "не хватает доказательств",
    duplicate_or_already_matched: "повтор вывода", no_issues_in_truth: "в книгах не было ошибок" };
  function finish(r) {
    if (!S || S.done) return; S.done = true; stage(5);
    const { grader, truth } = call("result"); const g = grader.result;
    $$("#pl-work .pl-side input, #pl-work .pl-side select, #pl-form button, #pl-submit, #pl-more, #pl-all").forEach(x => { x.disabled = true; });
    renderFindings(); renderTable();
    const verdicts = (g.per_finding || []).map(p => { const f = S.findings[p.finding];
      return `<div class="v"><span class="tag ${p.result === "TP" ? "tp" : "fp"}">${p.result === "TP" ? "Верно" : "Неверно"}</span><span>${typeRu[f.type]} · ${esc(f.affected_ids.join(", "))}${p.result === "FP" ? ` — ${WHY[p.closest_failure] || p.closest_failure}` : ""}</span></div>`; }).join("");
    const missed = new Set(g.missed_issue_ids || []);
    const issues = truth.issues.map(i => `<div class="v"><span class="tag ${missed.has(i.issue_id) ? "fn" : "tp"}">${missed.has(i.issue_id) ? "Пропущено" : "Найдено"}</span><span><b>${typeRu[i.type]}</b> · ${esc(i.affected_ids.join(", "))} · ${money(i.expected_amount_minor, i.currency)}<br><span class="null">доказательства: ${esc(i.evidence_sets[0].join(", "))}</span></span></div>`).join("")
      || `<p class="empty">Компания была чистой — ошибок не было.</p>`;
    const rew = g.reward;
    $("#pl-result").innerHTML = `<div class="res-head glass"><div><span class="label">${r && r.truncated ? "Шаги закончились — засчитан пустой ответ" : "Оценщик проверил ваш ответ"}</span>
      <div class="big ${rew < 0 ? "neg" : "pos"}">${rew > 0 ? "+" : ""}${rew.toFixed(3)}</div><span class="label">награда от −1 до +1</span></div>
      <div class="meters">${[["Точность", g.precision.toFixed(2)], ["Полнота", g.recall.toFixed(2)], ["F1", g.f1.toFixed(2)], ["Шагов", g.inspection_steps]].map(([k, v]) => `<div><span class="label">${k}</span><div class="n">${v}</div></div>`).join("")}</div>
      <button class="btn" id="pl-again">Новая компания <span class="arr">→</span></button></div>
      <form class="glass pl-save" id="pl-save"><div><div class="t">Сохранить в таблицу лидеров</div><p class="label" id="pl-save-who"></p></div>
        <label class="fld" id="pl-name-wrap"><span>Ваше имя</span><input id="pl-name" maxlength="32" placeholder="Например, Айгерим" autocomplete="nickname"></label>
        <button class="btn" type="submit">Сохранить <span class="arr">→</span></button><p class="save-msg" id="save-msg" role="status" aria-live="polite"></p></form>
      <div class="res-cols"><div class="glass"><div class="t">Ваши выводы</div>${verdicts || '<p class="empty">Вы не отправили выводов.</p>'}</div>
      <div class="glass"><div class="t">Что было спрятано</div>${issues}</div></div>`;
    $("#pl-result").hidden = false; bindSave(g.inspection_steps);
    $("#pl-again").onclick = () => { $("#pl-seed").value = Math.floor(Math.random() * 999999); generate(); };
    $("#pl-result").scrollIntoView({ behavior: UI.reduce ? "auto" : "smooth", block: "start" });
    status("Эпизод завершён. Сохраните результат или сравните себя с базовыми политиками ниже.");
  }

  // ================================================================ сохранение, компания дня, базовые политики
  function bindSave(stepsUsed) { const f = $("#pl-save"), msg = $("#save-msg"), u = AUTH.user();
    if (u) { $("#pl-name-wrap").hidden = true; $("#pl-save-who").innerHTML = `Сохранится в профиль <b>${esc(u.display)}</b>.`; }
    else { try { $("#pl-name").value = localStorage.getItem("fa-name") || ""; } catch (e) {}
      $("#pl-save-who").innerHTML = '<a href="profile.html">Войдите</a>, чтобы результаты копились в профиле и открывали достижения.'; }
    f.onsubmit = async e => { e.preventDefault(); const name = u ? null : $("#pl-name").value.trim();
      if (!u && name.length < 2) { msg.textContent = "Имя должно содержать от 2 до 32 символов."; return; }
      const btn = f.querySelector("button"); btn.disabled = true; msg.innerHTML = '<span class="spin"></span>Сервер пересчитывает ваш результат… Если он спал, это займёт до минуты.';
      try { const r = await AUTH.api("/api/results", { method: "POST", body: { name, seed: S.seed, preset: S.preset, steps: stepsUsed, findings: S.findings } });
        if (!u) try { localStorage.setItem("fa-name", name); } catch (e) {}
        msg.innerHTML = `Сохранено. ${r.daily ? "Место в рейтинге дня" : "Место в общем рейтинге"}: <b>#${r.rank}</b>. Балл по пересчёту сервера: <b>${r.reward > 0 ? "+" : ""}${r.reward.toFixed(3)}</b>. <a href="leaders.html">Таблица лидеров →</a>${u ? ' · <a href="profile.html">Профиль →</a>' : ""}`; }
      catch (err) { btn.disabled = false; msg.textContent = err.message; } }; }
  async function daily() { const b = $("#pl-daily"); b.disabled = true; status("Узнаём компанию дня…", true);
    try { const d = await AUTH.api("/api/daily", { auth: false }); $("#pl-seed").value = d.seed; $("#pl-preset").value = "mixed"; generate(); }
    catch (e) { status(esc(e.message)); } finally { b.disabled = false; } }
  $("#pl-daily").onclick = daily;
  $$(".pl-base-btns .chip").forEach(b => b.onclick = () => { if (!S) return; const name = b.dataset.p; b.disabled = true;
    const out = $("#pl-base-out"); const old = $("#br-" + name); if (old) old.remove();
    out.insertAdjacentHTML("beforeend", `<div class="br" id="br-${name}"><b>${b.textContent}</b><span>считаем…</span></div>`);
    setTimeout(() => { const r = call("baseline", name);
      $("#br-" + name).innerHTML = `<b>${b.textContent}</b><span>награда <em class="${r.reward < 0 ? "neg" : "pos"}">${r.reward > 0 ? "+" : ""}${r.reward.toFixed(3)}</em> · F1 ${r.f1.toFixed(2)} · верно ${r.tp} · неверно ${r.fp} · пропущено ${r.fn} · шагов ${r.inspection_steps}</span>`;
      b.disabled = false; }, 30); });

  renderHint();
  boot();
})();
