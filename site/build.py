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
    ("play.html", "01", "Песочница"),
    ("leaders.html", "02", "Лидеры"),
    ("episode.html", "03", "Как устроено"),
    ("reward.html", "04", "Награда"),
    ("start.html", "05", "Для жюри"),
    ("books.html", "06", "Книги эпизода"),
    ("run.html", "07", "Прогон политики"),
    ("policies.html", "08", "Базовые политики"),
    ("profile.html", "09", "Профиль"),
]
NAV = ["play.html", "leaders.html", "episode.html", "reward.html", "start.html"]
NEXT = {"index.html": "play.html", "play.html": "leaders.html", "leaders.html": "episode.html", "episode.html": "reward.html",
        "reward.html": "start.html", "start.html": "play.html", "books.html": "run.html", "run.html": "policies.html",
        "policies.html": "start.html", "profile.html": "play.html"}

LOGO = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">'
        '<path d="M12 2v6M12 16v6M2 12h6M16 12h6M5 5l3.5 3.5M15.5 15.5 19 19"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/></svg>')

HEAD = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — FinSpector</title>
<meta name="description" content="Среда, в которой ИИ учится находить ошибки в финансовых книгах: вымышленные компании, скрытые расхождения и честная награда.">
<meta name="theme-color" content="#0A2246">
<meta property="og:type" content="website">
<meta property="og:title" content="{title} — FinSpector">
<meta property="og:description" content="Найдите ошибки в книгах вымышленной компании и получите честный балл от оценщика. Среда для обучения ИИ-аудиторов.">
<meta property="og:site_name" content="FinSpector">
<link rel="preload" href="assets/fonts/inter-tight-cyrillic-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/style.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%2304070D'/%3E%3Cpath d='M16 5v8M16 19v8M5 16h8M19 16h8' stroke='%23A9CBFF' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E">
</head>
<body data-page="{slug}">
<a class="skip" href="#main">К содержанию</a>
<div class="progress"></div>
<header class="top"><div class="bar">
  <a class="brand" href="index.html">{logo}FinSpector</a>
  <button class="burger" aria-expanded="false" aria-controls="menu">Меню</button>
  <nav class="menu" id="menu" aria-label="Разделы сайта">{nav}</nav>
</div></header>
<main id="main">
"""

FOOT = """</main>
<footer class="bottom"><div class="wrap"><span>FinSpector · кейс 01 FinTech · 2026</span><span>Все компании, люди и деньги вымышлены · MIT</span></div></footer>
<button class="totop" aria-label="Наверх">↑</button>
<script src="assets/config.js"></script>
<script src="assets/data.js"></script>
<script src="assets/app.js"></script>
<script src="assets/auth.js"></script>
<script src="assets/floaters.js"></script>
<script src="assets/guide.js"></script>
{script}
</body>
</html>
"""


def nav(active):
    names = {f: n for f, _, n in PAGES}
    out = []
    for f in NAV:
        on = f == active or (f == "start.html" and active in ("books.html", "run.html", "policies.html"))
        cur = ' class="on" aria-current="page"' if on else ""
        out.append(f'<a href="{f}"{cur}>{names[f]}</a>')
    return "".join(out)


def grid(vs=(), hs=(), nodes=()):
    h = '<div class="grid-lines" aria-hidden="true">'
    h += "".join(f'<i class="v" style="left:{x}%"></i>' for x in vs)
    h += "".join(f'<i class="h" style="top:{y}%"></i>' for y in hs)
    h += "".join(f'<b style="left:{x}%;top:{y}%"></b>' for x, y in nodes)
    return h + "</div>"


def next_panel(f):
    names = {p[0]: p[2] for p in PAGES}
    nf = NEXT[f]
    return (f'<section class="panel"><div class="wrap"><a class="next" href="{nf}"><div><span class="label">Дальше</span>'
            f'<div class="t">{names[nf]}</div></div><span class="go">→</span></a></div></section>\n')


def inner_page(f):
    p = INNER[f]
    rest = p["rest"].replace('<div class="calc" data-r', '<div class="calc glass" data-r')
    return f"""<section class="panel" data-float="head">
  {grid((22, 78), (78,), ((22, 78), (78, 78)))}<div class="stars" style="opacity:.5"></div>
  <div class="wrap page-head">
    <div class="crumbs"><span class="label"><span class="num">{p["num"]}</span> · {p["crumb"]}</span><span class="label">FinSpector</span></div>
    <h1 class="title">{p["title"]}</h1>
    <p class="intro" data-r style="--d:3">{p["intro"]}</p>
  </div>
