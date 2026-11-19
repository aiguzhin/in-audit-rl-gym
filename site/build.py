"""Собирает многостраничный сайт из общих шаблонов: python site/build.py"""
from pathlib import Path

ROOT = Path(__file__).parent

PAGES = [
    ("index.html", "00", "Главная"),
    ("episode.html", "01", "Эпизод"),
    ("books.html", "02", "Книги"),
    ("run.html", "03", "Прогон"),
    ("reward.html", "04", "Награда"),
    ("policies.html", "05", "Политики"),
    ("start.html", "06", "Запуск"),
]

HEAD = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Fin-Audit RL Gym</title>
<meta name="description" content="Воспроизводимая RL-среда для ИИ-аудитора: синтетические книги компании, скрытые ошибки, инструменты расследования и честная функция награды.">
<link rel="preload" href="assets/fonts/unbounded-cyrillic-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/style.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='13' fill='none' stroke='%23E0401E' stroke-width='3'/%3E%3Ctext x='16' y='21' font-size='13' text-anchor='middle' font-family='monospace' font-weight='700' fill='%23111110'%3EDr%3C/text%3E%3C/svg%3E">
</head>
<body data-page="{slug}">
<a class="skip" href="#main">К содержанию</a>
<div class="progress"></div>
<header class="top"><div class="wrap">
  <a class="brand" href="index.html"><i>Dr</i>Fin-Audit RL Gym</a>
  <button class="burger" aria-expanded="false" aria-controls="menu">Меню</button>
  <nav class="menu" id="menu" aria-label="Разделы сайта">{nav}</nav>
</div></header>
<main id="main">
"""

FOOT = """</main>
<footer class="bottom">
  <div class="wrap"><span>Fin-Audit RL Gym · кейс 01 FinTech · 2026</span><span>Все компании, люди, счета и деньги вымышлены · MIT</span></div>
  <div class="wrap"><div class="big-foot">Dr = Cr · Dr = Cr · Dr = Cr</div></div>
</footer>
<button class="totop" aria-label="Наверх">↑</button>
<script src="assets/data.js"></script>
<script src="assets/app.js"></script>
{script}
</body>
</html>
"""


def nav(active):
    out = []
    for f, n, name in PAGES[1:]:
        cls = ' class="on" aria-current="page"' if f == active else ""
        out.append(f'<a href="{f}"{cls}><span>{n}</span>{name}</a>')
    return "".join(out)


def head_block(num, crumb, title, intro):
    return f"""<div class="wrap page-head">
  <div class="crumbs"><span class="label"><span class="num">{num}</span> · {crumb}</span><span class="label">Fin-Audit RL Gym</span></div>
  <h1 class="title">{title}</h1>
  <p class="intro" data-r style="--d:3">{intro}</p>
</div>"""


def next_link(f):
    i = [p[0] for p in PAGES].index(f)
    nf, nn, name = PAGES[i + 1] if i + 1 < len(PAGES) else PAGES[1]
    lab = "Дальше" if i + 1 < len(PAGES) else "Сначала"
    return f"""<div class="wrap"><a class="next" href="{nf}"><div><span class="label">{lab} · {nn}</span><div class="t">{name}</div></div><span class="go">→</span></a></div>"""


BODY = {}
SCRIPT = {}

# ------------------------------------------------------------------ главная
BODY["index.html"] = """<div class="wrap hero">
  <div class="ledger3d" aria-hidden="true" id="ledger3d"><div class="book"><div class="shadow"></div><div class="cover"></div><div class="stack l"></div><div class="stack r"></div>
    <div class="pg left" id="bpL"></div><div class="pg right" id="bpR"></div>
    <div class="leaf" style="--d:0s"><div class="pg front" id="bf0"></div><div class="pg back" id="bb0"></div></div>
    <div class="leaf" style="--d:3s"><div class="pg front" id="bf1"></div><div class="pg back" id="bb1"></div></div>
    <div class="leaf" style="--d:6s"><div class="pg front" id="bf2"></div><div class="pg back" id="bb2"></div></div>
    <div class="ribbon"></div></div></div>
  <div class="stamp" aria-hidden="true"><svg viewBox="0 0 200 200"><defs><path id="cp" d="M100,100 m-78,0 a78,78 0 1,1 156,0 a78,78 0 1,1 -156,0"/></defs><circle cx="100" cy="100" r="96" fill="none" stroke="currentColor" stroke-width="3"/><circle cx="100" cy="100" r="60" fill="none" stroke="currentColor" stroke-width="1.5"/><text font-family="JetBrains Mono" font-size="14.5" font-weight="700" letter-spacing="3" fill="currentColor"><textPath href="#cp">ПРОВЕРЕНО · DR = CR · БЕЗ СЕТИ · БЕЗ GPU · </textPath></text></svg><div class="core"><div>20/20<small>ЭПИЗОДОВ</small></div></div></div>
  <div class="crumbs"><span class="label">Среда для обучения с подкреплением · Python 3.11</span><span class="label">Кейс 01 · FinTech · 19–22.11.2026</span></div>
  <h1 id="hero-h"><span class="ln">Найди</span><span class="ln keep"><span class="circ-wrap"><span class="circ">ошибку</span><svg viewBox="0 0 400 140" preserveAspectRatio="none"><path d="M30 78 C 22 30, 150 8, 250 14 C 352 20, 392 52, 382 86 C 370 124, 240 136, 150 130 C 66 124, 14 104, 22 72 C 28 50, 70 34, 112 28"/></svg></span></span><span class="ln">в книгах.</span></h1>
  <div class="hero-grid">
    <div data-r style="--d:6">
      <p class="lede"><b>Готовый тренажёр для ИИ-аудиторов.</b> Генерирует тысячи вымышленных компаний со спрятанными финансовыми ошибками и честно оценивает, нашёл ли агент их с доказательствами. Запускается одной командой, без GPU и платных API.</p>
      <div class="hero-cta"><a class="btn" href="books.html">Посмотреть в деле <span class="arr">→</span></a><a class="btn ghost" href="start.html">Запустить за минуту</a></div>
    </div>
    <div class="stats" id="stats" data-r style="--d:8"></div>
  </div>
