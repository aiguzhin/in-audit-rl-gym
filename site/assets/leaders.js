/* Таблица лидеров: всё время и «компания дня». */
(function () {
  const { $, $$, esc } = UI;
  const PRESET_RU = { mixed: "обычная", inter: "взаимодействие", clean: "чистая", single: "по одной" };
  let scope = "daily";
  async function load() {
    const box = $("#lb-body");
    box.innerHTML = '<p class="empty"><span class="spin"></span> Загружаем… Бесплатный сервер просыпается до минуты.</p>';
    try {
      const [b, s] = await Promise.all([AUTH.api("/api/leaderboard?limit=50&scope=" + scope, { auth: false }), AUTH.api("/api/stats", { auth: false })]);
      $("#lb-stats").innerHTML = [["Прохождений", s.runs], ["Сегодня", s.today], ["Профилей", s.users],
        ["Лучший балл", s.runs ? (s.best_reward > 0 ? "+" : "") + s.best_reward.toFixed(3) : "—"]].map(([k, v]) => `<div class="glass"><span class="label">${k}</span><b>${v}</b></div>`).join("");
      $("#lb-day").innerHTML = scope === "daily" ? `Компания дня на ${new Date(b.day).toLocaleDateString("ru-RU", { day: "numeric", month: "long" })}: <b>№${b.daily_seed}</b> · <a href="play.html?daily=1">Пройти сейчас →</a>` : "Лучшие результаты на любых компаниях.";
      const me = (AUTH.user() || {}).display;
      box.innerHTML = b.results.length ? `<table class="grid board big rank"><thead><tr><th>#</th><th>Участник</th><th>Награда</th><th>F1</th><th>TP / FP / FN</th><th>Шаги</th><th>Компания</th></tr></thead><tbody>
        ${b.results.map((r, i) => `<tr class="${r.name === me && r.registered ? "mine" : ""}" style="--k:${Math.min(i, 20)}"><td>${i + 1}</td><td>${esc(r.name)}${r.registered ? ' <span class="tag-ok" title="Зарегистрированный участник">✓</span>' : ""}</td>
          <td class="num"><em class="${r.reward < 0 ? "neg" : "pos"}">${r.reward > 0 ? "+" : ""}${r.reward.toFixed(3)}</em></td><td class="num">${(r.f1 ?? 0).toFixed(2)}</td>
          <td>${r.tp} / ${r.fp} / ${r.fn}</td><td class="num">${r.steps}</td><td>№${r.seed} · ${PRESET_RU[r.preset] || r.preset}</td></tr>`).join("")}</tbody></table>`
        : `<div class="empty-state"><b>${scope === "daily" ? "Сегодня ещё никто не прошёл компанию дня" : "Пока нет результатов"}</b><p>Станьте первым в таблице.</p><a class="btn" href="play.html${scope === "daily" ? "?daily=1" : ""}">Начать аудит <span class="arr">→</span></a></div>`;
    } catch (e) { box.innerHTML = `<p class="empty">${esc(e.message)} <button class="chip" id="lb-retry">Повторить</button></p>`; $("#lb-retry").onclick = load; }
  }
  $$(".seg button").forEach(b => b.onclick = () => { scope = b.dataset.s; $$(".seg button").forEach(x => x.setAttribute("aria-selected", x === b)); load(); });
  load();
})();
