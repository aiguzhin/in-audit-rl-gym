/* Общий код: меню, переходы между страницами, прогресс, появление, счётчики, утилиты. */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const exps = Object.assign({ USD: 2, EUR: 2, GBP: 2, KZT: 2, CNY: 2, JPY: 0, KWD: 3 }, (window.D && D.manifest.currency_exponents) || {});
  const money = (minor, cur) => { const e = exps[cur] ?? 2;
    return (minor / Math.pow(10, e)).toLocaleString("ru-RU", { minimumFractionDigits: e, maximumFractionDigits: e }) + " " + cur; };
  const typeRu = { duplicate_invoice: "Дубль счёта", missing_or_partial_allocation: "Неполное разнесение",
    fx_conversion_error: "Неверный курс", period_cutoff_error: "Не тот период" };
  const evAll = new Set();
  if (window.D) D.truth.forEach(i => i.evidence_sets.forEach(s => s.forEach(x => evAll.add(x))));

  // меню
  const burger = $(".burger"), menu = $("nav.menu");
  if (burger) burger.addEventListener("click", () => { const o = menu.classList.toggle("open"); burger.setAttribute("aria-expanded", o); burger.textContent = o ? "Закрыть" : "Меню"; });

  // плавный уход со страницы
  $$("a[href$='.html']").forEach(a => a.addEventListener("click", e => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || a.target) return;
    const href = a.getAttribute("href");
    if (href === location.pathname.split("/").pop()) return;
    e.preventDefault(); if (reduce) { location.href = href; return; }
    document.body.classList.add("leaving"); setTimeout(() => { location.href = href; }, 260);
  }));
  addEventListener("pageshow", e => { if (e.persisted) document.body.classList.remove("leaving"); });

  // заголовки по строкам
  $$("h1.title").forEach(h => { const lines = h.innerHTML.split("<br>");
    h.innerHTML = lines.map((l, i) => `<span class="ln"><span style="--i:${i}">${l}</span></span>`).join(""); });

  // появление
  const ro = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("seen"); ro.unobserve(e.target); } }),
    { threshold: .12, rootMargin: "0px 0px -30px 0px" });
  $$("[data-r]").forEach(el => ro.observe(el));

  // прогресс + подвал
  const prog = $(".progress"), foot = $(".big-foot");
  let onScroll = function () { const h = document.documentElement; const p = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
    if (prog) prog.style.transform = `scaleX(${p})`;
    if (foot && !reduce) { const r = foot.getBoundingClientRect(); foot.style.transform = `translateX(${(r.top - innerHeight) * .3}px)`; } };
  const top = $(".totop"); if (top) top.onclick = () => scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
  const _onScroll = onScroll; onScroll = function(){ _onScroll(); if (top) top.classList.toggle("show", scrollY > 700); };
  addEventListener("scroll", () => onScroll(), { passive: true }); onScroll();

  function countUp(el, to, dur = 1300, dec = 0) {
    if (reduce) { el.textContent = to.toFixed(dec); return; }
    const t0 = performance.now();
    (function f(t) { const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = (to * e).toFixed(dec); if (p < 1) requestAnimationFrame(f); })(t0);
  }
  function onView(el, fn, threshold = .35) { if (!el) return;
    const o = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { fn(); o.disconnect(); } }), { threshold }); o.observe(el); }

  // мягкая подсветка карточки и панели под курсором (обновляем только их — без пересчёта всей страницы)
  if (!reduce && matchMedia("(pointer:fine)").matches) {
    let raf = 0, ev = null, lastG = null, lastP = null;
    const set = (el, x, y) => { el.style.setProperty("--mx", x + "px"); el.style.setProperty("--my", y + "px"); };
    addEventListener("pointermove", e => { ev = e; if (raf) return; raf = requestAnimationFrame(() => { raf = 0;
      const t = ev.target instanceof Element ? ev.target : null;
      const g = t && t.closest(".glass"), p = t && t.closest(".panel");
      if (lastG && lastG !== g) set(lastG, -999, -999);
      if (g) { const r = g.getBoundingClientRect(); set(g, ev.clientX - r.left, ev.clientY - r.top); }
      if (p) { const r = p.getBoundingClientRect(); set(p, ev.clientX - r.left, ev.clientY - r.top); }
      if (lastP && lastP !== p) set(lastP, -999, -999);
      lastG = g; lastP = p; }); }, { passive: true });
  }

  window.UI = { $, $$, esc, money, typeRu, evAll, countUp, onView, reduce };
})();