</div>
<div class="tape" aria-hidden="true"><div class="tape-track" id="tape"></div></div>
<div class="wrap">
  <section class="sell">
    <div class="sell-head"><span class="label"><span class="accent">●</span> Для кого</span><h2 class="h2 tight" data-r>Кому это нужно</h2></div>
    <div class="aud">
      <div class="a-card" data-r style="--d:0"><span class="ico">ML</span><h3>ML-команды</h3><p>Дообучайте и сравнивайте модели-аудиторов на воспроизводимых эпизодах вместо ручной разметки.</p></div>
      <div class="a-card" data-r style="--d:1"><span class="ico">FT</span><h3>Финтех и банки</h3><p>Проверьте, ловит ли ваш ИИ дубли, курсы и границы периода до того, как он увидит настоящие книги.</p></div>
      <div class="a-card" data-r style="--d:2"><span class="ico">AU</span><h3>Аудиторские компании</h3><p>Безопасная песочница: все данные вымышлены, но устроены как настоящая дебиторская задолженность.</p></div>
      <div class="a-card" data-r style="--d:3"><span class="ico">RS</span><h3>Исследователи</h3><p>Честная награда без обходных путей: атака «пометить всё» получает −1, а молчание на чистых книгах — максимум.</p></div>
    </div>
  </section>
  <section class="sell">
    <div class="sell-head"><span class="label"><span class="accent">●</span> Что вы получаете</span><h2 class="h2 tight" data-r>Почему это работает</h2></div>
    <div class="why">
      <div class="w" data-r><div class="big"><span data-to="200">200</span></div><h3>компаний проверено</h3><p>Независимая сверка по открытым записям нашла ровно те ошибки, что записаны в эталоне. Лишних расхождений нет.</p></div>
      <div class="w" data-r style="--d:1"><div class="big">−1<span class="u">.00</span></div><h3>награда атаки</h3><p>Попытка «пометить всё» проигрывает на всех 20 закрытых эпизодах. Награду не обмануть красивым текстом.</p></div>
      <div class="w" data-r style="--d:2"><div class="big"><span data-to="60">60</span><span class="u">с</span></div><h3>на эпизод максимум</h3><p>2 ядра CPU, 4 ГБ памяти, без сети. Вся проверка из 5 шагов занимает около 10 секунд.</p></div>
    </div>
  </section>
  <section class="sell">
    <div class="sell-head"><span class="label"><span class="accent">●</span> Старт</span><h2 class="h2 tight" data-r>Три шага до первого эпизода</h2></div>
    <ol class="how">
      <li data-r><span class="n">1</span><div><h3>Запустите проверку</h3><p><code>python -m auditenv check</code> — тесты, данные, политики и отчёт.</p></div></li>
      <li data-r style="--d:1"><span class="n">2</span><div><h3>Подключите агента</h3><p><code>env.reset(seed)</code> и <code>env.step(action)</code> — контракт в стиле Gymnasium.</p></div></li>
      <li data-r style="--d:2"><span class="n">3</span><div><h3>Сравните с базой</h3><p>Четыре базовые политики и разбор сбоев уже посчитаны на тех же эпизодах.</p></div></li>
    </ol>
  </section>
  <div class="sell-head"><span class="label"><span class="accent">●</span> Разделы</span><h2 class="h2 tight" data-r>Изучите подробно</h2></div>
  <div class="cards">
    <a class="card" href="episode.html" data-r style="--d:0"><span class="k">01</span><span class="go">→</span><h3>Эпизод</h3><p>Как рождается компания и четыре типа ошибок с ловушками.</p></a>
    <a class="card" href="books.html" data-r style="--d:1"><span class="k">02</span><span class="go">→</span><h3>Книги</h3><p>Настоящие таблицы эпизода и режим оценщика с эталоном.</p></a>
    <a class="card" href="run.html" data-r style="--d:2"><span class="k">03</span><span class="go">→</span><h3>Прогон</h3><p>Политика шаг за шагом и вердикт оценщика по каждому выводу.</p></a>
    <a class="card" href="reward.html" data-r style="--d:0"><span class="k">04</span><span class="go">→</span><h3>Награда</h3><p>Формула, правила против трюков и живой калькулятор.</p></a>
    <a class="card" href="policies.html" data-r style="--d:1"><span class="k">05</span><span class="go">→</span><h3>Политики</h3><p>Четыре базовые политики на 20 закрытых эпизодах.</p></a>
    <a class="card" href="start.html" data-r style="--d:2"><span class="k">06</span><span class="go">→</span><h3>Запуск</h3><p>Одна команда проверки, структура кода и ограничения.</p></a>
  </div>
  <div class="cta-band" data-r>
    <div><span class="label">Попробуйте сейчас</span><h2>Увидьте ошибку раньше,<br>чем её увидит аудитор.</h2></div>
    <div class="cta-actions"><a class="btn big" href="books.html">Посмотреть книги <span class="arr">→</span></a><button class="btn ghost big" id="copycmd">Скопировать команду</button></div>
  </div>
