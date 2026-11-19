/* Общий код: меню, переходы между страницами, прогресс, появление, счётчики, утилиты. */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const exps = (window.D && D.manifest.currency_exponents) || {};
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

  // ---------- фон с книгами ----------
  (function () {
    const closed = (w = 120, h = 160) => `<svg viewBox="0 0 ${w} ${h}" fill="none" stroke="currentColor" stroke-width="2"><rect x="10" y="6" width="${w - 20}" height="${h - 12}" rx="6"/><path d="M24 6v${h - 12}"/><rect x="38" y="30" width="${w - 62}" height="26" rx="3"/><path d="M44 40h${w - 74}M44 47h${w - 90}"/><path d="M38 ${h - 34}h${w - 62}M38 ${h - 26}h${w - 80}"/><path d="M${w - 30} 6v40l8-7 8 7V6" fill="currentColor" fill-opacity=".25"/></svg>`;
    const open = () => `<svg viewBox="0 0 220 140" fill="none" stroke="currentColor" stroke-width="2"><path d="M110 22C80 8 40 8 12 16v108c28-8 68-8 98 6 30-14 70-14 98-6V16C180 8 140 8 110 22z"/><path d="M110 22v108"/>${[0,1,2,3,4,5,6].map(i => `<path d="M26 ${40 + i * 12}h${64 - (i % 3) * 10}M130 ${40 + i * 12}h${64 - ((i + 1) % 3) * 10}"/>`).join("")}<ellipse cx="160" cy="76" rx="34" ry="11" stroke-width="2.4"/></svg>`;
    const stack = () => `<svg viewBox="0 0 200 130" fill="none" stroke="currentColor" stroke-width="2"><rect x="20" y="86" width="168" height="30" rx="4"/><path d="M34 86v30M160 96h16M160 104h10"/><rect x="10" y="54" width="160" height="30" rx="4" transform="rotate(-3 90 69)"/><path d="M26 56v28" transform="rotate(-3 90 69)"/><rect x="30" y="22" width="150" height="30" rx="4" transform="rotate(4 105 37)"/><path d="M46 22v30M120 32h40M120 40h28" transform="rotate(4 105 37)"/></svg>`;
    const items = [
      [closed(), "6%", "16%", 120, 22, -8, 6, ""], [open(), "78%", "8%", 230, 26, 3, -4, ""], [stack(), "84%", "62%", 200, 30, -4, 3, ""],
      [closed(140, 180), "2%", "70%", 130, 24, 10, -2, ""], [open(), "34%", "86%", 200, 28, -2, 5, "red"], [closed(), "56%", "40%", 90, 20, 14, 2, ""],
      [stack(), "18%", "44%", 150, 34, 2, -6, ""], [closed(), "92%", "30%", 80, 19, -14, -4, "red"]];
    const host = document.createElement("div"); host.className = "bg-books"; host.setAttribute("aria-hidden", "true");
    host.innerHTML = `<div class="lines"></div><div class="margin"></div>` + items.map(([svg, x, y, w, dur, r0, r1, cls], i) =>
      `<div class="bk ${cls}" data-sp="${(.04 + (i % 4) * .035).toFixed(3)}" style="left:${x};top:${y};width:${w}px;--dur:${dur}s;--del:${-i * 2.3}s;--r0:${r0}deg;--r1:${r1}deg">${svg}</div>`).join("");
    document.body.prepend(host);
    if (reduce) return;
    const bks = [...host.querySelectorAll(".bk")]; let mx = 0, my = 0, raf = 0;
    function apply() { raf = 0; const y = scrollY; bks.forEach((b, i) => { const s = +b.dataset.sp;
      b.style.transform = `translate3d(${mx * s * 120}px, ${-y * s + my * s * 80}px, 0)`; }); }
    addEventListener("scroll", () => { if (!raf) raf = requestAnimationFrame(apply); }, { passive: true });
    addEventListener("pointermove", e => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; if (!raf) raf = requestAnimationFrame(apply); }, { passive: true });
  })();

  window.UI = { $, $$, esc, money, typeRu, evAll, countUp, onView, reduce };
})();