</section>
<section class="panel"><div class="content">{rest}</div></section>
"""



PLAY = """<section class="panel" data-float="head">
  {grid}<div class="stars" style="opacity:.5"></div>
  <div class="wrap page-head">
    <div class="crumbs"><span class="label"><span class="num">01</span> · Песочница</span><span class="label">Настоящая среда · Python в браузере</span></div>
    <h1 class="title">Проведите<br>аудит сами</h1>
    <p class="intro" data-r style="--d:3">Вы — аудитор. В книгах вымышленной компании спрятаны ошибки. Найдите их, опишите с доказательствами и получите честный балл от оценщика.</p>
  </div>
</section>
<section class="panel"><div class="content"><div class="wrap">
  <ol class="pl-steps" aria-label="Этапы аудита">
    <li class="on"><span>1</span>Выберите компанию</li><li><span>2</span>Изучите книги</li><li><span>3</span>Опишите ошибки</li><li><span>4</span>Отправьте оценщику</li>
  </ol>
  <div class="pl-bar glass">
    <label class="fld"><span>Номер компании</span><input id="pl-seed" type="number" min="0" max="999999" value="2026"></label>
    <label class="fld"><span>Сценарий</span><select id="pl-preset">
      <option value="single">Учебный: по одной ошибке каждого типа</option><option value="mixed" selected>Обычная компания</option><option value="inter">Сложный: ошибки переплетены</option><option value="clean">Проверка: чистая компания</option></select></label>
    <button class="btn" id="pl-gen" disabled>Сгенерировать <span class="arr">→</span></button>
    <button class="btn ghost" id="pl-daily" type="button" disabled><span class="dot"></span>Компания дня</button>
    <div class="pl-status" id="pl-status" role="status" aria-live="polite"><span class="spin"></span>Загружаем Python…</div>
  </div>
  <div id="pl-work" hidden>
    <div class="pl-company" id="pl-company"></div>
    <div class="pl-grid">
      <div class="pl-books glass">
        <div class="ex-bar"><div id="pl-tabs" class="tabs"><button class="tab" data-t="ledger" aria-pressed="true">Журнал проводок</button><button class="tab" data-t="invoices" aria-pressed="false">Счета</button><button class="tab" data-t="payments" aria-pressed="false">Платежи</button><button class="tab" data-t="fx" aria-pressed="false">Курсы валют</button></div>
          <label class="search"><span class="sr">Поиск по загруженным строкам</span><input id="pl-search" type="search" placeholder="Поиск: ID, счёт, сумма…" autocomplete="off"></label></div>
        <div class="tbl-wrap"><table class="grid" id="pl-tbl"></table></div>
        <div class="pl-pager"><span id="pl-count" class="label"></span><span class="sp1"></span><button class="chip" id="pl-more">Ещё 50 строк · 1 шаг</button><button class="chip" id="pl-all">Загрузить всё</button></div>
      </div>
      <aside class="pl-side">
        <div class="seg side-tabs" id="side-tabs" role="tablist"><button type="button" role="tab" aria-selected="true" data-s="inspect">Инспектор</button><button type="button" role="tab" aria-selected="false" data-s="form">Вывод<span class="cnt" id="form-cnt" hidden></span></button><button type="button" role="tab" aria-selected="false" data-s="calc">Расчёты</button><button type="button" role="tab" aria-selected="false" data-s="help">Подсказки</button></div>
        <div class="glass side-panel sp" id="sp-inspect"></div>
        <div class="glass side-panel sp" id="sp-calc" hidden>
          <div class="t">Калькулятор</div><p class="label">Считает здесь, шаги не тратит.</p>
          <label class="fld"><span>Выражение</span><input id="calc-in" placeholder="например 48000 − 29500 × 2" autocomplete="off"></label><div class="calc-out" id="calc-out"></div>
          <div class="t mt">Перевод в валюту учёта</div><p class="label">Курс берётся на выбранную дату. Если его нет среди загруженных, запрос стоит 1 шаг.</p>
          <div class="cv"><label class="fld"><span>Сумма</span><input id="cv-amt" inputmode="decimal" placeholder="1250,50"></label><label class="fld"><span>Валюта</span><select id="cv-from"></select></label><label class="fld"><span>Дата</span><input id="cv-date" type="date"></label></div>
          <button class="btn plain" id="cv-btn" type="button">Пересчитать</button><div class="calc-out" id="cv-out"></div>
        </div>
        <div class="glass side-panel sp help" id="sp-help" hidden>
          <div class="t">Как искать ошибки</div>
          <details open><summary>Дубль счёта</summary><ol><li>Откройте «Счета» и счёт в инспекторе.</li><li>Смотрите «Другие счета этого контрагента»: та же дата, те же позиции и сумма — подозрение на дубль.</li><li>Подписки с разными периодами услуг — это не дубль.</li></ol></details>
          <details><summary>Неполное разнесение</summary><ol><li>Откройте платёж со ссылкой на счёт.</li><li>Инспектор сравнит «по документу» и «разнесено в 1200». Если есть разница, а остаток ушёл в 2900 — это ошибка.</li><li>Сумма вывода — неразнесённая часть в валюте платежа.</li></ol></details>
          <details><summary>Неверный курс</summary><ol><li>Откройте валютный счёт или платёж.</li><li>Узнайте курс на его дату — инспектор посчитает правильную сумму.</li><li>Сравните со строкой журнала 1200 (счёт) или 1000 (платёж). Разница — сумма вывода.</li></ol></details>
          <details><summary>Не тот период</summary><ol><li>В таблицах ищите метку «вне периода» — даты уже переведены в пояс компании.</li><li>Если такой документ всё равно проведён в журнале — это ошибка.</li><li>Документы следующего месяца без проводок — законны.</li></ol></details>
        </div>
        <div class="sp" id="sp-form" hidden><form class="glass pl-form side-panel" id="pl-form" novalidate>
          <div class="t">Новый вывод</div>
          <label class="fld"><span>Тип ошибки</span><select id="f-type"><option value="duplicate_invoice">Дубль счёта</option><option value="missing_or_partial_allocation">Неполное разнесение</option><option value="fx_conversion_error">Неверный курс</option><option value="period_cutoff_error">Не тот период</option></select></label>
          <ul class="f-hint" id="f-hint"></ul>
          <div class="fld"><span>Затронутые ID</span><div class="chips" id="f-aff-list"></div><input id="f-aff-in" placeholder="или впишите ID и нажмите Enter" autocomplete="off"></div>
          <div class="two"><label class="fld"><span>Сумма</span><input id="f-amt" inputmode="decimal" placeholder="1250,50"></label><label class="fld"><span>Валюта</span><select id="f-cur"></select></label></div>
          <div class="fld"><span>Доказательства</span><div class="chips" id="f-ev-list"></div><input id="f-ev-in" placeholder="или впишите ID и нажмите Enter" autocomplete="off"></div>
          <label class="fld"><span>Пояснение (необязательно)</span><input id="f-exp" maxlength="1000" placeholder="Коротко, в чём ошибка"></label>
          <p class="err" id="f-err" role="alert"></p>
          <button class="btn plain" type="submit">Добавить вывод</button>
        </form></div>
        <div class="glass pl-list"><div class="t">Мои выводы <span id="pl-n" class="label"></span></div><div id="pl-findings" class="pl-findings"></div>
          <button class="btn" id="pl-submit" type="button">Отправить оценщику <span class="arr">→</span></button></div>
      </aside>
    </div>
    <div class="pl-result" id="pl-result" hidden></div>
    <div class="glass pl-base">
      <div class="t">Сравнить с программами на этой же компании</div>
      <div class="pl-base-btns"><button class="chip" data-p="simple_reconciler">Простая сверка</button><button class="chip" data-p="random_explorer">Случайный поиск</button><button class="chip" data-p="flag_all">«Пометить всё»</button><button class="chip" data-p="oracle">Идеальный ответ</button></div>
      <div id="pl-base-out" class="pl-base-out"></div>
    </div>
  </div>