</div>"""
SCRIPT["index.html"] = r"""<script>
(function(){ const {$, $$, esc, evAll, countUp, onView} = UI;
  // заголовок по буквам
  let i = 0;
  $$("#hero-h .ln").forEach(ln => {
    const target = ln.querySelector(".circ") || ln;
    const txt = target.textContent; target.textContent = "";
    [...txt].forEach(c => { const s = document.createElement("span"); s.className = "ch"; s.style.setProperty("--i", i++);
      s.textContent = c === " " ? " " : c; target.append(s); });
  });
  $("#stats").innerHTML = [[D.checks.data, "/20", "эпизодов прошли проверку данных и эталона"], [D.checks.paired, "/20", "парных проверок: seed, ID, порядок"],
    [27, "", "тестов среды, matcher и награды"], [4, "", "типа ошибок и 2 сценария их взаимодействия"]]
    .map(([n, s, t]) => `<div class="stat"><div class="n"><span data-to="${n}">${n}</span><small>${s}</small></div><div class="t">${t}</div></div>`).join("");
  onView($("#stats"), () => $$("#stats [data-to]").forEach(el => countUp(el, +el.dataset.to)));
  const items = D.ledger.slice(0, 40).map(r => { const dr = r.debit_minor > 0;
    return `<span class="tape-item${evAll.has(r.row_id) ? " flag" : ""}"><b>${r.row_id}</b> · ${esc(r.account)} · <span class="${dr ? "dr" : "cr"}">${dr ? "Dr" : "Cr"} ${(dr ? r.debit_minor : r.credit_minor).toLocaleString("ru-RU")}</span></span>`; }).join("");
  $("#tape").innerHTML = items + items;
  // страницы 3D-книги из настоящего журнала
  const L = D.ledger; const acc = a => a.replace(/ - .*/, "").replace("Accounts receivable","AR").replace("Opening balance equity","Opening").replace("unapplied cash","");
  function page(off, title, n, hl){ let h = `<div class="ph">${title}<span>${D.manifest.period_start.slice(0,7)}</span></div>`;
    for (let k = 0; k < 9; k++){ const r = L[(off + k) % L.length]; const v = r.debit_minor || r.credit_minor;
      h += `<div class="rw${evAll.has(r.row_id) && hl ? " hl" : ""}"><span>${r.row_id}</span><span>${esc(acc(r.account)).slice(0, 18)}</span><b>${(r.debit_minor ? "" : "−") + v.toLocaleString("ru-RU")}</b></div>`; }
    return h + `<div style="text-align:right;font:700 7px var(--mono);margin-top:6px;color:var(--ink-3)">стр. ${n}</div>`; }
  const ids = ["bpL","bpR","bf0","bb0","bf1","bb1","bf2","bb2"];
  ids.forEach((id, i) => { const el = document.getElementById(id); if (el) el.innerHTML = page(i * 6, ["Журнал","Проводки","Сверка","Платежи"][i % 4], 41 + i, true); });
  const R = document.getElementById("bpR"); if (R) R.insertAdjacentHTML("beforeend", `<svg class="mark" style="top:44%" viewBox="0 0 200 40" preserveAspectRatio="none"><path d="M8 22C6 8 70 3 120 5c50 2 76 8 72 18-4 12-70 15-118 13C30 34 6 30 10 18c3-7 20-10 36-11"/></svg>`);
  onView($(".why"), () => $$(".why [data-to]").forEach(el => countUp(el, +el.dataset.to, 1400)), .3);
  $("#copycmd").onclick = async () => { const b = $("#copycmd");
    try { await navigator.clipboard.writeText("python -m auditenv check"); b.textContent = "Скопировано ✓"; } catch (e) { b.textContent = "python -m auditenv check"; }
    setTimeout(() => b.textContent = "Скопировать команду", 2200); };
})();
</script>"""

# ------------------------------------------------------------------ эпизод
BODY["episode.html"] = head_block("01", "Эпизод", "Как рождается<br>эпизод",
    "Сначала строится согласованная скрытая история компании, и только потом в неё вносятся ошибки. Поэтому эталон описывает реальное расхождение, а не случайную подозрительную строку.") + """
