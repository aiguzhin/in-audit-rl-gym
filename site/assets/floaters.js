/* Парящие 3D-предметы для аудита и расчётов на фоне панелей.
   Все модели — векторные: изометрическая проекция граней, градиенты, блики, синий контровой свет. */
(function () {
  if (!window.UI) return;
  const reduce = UI.reduce;
  let uid = 0;

  // ---------- геометрия: изометрическая грань (u,v ∈ [0,1]) ----------
  const face = (o, a, b) => (u, v) => [o[0] + a[0] * u + b[0] * v, o[1] + a[1] * u + b[1] * v];
  const pt = p => p[0].toFixed(1) + "," + p[1].toFixed(1);
  const quad = (f, u0, v0, u1, v1) => [f(u0, v0), f(u1, v0), f(u1, v1), f(u0, v1)].map(pt).join(" ");
  const ext = (p, t) => [p[0] + t[0], p[1] + t[1]];
  const onFace = (o, a, b, inner) => `<g transform="matrix(${a[0]} ${a[1]} ${b[0]} ${b[1]} ${o[0]} ${o[1]})">${inner}</g>`;
  const ftxt = (u, v, s, txt, fill, opts = "") => `<text transform="translate(${u} ${v}) scale(${s * 1.3} ${s})" font-size="1" fill="${fill}" ${opts}>${txt}</text>`;
  const side = (p1, p2, t) => [p1, p2, ext(p2, t), ext(p1, t)].map(pt).join(" ");

  // ---------- общие фильтры ----------
  const defsCommon = id => `
    <filter id="${id}sh" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="14" stdDeviation="10" flood-color="#000" flood-opacity=".55"/></filter>
    <radialGradient id="${id}glow"><stop offset="0" stop-color="#4A90FF" stop-opacity=".45"/><stop offset="1" stop-color="#4A90FF" stop-opacity="0"/></radialGradient>`;

  // ================================================================ МОДЕЛИ
  function book(id, cover = ["#1E3A66", "#0B1830"], title = "LEDGER") {
    const o = [42, 26], a = [138, 30], b = [-34, 62], t = [0, 24], f = face(o, a, b);
    const P = [f(0, 0), f(1, 0), f(1, 1), f(0, 1)];
    let lines = ""; for (let i = 1; i < 9; i++) { const k = i / 9; lines += `<line x1="${pt(ext(P[3], [0, t[1] * k])).split(",")[0]}" y1="${ext(P[3], [0, t[1] * k])[1]}" x2="${ext(P[2], [0, t[1] * k])[0]}" y2="${ext(P[2], [0, t[1] * k])[1]}" stroke="#CBBE9E" stroke-width=".6" opacity=".7"/>`; }
    return `<svg viewBox="0 0 220 170"><defs>${defsCommon(id)}
      <linearGradient id="${id}c" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${cover[0]}"/><stop offset=".55" stop-color="${cover[1]}"/><stop offset="1" stop-color="#050A14"/></linearGradient>
      <linearGradient id="${id}p" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F6F0E0"/><stop offset="1" stop-color="#C9BC9C"/></linearGradient>
      <linearGradient id="${id}r" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#E9E0C8"/><stop offset="1" stop-color="#B7AA88"/></linearGradient>
      <linearGradient id="${id}hl" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".4" stop-color="#fff" stop-opacity="0"/></linearGradient>
      <linearGradient id="${id}rim" x1="0" y1="0" x2="1" y2="0"><stop offset=".6" stop-color="#7FB2FF" stop-opacity="0"/><stop offset="1" stop-color="#9CC6FF" stop-opacity=".8"/></linearGradient>
      <linearGradient id="${id}foil" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8FA9D6"/><stop offset=".5" stop-color="#E6EEFF"/><stop offset="1" stop-color="#8FA9D6"/></linearGradient></defs>
      <ellipse cx="110" cy="150" rx="88" ry="12" fill="url(#${id}glow)"/>
      <g filter="url(#${id}sh)">
        <polygon points="${side(P[3], P[2], t)}" fill="url(#${id}p)"/>${lines}
        <polygon points="${side(P[2], P[1], t)}" fill="url(#${id}r)"/>
        <polygon points="${side(ext(P[3], [0, t[1]]), ext(P[2], [0, t[1]]), [0, 3])}" fill="#0A1426"/>
        <polygon points="${side(ext(P[2], [0, t[1]]), ext(P[1], [0, t[1]]), [0, 3])}" fill="#0A1426"/>
        <polygon points="${side(P[0], P[3], [0, t[1] + 3])}" fill="#08101F"/>
        <polygon points="${quad(f, -0.02, -0.03, 1.02, 1.03)}" fill="url(#${id}c)"/>
        <polygon points="${quad(f, 0, 0, 0.09, 1)}" fill="#050B16" opacity=".55"/>
        <polygon points="${quad(f, 0.03, 0.15, 0.06, 0.2)}" fill="#3A5A8F" opacity=".7"/><polygon points="${quad(f, 0.03, 0.8, 0.06, 0.85)}" fill="#3A5A8F" opacity=".7"/>
        <polygon points="${quad(f, 0.16, 0.08, 0.95, 0.92)}" fill="none" stroke="#6F8FC4" stroke-opacity=".35" stroke-width="1"/>
        <polygon points="${quad(f, 0.32, 0.3, 0.82, 0.52)}" fill="url(#${id}foil)" opacity=".85"/>
        <polygon points="${quad(f, 0.36, 0.6, 0.78, 0.64)}" fill="#8FA9D6" opacity=".55"/><polygon points="${quad(f, 0.42, 0.7, 0.72, 0.73)}" fill="#8FA9D6" opacity=".4"/>
        <polygon points="${quad(f, 0.7, -0.02, 0.76, 1.25)}" fill="#C8372D"/><polygon points="${pt(f(0.7, 1.25))} ${pt(f(0.73, 1.18))} ${pt(f(0.76, 1.25))}" fill="#0000"/>
        <polygon points="${quad(f, -0.02, -0.03, 1.02, 1.03)}" fill="url(#${id}hl)"/>
        <polygon points="${quad(f, -0.02, -0.03, 1.02, 1.03)}" fill="url(#${id}rim)"/>
      </g></svg>`;
  }

  function calculator(id) {
    const o = [58, 18], a = [96, 24], b = [-40, 122], t = [0, 12], f = face(o, a, b);
    const P = [f(0, 0), f(1, 0), f(1, 1), f(0, 1)];
    let keys = "";
    const labels = ["7", "8", "9", "÷", "4", "5", "6", "×", "1", "2", "3", "−", "0", ".", "=", "+"];
    for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) {
      const u0 = 0.08 + c * 0.225, v0 = 0.42 + r * 0.135, u1 = u0 + 0.19, v1 = v0 + 0.105;
      const op = c === 3, eq = r === 3 && c === 2;
      const fill = eq ? `url(#${id}ka)` : op ? `url(#${id}ko)` : `url(#${id}k)`;
      keys += `<polygon points="${quad(f, u0, v0 + 0.012, u1, v1 + 0.012)}" fill="#02050B" opacity=".7"/><polygon points="${quad(f, u0, v0, u1, v1)}" fill="${fill}"/>
        <polygon points="${quad(f, u0 + 0.01, v0 + 0.008, u1 - 0.01, v0 + 0.03)}" fill="#fff" opacity=".18"/>`;
      keys += onFace(o, a, b, ftxt(u0 + 0.095, v0 + 0.08, 0.055, labels[r * 4 + c], eq ? "#05080F" : "#DCE8FF", 'font-family="Inter Tight,sans-serif" font-weight="600" text-anchor="middle"'));
    }
    return `<svg viewBox="0 0 170 190"><defs>${defsCommon(id)}
      <linearGradient id="${id}b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3A4A66"/><stop offset=".5" stop-color="#1A2436"/><stop offset="1" stop-color="#0A0F19"/></linearGradient>
      <linearGradient id="${id}s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#B7D79A"/><stop offset="1" stop-color="#7FA36A"/></linearGradient>
      <linearGradient id="${id}k" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4C5D7C"/><stop offset="1" stop-color="#2A3650"/></linearGradient>
      <linearGradient id="${id}ko" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3E7BE0"/><stop offset="1" stop-color="#1D4FA8"/></linearGradient>
      <linearGradient id="${id}ka" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#BFD3F5"/></linearGradient>
      <linearGradient id="${id}hl" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset=".35" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
      <ellipse cx="85" cy="176" rx="70" ry="10" fill="url(#${id}glow)"/>
      <g filter="url(#${id}sh)">
        <polygon points="${side(P[3], P[2], t)}" fill="#0A0F19"/><polygon points="${side(P[2], P[1], t)}" fill="#141C2B"/>
        <polygon points="${side(P[3], P[2], [0, 2])}" fill="#7FB2FF" opacity=".25"/>
        <polygon points="${quad(f, 0, 0, 1, 1)}" fill="url(#${id}b)"/>
        <polygon points="${quad(f, 0.06, 0.05, 0.94, 0.32)}" fill="#0B1220"/>
        <polygon points="${quad(f, 0.1, 0.09, 0.9, 0.27)}" fill="url(#${id}s)"/>
        <polygon points="${quad(f, 0.1, 0.09, 0.9, 0.12)}" fill="#000" opacity=".18"/>
        ${onFace(o, a, b, ftxt(0.86, 0.225, 0.075, "93 049", "#1D2B12", 'font-family="JetBrains Mono,monospace" font-weight="700" text-anchor="end"'))}
        <polygon points="${quad(f, 0.55, 0.34, 0.93, 0.385)}" fill="#3B2A12"/><polygon points="${quad(f, 0.57, 0.348, 0.91, 0.377)}" fill="#6B4A1E" opacity=".8"/>
        ${keys}
        <polygon points="${quad(f, 0, 0, 1, 1)}" fill="url(#${id}hl)"/>
      </g></svg>`;
  }

  function coins(id) {
    let s = "";
    const stack = (cx, base, n, tilt) => { for (let i = 0; i < n; i++) { const y = base - i * 7, dx = Math.sin(i * 1.7) * tilt;
      s += `<ellipse cx="${cx + dx}" cy="${y + 3.5}" rx="30" ry="9.5" fill="url(#${id}e)"/>${[...Array(18)].map((_, k) => { const ang = Math.PI * (k / 17); const x = cx + dx - 30 * Math.cos(ang);
        return `<line x1="${x.toFixed(1)}" y1="${(y + 3.5 + 9.5 * Math.sin(ang) * .2).toFixed(1)}" x2="${x.toFixed(1)}" y2="${(y + 3.5 + 9.5 * Math.sin(ang)).toFixed(1)}" stroke="#8A6A1E" stroke-width=".6" opacity=".55"/>`; }).join("")}
        <ellipse cx="${cx + dx}" cy="${y}" rx="30" ry="9.5" fill="url(#${id}t)"/><ellipse cx="${cx + dx}" cy="${y}" rx="23" ry="7" fill="none" stroke="#B98A2A" stroke-width="1" opacity=".7"/>`; }
      const top = base - (n - 1) * 7; s += `<text x="${cx + Math.sin((n - 1) * 1.7) * tilt}" y="${top + 3.5}" font-family="Inter Tight,sans-serif" font-size="11" font-weight="700" fill="#8A6414" text-anchor="middle" transform="scale(1 .45)" style="transform-box:fill-box;transform-origin:center">₸</text>`; };
    stack(62, 128, 7, 1.6); stack(118, 140, 4, 1.2);
    return `<svg viewBox="0 0 180 170"><defs>${defsCommon(id)}
      <linearGradient id="${id}e" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7A5A14"/><stop offset=".35" stop-color="#E8C35A"/><stop offset=".55" stop-color="#FFF0B0"/><stop offset=".75" stop-color="#C99B32"/><stop offset="1" stop-color="#6B4E10"/></linearGradient>
      <radialGradient id="${id}t" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="#FFF4C4"/><stop offset=".45" stop-color="#F1CE6A"/><stop offset="1" stop-color="#B98A2A"/></radialGradient></defs>
      <ellipse cx="90" cy="152" rx="80" ry="11" fill="url(#${id}glow)"/><g filter="url(#${id}sh)">${s}</g></svg>`;
  }

  function magnifier(id) {
    return `<svg viewBox="0 0 200 200"><defs>${defsCommon(id)}
      <linearGradient id="${id}m" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F2F6FF"/><stop offset=".3" stop-color="#8E9BB4"/><stop offset=".55" stop-color="#E4EAF7"/><stop offset=".8" stop-color="#5E6A82"/><stop offset="1" stop-color="#C9D3E6"/></linearGradient>
      <radialGradient id="${id}l" cx=".4" cy=".35" r=".75"><stop offset="0" stop-color="#CFE4FF" stop-opacity=".35"/><stop offset=".7" stop-color="#4A90FF" stop-opacity=".12"/><stop offset="1" stop-color="#1A3A70" stop-opacity=".35"/></radialGradient>
      <linearGradient id="${id}h" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0E1626"/><stop offset=".4" stop-color="#3C4E70"/><stop offset=".6" stop-color="#22304A"/><stop offset="1" stop-color="#070C16"/></linearGradient>
      <clipPath id="${id}cp"><circle cx="72" cy="72" r="44"/></clipPath></defs>
      <ellipse cx="110" cy="186" rx="76" ry="9" fill="url(#${id}glow)"/>
      <g filter="url(#${id}sh)">
        <g transform="rotate(-45 72 72)"><rect x="66" y="122" width="13" height="16" rx="2" fill="url(#${id}m)"/><rect x="64.5" y="136" width="16" height="50" rx="7" fill="url(#${id}h)"/>
          <rect x="67" y="140" width="3" height="40" rx="1.5" fill="#fff" opacity=".18"/><rect x="64.5" y="150" width="16" height="2" fill="#000" opacity=".35"/><rect x="64.5" y="162" width="16" height="2" fill="#000" opacity=".35"/></g>
        <circle cx="72" cy="72" r="52" fill="url(#${id}m)"/><circle cx="72" cy="72" r="45.5" fill="#0B1424"/>
        <g clip-path="url(#${id}cp)"><rect x="20" y="20" width="110" height="110" fill="#F2EEE2" opacity=".9"/>
          ${[0, 1, 2, 3, 4].map(i => `<rect x="34" y="${42 + i * 13}" width="${50 - (i % 2) * 14}" height="4" rx="2" fill="#2A3A66" opacity=".55"/><rect x="${92 - (i % 3) * 4}" y="${42 + i * 13}" width="${18 + (i % 3) * 4}" height="4" rx="2" fill="#2A3A66" opacity=".7"/>`).join("")}
          <ellipse cx="98" cy="74" rx="20" ry="9" fill="none" stroke="#D2372B" stroke-width="2.4" transform="rotate(-6 98 74)"/>
          <circle cx="72" cy="72" r="45" fill="url(#${id}l)"/><path d="M38 52 Q50 30 76 28" stroke="#fff" stroke-width="5" stroke-linecap="round" fill="none" opacity=".55"/><path d="M44 62 Q48 52 56 46" stroke="#fff" stroke-width="2.5" stroke-linecap="round" fill="none" opacity=".4"/></g>
        <circle cx="72" cy="72" r="52" fill="none" stroke="#9CC6FF" stroke-width="1.2" opacity=".6"/>
      </g></svg>`;
  }

  function pen(id) {
    return `<svg viewBox="14 18 196 66"><defs>${defsCommon(id)}
      <linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4C6FAE"/><stop offset=".3" stop-color="#1B2F57"/><stop offset=".55" stop-color="#0B1630"/><stop offset=".8" stop-color="#22396A"/><stop offset="1" stop-color="#0A1226"/></linearGradient>
      <linearGradient id="${id}g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF6D2"/><stop offset=".45" stop-color="#D4A84A"/><stop offset="1" stop-color="#7A5A16"/></linearGradient>
      <linearGradient id="${id}n" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".5" stop-color="#B9C2D6"/><stop offset="1" stop-color="#6A748A"/></linearGradient></defs>
      <ellipse cx="110" cy="78" rx="92" ry="7" fill="url(#${id}glow)"/>
      <g filter="url(#${id}sh)" transform="rotate(-12 110 45)">
        <path d="M30 34 h120 a11 11 0 0 1 0 22 h-120 a11 11 0 0 1 0 -22z" fill="url(#${id}b)"/>
        <rect x="150" y="35.5" width="9" height="19" fill="url(#${id}g)"/><rect x="104" y="35.5" width="5" height="19" fill="url(#${id}g)"/>
        <path d="M48 31 h44 q4 0 4 4 v3 h-48z" fill="url(#${id}g)"/><circle cx="50" cy="35" r="3" fill="url(#${id}g)"/>
        <path d="M159 36.5 L188 43 Q194 45 188 47 L159 53.5z" fill="url(#${id}n)"/><line x1="166" y1="45" x2="190" y2="45" stroke="#3A4258" stroke-width=".9"/><circle cx="168" cy="45" r="1.6" fill="#3A4258"/>
        <path d="M30 37 h120" stroke="#fff" stroke-width="2.2" stroke-linecap="round" opacity=".35"/>
        <path d="M22 45 a11 11 0 0 1 8 -11 v22 a11 11 0 0 1 -8 -11z" fill="#0A1226"/>
      </g></svg>`;
  }

  function receipt(id) {
    const o = [40, 14], a = [96, 18], b = [-26, 130], f = face(o, a, b);
    let zig = ""; for (let i = 12; i >= 0; i--) { const u = i / 12; zig += pt(f(u, i % 2 ? 0.97 : 1)) + " "; }
    const rows = [["Услуги", "48 000"], ["Лицензия", "29 500"], ["Поддержка", "15 549"], ["НДС 12%", "11 166"]];
    const M = 'font-family="JetBrains Mono,monospace"', S = 'font-family="Inter Tight,sans-serif" font-weight="700"';
    let txt = ftxt(0.5, 0.11, 0.05, "ЧЕК № 0417", "#1A2236", S + ' text-anchor="middle"');
    rows.forEach((r, i) => { txt += ftxt(0.1, 0.26 + i * 0.11, 0.04, r[0], "#3A4258", M) + ftxt(0.9, 0.26 + i * 0.11, 0.04, r[1], "#1A2236", M + ' text-anchor="end"'); });
    txt += ftxt(0.1, 0.79, 0.05, "ИТОГО", "#1A2236", S) + ftxt(0.9, 0.79, 0.05, "104 215", "#D2372B", M + ' font-weight="700" text-anchor="end"');
    return `<svg viewBox="0 0 170 180"><defs>${defsCommon(id)}
      <linearGradient id="${id}p" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".7" stop-color="#ECE7DA"/><stop offset="1" stop-color="#D2CAB6"/></linearGradient>
      <linearGradient id="${id}c" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity=".18"/><stop offset=".15" stop-color="#000" stop-opacity="0"/></linearGradient></defs>
      <ellipse cx="85" cy="168" rx="64" ry="8" fill="url(#${id}glow)"/>
      <g filter="url(#${id}sh)"><polygon points="${pt(f(0, 0))} ${pt(f(1, 0))} ${zig}" fill="url(#${id}p)"/><polygon points="${pt(f(0, 0))} ${pt(f(1, 0))} ${zig}" fill="url(#${id}c)"/>
<polygon points="${quad(f, 0.1, 0.16, 0.9, 0.165)}" fill="#1A2236" opacity=".4"/>${onFace(o, a, b, txt)}
        <polygon points="${quad(f, 0.1, 0.7, 0.9, 0.705)}" fill="#1A2236" opacity=".5"/>
        ${[...Array(14)].map((_, i) => `<polygon points="${quad(f, 0.18 + i * 0.045, 0.86, 0.2 + i * 0.045 + (i % 3) * 0.01, 0.94)}" fill="#1A2236" opacity=".75"/>`).join("")}</g></svg>`;
  }

  function abacus(id) {
    let rods = ""; const colors = ["#E04A3A", "#F2F6FF", "#4A90FF"];
    for (let r = 0; r < 5; r++) { const y = 42 + r * 20; rods += `<rect x="30" y="${y - 1.2}" width="140" height="2.4" fill="url(#${id}rod)"/>`;
      const n = [6, 4, 7, 3, 5][r]; for (let k = 0; k < 10; k++) { const left = k < n; const x = left ? 42 + k * 10.5 : 158 - (9 - k) * 10.5; const col = colors[(r + (k > 4 ? 1 : 0)) % 3];
        rods += `<ellipse cx="${x}" cy="${y}" rx="5.4" ry="7.4" fill="url(#${id}bd${(r + (k > 4 ? 1 : 0)) % 3})"/><ellipse cx="${x - 1.6}" cy="${y - 3}" rx="1.6" ry="2.2" fill="#fff" opacity=".6"/>`; } }
    return `<svg viewBox="0 0 200 170"><defs>${defsCommon(id)}
      <linearGradient id="${id}fr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4A5A78"/><stop offset=".5" stop-color="#1A2436"/><stop offset="1" stop-color="#0A0F19"/></linearGradient>
      <linearGradient id="${id}rod" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E9EEF8"/><stop offset="1" stop-color="#6A748A"/></linearGradient>
      ${colors.map((c, i) => `<radialGradient id="${id}bd${i}" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset=".25" stop-color="${c}"/><stop offset="1" stop-color="#05080F"/></radialGradient>`).join("")}</defs>
      <ellipse cx="100" cy="160" rx="84" ry="9" fill="url(#${id}glow)"/>
      <g filter="url(#${id}sh)" transform="rotate(-8 100 85)"><rect x="18" y="22" width="164" height="118" rx="10" fill="url(#${id}fr)"/><rect x="28" y="30" width="144" height="102" rx="4" fill="#060B15"/>
        <rect x="18" y="22" width="164" height="118" rx="10" fill="none" stroke="#8FB8F5" stroke-opacity=".45"/>${rods}
        <rect x="20" y="24" width="160" height="6" rx="3" fill="#fff" opacity=".12"/></g></svg>`;
  }

  function stamp(id) {
    return `<svg viewBox="0 0 170 190"><defs>${defsCommon(id)}
      <radialGradient id="${id}k" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#8FB5F5"/><stop offset=".4" stop-color="#2A4F92"/><stop offset="1" stop-color="#091530"/></radialGradient>
      <linearGradient id="${id}n" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0A1226"/><stop offset=".4" stop-color="#3C5A92"/><stop offset="1" stop-color="#0A1226"/></linearGradient>
      <linearGradient id="${id}s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5C6680"/><stop offset=".5" stop-color="#E4EAF7"/><stop offset="1" stop-color="#5C6680"/></linearGradient></defs>
      <ellipse cx="85" cy="176" rx="70" ry="9" fill="url(#${id}glow)"/>
      <g opacity=".85" transform="translate(85 160) scale(1 .38)"><circle r="48" fill="none" stroke="#D2372B" stroke-width="5"/><circle r="38" fill="none" stroke="#D2372B" stroke-width="1.6"/>
        <text y="6" font-family="Inter Tight,sans-serif" font-size="12.5" font-weight="800" fill="#D2372B" text-anchor="middle">ПРОВЕРЕНО</text></g>
      <g filter="url(#${id}sh)"><circle cx="85" cy="38" r="26" fill="url(#${id}k)"/><ellipse cx="76" cy="27" rx="8" ry="5" fill="#fff" opacity=".45"/>
        <path d="M74 60 q11 6 22 0 l4 40 q-15 7 -30 0z" fill="url(#${id}n)"/>
        <path d="M44 104 q41 -14 82 0 v18 q-41 12 -82 0z" fill="url(#${id}s)"/><path d="M44 104 q41 -14 82 0 q-41 12 -82 0z" fill="#F2F6FF" opacity=".55"/>
        <path d="M48 122 q37 10 74 0 v8 q-37 10 -74 0z" fill="#8F1E16"/></g></svg>`;
  }

  function folder(id) {
    return `<svg viewBox="0 0 200 160"><defs>${defsCommon(id)}
      <linearGradient id="${id}f" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5D93E8"/><stop offset=".6" stop-color="#2459B5"/><stop offset="1" stop-color="#123672"/></linearGradient>
      <linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1D4A98"/><stop offset="1" stop-color="#0B2350"/></linearGradient>
      <linearGradient id="${id}hl" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".4" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
      <ellipse cx="100" cy="150" rx="84" ry="9" fill="url(#${id}glow)"/>
      <g filter="url(#${id}sh)" transform="rotate(-6 100 80)">
        <path d="M20 34 q0 -8 8 -8 h46 l12 12 h86 q8 0 8 8 v84 h-160z" fill="url(#${id}b)"/>
        <rect x="36" y="28" width="122" height="96" rx="3" fill="#F4F1E8" transform="rotate(-4 97 76)"/>
        <rect x="44" y="34" width="122" height="96" rx="3" fill="#FFFFFF" transform="rotate(3 105 82)"/>
        ${[0, 1, 2, 3].map(i => `<rect x="58" y="${48 + i * 11}" width="${70 - i * 8}" height="3.5" rx="1.7" fill="#2A3A66" opacity=".45" transform="rotate(3 105 82)"/>`).join("")}
        <path d="M14 62 q0 -8 8 -8 h158 q8 0 6 8 l-10 66 q-1 6 -8 6 h-140 q-7 0 -8 -6z" fill="url(#${id}f)"/>
        <path d="M14 62 q0 -8 8 -8 h158 q8 0 6 8 l-10 66 q-1 6 -8 6 h-140 q-7 0 -8 -6z" fill="url(#${id}hl)"/>
        <rect x="80" y="80" width="40" height="10" rx="5" fill="#fff" opacity=".22"/></g></svg>`;
  }

  function chartCard(id) {
    return `<svg viewBox="0 0 190 150"><defs>${defsCommon(id)}
      <linearGradient id="${id}g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity=".04"/></linearGradient>
      <linearGradient id="${id}bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#A9CBFF"/><stop offset="1" stop-color="#2F6FD8"/></linearGradient></defs>
      <ellipse cx="95" cy="140" rx="76" ry="8" fill="url(#${id}glow)"/>
      <g filter="url(#${id}sh)" transform="rotate(7 95 70)"><rect x="18" y="14" width="154" height="112" rx="16" fill="#0B1630" opacity=".55"/><rect x="18" y="14" width="154" height="112" rx="16" fill="url(#${id}g)" stroke="#fff" stroke-opacity=".28"/>
        <circle cx="38" cy="34" r="5" fill="#fff"/><rect x="50" y="31" width="44" height="6" rx="3" fill="#fff" opacity=".7"/>
        ${[34, 52, 40, 64, 58, 78].map((h, i) => `<rect x="${36 + i * 20}" y="${112 - h}" width="11" height="${h}" rx="3" fill="url(#${id}bar)" opacity="${.55 + i * .07}"/>`).join("")}
        <path d="M34 86 C 60 80, 74 60, 100 66 S 140 40, 158 30" fill="none" stroke="#E9F27A" stroke-width="2.4" stroke-linecap="round"/></g></svg>`;
  }

  const MODELS = { book, calculator, coins, magnifier, pen, receipt, abacus, stamp, folder, chartCard };
  const BOOK2 = id => book(id, ["#5A2330", "#24101A"], "AUDIT");
  const BOOK3 = id => book(id, ["#1F4A3A", "#0B1E17"], "2026");

  // ================================================================ СЦЕНЫ
  // [модель, left%, top%, ширина px, глубина 0..1 (1 — ближе), поворот°]
  const SCENES = {
    hero: [[book, 3, 10, 170, .55, -14], [calculator, 86, 52, 140, .75, 12], [coins, 4, 42, 120, .7, 0], [magnifier, 80, 6, 120, .4, -20],
           [pen, 38, 90, 160, .35, 8], [BOOK2, 66, 74, 150, .3, 18], [receipt, 92, 22, 110, .25, -8], [stamp, 22, 24, 84, .2, 10]],
    a: [[abacus, 2, 8, 170, .55, -6], [BOOK3, 86, 60, 160, .6, 14], [receipt, 82, 6, 120, .35, 10], [coins, 6, 70, 110, .3, 0], [pen, 46, 88, 150, .2, -6]],
    b: [[calculator, 4, 20, 130, .5, -10], [folder, 84, 8, 160, .55, 8], [magnifier, 88, 62, 120, .4, 16], [book, 10, 72, 140, .3, 12], [chartCard, 50, 4, 120, .2, -8]],
    c: [[stamp, 6, 12, 120, .55, -8], [BOOK2, 82, 14, 160, .6, 12], [coins, 86, 66, 120, .4, 0], [calculator, 2, 62, 120, .35, 16], [receipt, 46, 80, 110, .2, -10]],
    head: [[book, 70, 30, 150, .5, 12], [calculator, 90, 50, 110, .35, -10], [coins, 66, 64, 100, .25, 0], [pen, 54, 8, 140, .2, -10]],
  };

  function build(panel, scene) {
    const wrap = document.createElement("div"); wrap.className = "floaters"; wrap.setAttribute("aria-hidden", "true");
    SCENES[scene].forEach(([fn, x, y, w, depth, rot], i) => {
      const el = document.createElement("div"); el.className = "flo";
      const blur = depth < .3 ? 2.2 : depth < .45 ? 1 : 0;
      el.style.cssText = `left:${x}%;top:${y}%;width:${w * (.7 + depth * .5)}px;--rot:${rot}deg;--dep:${depth};--dur:${(16 + (1 - depth) * 14 + i * 1.3).toFixed(1)}s;--del:${(-i * 2.7).toFixed(1)}s;` +
        `opacity:${(.35 + depth * .55).toFixed(2)};filter:${blur ? `blur(${blur}px) ` : ""}saturate(${.8 + depth * .3});z-index:${Math.round(depth * 10)}`;
      el.innerHTML = `<div class="flo-in">${fn("f" + (uid++) + "_")}</div>`;
      wrap.append(el);
    });
    panel.prepend(wrap);
    return wrap;
  }

  const layers = [];
  document.querySelectorAll(".panel").forEach((p, i) => {
    let scene = p.dataset.float; if (!scene) return;
    if (innerWidth < 700) { const keep = scene === "hero" ? 4 : 2; SCENES[scene] = SCENES[scene].slice(0, keep); }
    layers.push(build(p, scene));
  });
  if (reduce || !layers.length) return;
  let mx = 0, my = 0, raf = 0;
  function apply() { raf = 0;
    layers.forEach(w => { const r = w.getBoundingClientRect(); if (r.bottom < -200 || r.top > innerHeight + 200) return;
      const off = (r.top + r.height / 2 - innerHeight / 2);
      w.querySelectorAll(".flo").forEach(el => { const d = +el.style.getPropertyValue("--dep");
        el.style.transform = `translate3d(${(mx * 40 * d).toFixed(1)}px, ${(-off * .12 * d + my * 30 * d).toFixed(1)}px, 0)`; }); }); }
  addEventListener("scroll", () => { if (!raf) raf = requestAnimationFrame(apply); }, { passive: true });
  addEventListener("pointermove", e => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; if (!raf) raf = requestAnimationFrame(apply); }, { passive: true });
  apply();
})();