</div></div></section>
"""

LEADERS = """<section class="panel" data-float="head">
  {grid}<div class="stars" style="opacity:.5"></div>
  <div class="wrap page-head">
    <div class="crumbs"><span class="label"><span class="num">02</span> · Лидеры</span><span class="label">Результаты из базы данных</span></div>
    <h1 class="title">Таблица<br>лидеров</h1>
    <p class="intro" data-r style="--d:3">Каждый результат сервер пересчитывает сам: заново создаёт ту же компанию и сверяет выводы с эталоном. Поэтому балл здесь честный.</p>
  </div>
</section>
<section class="panel"><div class="content"><div class="wrap">
  <div class="lb-stats" id="lb-stats" data-r></div>
  <div class="lb-bar" data-r><div class="seg" role="tablist" aria-label="Период"><button type="button" role="tab" aria-selected="true" data-s="daily">Компания дня</button><button type="button" role="tab" aria-selected="false" data-s="all">Всё время</button></div><p class="label" id="lb-day"></p></div>
  <div class="glass lb-card" data-r><div class="tbl-wrap" id="lb-body"></div></div>
</div></div></section>
"""

PROFILE = """<section class="panel"><div class="content"><div class="wrap" id="profile"><p class="empty"><span class="spin"></span> Загружаем…</p></div></div></section>
"""

NOTFOUND = """<section class="panel hero-404" data-float="c">
  <div class="stars"></div>{grid}
  <div class="wrap nf"><div class="nf-code">404</div><h1 class="title">Такой страницы<br>нет в книгах</h1>
    <p class="intro">Похоже, ссылка устарела или в адресе опечатка. Как и ошибка в проводке — бывает.</p>
    <div class="cta"><a class="btn" href="index.html">На главную <span class="arr">→</span></a><a class="btn ghost" href="play.html"><span class="dot"></span>В песочницу</a></div></div>