<div class="wrap">
  <div class="steps4">
    <div class="step4" data-r style="--d:0"><div class="i">01</div><h3>Скрытая история</h3><p>Клиенты, подписки, поставщики, счета прошлого, текущего и следующего месяца, платежи и курсы. Всё выводится из seed.</p></div>
    <div class="step4" data-r style="--d:1"><div class="i">02</div><h3>Чистые проводки</h3><p>Проводки по правилам policy.json. Равенство Dr = Cr проверяется по каждому счёту и платежу ещё до ошибок.</p></div>
    <div class="step4" data-r style="--d:2"><div class="i">03</div><h3>Ошибки с причиной</h3><p>Изменение строк записывается в provenance. Эталон получает тип, ID, сумму, допуск и наборы доказательств.</p></div>
    <div class="step4" data-r style="--d:3"><div class="i">04</div><h3>Отрисовка</h3><p>Публичные ID и порядок зависят только от «соли». Смена ID и перестановка не меняют компанию и ответ.</p></div>
  </div>
  <h2 class="h2" data-r>Четыре типа ошибок</h2>
  <div class="types">
    <div class="type" data-r style="--d:0"><code>duplicate_invoice</code><h3>Дубль счёта</h3><p>Тот же счёт введён и проведён дважды в один день: те же строки, тот же заказ.</p><p class="trap"><b>Ловушка:</b> еженедельные подписки с одинаковой суммой — это не дубли.</p></div>
    <div class="type" data-r style="--d:1"><code>missing_or_partial_allocation</code><h3>Неполное разнесение</h3><p>Платёж ссылается на счёт, но в 1200 ушло меньше, а остаток лёг в 2900.</p><p class="trap"><b>Ловушка:</b> нераспознанные поступления в 2900 законны.</p></div>
    <div class="type" data-r style="--d:0"><code>fx_conversion_error</code><h3>Неверный курс</h3><p>Курс чужой даты или переставленные цифры в курсе при пересчёте в базовую валюту.</p><p class="trap"><b>Ловушка:</b> курсовая разница 7000 при оплате — это норма.</p></div>
    <div class="type" data-r style="--d:1"><code>period_cutoff_error</code><h3>Не тот период</h3><p>Документ следующего месяца проведён в текущем.</p><p class="trap"><b>Ловушка:</b> время в UTC выглядит как текущий период, хотя по поясу компании это уже следующий.</p></div>
  </div>
  <h2 class="h2" data-r>Взаимодействующие сценарии</h2>
  <div class="types">
    <div class="type" data-r><code>partial_payment_wrong_fx</code><h3>Частичная оплата по неверному курсу</h3><p>Валютный платёж разнесён не полностью и проведён по курсу чужой даты. В эталоне две ошибки, и одна мешает увидеть другую.</p></div>
    <div class="type" data-r style="--d:1"><code>cutoff_partial_payment_fx</code><h3>Частичный платёж на границе</h3><p>Валютный платёж первых часов следующего месяца проведён рано и разнесён не до конца.</p></div>
  </div>
</div>"""

# ------------------------------------------------------------------ книги
BODY["books.html"] = head_block("02", "Книги", "Открытые<br>книги",
    "Настоящий dev-эпизод с двумя сценариями взаимодействующих ошибок. Агент видит только эти таблицы. Включите режим оценщика и нажмите на ошибку: её доказательства подсветятся.") + """
<div class="wrap">
  <div class="explorer" id="ex" data-r>
    <div class="ex-main">
      <div class="ex-bar" role="group" aria-label="Таблица">
        <button class="tab" data-t="ledger" aria-pressed="true">Журнал</button>
        <button class="tab" data-t="invoices" aria-pressed="false">Счета</button>
        <button class="tab" data-t="payments" aria-pressed="false">Платежи</button>
        <label class="switch"><input type="checkbox" id="gr"> Режим оценщика</label>
      </div>
      <div class="manifest" id="mf"></div>
      <div class="legend"><span><i class="l-ev"></i>● строка-доказательство из эталона</span><span><i class="l-fo"></i>строки выбранной ошибки</span></div>
      <div class="tbl-wrap"><table class="grid" id="tbl"></table></div>
    </div>
    <aside class="ex-side" aria-label="Эталон"><span class="label">Эталон · truth.json</span><div id="side" aria-live="polite"></div></aside>
  </div>
