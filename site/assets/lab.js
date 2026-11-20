/* FinSpector · Python-лаборатория: редактор, запуск, примеры. */
(function () {
  const { $, $$, esc } = UI;
  const EX = [
    { f: "01_first_steps", t: "Первые шаги", d: "Создать компанию и прочитать первые счета" },
    { f: "02_find_duplicates", t: "Поиск дублей", d: "Своя проверка и честная награда" },
    { f: "03_baselines", t: "Базовые политики", d: "Сравнить пять готовых программ" },
    { f: "04_own_policy", t: "Своя политика", d: "Класс begin/act, как у ИИ-агента" },
    { f: "05_blank", t: "Чистый лист", d: "Пишите что угодно" },
  ];
  const KEY = f => "fs-lab-" + f;
  const store = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
                  set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} },
                  del: k => { try { localStorage.removeItem(k); } catch (e) {} } };
  let errBuf = "";
  const src = {}; let cur = EX[0].f, worker = null, ready = false, running = false, runId = 0, bootT = 0;
  const ed = $("#lab-code"), gut = $("#lab-gutter"), out = $("#lab-out"), st = $("#lab-status"), runB = $("#lab-run"), stopB = $("#lab-stop");

  function status(html, kind) { st.className = "lab-status " + (kind || ""); st.innerHTML = html; }
  function lines() { const n = ed.value.split("\n").length; let s = ""; for (let i = 1; i <= n; i++) s += i + "\n"; const bad = +gut.dataset.bad || 0;
    gut.innerHTML = bad ? s.split("\n").map((x, i) => i + 1 === bad ? `<b>${x}</b>` : x).join("\n") : s; gut.scrollTop = ed.scrollTop; }
  function write(s, cls) { const span = document.createElement("span"); if (cls) span.className = cls; span.textContent = s; out.append(span); out.scrollTop = out.scrollHeight; }

  // ---------------------------------------------------------------- поток Python
  function boot() {
    ready = false; bootT = performance.now();
    status('<span class="spin"></span>Запускаем Python в браузере… первый раз около 5–10 секунд', "busy");
    runB.disabled = true;
    worker = new Worker("assets/lab-worker.js");
    worker.onmessage = e => {
      const m = e.data;
      if (m.t === "ready") { ready = true; runB.disabled = false;
        status(`Python ${esc(m.version.split(".").slice(0, 2).join("."))} готов за ${((performance.now() - bootT) / 1000).toFixed(1)} с · среда FinSpector установлена`, "ok"); }
      else if (m.t === "fail") status("Не удалось запустить Python: " + esc(m.s) + ". Обновите страницу.", "bad");
      else if (m.t === "out") write(m.s);
      else if (m.t === "err") { write(m.s, "e"); errBuf += m.s; }
      else if (m.t === "done" && m.id === runId) {
        running = false; runB.disabled = false; stopB.hidden = true;
        write(`\n— ${m.ok ? "готово" : "ошибка"} за ${(m.ms / 1000).toFixed(2)} с —\n`, m.ok ? "dim" : "e dim");
        status(m.ok ? "Готово. Измените код и запустите ещё раз." : "В коде ошибка — помощник подсказал, где и почему.", m.ok ? "ok" : "bad");
        if (!m.ok && window.LAB_HELP) LAB_HELP.report(errBuf);
      }
    };
    worker.onerror = e => status("Python остановился: " + esc(e.message || "ошибка") + ". Нажмите «Остановить» и попробуйте снова.", "bad");
  }
  function run() {
    if (!ready || running) return;
    running = true; runId++; out.textContent = ""; errBuf = ""; if (window.LAB_HELP) LAB_HELP.clear(); runB.disabled = true; stopB.hidden = false;
    status('<span class="spin"></span>Выполняется…', "busy");
    worker.postMessage({ code: ed.value, id: runId });
  }
  function stop() {
    if (worker) worker.terminate();
    running = false; stopB.hidden = true; write("\n— остановлено —\n", "e dim"); boot();
  }

  // ---------------------------------------------------------------- примеры
  async function load(f) {
    cur = f; if (window.LAB_HELP) LAB_HELP.clear();
    $$("#lab-ex button").forEach(b => b.setAttribute("aria-selected", b.dataset.f === f));
    if (!src[f]) { try { const r = await fetch(`py/examples/${f}.py`); src[f] = r.ok ? await r.text() : "# не удалось загрузить пример\n"; } catch (e) { src[f] = "# нет сети\n"; } }
    ed.value = store.get(KEY(f)) ?? src[f]; lines(); ed.scrollTop = 0;
    $("#lab-file").textContent = f + ".py";
    $("#lab-dirty").hidden = store.get(KEY(f)) == null;
  }
  $("#lab-ex").innerHTML = EX.map((x, i) => `<button type="button" role="tab" data-f="${x.f}" aria-selected="${i === 0}"><b>${String(i + 1).padStart(2, "0")} ${x.t}</b><small>${x.d}</small></button>`).join("");
  $("#lab-ex").onclick = e => { const b = e.target.closest("button"); if (b) load(b.dataset.f); };

  // ---------------------------------------------------------------- редактор
  let saveT;
  ed.addEventListener("input", () => { lines(); clearTimeout(saveT); saveT = setTimeout(() => { store.set(KEY(cur), ed.value); $("#lab-dirty").hidden = false; }, 400); });
  ed.addEventListener("scroll", () => { gut.scrollTop = ed.scrollTop; });
  ed.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); run(); return; }
    if (e.key === "Tab" && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      const s = ed.selectionStart, en = ed.selectionEnd, v = ed.value;
      if (s === en && !e.shiftKey) { ed.setRangeText("    ", s, en, "end"); }
      else {
        const ls = v.lastIndexOf("\n", s - 1) + 1, block = v.slice(ls, en);
        const nb = e.shiftKey ? block.replace(/^ {1,4}/gm, "") : block.replace(/^/gm, "    ");
        ed.setRangeText(nb, ls, en, "select");
      }
      ed.dispatchEvent(new Event("input"));
    }
    if (e.key === "Enter" && !e.ctrlKey && !e.metaKey) {
      const s = ed.selectionStart, v = ed.value, ls = v.lastIndexOf("\n", s - 1) + 1, line = v.slice(ls, s);
      let ind = (/^ */.exec(line) || [""])[0]; if (/:\s*$/.test(line)) ind += "    ";
      if (ind) { e.preventDefault(); ed.setRangeText("\n" + ind, s, ed.selectionEnd, "end"); ed.dispatchEvent(new Event("input")); }
    }
  });
  runB.onclick = run; stopB.onclick = stop;
  $("#lab-reset").onclick = () => { store.del(KEY(cur)); ed.value = src[cur] || ""; lines(); $("#lab-dirty").hidden = true; };
  $("#lab-copy").onclick = async e => { const b = e.currentTarget; try { await navigator.clipboard.writeText(ed.value); b.textContent = "Скопировано"; } catch (err) { ed.select(); b.textContent = "Выделено"; } setTimeout(() => b.textContent = "Копировать", 1600); };
  $("#lab-clear").onclick = () => { out.textContent = ""; };
  $$("[data-copy]").forEach(b => b.onclick = async () => { try { await navigator.clipboard.writeText(b.dataset.copy); b.textContent = "Скопировано"; } catch (e) { b.textContent = "Выделите вручную"; } setTimeout(() => b.textContent = "Копировать", 1600); });

  load(cur); boot();
})();
