"""Собирает многостраничный сайт: python site/build.py
Стиль: тёмно-синие светящиеся панели, стекло, тонкая сетка, Inter Tight.
Внутренние страницы берут разметку и скрипты из pages.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
PARTS = json.loads((ROOT / "pages.json").read_text(encoding="utf-8"))
INNER, SCRIPT = PARTS["inner"], PARTS["scripts"]

PAGES = [
    ("index.html", "00", "Главная"),
    ("episode.html", "01", "Эпизод"),
    ("books.html", "02", "Книги"),
    ("run.html", "03", "Прогон"),
    ("reward.html", "04", "Награда"),
    ("policies.html", "05", "Политики"),
    ("start.html", "06", "Запуск"),
]

LOGO = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">'
        '<path d="M12 2v6M12 16v6M2 12h6M16 12h6M5 5l3.5 3.5M15.5 15.5 19 19"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/></svg>')

HEAD = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Fin-Audit RL Gym</title>
<meta name="description" content="Среда, в которой ИИ учится находить ошибки в финансовых книгах: вымышленные компании, скрытые расхождения и честная награда.">
<meta name="theme-color" content="#0A2246">
<link rel="preload" href="assets/fonts/inter-tight-cyrillic-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/style.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%2304070D'/%3E%3Cpath d='M16 5v8M16 19v8M5 16h8M19 16h8' stroke='%23A9CBFF' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E">
</head>
<body data-page="{slug}">
<a class="skip" href="#main">К содержанию</a>
<div class="progress"></div>
<header class="top"><div class="bar">
  <a class="brand" href="index.html">{logo}Fin-Audit</a>
  <button class="burger" aria-expanded="false" aria-controls="menu">Меню</button>
  <nav class="menu" id="menu" aria-label="Разделы сайта">{nav}</nav>
</div></header>
<main id="main">
"""

FOOT = """</main>
<footer class="bottom"><div class="wrap"><span>Fin-Audit RL Gym · кейс 01 FinTech · 2026</span><span>Все компании, люди и деньги вымышлены · MIT</span></div></footer>
<button class="totop" aria-label="Наверх">↑</button>
<script src="assets/data.js"></script>
<script src="assets/app.js"></script>
{script}
</body>
</html>
"""


def nav(active):
    out = []
    for f, _, name in PAGES[1:]:
        cur = ' class="on" aria-current="page"' if f == active else ""
        out.append(f'<a href="{f}"{cur}>{name}</a>')
    return "".join(out)


def grid(vs=(), hs=(), nodes=()):
    h = '<div class="grid-lines" aria-hidden="true">'
    h += "".join(f'<i class="v" style="left:{x}%"></i>' for x in vs)
    h += "".join(f'<i class="h" style="top:{y}%"></i>' for y in hs)
    h += "".join(f'<b style="left:{x}%;top:{y}%"></b>' for x, y in nodes)
    return h + "</div>"


def next_panel(f):
    i = [p[0] for p in PAGES].index(f)
    nf, _, name = PAGES[i + 1] if i + 1 < len(PAGES) else PAGES[1]
    lab = "Следующий раздел" if i + 1 < len(PAGES) else "Вернуться к началу"
    return (f'<section class="panel"><div class="wrap"><a class="next" href="{nf}"><div><span class="label">{lab}</span>'
            f'<div class="t">{name}</div></div><span class="go">→</span></a></div></section>\n')


def inner_page(f):
    p = INNER[f]
    rest = p["rest"].replace('<div class="calc" data-r', '<div class="calc glass" data-r')
    return f"""<section class="panel">
  {grid((22, 78), (78,), ((22, 78), (78, 78)))}<div class="stars" style="opacity:.5"></div>
  <div class="wrap page-head">
    <div class="crumbs"><span class="label"><span class="num">{p["num"]}</span> · {p["crumb"]}</span><span class="label">Fin-Audit RL Gym</span></div>
    <h1 class="title">{p["title"]}</h1>
    <p class="intro" data-r style="--d:3">{p["intro"]}</p>
  </div>
</section>
<section class="panel"><div class="content">{rest}</div></section>
"""