</div>"""
SCRIPT["books.html"] = r"""<script>
(function(){ const {$, $$, esc, money, typeRu, evAll} = UI; const m = D.manifest;
  $("#mf").innerHTML = `<span>эпизод <b>${m.episode_id}</b></span><span>период <b>${m.period_start} — ${m.period_end}</b></span><span>пояс <b>${m.timezone}</b></span><span>база <b>${m.base_currency}</b></span><span>проводок <b>${m.counts.ledger}</b></span><span>документов <b>${m.counts.documents}</b></span>`;
  let tab = "ledger", focus = null;
  const cols = {
    ledger: [["row_id","row_id"],["timestamp","время"],["account","счёт"],["debit_minor","дебет, мин.",1],["credit_minor","кредит, мин.",1],["invoice_id","invoice_id"],["payment_id","payment_id"]],
    invoices: [["doc_id","doc_id"],["invoice_id","invoice_id"],["issued_at","issued_at"],["currency","вал."],["total_minor","сумма, мин.",1],["entity_id","контрагент"]],
    payments: [["doc_id","doc_id"],["payment_id","payment_id"],["timestamp","время (UTC)"],["currency","вал."],["amount_minor","сумма, мин.",1],["invoice_refs","invoice_refs"]]};
  function cell(r, k, num){ const v = r[k];
    if (v === null || v === undefined) return `<td class="null">null</td>`;
    if (k === "invoice_refs") return `<td>${v.length ? v.map(x => esc(x.invoice_id) + " · " + x.amount_minor).join(", ") : '<span class="null">[]</span>'}</td>`;
    if (num) return `<td class="num">${v === 0 ? '<span class="null">0</span>' : Number(v).toLocaleString("ru-RU")}</td>`;
    return `<td>${esc(v)}</td>`; }
  function renderTable(){ const rows = D[tab], c = cols[tab];
    const fs = focus ? new Set(focus.evidence_sets.flat().concat(focus.affected_ids)) : null;
    $("#tbl").innerHTML = `<thead><tr>${c.map(x => `<th>${x[1]}</th>`).join("")}</tr></thead><tbody>` + rows.map((r, n) => {
      const k = r.row_id || r.doc_id; const ev = evAll.has(k) ? "ev" : "";
      const fo = fs && (fs.has(k) || (tab !== "ledger" && (fs.has(r.invoice_id) || fs.has(r.payment_id)))) ? " focus" : "";
      const cells = c.map(x => cell(r, x[0], x[2])); if (ev && $("#gr").checked) cells[0] = cells[0].replace("<td>", '<td><span class="evmark" aria-hidden="true">●</span><span class="sr">Доказательство: </span>');
      return `<tr class="${ev}${fo}" style="--k:${Math.min(n, 30)}">${cells.join("")}</tr>`; }).join("") + "</tbody>"; }
  function renderSide(){
    if (!$("#gr").checked){ $("#side").innerHTML = `<div class="locked"><b>Эталон закрыт</b>В закрытом прогоне агент его не видит: ни в наблюдениях, ни в путях, ни в ошибках. Включите режим оценщика, чтобы посмотреть, что спрятано в этих книгах.</div>`; return; }
    $("#side").innerHTML = `<div class="issues">` + D.truth.map((i, n) => `<button class="issue${focus === i ? " on" : ""}" data-n="${n}" style="--k:${n}">
      <div class="k">${typeRu[i.type]}</div><div class="s">${i.scenario ? "сценарий: " + i.scenario : "одиночная ошибка"} · ${i.affected_ids.join(", ")}</div>
      <div class="a">${money(i.expected_amount_minor, i.currency)}${i.tolerance_minor ? ` <span class="null">± ${i.tolerance_minor}</span>` : ""}</div></button>`).join("") + `</div>`;
    $$(".issue").forEach(b => b.onclick = () => { const i = D.truth[+b.dataset.n]; focus = focus === i ? null : i; renderSide(); renderTable();
      const f = $("tr.focus"); if (f) { const w = $(".tbl-wrap"); w.scrollTo({top: f.offsetTop - w.clientHeight / 3, behavior: "smooth"}); } }); }
  $$(".tab").forEach(b => b.onclick = () => { $$(".tab").forEach(x => x.setAttribute("aria-pressed", x === b)); tab = b.dataset.t; renderTable(); });
  $("#gr").onchange = () => { $("#ex").classList.toggle("grader", $("#gr").checked); if (!$("#gr").checked) focus = null; renderSide(); renderTable(); };
  renderTable(); renderSide();
})();
</script>"""

# ------------------------------------------------------------------ прогон
BODY["run.html"] = head_block("03", "Прогон", "Прогон<br>политики",
    "Простой алгоритм сверки на том же эпизоде читает таблицы страницами по 50 строк и отправляет выводы. Курсы и часовой пояс он не учитывает, и оценщик это видит.") + """
