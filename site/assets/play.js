/* Песочница: настоящая среда auditenv (Python) в браузере через Pyodide. */
(function () {
  const { $, $$, esc, money, typeRu } = UI;
  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
  const FILES = ["__init__", "money", "config", "generator", "policy", "reference", "matcher", "calculator", "env", "policies"];
  const PRESETS = {
    mixed: {},
    inter: { clean: false, interactions: { partial_payment_wrong_fx: [1, 1], cutoff_partial_payment_fx: [1, 1] } },
    clean: { clean: true },
    single: { clean: false, interactions: { partial_payment_wrong_fx: [0, 0], cutoff_partial_payment_fx: [0, 0] },
      errors: { duplicate_invoice: [1, 1], missing_or_partial_allocation: [1, 1], fx_conversion_error: [1, 1], period_cutoff_error: [1, 1] } },
  };
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
  let py = null, state = null;
  const status = (html, busy) => { $("#pl-status").innerHTML = (busy ? '<span class="spin"></span>' : "") + html; };

  async function boot() {
    try {
      await new Promise((res, rej) => { const s = document.createElement("script"); s.src = PYODIDE + "pyodide.js"; s.onload = res; s.onerror = rej; document.head.append(s); });
      status("Запускаем интерпретатор…", true);
      py = await loadPyodide({ indexURL: PYODIDE });
      py.FS.mkdirTree("/home/pyodide/auditenv");
      await Promise.all(FILES.map(async f => {
        const r = await fetch(`py/auditenv/${f}.py`); if (!r.ok) throw new Error("файл " + f);
        py.FS.writeFile(`/home/pyodide/auditenv/${f}.py`, await r.text()); }));
      py.runPython(`import sys; sys.path.insert(0, "/home/pyodide")\n` + BRIDGE);
      status("Готово. Выберите компанию и нажмите «Сгенерировать».");
      $("#pl-gen").disabled = false;
    } catch (e) {
      status(`Не удалось загрузить Python. Проверьте интернет и обновите страницу. <span class="label">(${esc(e.message || e)})</span>`);
    }
  }

  const call = (fn, ...args) => JSON.parse(py.globals.get(fn)(...args));
  const act = (name, args) => call("step", JSON.stringify({ name, args }));

  // ---------------------------------------------------------------- генерация
  $("#pl-gen").onclick = () => {
    const seed = Math.max(0, Math.min(999999, parseInt($("#pl-seed").value || "0", 10)));
    status("Строим компанию и вносим ошибки…", true);
    setTimeout(() => {
      const r = call("new_episode", seed, JSON.stringify(PRESETS[$("#pl-preset").value]));
      const m = r.obs.manifest;
      state = { m, steps: 100, done: false, tables: {}, tab: "ledger", findings: [] };
      $("#pl-meta").innerHTML = [["Компания", m.episode_id], ["Период", `${m.period_start} — ${m.period_end}`], ["Часовой пояс", m.timezone],
        ["Валюта учёта", m.base_currency], ["Проводок", m.counts.ledger], ["Документов", m.counts.documents]]
        .map(([k, v]) => `<div><span class="label">${k}</span><b>${esc(v)}</b></div>`).join("");
      $("#f-cur").innerHTML = m.currencies.map(c => `<option${c === m.base_currency ? " selected" : ""}>${c}</option>`).join("");
      $("#pl-work").hidden = false; $("#pl-result").hidden = true; $("#pl-base-out").innerHTML = "";
      $("#pl-form").querySelectorAll("input,select,button").forEach(x => x.disabled = false); $("#pl-submit").disabled = false;
      renderFindings(); setTab("ledger");
      status(`Компания готова. В ней ${m.counts.ledger} проводок. Ищите ошибки.`);
      $("#pl-work").scrollIntoView({ behavior: UI.reduce ? "auto" : "smooth", block: "start" });
    }, 30);
  };

  // ---------------------------------------------------------------- таблицы
  const COLS = {
    ledger: [["row_id", "row_id", "id"], ["timestamp", "время"], ["account", "счёт"], ["debit_minor", "дебет", "n"], ["credit_minor", "кредит", "n"], ["invoice_id", "invoice_id", "id"], ["payment_id", "payment_id", "id"]],
    invoices: [["doc_id", "doc_id", "id"], ["invoice_id", "invoice_id", "id"], ["entity_id", "контрагент"], ["issued_at", "issued_at"], ["currency", "вал."], ["total_minor", "сумма", "n"], ["line_items", "позиции"]],
    payments: [["doc_id", "doc_id", "id"], ["payment_id", "payment_id", "id"], ["timestamp", "время"], ["currency", "вал."], ["amount_minor", "сумма", "n"], ["invoice_refs", "ссылки на счета"]],
    fx: [["fx_id", "fx_id", "id"], ["date", "дата"], ["source_currency", "из"], ["target_currency", "в"], ["rate", "курс"]],
  };
  function load(table) {
    if (state.done) return;
    const t = state.tables[table] || (state.tables[table] = { rows: [], next: null, total: 0, started: false });
    if (t.started && !t.next) return;
    const r = act("list_records", { table, cursor: t.next, limit: 50 });
    stepsLeft(r.obs.remaining_steps);
    if (r.truncated) return finish(r);
    if (r.obs.error) { status(esc(r.obs.error.message)); return; }
    t.started = true; t.rows.push(...r.obs.result.records); t.next = r.obs.result.next_cursor; t.total = r.obs.result.total;
  }
  function setTab(table) { state.tab = table; $$("#pl-work .tab").forEach(b => b.setAttribute("aria-pressed", b.dataset.t === table));
    if (!state.tables[table]) load(table); renderTable(); }
  function cell(r, [k, , kind]) { const v = r[k];
    if (v === null || v === undefined) return '<td class="null">null</td>';
    if (kind === "id") return `<td><button type="button" class="idc" data-id="${esc(v)}">${esc(v)}</button></td>`;
    if (kind === "n") return `<td class="num">${Number(v).toLocaleString("ru-RU")}</td>`;
    if (k === "invoice_refs") return `<td>${v.length ? v.map(x => `<button type="button" class="idc" data-id="${esc(x.invoice_id)}">${esc(x.invoice_id)}</button> · ${x.amount_minor}`).join(", ") : '<span class="null">[]</span>'}</td>`;
    if (k === "line_items") return `<td class="li">${v.map(l => esc(`${l.sku}×${l.qty}${l.service_period ? " " + l.service_period : ""}`)).join("; ")}</td>`;
    return `<td>${esc(v)}</td>`; }
  function renderTable() { const t = state.tables[state.tab]; const c = COLS[state.tab];
    $("#pl-tbl").innerHTML = `<thead><tr>${c.map(x => `<th>${x[1]}</th>`).join("")}</tr></thead><tbody>${(t ? t.rows : []).map((r, i) =>
      `<tr style="--k:${Math.max(0, i - (t.rows.length - 50))}">${c.map(x => cell(r, x)).join("")}</tr>`).join("")}</tbody>`;
    $("#pl-count").textContent = t ? `Показано ${t.rows.length} из ${t.total}` : "";
    $("#pl-more").disabled = !t || !t.next || state.done; }
  $$("#pl-work .tab").forEach(b => b.onclick = () => setTab(b.dataset.t));
  $("#pl-more").onclick = () => { load(state.tab); renderTable(); };
  function stepsLeft(n) { state.steps = n; $("#pl-steps").innerHTML = `Осталось шагов: <b>${n}</b>`; $("#pl-steps").classList.toggle("low", n <= 15); }

  // клик по ID: в доказательства (Shift — в затронутые)
  $("#pl-tbl").addEventListener("click", e => { const b = e.target.closest(".idc"); if (!b || state.done) return;
    const inp = e.shiftKey ? $("#f-aff") : $("#f-ev"); const ids = inp.value.split(",").map(s => s.trim()).filter(Boolean);
    if (!ids.includes(b.dataset.id)) ids.push(b.dataset.id); inp.value = ids.join(", ");
    b.classList.add("picked"); inp.classList.add("flash"); setTimeout(() => inp.classList.remove("flash"), 500); });

  // ---------------------------------------------------------------- выводы
  const list = s => s.split(",").map(x => x.trim()).filter(Boolean);
  $("#pl-form").onsubmit = e => { e.preventDefault(); const err = $("#f-err"); err.textContent = "";
    const aff = list($("#f-aff").value), ev = list($("#f-ev").value), amt = $("#f-amt").value;
    if (!aff.length) { err.textContent = "Укажите хотя бы один затронутый ID: нажмите на ID в таблице с зажатым Shift."; return; }
    if (amt === "" || !/^\d+$/.test(amt)) { err.textContent = "Сумма — целое число в минимальных единицах, например 93049."; return; }
    if (ev.length > 10) { err.textContent = "Доказательств может быть не больше 10."; return; }
    if (state.findings.length >= 30) { err.textContent = "Выводов может быть не больше 30."; return; }
    state.findings.push({ type: $("#f-type").value, affected_ids: aff, claimed_amount_minor: parseInt(amt, 10), currency: $("#f-cur").value,
      evidence_ids: ev, explanation: $("#f-exp").value.slice(0, 1000) });
    ["#f-aff", "#f-ev", "#f-amt", "#f-exp"].forEach(s => $(s).value = ""); renderFindings(); };
  function renderFindings() { const f = state ? state.findings : [];
    $("#pl-n").textContent = f.length ? `· ${f.length}` : "";
    $("#pl-findings").innerHTML = f.length ? f.map((x, i) => `<div class="fd"><div><b>${typeRu[x.type]}</b><span>${esc(x.affected_ids.join(", "))} · ${money(x.claimed_amount_minor, x.currency)}</span></div>
      ${state.done ? "" : `<button type="button" class="x" data-i="${i}" aria-label="Удалить вывод">×</button>`}</div>`).join("")
      : `<p class="empty">Пока пусто. Если книги чистые, отправьте пустой список: на чистой компании это лучший ответ.</p>`;
    $$("#pl-findings .x").forEach(b => b.onclick = () => { state.findings.splice(+b.dataset.i, 1); renderFindings(); }); }

  $("#pl-submit").onclick = () => { if (!state || state.done) return;
    const r = act("submit", { findings: { episode_id: state.m.episode_id, findings: state.findings } }); stepsLeft(r.obs.remaining_steps); finish(r); };

  const WHY = { type: "не тот тип", affected_ids: "не те ID", currency: "не та валюта", amount: "сумма вне допуска", evidence: "не хватает доказательств",
    duplicate_or_already_matched: "повтор вывода", no_issues_in_truth: "в книгах нет ошибок" };
  function finish(r) {
    state.done = true; const { grader, truth } = call("result"); const g = grader.result;
    $("#pl-form").querySelectorAll("input,select,button").forEach(x => x.disabled = true); $("#pl-submit").disabled = true; $("#pl-more").disabled = true;
    renderFindings();
    const verdicts = (g.per_finding || []).map(p => { const f = state.findings[p.finding];
      return `<div class="v"><span class="tag ${p.result === "TP" ? "tp" : "fp"}">${p.result}</span><span>${typeRu[f.type]} · ${esc(f.affected_ids.join(", "))}${p.result === "FP" ? ` — ${WHY[p.closest_failure] || p.closest_failure}` : ""}</span></div>`; }).join("");
    const missed = new Set(g.missed_issue_ids || []);
    const issues = truth.issues.map(i => `<div class="v"><span class="tag ${missed.has(i.issue_id) ? "fn" : "tp"}">${missed.has(i.issue_id) ? "FN" : "✓"}</span><span>${typeRu[i.type]} · ${esc(i.affected_ids.join(", "))} · ${money(i.expected_amount_minor, i.currency)}${i.scenario ? ` · ${i.scenario}` : ""}<br><span class="null">доказательства: ${esc(i.evidence_sets[0].join(", "))}</span></span></div>`).join("")
      || `<p class="empty">Компания была чистой — ошибок не было.</p>`;
    const rew = g.reward;
    $("#pl-result").innerHTML = `<div class="res-head glass"><div><span class="label">${r.truncated ? "Шаги закончились — засчитан пустой ответ" : "Оценщик проверил ваш ответ"}</span>
      <div class="big ${rew < 0 ? "neg" : "pos"}">${rew > 0 ? "+" : ""}${rew.toFixed(3)}</div><span class="label">награда</span></div>
      <div class="meters">${[["Точность", g.precision], ["Полнота", g.recall], ["F1", g.f1], ["Шагов", g.inspection_steps]].map(([k, v]) =>
        `<div><span class="label">${k}</span><div class="n">${typeof v === "number" && k !== "Шагов" ? v.toFixed(2) : v}</div></div>`).join("")}</div>
      <button class="btn" id="pl-again">Новая компания <span class="arr">→</span></button></div>
      <div class="res-cols"><div class="glass"><div class="t">Ваши выводы</div>${verdicts || '<p class="empty">Вы не отправили выводов.</p>'}</div>
      <div class="glass"><div class="t">Что было спрятано</div>${issues}</div></div>`;
    $("#pl-result").hidden = false; $("#pl-again").onclick = () => { $("#pl-seed").value = Math.floor(Math.random() * 999999); $("#pl-gen").click(); };
    $("#pl-result").scrollIntoView({ behavior: UI.reduce ? "auto" : "smooth", block: "start" });
    status("Эпизод завершён. Сравните себя с базовыми политиками ниже.");
  }

  $$(".pl-base-btns .chip").forEach(b => b.onclick = () => { if (!state) return; const name = b.dataset.p; b.disabled = true;
    const out = $("#pl-base-out"); const old = $("#br-" + name); if (old) old.remove(); out.insertAdjacentHTML("beforeend", `<div class="br" id="br-${name}"><b>${b.textContent}</b><span>считаем…</span></div>`);
    setTimeout(() => { const r = call("baseline", name);
      $("#br-" + name).innerHTML = `<b>${b.textContent}</b><span>награда <em class="${r.reward < 0 ? "neg" : "pos"}">${r.reward > 0 ? "+" : ""}${r.reward.toFixed(3)}</em> · F1 ${r.f1.toFixed(2)} · TP ${r.tp} · FP ${r.fp} · FN ${r.fn} · шагов ${r.inspection_steps}</span>`;
      b.disabled = false; }, 30); });

  boot();
})();