</section>
"""

BOOK = """<div class="book-stage" aria-hidden="true"><div class="book-glow"></div><div class="book-float"><div class="book3">
      <div class="cover"></div><div class="block l"></div><div class="block r"></div>
      <div class="pg left" id="bpL"></div><div class="pg right" id="bpR"></div>
      <div class="leaf" style="--d:0s"><div class="pg front" id="bf0"></div><div class="pg back" id="bb0"></div><div class="shade"></div></div>
      <div class="leaf" style="--d:5s"><div class="pg front" id="bf1"></div><div class="pg back" id="bb1"></div><div class="shade"></div></div>
      <div class="ribbon"></div>
    </div></div></div>"""

RINGS = "".join(f'<ellipse cx="60" cy="120" rx="{18 + i * 14}" ry="{8 + i * 7}" transform="rotate(-{20 + i * 6} 60 120)"/>' for i in range(7))

INDEX = f"""<section class="panel hero" data-float="hero">
  <div class="stars"></div>{grid((30, 70), (), ())}
  <div class="wrap">
    <div class="giant" aria-hidden="true">FinSpector</div>
    <div class="hero-stage">
      <div class="hero-left" data-r style="--d:6">
        <h1 class="sr">FinSpector — среда для обучения ИИ-аудиторов</h1>
        <p>Среда, в которой ИИ учится находить ошибки в финансовых книгах. Вымышленные компании, спрятанные расхождения и честная проверка каждого вывода.</p>
        <a class="btn" href="play.html">Попробовать сейчас <span class="arr">→</span></a>
      </div>
      {BOOK}
      <div class="hero-right">
        <div class="anno" data-r style="--d:9">
          <svg class="leader" viewBox="0 0 120 120"><path d="M118 2H64L6 40v40"/></svg>
          <div class="big">20/20<small>эпизодов</small></div>
          <div class="row">Проверено без сети</div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="panel sec simple-panel" data-float="a">
  {grid((33.3, 66.6), (), ())}
  <div class="wrap">
    <p class="label center">Простыми словами</p>
    <h2 class="statement" data-r>Как это работает <span class="d">за три шага</span></h2>
    <div class="simple">
      <div class="sstep glass" data-r style="--d:0"><span class="sn">1</span><h3>Создаём компанию</h3><p>Программа придумывает компанию на месяц: счета, платежи, курсы валют. И незаметно прячет в книгах несколько ошибок.</p></div>
      <div class="sstep glass" data-r style="--d:1"><span class="sn">2</span><h3>Агент ищет ошибки</h3><p>ИИ или вы листаете таблицы, сверяете суммы и даты и описываете каждую найденную ошибку с доказательствами.</p></div>
      <div class="sstep glass" data-r style="--d:2"><span class="sn">3</span><h3>Оценщик ставит балл</h3><p>Оценщик знает, где ошибки, и сравнивает с ними каждый вывод. Балл от −1 до +1, и обмануть его нельзя.</p></div>
    </div>
    <div class="cta" data-r style="--d:3"><a class="btn" href="play.html">Попробовать самому <span class="arr">→</span></a></div>
    <p class="center-sub live" id="live-stats" hidden></p>
  </div>