BOOK = """<div class="book-stage" aria-hidden="true"><div class="book-glow"></div><div class="book-float"><div class="book3">
      <div class="cover"></div><div class="block l"></div><div class="block r"></div>
      <div class="pg left" id="bpL"></div><div class="pg right" id="bpR"></div>
      <div class="leaf" style="--d:0s"><div class="pg front" id="bf0"></div><div class="pg back" id="bb0"></div><div class="shade"></div></div>
      <div class="leaf" style="--d:5s"><div class="pg front" id="bf1"></div><div class="pg back" id="bb1"></div><div class="shade"></div></div>
      <div class="ribbon"></div>
    </div></div></div>"""

RINGS = "".join(f'<ellipse cx="60" cy="120" rx="{18 + i * 14}" ry="{8 + i * 7}" transform="rotate(-{20 + i * 6} 60 120)"/>' for i in range(7))

INDEX = f"""<section class="panel hero">
  <div class="stars"></div>{grid((30, 70), (), ())}
  <div class="wrap">
    <div class="giant" aria-hidden="true">Fin-Audit</div>
    <div class="hero-stage">
      <div class="hero-left" data-r style="--d:6">
        <h1 class="sr">Fin-Audit RL Gym — среда для обучения ИИ-аудиторов</h1>
        <p>Среда, в которой ИИ учится находить ошибки в финансовых книгах. Вымышленные компании, спрятанные расхождения и честная проверка каждого вывода.</p>
        <a class="btn" href="books.html">Начать <span class="arr">→</span></a>
      </div>
      {BOOK}
      <div class="hero-right">
        <div class="anno" data-r style="--d:9">
          <svg class="leader" viewBox="0 0 120 120"><path d="M118 2H64L6 40v40"/></svg>
          <div class="big">20/20<small>эпизодов</small></div>
          <div class="row">Проверено без сети</div>
        </div>
        <div class="glass mini" data-r style="--d:11">
          <div class="t">Сверка</div>
          <div class="row"><span>1200 Дебиторка</span><b>93 049</b></div>
          <div class="row"><span>4000 Выручка</span><b>93 049</b></div>
          <div class="row err"><span>Дубль счёта</span><b>+93 049</b></div>
          <div class="foot">1 расхождение<small>найдено с доказательствами</small></div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="panel sec">
  {grid((27, 73), (14, 88), ((27, 14), (73, 14), (27, 88), (73, 88)))}
  <div class="wrap">
    <p class="statement" data-r>Компания на месяц. <span class="d">Сотни проводок.</span> Несколько <span class="d">тихих</span> ошибок.</p>
    <p class="center-sub" data-r style="--d:1">Агент читает журнал, счета и платежи, сверяет курсы и даты и отправляет выводы с доказательствами. Среда отвечает, насколько он прав.</p>
    <div class="side-row">
      <div class="glass feature" data-r>
        <div class="ico" aria-hidden="true"><svg viewBox="0 0 200 140" style="position:absolute;inset:0;width:100%;height:100%"><g fill="none" stroke="#A9CBFF" stroke-opacity=".7">{RINGS}</g></svg></div>
        <h3>Четыре типа ошибок</h3><p>И два сценария, где одна ошибка прячет другую.</p>
      </div>
      <div class="types-mini">
        <div class="tm" data-r style="--d:1"><span class="k">01</span><h4>Дубль счёта</h4></div>
        <div class="tm" data-r style="--d:2"><span class="k">02</span><h4>Неполное разнесение</h4></div>
        <div class="tm" data-r style="--d:3"><span class="k">03</span><h4>Неверный курс</h4></div>
        <div class="tm" data-r style="--d:4"><span class="k">04</span><h4>Не тот период</h4></div>
      </div>
      <div class="right-note" data-r style="--d:3">
        <p>Рядом с ошибками — честные ловушки: подписки, возвраты, платежи в полночь.</p>
        <a class="btn ghost" href="episode.html"><span class="dot"></span>Как устроен эпизод</a>
      </div>
    </div>
  </div>
</section>

<section class="panel blue">
  {grid((60,), (72,), ((60, 72),))}
  <div class="wrap blue-hero">
    <div class="glass perf" id="perf" data-r>
      <div class="t">Базовые политики</div>
      <svg viewBox="0 0 300 110" aria-hidden="true"><path class="l" d="M6 96 C 50 92, 70 70, 100 76 S 150 98, 180 86 S 240 30, 294 10"/></svg>
      <div class="rows" id="perf-rows"></div>
    </div>
    <div>
      <h2 class="grad" data-r>Награда,<br>которую<br>не обмануть</h2>
      <p data-r style="--d:1">Считаются только тип, сумма, валюта и доказательства. Атака «пометить всё» получает −1, а повтор вывода ничего не даёт.</p>
      <a class="btn" href="reward.html" data-r style="--d:2">Открыть калькулятор <span class="arr">→</span></a>
    </div>
  </div>
</section>

<section class="panel final">
  <div class="stars"></div>{grid((22, 76), (30, 74), ((22, 30), (76, 30), (22, 74), (76, 74)))}
  <div class="wrap">
    <p class="statement" data-r>Вся проверка — <span class="d">одна команда,</span> десять секунд <span class="d">и ноль облака.</span></p>
    <div class="pills" data-r style="--d:1"><span class="chip-dot">Python 3.11 · 2 CPU · 4 ГБ</span><span class="chip-dot">Без сети и GPU</span></div>
    <div class="cta" data-r style="--d:2"><span class="cmd">python -m auditenv check<button id="copycmd">Скопировать</button></span></div>
    <p class="center-sub" data-r style="--d:3">27 тестов, 20 эпизодов, четыре базовые политики и разбор сбоев в одном отчёте.</p>
    <div class="cta" data-r style="--d:4"><a class="btn" href="start.html">Как запустить <span class="arr">→</span></a></div>
  </div>
</section>
"""