<div class="wrap">
  <div class="replay" id="replay" data-r>
    <div class="rp-log">
      <div class="rp-ctl"><button class="btn" id="play">▶ Запустить прогон</button><button class="btn ghost" id="reset">Сбросить</button></div>
      <div class="rp-lines" id="lines"></div>
    </div>
    <div class="rp-res" id="res" aria-live="polite"></div>
  </div>
</div>"""
SCRIPT["run.html"] = r"""<script>
(function(){ const {$, esc, typeRu, countUp, onView} = UI; let timer = null;
  const key = f => f.type + "|" + [...f.affected_ids].sort().join(",");
  function verdicts(){ const R = D.run.result; const tk = new Map(D.truth.map(i => [key(i), i])); const used = new Set();
    const lines = D.run.findings.map((f, n) => { const t = tk.get(key(f));
      const ok = t && !used.has(key(f)) && Math.abs(f.claimed_amount_minor - t.expected_amount_minor) <= t.tolerance_minor
        && f.currency === t.currency && t.evidence_sets.some(s => s.every(x => f.evidence_ids.includes(x)));
      if (ok) used.add(key(f));
      return `<div class="v" style="--k:${n}"><span class="tag ${ok ? "tp" : "fp"}">${ok ? "TP" : "FP"}</span><span>${typeRu[f.type]} · ${f.affected_ids.join(", ")}</span></div>`; });
    D.truth.forEach(i => { if (!used.has(key(i))) lines.push(`<div class="v" style="--k:${lines.length}"><span class="tag fn">FN</span><span>${typeRu[i.type]} · ${i.affected_ids.join(", ")}${i.scenario ? " · " + i.scenario : ""}</span></div>`); });
    $("#res").innerHTML = `<span class="label">Вердикт оценщика · matcher.py</span><div class="verdicts">${lines.join("")}</div>
      <div class="meters">${[["P", R.precision], ["R", R.recall], ["F1", R.f1], ["Награда", R.reward]].map(([l, v]) =>
        `<div><span class="label">${l}</span><div class="n" data-v="${v}" style="${l === "Награда" ? `color:${v < 0 ? "var(--pen)" : "var(--ok)"}` : ""}">0</div></div>`).join("")}</div>`;
    document.querySelectorAll(".meters [data-v]").forEach(el => countUp(el, +el.dataset.v, 900, el.dataset.v.length > 6 ? 3 : 2)); }
  function resetRun(){ clearInterval(timer); timer = null; $("#play").textContent = "▶ Запустить прогон";
    $("#lines").innerHTML = D.run.steps.map(s => { const a = s.action === "reset" ? "reset → manifest, policy, 100 шагов" :
      s.action === "submit" ? `<span class="sub">submit → ${D.run.findings.length} вывода</span>` :
      `${s.action}(${esc(Object.entries(s.args).map(([k, v]) => k + "=" + JSON.stringify(v)).join(", "))})`;
      return `<div><span class="sn">${String(s.step).padStart(3, "0")}</span>${a}</div>`; }).join("");
    $("#res").innerHTML = `<div class="placeholder">Итог оценщика<br>появится после submit</div>`; }
  $("#play").onclick = () => { if (timer) return; resetRun(); $("#play").textContent = "Идёт прогон…";
    const ds = [...$("#lines").children]; let i = 0; const box = $("#lines");
    timer = setInterval(() => { if (i < ds.length) { ds.forEach(d => d.classList.remove("cur")); ds[i].classList.add("in", "cur");
        box.scrollTo({top: ds[i].offsetTop - box.clientHeight + 40, behavior: "smooth"}); i++; }
      else { clearInterval(timer); timer = null; $("#play").textContent = "▶ Запустить снова"; verdicts(); } }, 150); };
  $("#reset").onclick = resetRun; resetRun();
  onView($("#replay"), () => setTimeout(() => $("#play").click(), 500), .4);
})();
</script>"""

# ------------------------------------------------------------------ награда
BODY["reward.html"] = head_block("04", "Награда", "Награда, которую<br>не обмануть",
    "Награда зависит только от полей и доказательств, текст объяснения на неё не влияет. Сопоставление взаимно однозначное, повтор вывода считается ложным срабатыванием.") + """
