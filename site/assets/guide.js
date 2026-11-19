/* Гид по сайту (пошаговая подсветка) и помощник с базой знаний. Без внешних сервисов. */
(function () {
  const { $, $$, esc, reduce } = UI;
  const page = document.body.dataset.page;
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };

  // ================================================================ ГИД
  const TOURS = {
    index: [
      [null, "Добро пожаловать", "Это FinSpector — тренажёр, в котором ИИ учится находить ошибки в бухгалтерских книгах. Покажу главное за 30 секунд."],
      [".book-stage", "Книга учёта", "Каждый эпизод — книга вымышленной компании за месяц. В ней спрятаны настоящие ошибки, а красная ручка показывает, как их находят."],
      [".simple", "Простыми словами", "Три шага: создаём компанию с ошибками, агент ищет их, оценщик честно ставит балл."],
      ["nav.menu", "Разделы", "Все разделы в меню. Начните с «Песочницы» — там можно пройти аудит самому."],
      ["#acct", "Профиль", "Создайте профиль — так ваши результаты попадут в историю и таблицу лидеров."],
      [".fab", "Помощник", "Если что-то непонятно, спросите помощника. Он знает, как устроен сайт и кейс."],
    ],
    play: [
      [null, "Песочница", "Здесь работает настоящая среда. Вы — аудитор: найдите ошибки и получите балл."],
      [".pl-bar", "Шаг 1. Компания", "Выберите номер и сценарий, нажмите «Сгенерировать». Одинаковый номер — всегда одна и та же компания."],
      [".pl-steps", "Четыре этапа", "Выберите компанию, изучите книги, опишите ошибки и отправьте оценщику. Текущий этап подсвечен."],
      ["#pl-work .pl-books, .pl-bar", "Книги", "Суммы показаны в обычных единицах, даты уже переведены в пояс компании. Нажмите на строку — она откроется в инспекторе."],
      ["#side-tabs, .pl-bar", "Инспектор и калькулятор", "Инспектор сам пересчитывает по курсу, сверяет разнесение и показывает связанные записи. Кнопки «+ затронутые» и «+ доказательства» заполняют вывод."],
      ["#pl-daily", "Компания дня", "Каждый день у всех одна и та же компания. Пройдите её и сравните себя с другими в таблице лидеров."],
      ["#acct", "Профиль", "Войдите, чтобы результаты копились в профиле: история, график прогресса и достижения."],
    ],
    leaders: [[null, "Лидеры", "Здесь лучшие результаты. Каждый балл пересчитан сервером."], [".seg", "Период", "Переключайте «Компанию дня» и «Всё время»."]],
    profile: [[null, "Профиль", "Ваши прохождения, лучший балл, место в рейтинге и достижения."]],
    episode: [[null, "Эпизод", "Здесь показано, как рождается компания и какие ошибки в неё прячут."], [".types", "Четыре типа ошибок", "У каждого типа есть ловушка: законный случай, который похож на ошибку."]],
    books: [[null, "Книги", "Это настоящие таблицы одного эпизода."], [".switch", "Режим оценщика", "Включите его, чтобы увидеть спрятанные ошибки. Нажмите на ошибку — подсветятся её доказательства."]],
    run: [[null, "Прогон", "Здесь видно, как простая программа проходит эпизод шаг за шагом."], ["#res", "Вердикт", "После отправки оценщик отмечает каждый вывод: верный, ложный или пропущенный."]],
    reward: [[null, "Награда", "Как считается балл и почему его нельзя обмануть."], [".calc", "Калькулятор", "Подвигайте ползунки или нажмите готовые сценарии внизу."]],
    policies: [[null, "Политики", "Сравнение четырёх базовых программ на 20 закрытых эпизодах."], ["#bars", "Награды", "Справа от нуля — хорошо, слева — плохо. «Пометить всё» получает −1."]],
    start: [[null, "Запуск", "Как запустить проверку у себя одной командой."], ["pre.code", "Команды", "Скопируйте команду и выполните её в папке проекта."]],
  };
  let tIdx = 0, steps = [], layer = null;
  function buildLayer() {
    layer = document.createElement("div"); layer.className = "tour"; layer.setAttribute("role", "dialog"); layer.setAttribute("aria-modal", "true"); layer.setAttribute("aria-labelledby", "tour-t");
    layer.innerHTML = `<div class="tour-hole"></div><div class="tour-card glass"><div class="tour-n label" id="tour-n"></div><h3 id="tour-t"></h3><p id="tour-p"></p>
      <div class="tour-btns"><button class="chip" id="tour-skip">Пропустить</button><span class="tour-dots" id="tour-dots"></span><button class="btn" id="tour-next">Далее <span class="arr">→</span></button></div></div>`;
    document.body.append(layer);
    $("#tour-skip").onclick = endTour; $("#tour-next").onclick = () => show(tIdx + 1);
    layer.addEventListener("keydown", e => { if (e.key === "Escape") endTour(); if (e.key === "ArrowRight") show(tIdx + 1); if (e.key === "ArrowLeft" && tIdx > 0) show(tIdx - 1); });
  }
  function target(sel) { if (!sel) return null; for (const s of sel.split(",")) { const el = document.querySelector(s.trim());
      if (el && el.offsetParent !== null && el.getBoundingClientRect().height > 0) return el; } return null; }
  function show(i) {
    if (i >= steps.length) return endTour(); tIdx = i; const [sel, title, text] = steps[i]; const el = target(sel);
    $("#tour-n").textContent = `Шаг ${i + 1} из ${steps.length}`; $("#tour-t").textContent = title; $("#tour-p").textContent = text;
    $("#tour-dots").innerHTML = steps.map((_, k) => `<i class="${k === i ? "on" : ""}"></i>`).join("");
    $("#tour-next").innerHTML = i === steps.length - 1 ? "Понятно" : 'Далее <span class="arr">→</span>';
    const hole = layer.querySelector(".tour-hole"), card = layer.querySelector(".tour-card");
    const place = () => { if (!el) { hole.style.cssText = "left:50%;top:50%;width:0;height:0"; card.style.cssText = "left:50%;top:50%;transform:translate(-50%,-50%)"; return; }
      const r = el.getBoundingClientRect(), p = 10;
      hole.style.cssText = `left:${r.left - p}px;top:${r.top - p}px;width:${r.width + p * 2}px;height:${r.height + p * 2}px`;
      const cw = Math.min(380, innerWidth - 32), below = r.bottom + 20 + 220 < innerHeight;
      const left = Math.max(16, Math.min(innerWidth - cw - 16, r.left));
      card.style.cssText = `width:${cw}px;left:${left}px;top:${below ? r.bottom + 20 : Math.max(16, r.top - 20 - card.offsetHeight)}px`; };
    if (el) { el.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" }); setTimeout(place, reduce ? 0 : 450); } place();
    $("#tour-next").focus();
  }
  function startTour() { steps = TOURS[page] || TOURS.index; if (!layer) buildLayer(); layer.classList.add("on"); document.body.classList.add("touring"); show(0); }
  function endTour() { if (!layer) return; layer.classList.remove("on"); document.body.classList.remove("touring"); store.set("fa-tour-" + page, "1"); }
  addEventListener("resize", () => { if (layer && layer.classList.contains("on")) show(tIdx); });
  const gb = document.createElement("button"); gb.className = "guide-btn"; gb.type = "button"; gb.innerHTML = '<span aria-hidden="true">?</span>Гид';
  gb.setAttribute("aria-label", "Запустить гид по странице"); gb.onclick = startTour;
  const bar = $("header.top .bar"); if (bar) bar.insertBefore(gb, $(".burger")); gb.title = "Гид по странице";
  if (!store.get("fa-tour-" + page) && (page === "index" || page === "play") && !new URLSearchParams(location.search).get("daily")) setTimeout(startTour, 1800);

  // ================================================================ ПОМОЩНИК
  const KB = [
    [["сайт", "проект", "fin-audit", "зачем", "это за", "о чем"], "FinSpector — среда для обучения ИИ-аудиторов. Она генерирует вымышленные компании со спрятанными финансовыми ошибками, даёт агенту инструменты расследования и честно оценивает его выводы.", "index.html", "На главную"],
    [["начать", "попробовать", "песочница", "играть", "самому", "сам"], "Откройте «Песочницу»: выберите номер компании, нажмите «Сгенерировать», ищите ошибки в таблицах и отправьте выводы оценщику.", "play.html", "Открыть песочницу"],
    [["дубль", "дубликат", "повтор", "duplicate"], "Дубль счёта — тот же счёт введён и проведён дважды в один день: тот же контрагент, валюта и позиции. В выводе укажите ID обоих счетов и сумму дубля. Не путайте с подписками: у них разный период услуг.", "episode.html", "Типы ошибок"],
    [["разнесение", "разнес", "allocation", "2900", "невыясн", "suspense"], "Неполное разнесение — платёж ссылается на счёт, но в 1200 разнесено меньше, а остаток лёг в 2900. Сумма вывода — неразнесённая часть в валюте платежа. Затронутые ID — платёж и счёт.", "episode.html", "Типы ошибок"],
    [["курс", "fx", "валют", "конвертац"], "Неверный курс — документ пересчитан не по курсу своей даты. Правильный курс берите из таблицы «Курсы» на местную дату документа. Сумма вывода — разница в валюте учёта.", "episode.html", "Типы ошибок"],
    [["период", "cutoff", "граница", "месяц", "дата", "utc", "пояс"], "Не тот период — документ следующего месяца проведён в текущем. Ловушка: время может быть записано в UTC. Сначала переведите его в часовой пояс компании.", "episode.html", "Типы ошибок"],
    [["награда", "балл", "reward", "оценка", "считается", "формула"], "Награда = clip(2·F1 − 1 − 0.002·шаги, −1, 1). Верный ответ с доказательствами даёт почти +1, молчание на книгах с ошибками даёт −1, а на чистых книгах молчание — лучший ответ.", "reward.html", "Калькулятор награды"],
    [["f1", "точность", "полнота", "precision", "recall", "tp", "fp", "fn"], "TP — верный вывод, FP — ложный или повторный, FN — пропущенная ошибка. Точность = TP/(TP+FP), полнота = TP/(TP+FN), F1 объединяет обе.", "reward.html", "Подробнее"],
    [["доказательств", "evidence", "id", "кликнуть", "нажать"], "Доказательства — ID записей, по которым видна ошибка: документ, строка журнала, курс. В песочнице нажмите на ID в таблице, и он добавится в доказательства, а с Shift — в «затронутые».", "play.html", "В песочницу"],
    [["шаг", "шаги", "100", "лимит"], "У агента 100 шагов на эпизод. Каждая страница таблицы, запрос записи и отправка тратят шаг. Экономия шагов лишь немного повышает награду.", null, null],
    [["лидер", "таблиц", "рейтинг", "база", "сохран"], "После отправки выводов в песочнице введите имя и сохраните результат. Сервер заново создаст ту же компанию и сам пересчитает балл, поэтому таблица лидеров честная.", "play.html#pl-board", "Таблица лидеров"],
    [["запуск", "запуст", "установ", "команд", "docker", "python", "check"], "Проверка запускается одной командой: python -m auditenv check. Нужен Python 3.11, зависимостей нет. Есть и Docker-вариант без сети.", "start.html", "Как запустить"],
    [["политик", "baseline", "oracle", "сверка", "случайн"], "Базовые политики: случайный исследователь, простая сверка, атака «пометить всё» и oracle. Oracle знает ответ и показывает максимум награды.", "policies.html", "Политики"],
    [["оценщик", "эталон", "truth", "matcher", "честн"], "Оценщик сравнивает выводы с эталоном один к одному: тип, ID, сумма в допуске, валюта и полный набор доказательств. Красивый текст объяснения на балл не влияет.", "reward.html", "Награда"],
    [["кейс", "хакатон", "genesis", "сдача", "жюри"], "Это решение кейса FinTech №1 хакатона GENESIS: RL-среда для дообучения моделей финансового аудита. Код открыт, проверка воспроизводима.", "start.html", "Код и запуск"],
    [["реальн", "данные", "настоящ", "персональн"], "Все компании, люди, счета и деньги вымышлены. Реальные платежи и персональные данные не используются.", null, null],
    [["чист", "пусто", "нет ошибок", "молчан"], "Если компания чистая, правильный ответ — пустой список выводов. Он даёт максимальную награду, а любое ложное обвинение её снижает.", null, null],
    [["режим оценщика", "режим"], "Режим оценщика на странице «Книги» показывает эталон: какие ошибки спрятаны и какие записи их доказывают. Нажмите на ошибку справа — её строки подсветятся в таблице.", "books.html", "Открыть книги"],
    [["профил", "аккаунт", "регистрац", "войти", "вход", "логин", "пароль"], "Профиль создаётся на странице «Профиль»: придумайте логин и пароль. Все сохранённые результаты попадут в историю, а вы получите график прогресса и достижения.", "profile.html", "Открыть профиль"],
    [["компания дня", "дня", "ежедневн", "сегодня"], "Компания дня — одна и та же компания для всех участников в течение суток. Пройдите её в песочнице кнопкой «Компания дня» и сравните себя с другими.", "play.html?daily=1", "Пройти компанию дня"],
    [["достижен", "награды профил", "бейдж"], "В профиле 8 достижений: например, «Без единой ошибки» за F1 = 1 или «Чистые руки», если не обвинили чистую компанию.", "profile.html", "Профиль"],
    [["жюри", "материал", "github", "исходн", "код"], "Все материалы для проверки собраны в разделе «Для жюри»: книги эпизода, прогон политики, базовые политики и ссылка на исходный код.", "start.html", "Для жюри"],
    [["гид", "помощь", "подсказ", "тур"], "Нажмите «Гид» в шапке — я подсвечу главные элементы этой страницы по шагам.", null, null],
  ];
  const SUGGEST = { index: ["Что это за сайт?", "С чего начать?", "Как считается награда?"],
    play: ["Как добавить доказательство?", "Что такое компания дня?", "Как создать профиль?"],
    leaders: [[null, "Лидеры", "Здесь лучшие результаты. Каждый балл пересчитан сервером."], [".seg", "Период", "Переключайте «Компанию дня» и «Всё время»."]],
    profile: [[null, "Профиль", "Ваши прохождения, лучший балл, место в рейтинге и достижения."]],
    episode: ["Что такое дубль счёта?", "Что за ловушка с UTC?"], books: ["Что такое режим оценщика?", "Что такое 2900?"],
    run: ["Что значат TP, FP и FN?"], reward: ["Что такое F1?", "Почему молчание бывает лучшим ответом?"],
    policies: ["Что такое oracle?"], start: ["Как запустить проверку?", "Где исходный код?"],
    leaders: ["Что такое компания дня?", "Как попасть в таблицу?"], profile: ["Какие есть достижения?", "Как создать профиль?"] };
  const norm = s => s.toLowerCase().replace(/ё/g, "е");
  function answer(q) { const t = norm(q); let best = null, bs = 0;
    KB.forEach(item => { const s = item[0].reduce((a, k) => a + (t.includes(norm(k)) ? k.length : 0), 0); if (s > bs) { bs = s; best = item; } });
    if (!best) return { text: "Не нашёл точного ответа. Попробуйте спросить иначе: например, «как считается награда» или «что такое неполное разнесение». Ещё можно нажать «Гид» в шапке.", link: null };
    return { text: best[1], link: best[2], label: best[3] }; }

  const fab = document.createElement("button"); fab.className = "fab"; fab.type = "button"; fab.setAttribute("aria-expanded", "false"); fab.setAttribute("aria-controls", "asst");
  fab.innerHTML = '<span class="fab-dot" aria-hidden="true"></span><span>Помощник</span>';
  const box = document.createElement("section"); box.className = "asst glass"; box.id = "asst"; box.hidden = true; box.setAttribute("aria-label", "Помощник");
  box.innerHTML = `<div class="asst-head"><div><b>Помощник</b><span class="label">Отвечает по базе знаний сайта</span></div><button class="x" aria-label="Закрыть помощника">×</button></div>
    <div class="asst-log" id="asst-log" aria-live="polite"></div><div class="asst-sug" id="asst-sug"></div>
    <form class="asst-form" id="asst-form"><label class="sr" for="asst-in">Ваш вопрос</label><input id="asst-in" placeholder="Спросите про сайт или кейс" autocomplete="off" maxlength="200"><button aria-label="Отправить вопрос">→</button></form>`;
  document.body.append(fab, box);
  const log = $("#asst-log");
  function say(who, html) { const d = document.createElement("div"); d.className = "msg " + who; d.innerHTML = html; log.append(d); log.scrollTop = log.scrollHeight; }
  function ask(q) { if (!q.trim()) return; say("me", esc(q)); const a = answer(q);
    setTimeout(() => say("bot", esc(a.text) + (a.link ? `<a class="msg-link" href="${a.link}">${esc(a.label)} →</a>` : "")), reduce ? 0 : 350); }
  function openBox(o) { box.hidden = !o; fab.setAttribute("aria-expanded", o); fab.classList.toggle("on", o);
    if (o && !log.children.length) { say("bot", "Привет! Я помогу разобраться с сайтом. Выберите вопрос или напишите свой.");
      $("#asst-sug").innerHTML = (SUGGEST[page] || SUGGEST.index).map(s => `<button class="chip">${esc(s)}</button>`).join("");
      $$("#asst-sug .chip").forEach(c => c.onclick = () => ask(c.textContent)); }
    if (o) $("#asst-in").focus(); }
  fab.onclick = () => openBox(box.hidden); box.querySelector(".x").onclick = () => { openBox(false); fab.focus(); };
  box.addEventListener("keydown", e => { if (e.key === "Escape") { openBox(false); fab.focus(); } });
  $("#asst-form").onsubmit = e => { e.preventDefault(); const i = $("#asst-in"); ask(i.value); i.value = ""; };
})();