</section>

<section class="panel sec" data-float="b">
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

<section class="panel final" data-float="c">
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
  fetch(window.FA_API + "/api/stats").then(r => r.json()).then(s => { if (!s.runs) return; const el = $("#live-stats");
    el.innerHTML = `Уже <b>${s.runs}</b> прохождений от <b>${s.players}</b> участников · лучший балл <b>${s.best_reward > 0 ? "+" : ""}${s.best_reward.toFixed(3)}</b>`; el.hidden = false; }).catch(() => {});
  $("#copycmd").onclick = async () => { const b = $("#copycmd");
    try { await navigator.clipboard.writeText("python -m auditenv check"); b.textContent = "Скопировано"; } catch (e) { b.textContent = "Выделите вручную"; }
    setTimeout(() => b.textContent = "Скопировать", 2000); };
})();
</script>"""

for f, num, name in PAGES:
    title = "Среда для ИИ-аудиторов" if f == "index.html" else name
    if f == "index.html":
        body, script = INDEX, INDEX_SCRIPT
    elif f == "leaders.html":
        body, script = LEADERS.replace("{grid}", grid((22, 78), (78,), ((22, 78), (78, 78)))), '<script src="assets/leaders.js"></script>'
    elif f == "profile.html":
        body, script = PROFILE, '<script src="assets/profile.js"></script>'
    elif f == "play.html":
        body = PLAY.replace("{grid}", grid((22, 78), (78,), ((22, 78), (78, 78))))
        script = '<script src="assets/play.js"></script>'
    else:
        body, script = inner_page(f), SCRIPT.get(f, "")
    html = HEAD.format(title=title, slug=f[:-5], nav=nav(f), logo=LOGO) + body + next_panel(f) + FOOT.format(script=script)
    (ROOT / f).write_text(html, encoding="utf-8")
nf = HEAD.format(title="Страница не найдена", slug="404", nav=nav(""), logo=LOGO) + NOTFOUND.replace("{grid}", grid((30, 70), (), ())) + FOOT.format(script="")
(ROOT / "404.html").write_text(nf, encoding="utf-8")
print("built", len(PAGES) + 1, "pages")