<div class="wrap reward">
  <div>
    <div class="formula" data-r>R = clip(2·<em>F1</em> − 1 − 0.002·<em>шаги</em>, −1, 1)<br>F1 = 2TP / (2TP + FP + FN)</div>
    <ul class="rules" data-r style="--d:1">
      <li>Полный верный ответ с доказательствами лучше молчания на ошибочных книгах.</li>
      <li>Молчание на чистых книгах лучше ложного обвинения.</li>
      <li>Повтор вывода не даёт выгоды: второй такой же вывод — FP.</li>
      <li>«Пометить всё» получает −1 на всех 20 закрытых эпизодах.</li>
      <li>Экономия шагов лишь немного различает равные ответы: 50 шагов стоят 0.1.</li>
      <li>TP требует тип, ID, валюту, сумму в допуске и полный набор доказательств.</li>
      <li>Неверная структура ответа даёт −1 и запись в журнал оценщика.</li>
    </ul>
  </div>
  <div class="calc" data-r style="--d:2">
    <span class="label">Калькулятор награды</span>
    <div class="row"><label for="tp">TP · верные</label><input type="range" id="tp" min="0" max="12" value="5"><b id="tpv"></b></div>
    <div class="row"><label for="fp">FP · ложные</label><input type="range" id="fp" min="0" max="30" value="2"><b id="fpv"></b></div>
    <div class="row"><label for="fn">FN · пропуски</label><input type="range" id="fn" min="0" max="12" value="2"><b id="fnv"></b></div>
    <div class="row"><label for="st">Шаги</label><input type="range" id="st" min="0" max="99" value="30"><b id="stv"></b></div>
    <div class="out"><div><span class="label">F1</span><div class="n" id="f1o"></div></div><div><span class="label">Награда</span><div class="n" id="ro" aria-live="polite"></div></div></div>
    <div class="scale"><div class="zero"></div><div class="mark" id="mk"></div><span style="left:0">−1</span><span style="left:calc(50% - 4px)">0</span><span style="right:0">+1</span></div>
    <div class="presets">
      <button class="chip" data-p="6,0,0,25">Идеальный аудит</button>
      <button class="chip" data-p="0,0,6,5">Молчание</button>
      <button class="chip" data-p="0,30,6,2">Пометить всё</button>
      <button class="chip" data-p="0,0,0,40">Чистые книги</button>
    </div>
  </div>
</div>"""
SCRIPT["reward.html"] = r"""<script>
(function(){ const {$, $$} = UI; const ids = ["tp", "fp", "fn", "st"];
  function calc(){ const [tp, fp, fn, st] = ids.map(k => +$("#" + k).value); ids.forEach(k => $("#" + k + "v").textContent = $("#" + k).value);
    const f1 = (tp + fn === 0) ? (fp === 0 ? 1 : 0) : 2 * tp / (2 * tp + fp + fn);
    const r = Math.max(-1, Math.min(1, 2 * f1 - 1 - .002 * st));
    $("#f1o").textContent = f1.toFixed(3); $("#ro").textContent = (r > 0 ? "+" : "") + r.toFixed(3);
    $("#ro").style.color = r < 0 ? "var(--pen)" : "var(--ok)"; $("#mk").style.left = `${(r + 1) / 2 * 100}%`; }
  ids.forEach(k => $("#" + k).oninput = calc);
  $$(".chip").forEach(c => c.onclick = () => { c.dataset.p.split(",").forEach((v, i) => $("#" + ids[i]).value = v); calc(); });
  calc();
})();
</script>"""

# ------------------------------------------------------------------ политики
BODY["policies.html"] = head_block("05", "Политики", "Четыре базовые<br>политики",
    "Одни и те же 20 эпизодов закрытой структуры: 5 чистых, 5 с взаимодействующими ошибками и 10 обычных. Политики работают через отдельный процесс, а эталон остаётся у оценщика.") + """
<div class="wrap">
  <div class="bars" id="bars" data-r></div>
  <h2 class="h2" data-r>Измеренный разбор сбоев</h2>
  <div class="miss" id="missbox" data-r>
    <div><span class="label">Что пропускает простой алгоритм</span><div id="missed"></div></div>
    <div><span class="label">Почему его выводы становятся FP</span><div id="fps"></div></div>
  </div>