INDEX_SCRIPT = r"""<script>
(function(){ const {$, esc, onView} = UI;
  const L = D.ledger;
  const short = a => a.replace(/ - .*/, "").replace("Accounts receivable", "Дебиторка").replace("Revenue", "Выручка").replace("Cash", "Касса")
    .replace("Suspense", "Невыясн.").replace("Opening balance equity", "Остаток").replace("FX gain/loss", "Курс. разн.").replace(/^\d+ /, "");
  function page(off, title, n){ let h = `<div class="ph"><span>${title}</span><span>${D.manifest.period_start.slice(0, 7)}</span></div>`;
    for (let k = 0; k < 8; k++){ const r = L[(off + k) % L.length]; const v = r.debit_minor || r.credit_minor;
      h += `<div class="hw"><span>${esc(short(r.account))}</span><b>${(r.debit_minor ? "" : "−") + v.toLocaleString("ru-RU")}</b></div>`; }
    return h + `<div class="light"></div><div class="pgn">${n}</div>`; }
  [["bpL","Журнал"],["bpR","Сверка"],["bf0","Счета"],["bb0","Платежи"],["bf1","Курсы"],["bb1","Итоги"]].forEach(([id, t], i) => {
    const el = document.getElementById(id); if (el) el.innerHTML = page(i * 7 + 3, t, 41 + i); });
  $("#bpR").insertAdjacentHTML("beforeend", `<svg class="pen" style="top:47%" viewBox="0 0 200 50" preserveAspectRatio="none"><path d="M10 28C6 10 70 4 120 6c52 2 76 10 72 22-4 14-74 18-120 15C30 41 6 34 12 22c4-8 22-12 40-13"/></svg>`);
  const B = D.baselines, names = {oracle: "Oracle", simple_reconciler: "Простая сверка", random_explorer: "Случайный поиск", flag_all: "«Пометить всё»"};
  $("#perf-rows").innerHTML = ["oracle", "simple_reconciler", "random_explorer", "flag_all"].map(k =>
    `<div class="r"><span>${names[k]}</span><b class="${B[k].reward < 0 ? "neg" : "pos"}">${(B[k].reward > 0 ? "+" : "") + B[k].reward.toFixed(2)}</b></div>`).join("");
  onView($("#perf"), () => $("#perf").classList.add("seen"), .3);
  $("#copycmd").onclick = async () => { const b = $("#copycmd");
    try { await navigator.clipboard.writeText("python -m auditenv check"); b.textContent = "Скопировано"; } catch (e) { b.textContent = "Выделите вручную"; }
    setTimeout(() => b.textContent = "Скопировать", 2000); };
})();
</script>"""

for f, num, name in PAGES:
    title = "Среда для ИИ-аудиторов" if f == "index.html" else name
    body = INDEX if f == "index.html" else inner_page(f)
    script = INDEX_SCRIPT if f == "index.html" else SCRIPT.get(f, "")
    html = HEAD.format(title=title, slug=f[:-5], nav=nav(f), logo=LOGO) + body + next_panel(f) + FOOT.format(script=script)
    (ROOT / f).write_text(html, encoding="utf-8")
print("built", len(PAGES), "pages")
