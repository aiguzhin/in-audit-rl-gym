/* FinSpector · живая страница книги на главной.
   Лист собран из узких полос, соединённых «шарнирами». Каждый шарнир — пружина с затуханием:
   на полосы действуют инерция (лист отстаёт от руки), сила тяжести (стремится уложить лист)
   и столкновение с разворотом (бумага не проходит сквозь страницы). Отсюда изгиб, волна и мягкая посадка. */
(function () {
  const book = document.querySelector(".book3");
  if (!book || !window.BOOK_PAGE) return;
  const N = 12;                                        // полос в листе
  const L = book.querySelector("#bpL"), R = book.querySelector("#bpR");
  let n = 0;                                           // номер разворота

  // ---------- сборка листа ----------
  const leaf = document.createElement("div"); leaf.className = "leaf2";
  let parent = leaf; const strips = [];
  for (let i = 0; i < N; i++) {
    const s = document.createElement("div"); s.className = "st" + (i ? "" : " st0");
    s.innerHTML = `<div class="fc f"><div class="cut"><div class="pw"><div class="pg"></div></div></div><i class="sh"></i></div>
                   <div class="fc b"><div class="cut"><div class="pw"><div class="pg"></div></div></div><i class="sh"></i></div>`;
    parent.append(s); parent = s; strips.push(s);
  }
  book.insertBefore(leaf, book.querySelector(".ribbon"));
  const fronts = strips.map(s => s.querySelector(".f .pg")), backs = strips.map(s => s.querySelector(".b .pg"));
  const shF = strips.map(s => s.querySelector(".f .sh")), shB = strips.map(s => s.querySelector(".b .sh"));
  const castR = document.createElement("i"); castR.className = "cast r"; R.append(castR);
  const castL = document.createElement("i"); castL.className = "cast l"; L.append(castL);

  function layout() {
    const W = leaf.getBoundingClientRect().width / Math.max(.01, Math.abs(Math.cos(0))) || R.offsetWidth;
    const w = R.offsetWidth || W;
    strips.forEach((s, i) => {
      s.querySelector(".f .pw").style.cssText = `width:${w}px;left:${-i * w / N}px`;
      s.querySelector(".b .pw").style.cssText = `width:${w}px;left:${-(N - 1 - i) * w / N}px`;
    });
  }
  function fill() {                                   // содержимое страниц разворота n
    L.querySelectorAll(":scope > :not(.cast)").forEach(x => x.remove());
    R.querySelectorAll(":scope > :not(.cast)").forEach(x => x.remove());
    L.insertAdjacentHTML("afterbegin", BOOK_PAGE(2 * n - 1));
    R.insertAdjacentHTML("afterbegin", BOOK_PAGE(2 * n + 2));   // под листом — следующая правая страница
    const fh = BOOK_PAGE(2 * n), bh = BOOK_PAGE(2 * n + 1);
    fronts.forEach(p => p.innerHTML = fh); backs.forEach(p => p.innerHTML = bh);
  }

  // ---------- физика ----------
  const K = 210, C = 10.5, G = 1100, INERTIA = 2.6, TURN = 1.9, REST = 2.6, SETTLE = 1.6;
  const rho = new Float64Array(N), vel = new Float64Array(N);   // rho[0] не используется: это основание (рука)
  const mass = i => (N - i) / N;                                // какая доля листа «висит» за шарниром
  const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  let t0 = performance.now(), phase = "rest", base = 0, baseV = 0;
  const theta = new Float64Array(N);

  function baseAt(t) { return 180 * ease(Math.min(1, Math.max(0, t / TURN))); }
  function step(dt, tTurn) {
    const b0 = base, nb = phase === "turn" ? baseAt(tTurn) : phase === "settle" ? 180 : 0;
    const nv = (nb - b0) / dt, acc = (nv - baseV) / dt;
    base = nb; baseV = nv;
    let cum = base;
    for (let i = 1; i < N; i++) {
      const th = cum + rho[i];
      const g = -G * Math.cos(th * Math.PI / 180) * mass(i);          // тяжесть укладывает лист к ближайшей стороне
      const a = -K * rho[i] - C * vel[i] + g - INERTIA * acc * mass(i) * .08;
      vel[i] += a * dt; rho[i] += vel[i] * dt;
      let t = cum + rho[i];
      if (t < .4) { rho[i] = .4 - cum; if (vel[i] < 0) vel[i] *= -.15; t = .4; }        // не проходит сквозь правую страницу
      if (t > 179.6) { rho[i] = 179.6 - cum; if (vel[i] > 0) vel[i] *= -.15; t = 179.6; } // и сквозь левую
      cum = t;
    }
  }
  function render() {
    let cum = base;
    strips[0].style.transform = `translateZ(1.4px) rotateY(${-base}deg)`;
    theta[0] = base;
    for (let i = 1; i < N; i++) { strips[i].style.transform = `rotateY(${-rho[i]}deg)`; cum += rho[i]; theta[i] = cum; }
    for (let i = 0; i < N; i++) {                                     // освещение: свет сверху
      const c = Math.cos(theta[i] * Math.PI / 180), s = Math.sin(theta[i] * Math.PI / 180);
      shF[i].style.opacity = (Math.max(0, 1 - c) * .32 + s * .06).toFixed(3);
      shB[i].style.opacity = (Math.max(0, 1 + c) * .32 + s * .06).toFixed(3);
    }
    const lift = Math.sin(base * Math.PI / 180);
    castR.style.opacity = (base < 90 ? lift * .55 : 0).toFixed(3);
    castL.style.opacity = (base >= 90 ? lift * .55 : 0).toFixed(3);
  }

  let raf = 0, visible = true, last = performance.now();
  function frame(now) {
    raf = 0;
    let dt = Math.min(.05, (now - last) / 1000); last = now;
    const el = (now - t0) / 1000;
    if (phase === "rest" && el > REST) { phase = "turn"; t0 = now; }
    else if (phase === "turn" && el > TURN) { phase = "settle"; t0 = now; }
    else if (phase === "settle" && el > SETTLE) {                     // лист лёг: незаметно переносим его направо со следующими страницами
      phase = "rest"; t0 = now; n++; base = 0; baseV = 0; rho.fill(0); vel.fill(0); fill();
    }
    const tt = (now - t0) / 1000;
    const sub = Math.max(1, Math.ceil(dt / (1 / 240)));
    for (let k = 0; k < sub; k++) step(dt / sub, tt - dt + (k + 1) * dt / sub);
    render();
    if (visible && !document.hidden) raf = requestAnimationFrame(frame);
  }
  function start() { if (!raf && visible && !document.hidden) { last = performance.now(); raf = requestAnimationFrame(frame); } }

  layout(); fill(); render();
  addEventListener("resize", () => { layout(); });
  if (UI.reduce) return;
  new IntersectionObserver(es => { visible = es[0].isIntersecting; if (visible) { t0 = performance.now() - 0; start(); } }).observe(book);
  document.addEventListener("visibilitychange", start);
  start();
})();
