/* FinSpector · помощник Python-редактора: шаблоны кода и понятные объяснения ошибок с подсветкой строки. */
(function () {
  const { $, esc } = UI;
  const ed = $("#lab-code"); if (!ed) return;

  // ---------------------------------------------------------------- шаблоны
  const T = [
    ["Начало", "Создать компанию", `from auditenv.env import AuditEnv

env = AuditEnv(mode="train")
obs, info = env.reset(seed=2026)        # номер компании
m = obs["manifest"]
episode_id = m["episode_id"]
print("Период:", m["period_start"], "—", m["period_end"], "| валюта:", m["base_currency"])
`],
    ["Чтение", "Прочитать таблицу целиком", `def read_all(table):
    """Читает таблицу страницами по 50 строк (1 страница = 1 шаг)."""
    rows, cursor = [], None
    while True:
        args = {"table": table, "limit": 50}
        if cursor:
            args["cursor"] = cursor
        obs, *_ = env.step({"name": "list_records", "args": args})
        rows += obs["result"]["records"]
        cursor = obs["result"]["next_cursor"]
        if not cursor:
            return rows

invoices = read_all("invoices")
payments = read_all("payments")
ledger = read_all("ledger")
`],
    ["Чтение", "Одна запись по ID", `obs, *_ = env.step({"name": "get_record", "args": {"table": "invoices", "id": "INV-XXXXXX"}})
if obs["error"]:
    print("Ошибка:", obs["error"]["message"])
else:
    print(obs["result"]["record"])
`],
    ["Чтение", "Документ целиком", `obs, *_ = env.step({"name": "get_document", "args": {"doc_id": "DOC-XXXXXXXX"}})
print(obs["result"]["doc_type"], obs["result"]["document"])
`],
    ["Расчёты", "Калькулятор среды", `obs, *_ = env.step({"name": "calculator", "args": {"expression": "1250.50 * 0.9210"}})
print("Результат:", obs["result"]["value"])
`],
    ["Расчёты", "Сумма в обычных единицах", `exp = m["currency_exponents"]

def money(minor, currency):
    """Сумма из «копеек» в обычный вид: 125050 → 1 250.50"""
    return f"{minor / 10 ** exp[currency]:,.{exp[currency]}f} {currency}".replace(",", " ")
`],
    ["Расчёты", "Курс валюты на дату", `fx = read_all("fx")
rates = {(r["date"], r["source_currency"], r["target_currency"]): float(r["rate"]) for r in fx}

def convert(minor, currency, date):
    """Пересчёт в валюту учёта по курсу на дату (YYYY-MM-DD)."""
    base = m["base_currency"]
    if currency == base:
        return minor
    rate = rates[(date, currency, base)]
    return round(minor / 10 ** exp[currency] * rate * 10 ** exp[base])
`],
    ["Выводы", "Вывод: дубль счёта", `findings.append({
    "type": "duplicate_invoice",
    "affected_ids": [first["invoice_id"], dup["invoice_id"]],
    "claimed_amount_minor": dup["total_minor"],
    "currency": dup["currency"],
    "evidence_ids": [first["doc_id"], dup["doc_id"], ledger_row_id],
    "explanation": "Тот же клиент, сумма и день",
})
`],
    ["Выводы", "Вывод: неполное разнесение", `findings.append({
    "type": "missing_or_partial_allocation",
    "affected_ids": [payment["payment_id"], invoice_id],
    "claimed_amount_minor": unallocated,          # неразнесённая часть
    "currency": payment["currency"],
    "evidence_ids": [payment["doc_id"], invoice_id, suspense_row_id, ar_row_id],
    "explanation": "Часть оплаты осталась на 2900",
})
`],
    ["Выводы", "Вывод: неверный курс", `findings.append({
    "type": "fx_conversion_error",
    "affected_ids": [invoice["invoice_id"]],
    "claimed_amount_minor": abs(posted - expected),   # разница в валюте учёта
    "currency": m["base_currency"],
    "evidence_ids": [invoice["doc_id"], ledger_row_id, fx_id],
    "explanation": "Пересчёт не по курсу даты документа",
})
`],
    ["Выводы", "Вывод: не тот период", `findings.append({
    "type": "period_cutoff_error",
    "affected_ids": [invoice["invoice_id"]],
    "claimed_amount_minor": invoice["total_minor"],
    "currency": invoice["currency"],
    "evidence_ids": [invoice["doc_id"], ledger_row_id],
    "explanation": "Документ следующего месяца проведён в текущем",
})
`],
    ["Выводы", "Отправить выводы", `submit = {"name": "submit", "args": {"findings": {"episode_id": episode_id, "findings": findings}}}
obs, reward, terminated, truncated, info = env.step(submit)
print(f"Награда: {reward:+.3f}")
print(f'Верно {info["tp"]} · ложно {info["fp"]} · пропущено {info["fn"]} · F1 {info["f1"]:.2f}')
`],
    ["Агент", "Своя политика (класс)", `from auditenv.policies import Policy, submit_action

class MyPolicy(Policy):
    name = "my_policy"

    def begin(self, obs, info):
        super().begin(obs, info)
        self.rows = []

    def act(self, obs):
        res = obs.get("result") or {}
        if "records" in res:
            self.rows += res["records"]
        if not self.rows:
            return {"name": "list_records", "args": {"table": "invoices", "limit": 50}}
        findings = []                      # ваша логика поиска ошибок
        return submit_action(self.episode_id, findings)
`],
    ["Агент", "Прогнать на 5 компаниях", `total = 0
for seed in range(1, 6):
    env = AuditEnv(mode="train", time_limit_s=10**9)
    obs, info = env.reset(seed=seed)
    pol = MyPolicy()
    pol.begin(obs, info)
    while True:
        obs, reward, done, cut, info = env.step(pol.act(obs))
        if done or cut:
            break
    total += reward
    print(f"компания №{seed}: {reward:+.3f}")
print(f"Среднее: {total / 5:+.3f}")
`],
  ];
  const menu = $("#lab-tpl-menu"), btn = $("#lab-tpl"), list = $("#lab-tpl-list"), q = $("#lab-tpl-q"), pv = $("#lab-tpl-pv"), pvT = $("#lab-tpl-name");
  let sel = 0;
  function draw() {
    const s = q.value.trim().toLowerCase(); let g = "", out = "", first = -1;
    T.forEach(([grp, name, code], i) => {
      if (s && !(name + " " + grp + " " + code).toLowerCase().includes(s)) return;
      if (first < 0) first = i;
      if (grp !== g) { out += `<div class="tpl-g">${grp}</div>`; g = grp; }
      out += `<button type="button" role="option" class="tpl-i" data-i="${i}" aria-selected="false">${name}</button>`;
    });
    list.innerHTML = out || `<p class="tpl-tip">Ничего не нашлось.</p>`;
    if (first >= 0) pick(list.querySelector(`[data-i="${sel}"]`) ? sel : first); else { pv.textContent = ""; pvT.textContent = ""; }
  }
  function pick(i) { sel = i; list.querySelectorAll(".tpl-i").forEach(b => b.setAttribute("aria-selected", +b.dataset.i === i)); pvT.textContent = T[i][1]; pv.textContent = T[i][2].replace(/\n$/, ""); }
  let caret = 0;
  function open(on) { if (on) menu.style.top = (menu.parentNode.querySelector(".lab-bar").offsetHeight + 8) + "px"; menu.hidden = !on; btn.setAttribute("aria-expanded", on); if (on) { caret = ed.selectionStart; q.value = ""; draw(); q.focus(); } }
  btn.onclick = () => open(menu.hidden);
  $("#lab-tpl-close").onclick = () => { open(false); btn.focus(); };
  q.oninput = draw;
  menu.addEventListener("keydown", e => {
    if (e.key === "Escape") { open(false); btn.focus(); return; }
    const items = [...list.querySelectorAll(".tpl-i")], k = items.findIndex(b => +b.dataset.i === sel);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); const n = items[Math.max(0, Math.min(items.length - 1, k + (e.key === "ArrowDown" ? 1 : -1)))]; if (n) { pick(+n.dataset.i); n.scrollIntoView({ block: "nearest" }); } }
    if (e.key === "Enter" && (document.activeElement === q || document.activeElement.classList.contains("tpl-i"))) { e.preventDefault(); insert(sel); }
  });
  document.addEventListener("click", e => { if (!menu.hidden && !e.target.closest("#lab-tpl-menu") && !e.target.closest("#lab-tpl")) open(false); });
  list.addEventListener("click", e => { const b = e.target.closest(".tpl-i"); if (b) pick(+b.dataset.i); });
  list.addEventListener("dblclick", e => { const b = e.target.closest(".tpl-i"); if (b) insert(+b.dataset.i); });
  $("#lab-tpl-ins").onclick = () => insert(sel);
  function insert(i) {
    const code = T[i][2], v = ed.value;
    const ls = v.lastIndexOf("\n", caret - 1) + 1, cur = v.slice(ls, caret), ind = (/^ */.exec(cur) || [""])[0];
    const atStart = cur.trim() === "";
    const text = (atStart ? "" : "\n" + ind) + code.replace(/\n(?=.)/g, "\n" + ind).replace(/\n$/, "") + "\n";
    open(false); ed.focus(); ed.setSelectionRange(atStart ? ls + ind.length : caret, caret);
    ed.setRangeText(atStart ? text.replace(/^ */, "") : text, ed.selectionStart, ed.selectionEnd, "end");
    ed.dispatchEvent(new Event("input"));
    toast(`Вставлен шаблон «${T[i][1]}»`);
  }

  // ---------------------------------------------------------------- ошибки: строка + объяснение
  const EXPLAIN = [
    [/^SyntaxError: .*was never closed|^SyntaxError: unexpected EOF/, "Не закрыта скобка или кавычка", "Проверьте, что у каждой ( [ { и кавычки есть пара."],
    [/^SyntaxError: expected ':'/, "Нет двоеточия", "После if, for, while, def и class нужно поставить «:»."],
    [/^SyntaxError: invalid syntax/, "Ошибка в записи кода", "Python не понял строку. Частые причины: пропущена запятая, скобка или кавычка."],
    [/^SyntaxError/, "Ошибка в записи кода", "Проверьте скобки, кавычки, запятые и двоеточия в этой строке."],
    [/^IndentationError: unexpected indent/, "Лишний отступ", "Строка сдвинута вправо без причины. Уберите пробелы в начале."],
    [/^IndentationError: expected an indented block/, "Нужен отступ", "После строки с «:» следующая строка должна быть сдвинута на 4 пробела (клавиша Tab)."],
    [/^IndentationError|^TabError/, "Неровные отступы", "Выровняйте отступы: используйте 4 пробела на уровень (Tab в редакторе)."],
    [/^NameError: name '(.+?)' is not defined/, "Неизвестное имя «$1»", "Переменная или функция ещё не создана. Проверьте написание или вставьте нужный шаблон выше."],
    [/^KeyError: '(.+?)'/, "Нет поля «$1»", "В словаре нет такого ключа. Напечатайте запись через print(), чтобы увидеть доступные поля."],
    [/^KeyError/, "Нет такого ключа", "В словаре нет этого ключа. Напечатайте словарь через print() и проверьте названия."],
    [/^TypeError: 'NoneType' object is not subscriptable/, "Пустой ответ среды", "Скорее всего действие вернуло ошибку и result = None. Проверьте obs[\"error\"]."],
    [/^TypeError/, "Неподходящий тип данных", "Вы смешали, например, текст и число. Используйте int(), float() или str()."],
    [/^IndexError/, "Нет элемента с таким номером", "Список короче, чем вы думали. Проверьте len(список)."],
    [/^AttributeError: '(.+?)' object has no attribute '(.+?)'/, "У «$1» нет «$2»", "Проверьте написание. Для словарей используйте d[\"ключ\"], а не d.ключ."],
    [/^ZeroDivisionError/, "Деление на ноль", "Перед делением проверьте, что делитель не равен нулю."],
    [/^ValueError/, "Неподходящее значение", "Функция получила значение не того вида — например, текст вместо числа."],
    [/^ModuleNotFoundError: No module named '(.+?)'/, "Нет модуля «$1»", "В браузере доступны стандартная библиотека Python и среда auditenv."],
    [/^RuntimeError: call reset\(\) first/, "Среда не запущена", "Сначала вызовите env.reset(seed=...)."],
  ];
  const errLine = $("#lab-errline"), help = $("#lab-help");
  const LH = () => parseFloat(getComputedStyle(ed).lineHeight) || 23;
  let errAt = 0;
  function place() { if (!errAt) return; const top = LAB_LINES.top(errAt) - ed.scrollTop, hh = LAB_LINES.height(errAt);
    errLine.style.transform = `translateY(${top}px)`; errLine.style.height = hh + "px"; errLine.hidden = top < -hh || top > ed.clientHeight; }
  ed.addEventListener("scroll", place);
  function clear() { errAt = 0; errLine.hidden = true; help.hidden = true; $("#lab-gutter").dataset.bad = ""; LAB_LINES.redraw(); }
  function markGutter(n) { $("#lab-gutter").dataset.bad = n || ""; LAB_LINES.redraw(); }
  function goto(n) { const lines = ed.value.split("\n"); let pos = 0; for (let i = 0; i < n - 1; i++) pos += lines[i].length + 1;
    ed.focus(); ed.setSelectionRange(pos, pos + (lines[n - 1] || "").length); ed.scrollTop = Math.max(0, LAB_LINES.top(n) - 16 - 2 * LAB_LINES.height(1)); place(); }
  window.LAB_HELP = {
    report(text) {
      const lines = text.trim().split("\n"), last = lines[lines.length - 1] || "";
      let n = 0; lines.forEach(l => { const mm = /(?:Ваш код|"<exec>")"?, line (\d+)/.exec(l); if (mm) n = +mm[1]; });
      const total = ed.value.split("\n").length; if (n > total) n = 0;
      let title = "Ошибка в коде", tip = "Прочитайте последнюю строку сообщения ниже — там написана причина.";
      for (const [re, t, d] of EXPLAIN) { const mm = re.exec(last); if (mm) { title = t.replace(/\$(\d)/g, (_, k) => mm[k] || ""); tip = d.replace(/\$(\d)/g, (_, k) => mm[k] || ""); break; } }
      errAt = n; markGutter(n); place();
      const src = n ? (ed.value.split("\n")[n - 1] || "").trim() : "";
      help.innerHTML = `<div class="lh-t"><span class="lh-badge">Помощник</span><b>${esc(title)}${n ? ` — строка ${n}` : ""}</b></div>
        ${src ? `<code class="lh-code">${esc(src)}</code>` : ""}<p>${esc(tip)}</p>
        ${n ? `<button type="button" class="chip sm" id="lh-go">Перейти к строке ${n}</button>` : ""}`;
      help.hidden = false; const g = $("#lh-go"); if (g) g.onclick = () => goto(n);
    },
    clear,
  };
  ed.addEventListener("input", () => { if (errAt) clear(); });

  function toast(t) { let el = $("#lab-toast"); if (!el) { el = document.createElement("div"); el.id = "lab-toast"; el.className = "lab-toast"; el.setAttribute("role", "status"); document.body.append(el); }
    el.textContent = t; el.classList.add("on"); clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove("on"), 1800); }
})();
