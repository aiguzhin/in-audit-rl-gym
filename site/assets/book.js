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
  const faceF = strips.map(s => s.querySelector(".fc.f")), faceB = strips.map(s => s.querySelector(".fc.b"));
  const side = new Int8Array(N).fill(-1);             // какая сторона полосы сейчас показана (Safari не всегда прячет обратную)
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
  const put = (el, html) => { if (el._h !== html) { el._h = html; el.innerHTML = html; } };
  const setPage = (P, k) => { const h = BOOK_PAGE(k); if (P._h === h) return; P._h = h; P.querySelectorAll(":scope > :not(.cast)").forEach(x => x.remove()); P.insertAdjacentHTML("afterbegin", h); };
  const setLeaf = () => { const fh = BOOK_PAGE(2 * n), bh = BOOK_PAGE(2 * n + 1); fronts.forEach(p => put(p, fh)); backs.forEach(p => put(p, bh)); };
  function fill() { setPage(L, 2 * n - 1); setPage(R, 2 * n + 2); setLeaf(); }


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
      if (t < 0) { rho[i] = -cum; if (vel[i] < 0) vel[i] = 0; t = 0; }              // не проходит сквозь правую страницу — ложится на неё
      if (t > 180) { rho[i] = 180 - cum; if (vel[i] > 0) vel[i] = 0; t = 180; }      // и сквозь левую
      cum = t;
    }
  }
  function render() {
    let cum = base;
    strips[0].style.transform = `translateZ(1.4px) rotateY(${-base}deg)`;
    theta[0] = base;
    for (let i = 1; i < N; i++) { strips[i].style.transform = `rotateY(${-rho[i]}deg)`; cum += rho[i]; theta[i] = cum; }
    for (let i = 0; i < N; i++) {                                     // показываем только сторону, обращённую к зрителю
      const s = theta[i] < 90 ? 0 : 1;
      if (side[i] !== s) { side[i] = s; faceF[i].style.visibility = s ? "hidden" : "visible"; faceB[i].style.visibility = s ? "visible" : "hidden"; }
    }
    for (let i = 0; i < N; i++) {                                     // освещение: свет сверху
      const c = Math.cos(theta[i] * Math.PI / 180), s = Math.sin(theta[i] * Math.PI / 180);
      shF[i].style.opacity = (Math.max(0, 1 - c) * .32 + s * .06).toFixed(3);
      shB[i].style.opacity = (Math.max(0, 1 + c) * .32 + s * .06).toFixed(3);
    }
    const lift = Math.sin(base * Math.PI / 180);
    castR.style.opacity = (base < 90 ? lift * .55 : 0).toFixed(3);
    castL.style.opacity = (base >= 90 ? lift * .55 : 0).toFixed(3);
  }

  // Смена разворота без рывка: под лёгшим листом уже та же страница → лист плавно растворяется,
  // возвращается направо (там под ним та же страница) и плавно проявляется. Глаз не видит подмены.
  function swap() {
    phase = "swap"; setPage(L, 2 * n + 1);
    leaf.style.opacity = "0";
    setTimeout(() => {
      n++; base = 0; baseV = 0; rho.fill(0); vel.fill(0); setLeaf(); render();
      leaf.style.opacity = "1";
      setTimeout(() => { setPage(R, 2 * n + 2); phase = "rest"; t0 = performance.now(); }, 260);
    }, 260);
  }
  let raf = 0, visible = true, last = performance.now();
  function frame(now) {
    raf = 0;
    const dt = Math.min(.05, (now - last) / 1000); last = now;
    const el = (now - t0) / 1000;
    if (phase === "swap") { /* ждём завершения плавной подмены */ }
    else if (phase === "rest") {                                          // лист лежит: ничего не считаем и не перерисовываем — никакой дрожи
      if (el > REST) { phase = "turn"; t0 = now; }
    } else {
      if (phase === "turn" && el > TURN) { phase = "settle"; t0 = now; }
      const tt = (now - t0) / 1000;
      const sub = Math.max(1, Math.ceil(dt / (1 / 240)));
      for (let k = 0; k < sub; k++) step(dt / sub, tt - dt + (k + 1) * dt / sub);
      render();
      if (phase === "settle") {
        let still = true; for (let i = 1; i < N; i++) if (Math.abs(vel[i]) > 12 || theta[i] < 179.2) still = false;
        if ((still && tt > .35) || tt > SETTLE) {                     // лист лёг ровно — незаметно переносим его направо со следующими страницами
          swap();
        }
      }
    }
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