</div>"""
SCRIPT["policies.html"] = r"""<script>
(function(){ const {$, $$, esc, onView, countUp} = UI;
  const names = {random_explorer: ["Случайный исследователь", "фиксированный seed"], simple_reconciler: ["Простой алгоритм", "читает всё, сверяет в лоб"],
    flag_all: ["«Пометить всё»", "атака: 30 выводов наугад"], oracle: ["Oracle", "только у оценщика"]};
  $("#bars").innerHTML = Object.entries(D.baselines).map(([k, v]) => `<div class="bar-row" data-rw="${v.reward}">
    <div class="nm">${names[k][0]}<small>${names[k][1]}</small></div>
    <div class="track"><div class="mid"></div><div class="fill${v.reward < 0 ? " neg" : ""}"></div></div>
    <div class="val"><span data-v="${v.reward}">0.00</span></div>
    <div class="det">F1 ${v.f1.toFixed(2)} · P ${v.precision.toFixed(2)} · R ${v.recall.toFixed(2)} · шагов ${v.inspection_steps} · ${v.episodes} эпизодов</div></div>`).join("");
  onView($("#bars"), () => $$(".bar-row").forEach(row => { const r = +row.dataset.rw, f = row.querySelector(".fill");
    f.style.left = (r < 0 ? 50 + r * 50 : 50) + "%"; f.style.width = Math.abs(r) * 50 + "%";
    const el = row.querySelector("[data-v]"); const to = +el.dataset.v; const t0 = performance.now();
    (function step(t){ const p = Math.min(1, (t - t0) / 1200), e = 1 - Math.pow(1 - p, 3), x = to * e; el.textContent = (x > 0 ? "+" : "") + x.toFixed(2);
      if (p < 1) requestAnimationFrame(step); })(t0); }), .3);
  function list(el, obj){ const mx = Math.max(...Object.values(obj));
    $(el).innerHTML = Object.entries(obj).map(([k, v]) => `<div class="m"><span>${esc(k)}<i data-w="${v / mx * 100}"></i></span><b>${v}</b></div>`).join(""); }
  list("#missed", D.failure.missed_by_type); list("#fps", D.failure.false_positive_reasons);
  onView($("#missbox"), () => $$("#missbox i").forEach((i, n) => setTimeout(() => i.style.width = i.dataset.w + "%", n * 60)), .2);
})();
</script>"""

# ------------------------------------------------------------------ запуск
BODY["start.html"] = head_block("06", "Запуск", "Одна<br>команда",
    "Тесты, проверка данных и эталона, базовые политики, парные проверки и разбор сбоев запускаются одной командой. Без сети, платных API и GPU.") + """
<div class="wrap run">
  <pre class="code" data-r><button class="copy" id="cp">Копировать команду</button><span class="c"># локально, Python 3.11, зависимостей нет</span>
<span class="p">$ </span>python -m auditenv check

<span class="c"># в контейнере, без сети</span>
<span class="p">$ </span>docker build -t fin-audit-rl .
<span class="p">$ </span>docker run --rm --network none fin-audit-rl

<span class="c"># 10 train + 10 dev эпизодов и траектории</span>
<span class="p">$ </span>python -m auditenv export

<span class="c"># показ эпизода со скриптовой политикой</span>
<span class="p">$ </span>python -m auditenv demo</pre>
  <div class="files" data-r style="--d:1">
    <div><b>auditenv/generator.py</b><span>история → проводки → ошибки → отрисовка</span></div>
    <div><b>auditenv/env.py</b><span>reset / step, 100 шагов, 60 секунд</span></div>
    <div><b>auditenv/matcher.py</b><span>нормализация, допуски, паросочетание, награда</span></div>
    <div><b>auditenv/reference.py</b><span>независимая сверка по открытым записям</span></div>
    <div><b>auditenv/server.py</b><span>изолированный процесс оценщика</span></div>
    <div><b>auditenv/policies.py</b><span>четыре адаптера базовых политик</span></div>
    <div><b>tests/test_all.py</b><span>27 тестов среды, matcher и награды</span></div>
    <div><b>episodes/ · trajectories/</b><span>открытые эпизоды и траектории</span></div>
  </div>
</div>
<div class="wrap">
  <h2 class="h2" data-r>Честные ограничения</h2>
  <div class="limits">
    <div data-r><b>Упрощённая модель</b>Только дебиторская задолженность, один период, книги в базовой валюте.</div>
    <div data-r style="--d:1"><b>Не реальный аудит</b>Высокая награда не доказывает пригодность для реального аудита.</div>
    <div data-r><b>Открытый генератор</b>Закрытая проверка обязана использовать секретные seed и соль, иначе seed можно перебрать.</div>
    <div data-r style="--d:1"><b>Без обучения весов</b>Модель не обучалась, улучшение модели не заявляется.</div>
  </div>
</div>"""
SCRIPT["start.html"] = r"""<script>
(function(){ const {$} = UI;
  $("#cp").onclick = async () => { try { await navigator.clipboard.writeText("python -m auditenv check"); $("#cp").textContent = "Скопировано"; }
    catch (e) { $("#cp").textContent = "Не удалось"; } setTimeout(() => $("#cp").textContent = "Копировать команду", 1600); };
})();
</script>"""


for f, num, name in PAGES:
    title = "Главная" if f == "index.html" else name
    html = HEAD.format(title=title, slug=f[:-5], nav=nav(f)) + BODY[f]
    if f != "index.html" or True:
        html += "\n" + next_link(f)
    html += FOOT.format(script=SCRIPT.get(f, ""))
    (ROOT / f).write_text(html, encoding="utf-8")
print("built", len(PAGES), "pages")
