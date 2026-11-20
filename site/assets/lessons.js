/* FinSpector · обучение: мой план, карта курса и проигрыватель уроков. Любой урок можно открыть и пройти в любой момент. */
(function () {
  const { $, $$, esc } = UI;
  const Lr = LEARN;
  const DATA = Object.fromEntries([

    { id: "books", teach: "У каждой компании три главные таблицы. Счета — кому и сколько выставили. Платежи — кто и сколько заплатил. Журнал проводок — бухгалтерская запись каждого события. Ошибки обычно видны там, где эти таблицы расходятся.",
      task: { kind: "pick", q: "Клиент оплатил счёт. Где появятся записи об этих деньгах?",
        cols: ["Таблица", "Что в ней", "Пример"], num: [],
        rows: [["Счета", "Сколько выставили клиенту", "INV-4K2P · 1 250,00 €"], ["Платежи", "Сколько клиент заплатил", "PAY-5H1 · 1 250,00 €"], ["Журнал", "Бухгалтерские проводки", "L-81A · Касса +1 250,00 €"]],
        opts: ["Только в счетах", "В платежах и в журнале", "Только в журнале"], answer: 1,
        ok: "Деньги приходят платежом (PAY-…), а бухгалтер отражает их в журнале: касса растёт, долг клиента уменьшается." },
      trap: { q: "Счёт есть в таблице счетов, но в журнале по нему нет ни одной строки. Это всегда ошибка?",
        opts: ["Да, всегда", "Нет, не всегда"], answer: 1,
        why: "Не всегда. Например, счёт следующего месяца лежит в системе, но в журнал этого месяца попадать не должен." } },

    { id: "dr", teach: "Каждая операция записывается дважды: в дебет одного счёта и в кредит другого — на одну и ту же сумму. Поэтому дебет всегда равен кредиту. Главные счета здесь: 1000 — касса, 1200 — долг клиентов, 4000 — выручка, 2900 — невыясненные поступления.",
      task: { kind: "row", q: "Клиенту выставили счёт на 800 €. Нажмите на строку, которая записывает его долг.",
        cols: ["Строка", "Счёт учёта", "Дебет", "Кредит"], num: [2, 3],
        rows: [["L-09", "1000 Касса", "150,00 €", "—"], ["L-11", "1200 Долг клиента", "800,00 €", "—"], ["L-12", "4000 Выручка", "—", "800,00 €"]],
        answer: 1, mark: [2],
        near: { 2: "Это вторая половина той же проводки — выручка. Долг клиента записан на счёте 1200.", 0: "Это другая операция: деньги в кассе. Ищите счёт 1200." },
        ok: "Долг клиента растёт по дебету счёта 1200, а выручка — по кредиту 4000. Обе строки на 800 €, поэтому проводка сбалансирована." },
      trap: { q: "В одной проводке дебет 800 €, а кредит 780 €. Так бывает?",
        opts: ["Да, нормально", "Нет, так не бывает"], answer: 1,
        why: "Не бывает: дебет и кредит одной проводки всегда равны. Такие нарушения FinSpector отсекает заранее — ищите ошибки в смысле, а не в арифметике." } },

    { id: "minor", teach: "В данных суммы хранятся в «копейках» — целыми числами без запятой: 125050 значит 1 250,50. Так не бывает ошибок округления. Сколько знаков после запятой — зависит от валюты: у евро и тенге 2, у японской иены 0, у кувейтского динара 3.",
      task: { kind: "pick", q: "Платёж в евро: amount_minor = 480530. Сколько это в обычном виде?",
        cols: ["Валюта", "Знаков", "В данных", "Обычная сумма"], num: [1, 2, 3],
        rows: [["EUR", "2", "125050", "1 250,50 €"], ["JPY", "0", "125050", "125 050 ¥"], ["KWD", "3", "125050", "125,050 KWD"]],
        opts: ["4 805,30 €", "48 053,00 €", "480 530,00 €"], answer: 0,
        ok: "У евро 2 знака после запятой: 480530 → 4 805,30 €. Песочница и инспектор переводят суммы сами, но в коде на Python делить придётся вам." },
      trap: { q: "Сумма 125050 в японских иенах — это 1 250,50 ¥?",
        opts: ["Да", "Нет"], answer: 1,
        why: "Нет: у иены нет «копеек», поэтому 125050 — это ровно 125 050 ¥." } },

    { id: "tz", teach: "Время в данных записано по Гринвичу (UTC). Чтобы понять, какой это день для компании, прибавьте её часовой пояс. Компания в Алматы живёт по UTC+5: 21:00 по UTC — это уже 02:00 следующего дня.",
      task: { kind: "pick", q: "Платёж пришёл 31 мая в 22:40 по UTC. Компания живёт по UTC+5. Какой это день для неё?",
        cols: ["По UTC", "+5 часов", "День компании"], num: [],
        rows: [["31 мая, 10:00", "15:00", "31 мая"], ["31 мая, 18:30", "23:30", "31 мая"], ["31 мая, 22:40", "?", "?"]],
        hl: [2], opts: ["31 мая", "1 июня"], answer: 1,
        ok: "22:40 + 5 часов = 03:40 следующего дня. Для компании это уже 1 июня — то есть другой отчётный месяц." },
      trap: { q: "Компания живёт по UTC−3. Платёж 1 июня в 01:30 по UTC — это июнь для неё?",
        opts: ["Да, июнь", "Нет, ещё май"], answer: 1,
        why: "Ещё май: 01:30 − 3 часа = 22:30 31 мая." } },


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

    { id: "subs", teach: "Подписки выставляются регулярно на одинаковую сумму — это не дубли. Дубль — когда один и тот же период или заказ выставлен дважды. Смотрите не на сумму, а на период услуги и номер заказа.",
      task: { kind: "row", q: "Среди счетов одного клиента есть настоящий дубль. Нажмите на лишний счёт.",
        cols: ["Счёт", "Выставлен", "Услуга", "Сумма"], num: [3],
        rows: [["INV-S01", "5 мая", "Подписка, 5–11 мая", "99,00 €"], ["INV-S02", "12 мая", "Подписка, 12–18 мая", "99,00 €"], ["INV-S03", "12 мая", "Подписка, 12–18 мая", "99,00 €"], ["INV-S04", "19 мая", "Подписка, 19–25 мая", "99,00 €"]],
        answer: 2, mark: [1],
        near: { 1: "Почти: это первый счёт за 12–18 мая, он законный. Лишний — второй за тот же период.", 0: "Это подписка за другую неделю — всё в порядке.", 3: "Это подписка за другую неделю — всё в порядке." },
        ok: "INV-S03 повторяет INV-S02: та же неделя 12–18 мая. Остальные счета — обычная еженедельная подписка." },
      trap: { q: "Два счёта одному клиенту в один день на одну сумму, но по разным заказам SO-1 и SO-2. Это дубль?",
        opts: ["Да, дубль", "Нет, разные продажи"], answer: 1,
        why: "Не дубль: разные заказы — разные продажи, даже если суммы совпали." } },

    { id: "combo", teach: "Иногда в одном валютном платеже сразу две ошибки: часть денег не разнесена, а сама сумма пересчитана по курсу не той даты. Одна ошибка мешает заметить другую. Каждую нужно описать отдельным выводом.",
      task: { kind: "pick", q: "Платёж 1 000 $ должен закрыть счёт целиком. Вот что вы нашли. Сколько выводов отправить?",
        cols: ["Что проверяем", "Должно быть", "В журнале"], num: [],
        rows: [["Разнесено на счёт клиента", "1 000 $", "700 $"], ["Курс на дату платежа", "0,9210", "0,9345"]],
        opts: ["Один общий", "Два отдельных", "Ни одного"], answer: 1,
        ok: "Два: «Неполное разнесение» на 300 $ и «Неверный курс» на разницу пересчёта. Общий вывод оценщик не засчитает ни за одну из ошибок." },
      trap: { q: "Можно ли отправить один и тот же вывод дважды, чтобы получить больше баллов?",
        opts: ["Да, баллов будет больше", "Нет"], answer: 1,
        why: "Нет: повтор считается ложным выводом и снижает балл." } },

    { id: "clean", teach: "Бывает, что в книгах нет ни одной ошибки. Тогда лучший ответ — отправить пустой список выводов. Любое обвинение на чистой компании снижает балл.",
      task: { kind: "pick", q: "Вы проверили всё, и всё сходится. Что отправить?",
        cols: ["Проверка", "Результат"], num: [],
        rows: [["Дубли счетов", "не найдены"], ["Разнесение оплат", "всё разнесено"], ["Курсы", "совпадают"], ["Периоды", "всё в мае"]],
        opts: ["Пустой список выводов", "Самый подозрительный счёт", "Все крупные счета"], answer: 0,
        ok: "Пустой список — честный ответ. На чистой компании он даёт максимальный балл." },
      trap: { q: "Стоит ли «на всякий случай» обвинить пару крупных счетов?",
        opts: ["Да, вдруг угадаю", "Нет"], answer: 1,
        why: "Нет: каждое ложное обвинение снижает балл, а «пометить всё» всегда даёт −1." } },

    { id: "evidence", teach: "Вывод засчитывается, только если к нему приложены все нужные доказательства — документы и строки журнала, по которым видна ошибка. Для дубля это оба счёта и проводка лишнего счёта.",
      task: { kind: "pick", q: "Дубль: счета INV-4K2P и INV-7T3M, лишний проведён строкой L-90. Какой набор доказательств полный?",
        cols: ["Запись", "Что это"], num: [],
        rows: [["INV-4K2P", "первый, настоящий счёт"], ["INV-7T3M", "второй, лишний счёт"], ["L-90", "проводка лишнего счёта"]],
        opts: ["Только INV-7T3M", "INV-4K2P и INV-7T3M", "INV-4K2P, INV-7T3M и L-90"], answer: 2,
        ok: "Полный набор — оба счёта и проводка лишнего. Без проводки не видно, что дубль попал в учёт и исказил отчёт." },
      trap: { q: "Добавить в доказательства десяток лишних строк «на всякий случай» — хорошая идея?",
        opts: ["Да, хуже не будет", "Нет, лучше точно"], answer: 1,
        why: "Лучше точно: лишние ID ничего не добавляют, а у списка есть предел длины. Прикладывайте то, что доказывает ошибку." } },

  ].map(x => [x.id, x]));

  const root = $("#learn");
  let cur = null, step = 0;

  // ---------------------------------------------------------------- главная обучения
  function home() {
    cur = null; const p = Lr.plan();
    root.innerHTML = `<div class="lp-plan glass" id="lp-plan"></div><div class="lp-course" id="lp-course"></div>`;
    p ? planView(p) : planChoose();
    courseView();
  }
  function planChoose(initial) {
    const box = $("#lp-plan");
    box.classList.add("choosing");
    box.innerHTML = `<div class="lp-ph"><div><span class="label">Мой план</span><h2>${initial ? "Изменить план учёбы" : "Выберите план учёбы"}</h2>
      <p>Темп и дни, когда вам удобно заниматься. Курс — ${Lr.ITEMS.length} шагов: 12 коротких уроков и 5 практик в песочнице. Уроки открыты всегда — план лишь подсказывает, что делать сегодня.</p></div></div><div id="lp-picker"></div>`;
    Lr.picker($("#lp-picker"), { initial, submitLabel: initial ? "Сохранить план" : "Начать по плану", onSaved: () => home(), onCancel: initial ? () => home() : null });
  }
  function planView(p) {
    const box = $("#lp-plan"); box.classList.remove("choosing");
    const s = Lr.status(p), t = Lr.todayIso();
    const fmt = d => new Date(d + "T12:00:00").toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "short" });
    const todayItems = s.due.slice(0, 6);
    const msg = s.finished ? "Курс пройден целиком. Теперь — компания дня и рейтинг." :
      todayItems.length ? (s.sessions.some(x => x.date < t && x.items.some(id => !Lr.isDone(id))) ? "Есть задания с прошлых занятий — ничего страшного, начните с них." : "Задания на сегодня:")
      : s.next ? `Сегодня по плану отдых. Следующее занятие — ${fmt(s.next.date)}.` : "Все занятия по плану пройдены.";
    box.innerHTML = `<div class="lp-ph"><div><span class="label">Мой план</span><h2>План «${esc(Lr.PACES[p.pace].name)}»</h2><p>${esc(Lr.describe(p))} в ${Lr.TIMES[p.time][1]}</p></div>
        <div class="lp-pa"><button type="button" class="chip sm" id="lp-edit">Изменить план</button><button type="button" class="chip sm" id="lp-ics" title="Скачать файл .ics с занятиями и напоминаниями">В календарь</button></div></div>
      <div class="lp-prog"><div class="lp-pn"><b>${s.nDone}</b> из ${s.total} шагов</div><div class="meter"><i style="width:${s.nDone / s.total * 100}%"></i></div></div>
      <div class="lp-cols">
        <div class="lp-today"><div class="t">Сегодня</div><p class="lp-msg">${msg}</p>
          ${todayItems.length ? `<div class="lp-tasks">${todayItems.map(id => taskBtn(id)).join("")}</div>` : (s.nextItem && !s.finished ? `<div class="lp-tasks">${taskBtn(s.nextItem.id, "Можно вперёд: ")}</div>` : "")}
          ${s.finished ? `<a class="btn" href="play.html?daily=1">Компания дня <span class="arr">→</span></a>` : ""}</div>
        <div class="lp-cal"><div class="t">Занятия</div><ol class="lp-days">${s.sessions.map(x => { const done = x.items.every(Lr.isDone), today = x.date === t, late = x.date < t && !done;
          return `<li class="${done ? "done" : today ? "today" : late ? "late" : ""}" title="${esc(x.items.map(id => Lr.BY[id].title).join(", "))}"><span class="d">${fmt(x.date)}</span><span class="n">${done ? "✓" : x.items.filter(Lr.isDone).length + "/" + x.items.length}</span></li>`; }).join("")}</ol>
          <p class="lp-hint">Наведите на занятие, чтобы увидеть темы. Файл «В календарь» добавит занятия с напоминанием за 10 минут.</p></div>
      </div>`;
    $("#lp-edit").onclick = () => planChoose(p);
    $("#lp-ics").onclick = () => Lr.downloadIcs(p);
  }
  function taskBtn(id, prefix = "") {
    const x = Lr.BY[id];
    return x.practice ? `<a class="lp-task" href="${x.href}"><span class="ic p" aria-hidden="true">▶</span><span><b>${prefix}${esc(x.title)}</b><small>Практика · ~${x.min} мин · ${esc(x.short)}</small></span></a>`
      : `<button type="button" class="lp-task" data-open="${id}"><span class="ic" aria-hidden="true">✎</span><span><b>${prefix}${esc(x.title)}</b><small>Урок · ~${x.min} мин · ${esc(x.short)}</small></span></button>`;
  }
  function courseView() {
    $("#lp-course").innerHTML = Lr.COURSE.map((m, mi) => {
      const n = m.items.filter(([id]) => Lr.isDone(id)).length;
      return `<section class="lp-mod"><div class="lp-mh"><div><span class="label">Модуль ${mi + 1}</span><h3>${m.title}</h3><p>${m.desc}</p></div><span class="lp-mc${n === m.items.length ? " ok" : ""}">${n} из ${m.items.length}</span></div>
        <div class="lp-grid">${m.items.map(([id, title, short, min, href]) => { const d = Lr.isDone(id);
          const inner = `<span class="st${d ? " ok" : ""}" aria-hidden="true">${d ? "✓" : m.practice ? "▶" : ""}</span><b>${title}</b><small>${short}</small><span class="mt">${m.practice ? "Практика" : "Урок"} · ~${min} мин${d ? " · пройдено" : ""}</span>`;
          return m.practice ? `<a class="lp-card glass${d ? " done" : ""}" href="${href}">${inner}</a>` : `<button type="button" class="lp-card glass${d ? " done" : ""}" data-open="${id}">${inner}</button>`; }).join("")}</div></section>`;
    }).join("") + `<p class="lp-foot">Прогресс сохраняется в вашем аккаунте и виден на любом устройстве. <button type="button" class="gt-link" id="lp-reset">Пройти уроки заново</button> — галочки останутся, просто начните с первого.</p>`;
    $("#lp-reset").onclick = () => open(Lr.ITEMS[0].id);
  }

  // ---------------------------------------------------------------- проигрыватель урока
  const LESSONS = Lr.ITEMS.filter(x => !x.practice).map(x => x.id);
  function open(id) { if (!DATA[id]) return; location.hash = "l=" + id; }
  function route() {
    const m = /l=([a-z_]+)/.exec(location.hash);
    if (m && DATA[m[1]]) { if (cur !== m[1]) { cur = m[1]; step = 0; } player(); } else home();
    root.scrollIntoView({ behavior: UI.reduce ? "auto" : "smooth", block: "start" });
  }
  function table(t, clickable) {
    return `<div class="ls-tbl-wrap"><table class="ls-tbl"><thead><tr>${t.cols.map((c, i) => `<th${t.num.includes(i) ? ' class="r"' : ""}>${c}</th>`).join("")}</tr></thead><tbody>
      ${t.rows.map((r, ri) => `<tr${(t.hl || []).includes(ri) ? ' class="hl"' : ""}${clickable ? ` tabindex="0" role="button" data-row="${ri}" aria-label="Выбрать строку ${esc(r[0])}"` : ""}>${r.map((c, i) => `<td${t.num.includes(i) ? ' class="r"' : ""}>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }
  function player() {
    const l = DATA[cur], meta = Lr.BY[cur], i = LESSONS.indexOf(cur), mod = Lr.COURSE.find(m => m.id === meta.module);
    const prev = LESSONS[i - 1], next = LESSONS[i + 1];
    const pips = `<ol class="ls-pips" aria-label="Шаги урока">${["Объяснение и задача", "Ловушка", "Итог"].map((s, k) => `<li class="${k < step ? "done" : k === step ? "on" : ""}">${s}</li>`).join("")}</ol>`;
    let body = "";
    if (step === 0) {
      const t = l.task;
      body = `<p class="ls-teach">${l.teach}</p><div class="ls-q"><b>Задача.</b> ${t.q}</div>${t.rows ? table(t, t.kind === "row") : ""}
        ${t.kind === "pick" ? `<div class="ls-opts" role="group" aria-label="Варианты ответа">${t.opts.map((o, k) => `<button type="button" class="ls-opt" data-o="${k}">${o}</button>`).join("")}</div>` : ""}
        <div class="ls-fb" id="ls-fb" role="status" aria-live="polite"></div>`;
    } else if (step === 1) {
      const t = l.trap;
      body = `<div class="ls-trap"><span class="ls-badge">Ловушка</span><p>${t.q}</p></div>
        <div class="ls-opts" role="group" aria-label="Варианты ответа">${t.opts.map((o, k) => `<button type="button" class="ls-opt" data-t="${k}">${o}</button>`).join("")}</div>
        <div class="ls-fb" id="ls-fb" role="status" aria-live="polite"></div>`;
    } else {
      const p = Lr.plan(), st = p ? Lr.status(p) : null, more = st ? st.due.filter(id => id !== cur) : [];
      body = `<div class="ls-done"><div class="ls-check" aria-hidden="true">✓</div><h3>Урок «${meta.title}» пройден</h3>
        <p>${Lr.status(p || { pace: "normal", days: [1], time: "day", start: Lr.todayIso() }).nDone} из ${Lr.ITEMS.length} шагов курса позади.${more.length ? ` На сегодня по плану осталось: ${more.length}.` : ""}</p>
        <div class="ls-actions">${next ? `<button type="button" class="btn" data-open="${next}">Следующий урок: ${Lr.BY[next].title} <span class="arr">→</span></button>` : `<a class="btn" href="play.html?preset=single">Практика в песочнице <span class="arr">→</span></a>`}
          <button type="button" class="chip" id="ls-home">К плану</button></div></div>`;
    }
    root.innerHTML = `<div class="ls-player glass">
      <div class="ls-top"><button type="button" class="chip sm" id="ls-back">← Все уроки</button><span class="ls-crumb">Модуль «${mod.title}» · урок ${i + 1} из ${LESSONS.length}</span>
        <span class="ls-nav2">${prev ? `<button type="button" class="chip sm" data-open="${prev}" aria-label="Предыдущий урок">←</button>` : ""}${next ? `<button type="button" class="chip sm" data-open="${next}" aria-label="Следующий урок">→</button>` : ""}</span></div>
      <div class="ls-head"><h2 tabindex="-1">${meta.title}${Lr.isDone(cur) && step < 2 ? ' <span class="ls-was">пройден раньше</span>' : ""}</h2></div>${pips}${body}</div>`;
    $("#ls-back").onclick = () => { location.hash = ""; };
    const h = $("#ls-home"); if (h) h.onclick = () => { location.hash = ""; };
    root.querySelector(".ls-head h2").focus({ preventScroll: true });
  }
  function feedback(ok, text, nextLabel) {
    const fb = $("#ls-fb"); fb.className = "ls-fb " + (ok ? "good" : "bad");
    fb.innerHTML = `<b>${ok ? "Верно." : "Не совсем."}</b> ${text}${ok ? `<button type="button" class="btn plain" id="ls-go">${nextLabel}</button>` : ""}`;
    if (ok) { const g = $("#ls-go"); g.onclick = () => { step++; player(); }; g.focus({ preventScroll: true }); }
  }
  root.addEventListener("click", e => {
    const o0 = e.target.closest("[data-open]"); if (o0) { open(o0.dataset.open); return; }
    if (!cur) return; const l = DATA[cur];
    const row = e.target.closest("tr[data-row]");
    if (row && step === 0 && l.task.kind === "row" && !row.closest("table").classList.contains("solved")) {
      const k = +row.dataset.row, t = l.task;
      $$("#learn tr[data-row]").forEach(r => r.classList.remove("wrong"));
      if (k === t.answer) { row.classList.add("right"); row.closest("table").classList.add("solved"); (t.mark || []).forEach(m => $(`#learn tr[data-row="${m}"]`).classList.add("pair")); feedback(true, t.ok, "К ловушке →"); }
      else { row.classList.add("wrong"); feedback(false, (t.near && t.near[k]) || "Эта строка в порядке. Сравните ещё раз."); }
      return;
    }
    const o = e.target.closest("[data-o]");
    if (o && step === 0 && !o.disabled) { const t = l.task, k = +o.dataset.o;
      if (k === t.answer) { $$("#learn [data-o]").forEach(b => b.disabled = true); o.classList.add("right"); feedback(true, t.ok, "К ловушке →"); }
      else { o.classList.add("wrong"); o.disabled = true; feedback(false, t.rows ? "Посмотрите ещё раз на таблицу и попробуйте другой вариант." : "Попробуйте другой вариант."); }
      return; }
    const tr = e.target.closest("[data-t]");
    if (tr && step === 1 && !tr.disabled) { const t = l.trap, k = +tr.dataset.t;
      $$("#learn [data-t]").forEach(b => b.disabled = true);
      tr.classList.add(k === t.answer ? "right" : "wrong"); if (k !== t.answer) $(`#learn [data-t="${t.answer}"]`).classList.add("right");
      const fb = $("#ls-fb"); fb.className = "ls-fb " + (k === t.answer ? "good" : "bad");
      fb.innerHTML = `<b>${k === t.answer ? "Верно." : "Это ловушка."}</b> ${t.why}<button type="button" class="btn plain" id="ls-go">Завершить урок</button>`;
      $("#ls-go").onclick = () => { step = 2; Lr.markDone(cur); player(); }; $("#ls-go").focus({ preventScroll: true }); }
  });
  root.addEventListener("keydown", e => { if ((e.key === "Enter" || e.key === " ") && e.target.matches("tr[data-row]")) { e.preventDefault(); e.target.click(); } });

  addEventListener("hashchange", route);
  addEventListener("fs:plan", () => { if (!cur) home(); });
  addEventListener("fs:auth", () => Lr.sync());
  route();
  Lr.sync();
})();
