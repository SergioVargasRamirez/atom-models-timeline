/* Teilchen-Engine für die Seiten zu Säuren und Basen (Quelle: template/site/teilchen.js).
   build.py kopiert diese Datei zwischen die Marken in jede Seite, die sie nutzt; jede Seite bleibt eine einzelne Datei.
   Die Seite definiert danach PAGE (Szenen, Formeln, Texte) und ruft boot(PAGE) auf. */
const $ = id => document.getElementById(id);
const cv = $("stage"), ctx = cv.getContext("2d");
const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const DEG = Math.PI / 180;

/* ---------- Vektoren und Zufall ---------- */
const V = (x = 0, y = 0, z = 0) => ({x, y, z});
const add = (a, b) => V(a.x + b.x, a.y + b.y, a.z + b.z);
const sub = (a, b) => V(a.x - b.x, a.y - b.y, a.z - b.z);
const mul = (a, s) => V(a.x * s, a.y * s, a.z * s);
const dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
const cross = (a, b) => V(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
const len = a => Math.hypot(a.x, a.y, a.z);
const norm = a => { const l = len(a) || 1; return mul(a, 1 / l); };
const pos = a => V(a.x, a.y, a.z);
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
function rotAxis(v, k, ang){                                     // Rodrigues-Drehung von v um die Einheitsachse k
  const c = Math.cos(ang), s = Math.sin(ang);
  return add(add(mul(v, c), mul(cross(k, v), s)), mul(k, dot(k, v) * (1 - c)));
}
function aligner(from, to){                                      // Drehung, die die Richtung from auf to abbildet
  const f = norm(from), t = norm(to), ax = cross(f, t), s = len(ax), c = dot(f, t);
  if (s < 1e-9) return c > 0 ? (v => v) : (v => rotAxis(v, norm(Math.abs(f.x) < .9 ? cross(f, V(1, 0, 0)) : cross(f, V(0, 1, 0))), Math.PI));
  const k = mul(ax, 1 / s), ang = Math.atan2(s, c);
  return v => rotAxis(v, k, ang);
}
let seed = 12345;
const rand = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
const gauss = () => { let u = 0; while (!u) u = rand(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand()); };
const randDir = () => { const z = 2 * rand() - 1, t = 2 * Math.PI * rand(), r = Math.sqrt(1 - z * z); return V(r * Math.cos(t), z, r * Math.sin(t)); };
function randomRot(){ const k = randDir(), ang = 2 * Math.PI * rand(); return v => rotAxis(v, k, ang); }
const smooth = u => { u = Math.min(1, Math.max(0, u)); return u * u * (3 - 2 * u); };

/* ---------- Teilchenmodell ---------- */
const EL = ["Cl", "H", "N", "Na", "O"];                          // Reihenfolge für die Abstandstabelle
const MASS = {H:1.008, N:14.007, O:16.0, Na:22.99, Cl:35.45};
const R_OH = 0.96, R_OH3 = 0.98, R_HCL = 1.27, R_NH = 1.01, R_NH4 = 1.03;   // Å
const HH = {                                                     // H–H-Abstände, die den Bindungswinkel festlegen
  O: n => n >= 3 ? 2 * R_OH3 * Math.sin(112 / 2 * DEG) : n === 2 ? 2 * R_OH * Math.sin(104.5 / 2 * DEG) : null,
  N: n => n >= 4 ? 2 * R_NH4 * Math.sin(109.47 / 2 * DEG) : n === 3 ? 2 * R_NH * Math.sin(107 / 2 * DEG) : null,
};
function bondLen(el, n){ return el === "Cl" ? R_HCL : el === "N" ? (n >= 4 ? R_NH4 : R_NH) : (n >= 3 ? R_OH3 : R_OH); }
const MIN_TAB = {"Cl-Cl":3.6, "Cl-H":1.95, "Cl-N":3.15, "Cl-Na":2.8, "Cl-O":3.05, "H-H":1.75, "H-N":1.7, "H-Na":2.0, "H-O":1.6,
                 "N-N":3.0, "N-Na":2.5, "N-O":2.8, "Na-Na":3.4, "Na-O":2.3, "O-O":2.7};
const MIN_D = EL.map(a => EL.map(b => MIN_TAB[[a, b].sort().join("-")]));
const HB_D0 = {O:1.85, N:1.95, Cl:2.2}, K_HB = 500;               // Wasserstoffbrücken-Feder
const F_ION = 150;                                               // Anziehung entgegengesetzt geladener Ionen
const GAMMA = 12;                                                // Dämpfung 1/ps
const H_MAX = 0.004;                                             // ps je Rechenschritt
const ITER = 4;
const REFR = 0.4;                                                // ps Sperrzeit nach einem Übergang
const CUT = {"O-O":3.0, "O-N":3.1, "N-O":3.1};                    // maximaler Abstand Donor–Akzeptor
const RATES = {                                                  // Protonenübergänge je ps bei passender Geometrie
  "H3O+>H2O":0.9,  "H3O+>OH-":12, "H2O>OH-":0.9, "H3O+>NH3":12,  // Grotthuss, Neutralisation, OH⁻-Wanderung
  "H2O>NH3":0.4, "NH4+>OH-":8,                                   // Ammoniak-Gleichgewicht (stark beschleunigt)
};
const MAX_ANGLE = {"NH4+>OH-":70, "H3O+>OH-":60};               // Ionenpaare ordnen sich schnell um: weitere Winkel erlaubt

let A = [];                                                      // alle Atome
let S = null;                                                    // aktuelle Szene
let hl = [];                                                     // H-Listen je Schweratom

function atom(el, p, owner = -1){
  const a = {el, ei:EL.indexOf(el), w:1 / MASS[el], x:p.x, y:p.y, z:p.z, vx:0, vy:0, vz:0, qx:0, qy:0, qz:0, fx:0, fy:0, fz:0,
             owner, tr:null, busy:false, last:-9, fade:false, hot:false, liquid:true, glow:0, pair:-1, guard:-1, guardUntil:0};
  A.push(a); return A.length - 1;
}
function water(p, rotate = (v => v), fade = false){
  const a = 52.25 * DEG;
  const o = atom("O", p);
  for (const s of [1, -1]) atom("H", add(p, mul(rotate(V(Math.cos(a), s * Math.sin(a), 0)), R_OH)), o);
  if (fade) for (let i = o; i < A.length; i++) A[i].fade = true;
  return o;
}
function hcl(p, dir){
  const c = atom("Cl", p);
  A[atom("H", add(p, mul(norm(dir), R_HCL)), c)].hot = true;      // Proton, das gleich übertragen wird: orange
  return c;
}
function nh3(p, rotate = (v => v)){                              // Pyramide; das freie Elektronenpaar zeigt (vor dem Drehen) nach +y
  const n = atom("N", p), rho = HH.N(3) / Math.sqrt(3), h = Math.sqrt(R_NH * R_NH - rho * rho);
  for (let k = 0; k < 3; k++){
    const ph = k * 2 * Math.PI / 3;
    atom("H", add(p, rotate(V(rho * Math.cos(ph), -h, rho * Math.sin(ph)))), n);
  }
  return n;
}
function naoh(p, dir){                                           // Formeleinheit NaOH: Na⁺ neben OH⁻, löst sich im Wasser
  const u = norm(dir), na = atom("Na", p), o = atom("O", add(p, mul(u, 2.35)));
  atom("H", add(pos(A[o]), mul(u, R_OH)), o);
  A[na].pair = o; A[o].pair = na;
  A[na].bindUntil = (S ? S.t : 0) + 0.5; A[na].relUntil = A[na].bindUntil + 0.8;
  return na;
}
function buildLists(){
  hl = A.map(() => []);
  for (let i = 0; i < A.length; i++) if (A[i].el === "H") hl[A[i].owner].push(i);
}
const molOf = i => A[i].el === "H" ? A[i].owner : i;
function kind(i){                                                // Teilchenart eines Schweratoms
  const n = hl[i].length, el = A[i].el;
  if (el === "Cl") return n ? "HCl" : "Cl-";
  if (el === "Na") return "Na+";
  if (el === "N") return n >= 4 ? "NH4+" : "NH3";
  return n >= 3 ? "H3O+" : n === 2 ? "H2O" : "OH-";
}
const LABEL = {H2O:"H₂O", "H3O+":"H₃O⁺", "OH-":"OH⁻", HCl:"HCl", "Cl-":"Cl⁻", NH3:"NH₃", "NH4+":"NH₄⁺", "Na+":"Na⁺"};
const LABEL_COL = {"H3O+":"#d7b8ff", "OH-":"#9fd8ff", "Cl-":"#9fe3ae", "NH4+":"#ffd59e", NH3:"#b9c8ff", "Na+":"#e3c8ff"};
function lonePair(o, which = 1){                                 // Richtung eines freien Elektronenpaars am O
  const [h1, h2] = hl[o], O = pos(A[o]);
  const b = norm(add(sub(pos(A[h1]), O), sub(pos(A[h2]), O)));
  const n = norm(cross(sub(pos(A[h1]), O), sub(pos(A[h2]), O)));
  return norm(add(mul(b, -Math.cos(54.7 * DEG)), mul(n, which * Math.sin(54.7 * DEG))));
}
function lonePairN(n){                                           // freies Elektronenpaar am N des NH₃
  const N = pos(A[n]); let s = V();
  for (const i of hl[n]) s = add(s, sub(pos(A[i]), N));
  return norm(mul(s, -1));
}

/* ---------- Kräfte, Bedingungen, Integration ---------- */
function spring(a, b, k, d0, mode){                              // mode: 0 beidseitig, 1 nur ziehen, -1 nur drücken
  const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z, d = Math.hypot(dx, dy, dz) || 1e-9;
  if ((mode === 1 && d < d0) || (mode === -1 && d > d0)) return;
  const f = k * (d - d0) / d;
  a.fx += f * dx; a.fy += f * dy; a.fz += f * dz;
  b.fx -= f * dx; b.fy -= f * dy; b.fz -= f * dz;
}
function tether(a, p, k){ a.fx += k * (p.x - a.x); a.fy += k * (p.y - a.y); a.fz += k * (p.z - a.z); }
function acceptsHB(j){                                           // nimmt eine Wasserstoffbrücke an (freies Elektronenpaar)
  const el = A[j].el, n = hl[j].length;
  return (el === "O" && n <= 2) || (el === "Cl" && !n) || (el === "N" && n === 3);
}
function forces(){
  for (const a of A){ a.fx = a.fy = a.fz = 0; }
  for (let i = 0; i < A.length; i++){                            // Wasserstoffbrücken
    const h = A[i]; if (h.el !== "H" || h.tr) continue;
    if (A[h.owner].el === "N" && hl[h.owner].length === 3) continue;   // NH₃ ist ein schwacher Donor, aber ein guter Akzeptor
    for (let j = 0; j < A.length; j++){
      if (A[j].el === "H" || j === h.owner || !acceptsHB(j)) continue;
      const b = A[j], d0 = HB_D0[b.el], d = dist(h, b);
      if (d > d0 + 1.0 || d < d0) continue;
      spring(h, b, K_HB, d0, 1);
    }
  }
  const plus = [], minus = [];                                  // Anziehung zwischen Kationen (H₃O⁺, NH₄⁺) und OH⁻
  for (let i = 0; i < A.length; i++){
    const a = A[i], n = hl[i].length;
    if ((a.el === "O" && n === 3) || (a.el === "N" && n === 4)) plus.push(a);
    else if (a.el === "O" && n === 1 && a.pair < 0) minus.push(a);
  }
  for (const a of plus) for (const b of minus){
    const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z, d = Math.hypot(dx, dy, dz);
    if (d < 3.2 || d > 10) continue;
    const f = F_ION / d;                                         // gleich große Kraft, unabhängig vom Abstand
    a.fx += f * dx; a.fy += f * dy; a.fz += f * dz; b.fx -= f * dx; b.fy -= f * dy; b.fz -= f * dz;
  }
  for (let i = 0; i < A.length; i++){                           // Na⁺: Hydrathülle, Formeleinheit NaOH
    const na = A[i]; if (na.el !== "Na") continue;
    if (na.pair >= 0){
      const o = A[na.pair];
      if (S.t < na.bindUntil) spring(na, o, 400, 2.35, 0);
      else if (S.t < na.relUntil) spring(na, o, 150, 4.6, -1);
      else { o.pair = -1; na.pair = -1; S.onDissociate && S.onDissociate(i); }
    }
    for (let j = 0; j < A.length; j++){
      if (A[j].el !== "O" || j === na.pair) continue;
      const d = dist(na, A[j]);
      if (d > 2.4 && d < 3.6) spring(na, A[j], 120, 2.4, 1);
    }
  }
  S.forces && S.forces();
}
function project(a, b, d0, k, minOnly){                          // Abstandsbedingung auf vorhergesagte Orte
  const dx = b.qx - a.qx, dy = b.qy - a.qy, dz = b.qz - a.qz, d = Math.hypot(dx, dy, dz) || 1e-9;
  if (minOnly && d >= d0) return;
  const ws = a.w + b.w, c = k * (d - d0) / (d * ws);
  a.qx += a.w * c * dx; a.qy += a.w * c * dy; a.qz += a.w * c * dz;
  b.qx -= b.w * c * dx; b.qy -= b.w * c * dy; b.qz -= b.w * c * dz;
}
function hhTarget(j){                                            // H–H-Sollabstand, während eines Übergangs gleitend
  const el = A[j].el, n = hl[j].length;
  for (const i of S.flying){
    const t = A[i].tr, e = smooth(t.s / t.tau);
    if (t.from === j){ const d0 = HH[el](n + 1), d1 = HH[el](n); return d0 && d1 ? d0 + (d1 - d0) * e : d1; }
    if (t.to === j){ const d0 = HH[el](n - 1), d1 = HH[el](n); return d0 && d1 ? d0 + (d1 - d0) * e : d1; }
  }
  return HH[el](n);
}
function constraints(){
  const n = A.length;
  for (let it = 0; it < ITER; it++){
    for (let i = 0; i < n; i++){                                 // Bindungen
      const h = A[i]; if (h.el !== "H" || h.tr) continue;
      project(h, A[h.owner], bondLen(A[h.owner].el, hl[h.owner].length), 1, false);
    }
    for (let j = 0; j < n; j++){                                 // Winkel über H–H-Abstände
      if (!HH[A[j].el]) continue;
      const hs = hl[j].filter(i => !A[i].tr), d0 = hhTarget(j);
      if (!d0) continue;
      for (let a = 0; a < hs.length; a++) for (let b = a + 1; b < hs.length; b++) project(A[hs[a]], A[hs[b]], d0, 1, false);
    }
    for (let i = 0; i < n; i++){                                 // Abstoßung zwischen verschiedenen Teilchen
      const a = A[i]; if (a.tr) continue;
      const mi = molOf(i), row = MIN_D[a.ei];
      for (let j = i + 1; j < n; j++){
        const b = A[j]; if (b.tr || molOf(j) === mi) continue;
        if (Math.abs(b.qx - a.qx) > 3.6 || Math.abs(b.qy - a.qy) > 3.6 || Math.abs(b.qz - a.qz) > 3.6) continue;
        project(a, b, row[b.ei], 0.6, true);
      }
    }
    S.walls && S.walls();
  }
  for (const i of S.flying){                                     // laufende Übergänge: das Proton gleitet entlang Donor–Akzeptor
    const h = A[i], t = h.tr, D = A[t.from], Ac = A[t.to];
    const dv = V(Ac.qx - D.qx, Ac.qy - D.qy, Ac.qz - D.qz), dl = len(dv) || 1, u = mul(dv, 1 / dl), e = smooth(t.s / t.tau);
    const r = (1 - e) * t.r0 + e * (dl - bondLen(Ac.el, hl[t.to].length));
    h.qx = D.qx + u.x * r; h.qy = D.qy + u.y * r; h.qz = D.qz + u.z * r;
  }
}
function excess(){                                               // überschüssige H₃O⁺ (positiv) bzw. OH⁻ (negativ)
  let ex = 0;
  for (let i = 0; i < A.length; i++) if (A[i].el === "O") ex += hl[i].length === 3 ? 1 : hl[i].length === 1 ? -1 : 0;
  return ex;
}
function step(h){
  buildLists();
  forces();
  const damp = Math.exp(-GAMMA * h);
  for (const a of A){
    const c = Math.sqrt(S.kT * a.w * (1 - damp * damp));
    a.vx = (a.vx + a.fx * a.w * h) * damp + c * gauss();
    a.vy = (a.vy + a.fy * a.w * h) * damp + c * gauss();
    a.vz = (a.vz + a.fz * a.w * h) * damp + c * gauss();
    a.qx = a.x + a.vx * h; a.qy = a.y + a.vy * h; a.qz = a.z + a.vz * h;
  }
  constraints();
  for (const a of A){
    a.vx = (a.qx - a.x) / h; a.vy = (a.qy - a.y) / h; a.vz = (a.qz - a.z) / h;
    a.x = a.qx; a.y = a.qy; a.z = a.qz;
    if (a.glow > 0) a.glow = Math.max(0, a.glow - h / 0.6);
  }
  S.t += h;
  for (const i of S.flying.slice()){                             // Übergänge fortschreiben
    const t = A[i].tr; t.s += h;
    if (t.s >= t.tau){
      A[i].tr = null; A[t.from].busy = A[t.to].busy = false; A[t.from].last = A[t.to].last = S.t;
      S.flying.splice(S.flying.indexOf(i), 1);
    }
  }
  if (S.auto) tryTransfers(h);
  if (S.autoprot) autoprotolysis();
  S.onStep && S.onStep(h);
  if (S.indicator){ buildLists(); S.exAvg += (excess() - S.exAvg) * (1 - Math.exp(-h / 1.0)); }   // zeitlich gemittelt
}
function startTransfer(i, from, to, tau){
  buildLists();
  const kd = kind(from), ka = kind(to), h = A[i];
  for (const a of A) if (a.el === "H" && a.owner === from) a.hot = false;   // nur das zuletzt übertragene Proton ist orange
  h.hot = true;
  h.tr = {from, to, s:0, tau, r0:dist(h, A[from])};
  h.owner = to; h.glow = 1;
  if (A[to].fade){ A[to].fade = false; for (const a of A) if (a.el === "H" && a.owner === to) a.fade = false; }
  A[from].busy = A[to].busy = true;
  S.flying.push(i);
  S.hops++;
  if ((kd === "H2O" && ka === "H2O") || (kd === "H2O" && ka === "NH3")){   // frisch getrenntes Ionenpaar kurz schonen
    A[from].guard = to; A[to].guard = from; A[from].guardUntil = A[to].guardUntil = S.t + (ka === "NH3" ? 0.5 : 1.0);
  }
  if (kd === "H2O" && ka === "H2O") S.nextAuto = Infinity;        // Autoprotolyse: bis zur Rückreaktion keine neue
  if (kd === "H3O+" && ka === "OH-") S.nextAuto = S.t + 3 + 4 * rand();
  S.onTransfer && S.onTransfer(i, from, to, kd, ka);
}
function tryTransfers(h){
  buildLists();
  for (let d = 0; d < A.length; d++){                            // HCl im Wasser gibt sein Proton sofort ab (starke Säure)
    const D = A[d];
    if (D.el !== "Cl" || hl[d].length !== 1 || D.busy || !D.liquid) continue;
    const i = hl[d][0];
    let best = -1, bd = 4.2;
    for (let a = 0; a < A.length; a++){
      if (A[a].el !== "O" || A[a].busy || hl[a].length !== 2) continue;
      const dh = dist(A[a], A[i]);
      if (dh < bd){ bd = dh; best = a; }
    }
    if (best >= 0) startTransfer(i, d, best, 0.15);
  }
  const rates = S.rates ? Object.assign({}, RATES, S.rates) : RATES;
  const cand = [];
  for (let d = 0; d < A.length; d++){
    const D = A[d]; if (D.el === "H" || D.el === "Cl" || D.el === "Na" || D.busy || D.pair >= 0 || S.t - D.last < REFR) continue;
    const kd = kind(d);
    for (const i of hl[d]){
      const H = A[i], u1 = norm(V(H.x - D.x, H.y - D.y, H.z - D.z));
      for (let a = 0; a < A.length; a++){
        const Ac = A[a];
        if (a === d || (Ac.el !== "O" && Ac.el !== "N") || Ac.busy || Ac.pair >= 0 || S.t - Ac.last < REFR) continue;
        const rule = kd + ">" + kind(a), rate = rates[rule]; if (!rate) continue;
        if ((D.guard === a || Ac.guard === d) && S.t < Math.max(D.guardUntil, Ac.guardUntil)) continue;
        if (dist(D, Ac) > CUT[D.el + "-" + Ac.el]) continue;
        if (dot(u1, norm(V(Ac.x - H.x, Ac.y - H.y, Ac.z - H.z))) < Math.cos((MAX_ANGLE[rule] || 40) * DEG)) continue;
        cand.push([i, d, a, rate]);
      }
    }
  }
  for (const [i, d, a, rate] of cand){
    if (A[d].busy || A[a].busy || A[i].tr) continue;
    if (rand() < rate * h) startTransfer(i, d, a, 0.12);
  }
}
function autoprotolysis(){                                       // stark beschleunigte Autoprotolyse, nur in reinem Wasser
  if (S.t < S.nextAuto || S.flying.length) return;
  buildLists();
  if (A.some((a, j) => a.el !== "H" && (a.el !== "O" || hl[j].length !== 2) && !(S.autoprotIgnore || []).includes(kind(j)))) return;
  const cand = [];
  for (let d = 0; d < A.length; d++){
    if (A[d].el !== "O" || hl[d].length !== 2) continue;
    for (const i of hl[d]) for (let a = 0; a < A.length; a++){
      if (A[a].el !== "O" || a === d || hl[a].length !== 2) continue;
      const D = A[d], H = A[i], Ac = A[a];
      if (dist(D, Ac) > 2.95) continue;
      if (dot(norm(V(H.x - D.x, H.y - D.y, H.z - D.z)), norm(V(Ac.x - H.x, Ac.y - H.y, Ac.z - H.z))) < Math.cos(30 * DEG)) continue;
      cand.push([i, d, a]);
    }
  }
  if (!cand.length) return;
  const [i, d, a] = cand[Math.floor(rand() * cand.length)];
  startTransfer(i, d, a, 0.15);
}
function equilibrate(ps){
  const auto = S.auto, ap = S.autoprot; S.auto = 0; S.autoprot = false;
  for (let t = 0; t < ps; t += H_MAX) step(H_MAX);
  S.auto = auto; S.autoprot = ap; S.t = 0; S.hops = 0; S.exAvg = 0;
}

/* ---------- Bausteine für Szenen ---------- */
function newScene(o){
  return Object.assign({kT:150, R:7.6, flying:[], hops:0, t:0, auto:1, exAvg:0, nextAuto:1.5, buttons:[], added:{}}, o);
}
function boxWalls(L, yLo, yHi){
  return () => {
    for (const a of A){
      const m = a.el === "H" ? 0.5 : 1.2;
      if (a.qx < -L + m) a.qx = -L + m; else if (a.qx > L - m) a.qx = L - m;
      if (a.qz < -L + m) a.qz = -L + m; else if (a.qz > L - m) a.qz = L - m;
      if (a.qy < yLo + m) a.qy = yLo + m; else if (a.qy > yHi - m) a.qy = yHi - m;
    }
  };
}
function fillWater(n, L, yLo, yHi, skip = [], sp = 2.75){        // Wassermoleküle auf ein zufällig verschobenes Gitter setzen
  const sites = [];
  for (let x = -L + 1.3; x <= L - 1.3; x += sp)
    for (let y = yLo + 1.3; y <= yHi - 1.3; y += sp)
      for (let z = -L + 1.3; z <= L - 1.3; z += sp) sites.push(V(x + .3 * gauss(), y + .3 * gauss(), z + .3 * gauss()));
  for (let i = sites.length - 1; i > 0; i--){ const j = Math.floor(rand() * (i + 1)); [sites[i], sites[j]] = [sites[j], sites[i]]; }
  const free = sites.filter(p => skip.every(q => len(sub(p, q)) > 2.6));
  for (let i = 0; i < Math.min(n, free.length); i++) water(free[i], randomRot());
  return free.slice(n);
}
function gasAndWater(s){                                         // Kasten mit Gasraum: Wasser unten, Gas sinkt zur Oberfläche
  s.level = s.ySurf;
  s.forces = () => {
    const ys = [];
    for (const a of A) if (a.el === "O" && a.liquid) ys.push(a.y);
    ys.sort((p, q) => p - q);
    s.level = ys[Math.floor(ys.length * 0.9)] + 0.9;            // Wasserspiegel: oberste Sauerstoffatome
    for (const a of A){
      if (a.el === "H") continue;
      if (!a.liquid){ if (a.y < s.level - 0.3) a.liquid = true; else { a.fy -= 70 / a.w; continue; } }
      a.fy -= 20 / a.w;                                          // leichte Schwerkraft hält das Wasser unten
    }
  };
}
function gasMolecule(builder, s){                                // Molekül ganz oben im Gasraum einsetzen
  const first = A.length, c = builder(V(0.6 * gauss(), s.yHi - 1.4, 0.6 * gauss()));
  for (let i = first; i < A.length; i++) A[i].liquid = false;
  return c;
}
function freeSpot(){                                             // freieste Stelle im Kasten
  let best = null, bd = -1;
  for (let k = 0; k < 80; k++){
    const p = V((2 * rand() - 1) * (S.L - 2), (2 * rand() - 1) * (S.L - 2), (2 * rand() - 1) * (S.L - 2));
    let m = 1e9;
    for (const a of A) if (a.el !== "H") m = Math.min(m, Math.hypot(a.x - p.x, a.y - p.y, a.z - p.z));
    if (m > bd){ bd = m; best = p; }
  }
  return best;
}
function addToBox(key, builder){                                 // für Knöpfe wie „HCl zugeben“
  S.added[key] = (S.added[key] || 0) + 1;
  const c = builder(freeSpot()); A[c].glow = 1;
  if (!running){ running = true; syncControls(); }               // gleich laufen lassen, damit man die Reaktion sieht
  syncButtons(); dirty = true;
  return c;
}
function phaseOf(t){ const P = S.PH; let k = 0; while (k + 1 < P.length && t >= P[k + 1]) k++; return k; }

/* ---------- Zeichnen ---------- */
let W = 0, H = 0, rotY = -0.35, rotX = 0.28, dirty = true, SC = 30;
const CAM = 46;
function resize(){
  const dpr = window.devicePixelRatio || 1;
  W = cv.clientWidth; H = cv.clientHeight;
  cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (S) draw();
}
const UI_COL = [[1, [214, 32, 44]], [2, [232, 72, 40]], [3, [244, 122, 38]], [4, [248, 166, 40]], [5, [240, 206, 48]],
  [6, [184, 208, 58]], [7, [76, 176, 72]], [8, [36, 158, 128]], [9, [38, 116, 190]], [10, [58, 76, 172]], [11, [92, 56, 160]], [14, [112, 40, 140]]];
const PH_ACID = [7, 5, 4, 3, 2.4, 1.8, 1.3], PH_BASE = [7, 9, 10, 11, 11.6, 12.2, 12.7];   // Modell-pH je überschüssigem Ion
function uiColor(ph){
  for (let k = 1; k < UI_COL.length; k++){
    const [p1, c1] = UI_COL[k];
    if (ph <= p1){ const [p0, c0] = UI_COL[k - 1], u = Math.max(0, (ph - p0) / (p1 - p0)); return mix(c0, c1, u); }
  }
  return UI_COL[UI_COL.length - 1][1];
}
function modelPH(){
  const ex = S.exAvg, tab = ex >= 0 ? PH_ACID : PH_BASE, x = Math.min(Math.abs(ex), tab.length - 1), k = Math.floor(x);
  return k >= tab.length - 1 ? tab[tab.length - 1] : tab[k] + (tab[k + 1] - tab[k]) * (x - k);
}
const phText = () => { const p = Math.round(modelPH() * 2) / 2; return fmt(p, p % 1 ? 1 : 0); };
function indicator(){
  const ph = modelPH(), cx = W - 62, cy = 92, r = 30, c = uiColor(ph);
  if (Math.abs(excess() - S.exAvg) > 0.01) dirty = true;
  ctx.fillStyle = "rgba(10,14,24,.6)"; ctx.beginPath(); ctx.roundRect ? ctx.roundRect(cx - 56, cy - 70, 112, 160, 10) : ctx.rect(cx - 56, cy - 70, 112, 160); ctx.fill();
  ctx.fillStyle = "#c9d3ea"; ctx.font = "600 12px 'Source Sans 3',system-ui,sans-serif"; ctx.textAlign = "center";
  ctx.fillText("Universalindikator", cx, cy - 50);
  const g = ctx.createRadialGradient(cx - r * .35, cy - r * .4, r * .1, cx, cy, r);
  g.addColorStop(0, rgb(mix(c, [255, 255, 255], .45))); g.addColorStop(.6, rgb(c)); g.addColorStop(1, rgb(mix(c, [0, 0, 0], .3)));
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 2 * Math.PI); ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,.55)"; ctx.lineWidth = 1.5; ctx.stroke();
  ctx.fillStyle = "#e8ecf3"; ctx.font = "700 13px 'Source Sans 3',system-ui,sans-serif";
  ctx.fillText(`Modell-pH ≈ ${phText()}`, cx, cy + r + 20);
  const bx = cx - 48, bw = 96, by = cy + r + 32;                 // Farbskala pH 1 bis 14 mit Marke
  const lg = ctx.createLinearGradient(bx, 0, bx + bw, 0);
  for (const [p, col] of UI_COL) lg.addColorStop((p - 1) / 13, rgb(col));
  ctx.fillStyle = lg; ctx.fillRect(bx, by, bw, 7);
  const mx = bx + (ph - 1) / 13 * bw;
  ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.moveTo(mx, by - 1); ctx.lineTo(mx - 4, by - 7); ctx.lineTo(mx + 4, by - 7); ctx.closePath(); ctx.fill();
  ctx.fillStyle = "#7482a3"; ctx.font = "10px 'Source Sans 3',system-ui,sans-serif";
  ctx.textAlign = "left"; ctx.fillText("sauer", bx, by + 18); ctx.textAlign = "right"; ctx.fillText("basisch", bx + bw, by + 18);
  ctx.textAlign = "center";
}
function gizmo(){                                                // Achsenkreuz zur Orientierung, unten links
  const gx = 50, gy = H - 50, Lg = 30;
  const cy = Math.cos(rotY), sy = Math.sin(rotY), cx = Math.cos(rotX), sx = Math.sin(rotX);
  const rot = (x, y, z) => { const x1 = x * cy + z * sy, z1 = -x * sy + z * cy; return [x1, y * cx - z1 * sx, y * sx + z1 * cx]; };
  ctx.fillStyle = "rgba(10,14,24,.6)"; ctx.beginPath(); ctx.arc(gx, gy, 42, 0, 2 * Math.PI); ctx.fill();
  ctx.font = "bold 12px ui-monospace,Consolas,monospace"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  [[[1, 0, 0], "x", "#ef5350"], [[0, 1, 0], "y", "#8bd17c"], [[0, 0, 1], "z", "#7d9bff"]]
    .map(([u, n, c]) => ({q:rot(...u), n, c})).sort((a, b) => a.q[2] - b.q[2]).forEach(o => {
      const ex = gx + o.q[0] * Lg, ey = gy - o.q[1] * Lg, l = Math.hypot(o.q[0], o.q[1]);
      ctx.strokeStyle = o.c; ctx.fillStyle = o.c; ctx.lineWidth = 2;
      if (l < 0.15){                                             // Achse zeigt auf den Betrachter (oder von ihm weg)
        ctx.beginPath(); ctx.arc(gx, gy, 5, 0, 2 * Math.PI); ctx.stroke();
        if (o.q[2] > 0){ ctx.beginPath(); ctx.arc(gx, gy, 1.8, 0, 2 * Math.PI); ctx.fill(); }
        ctx.fillText(o.n, gx + 12, gy + 12);
      } else {
        ctx.beginPath(); ctx.moveTo(gx, gy); ctx.lineTo(ex, ey); ctx.stroke();
        ctx.fillText(o.n, gx + o.q[0] * (Lg + 9) / Math.max(l, .5) * Math.min(l, 1), gy - o.q[1] * (Lg + 9) / Math.max(l, .5) * Math.min(l, 1));
      }
    });
  ctx.lineWidth = 1; ctx.textBaseline = "alphabetic";
}
function proj(x, y, z){
  const cy = Math.cos(rotY), sy = Math.sin(rotY), cx = Math.cos(rotX), sx = Math.sin(rotX);
  const x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
  const y2 = y * cx - z1 * sx, z2 = y * sx + z1 * cx;
  const f = CAM / (CAM - z2);
  return {X: W / 2 + x1 * SC * f, Y: H / 2 - y2 * SC * f, z: z2, f};
}
const COL = {O:[214, 40, 40], H:[236, 236, 236], Cl:[46, 170, 70], N:[52, 88, 224], Na:[171, 92, 242], M:[255, 150, 40]};
const R_STICK = {O:0.36, H:0.24, Cl:0.46, N:0.37, Na:0.38};   // Na⁺ kleiner als Cl⁻, wie die Ionenradien
let showHB = false, zoom = 1;
const rgb = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
const mix = (c, d, t) => c.map((v, i) => Math.round(v + (d[i] - v) * t));
function ball(X, Y, r, c, alpha){
  const g = ctx.createRadialGradient(X - r * .35, Y - r * .4, r * .08, X, Y, r);
  g.addColorStop(0, rgb(mix(c, [255, 255, 255], .65), alpha));
  g.addColorStop(.55, rgb(c, alpha));
  g.addColorStop(1, rgb(mix(c, [0, 0, 0], .55), alpha));
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(X, Y, r, 0, 2 * Math.PI); ctx.fill();
}
function atomColor(a){ return a.el === "H" && a.hot ? COL.M : COL[a.el]; }
function stick(p, q, c, w, alpha){
  ctx.strokeStyle = rgb(mix(c, [0, 0, 0], .15), alpha); ctx.lineWidth = w; ctx.lineCap = "round";
  ctx.beginPath(); ctx.moveTo(p.X, p.Y); ctx.lineTo(q.X, q.Y); ctx.stroke();
}
function drawBox(){
  if (!S.L) return;
  const L = S.L, y0 = S.yLo ?? -L, y1 = S.yHi ?? L;
  const c = [];
  for (const x of [-L, L]) for (const y of [y0, y1]) for (const z of [-L, L]) c.push(proj(x, y, z));
  ctx.strokeStyle = "rgba(160,175,210,.28)"; ctx.lineWidth = 1;
  const E = [[0,1],[2,3],[4,5],[6,7],[0,2],[1,3],[4,6],[5,7],[0,4],[1,5],[2,6],[3,7]];
  ctx.beginPath(); for (const [a, b] of E){ ctx.moveTo(c[a].X, c[a].Y); ctx.lineTo(c[b].X, c[b].Y); } ctx.stroke();
  if (S.level !== undefined){                                    // Wasseroberfläche
    const q = [proj(-L, S.level, -L), proj(L, S.level, -L), proj(L, S.level, L), proj(-L, S.level, L)];
    ctx.fillStyle = "rgba(90,150,255,.10)"; ctx.strokeStyle = "rgba(120,170,255,.45)";
    ctx.beginPath(); q.forEach((p, i) => i ? ctx.lineTo(p.X, p.Y) : ctx.moveTo(p.X, p.Y)); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "rgba(160,190,255,.75)"; ctx.font = "600 12px 'Source Sans 3',system-ui,sans-serif"; ctx.textAlign = "left";
    const g = proj(-L, S.yHi - 0.6, L), w = proj(-L, S.level - 0.8, L);
    ctx.fillText("Gasraum", g.X + 6, g.Y + 4); ctx.fillText("Wasser", w.X + 6, w.Y + 4);
  }
}
function draw(){
  if (!W) return;
  SC = Math.min(H * 0.47 / S.R, W * 0.47 / (S.Rw || S.R)) * zoom;   // Rw: halbe Breite der Szene
  ctx.clearRect(0, 0, W, H);
  buildLists();
  let cx = 0, cy = 0, cz = 0;
  if (S.closeup){                                                // Nahaufnahme: fester Mittelpunkt
    if (!S.center){ const c = V(); for (const a of A){ c.x += a.x; c.y += a.y; c.z += a.z; } S.center = mul(c, 1 / A.length); }
    ({x:cx, y:cy, z:cz} = S.center);
  }
  const P = A.map(a => proj(a.x - cx, a.y - cy, a.z - cz));
  drawBox();
  for (let i = 0; i < A.length; i++){                            // Leuchten um H₃O⁺ (violett) und OH⁻ (blau)
    if (A[i].el !== "O" || hl[i].length === 2 || A[i].pair >= 0) continue;
    const p = P[i], r = 2.2 * SC * p.f, c = hl[i].length >= 3 ? "170,110,255" : "80,190,255";
    const g = ctx.createRadialGradient(p.X, p.Y, 0, p.X, p.Y, r);
    g.addColorStop(0, `rgba(${c},.42)`); g.addColorStop(1, `rgba(${c},0)`);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.X, p.Y, r, 0, 2 * Math.PI); ctx.fill();
  }
  const items = [];                                              // Zeichenliste: Atome, Stäbe, Brücken, von hinten nach vorn
  for (let i = 0; i < A.length; i++) items.push({z:P[i].z, i, t:0});
  for (let i = 0; i < A.length; i++){                            // Stäbe: jede Bindung als zwei Hälften in den Atomfarben
    const h = A[i]; if (h.el !== "H") continue;
    const bonds = h.tr ? [[h.tr.from, 1 - smooth(h.tr.s / h.tr.tau)], [h.tr.to, smooth(h.tr.s / h.tr.tau)]] : [[h.owner, 1]];
    for (const [o, al] of bonds){
      if (al < 0.05) continue;
      const m = {X:(P[i].X + P[o].X) / 2, Y:(P[i].Y + P[o].Y) / 2};
      items.push({z:(P[i].z * 3 + P[o].z) / 4 - 0.01, t:1, a:P[i], b:m, c:atomColor(h), al, fade:h.fade});
      items.push({z:(P[o].z * 3 + P[i].z) / 4 - 0.01, t:1, a:P[o], b:m, c:COL[A[o].el], al, fade:A[o].fade});
    }
  }
  if (showHB){                                                   // Wasserstoffbrücken
    for (let i = 0; i < A.length; i++){
      const h = A[i]; if (h.el !== "H" || h.tr) continue;
      const D = A[h.owner];
      for (let j = 0; j < A.length; j++){
        const b = A[j]; if (b.el === "H" || b.el === "Na" || j === h.owner) continue;
        if (dist(b, h) > (b.el === "Cl" ? 2.7 : 2.4)) continue;
        if (dot(norm(V(h.x - D.x, h.y - D.y, h.z - D.z)), norm(V(b.x - h.x, b.y - h.y, b.z - h.z))) < Math.cos(45 * DEG)) continue;
        items.push({z:(P[i].z + P[j].z) / 2, t:2, a:P[i], b:P[j], fade:h.fade || b.fade});
      }
    }
  }
  items.sort((p, q) => p.z - q.z);
  for (const it of items){
    if (it.t === 2){
      ctx.setLineDash([4, 4]); ctx.lineWidth = 1.6; ctx.strokeStyle = `rgba(140,200,255,${it.fade ? .4 : .9})`;
      ctx.beginPath(); ctx.moveTo(it.a.X, it.a.Y); ctx.lineTo(it.b.X, it.b.Y); ctx.stroke(); ctx.setLineDash([]);
    } else if (it.t === 1){
      stick(it.a, it.b, it.c, 0.15 * SC * (it.a.f + 1) / 2, it.al * (it.fade ? .3 : 1));
    } else {
      const a = A[it.i], p = P[it.i];
      if (a.glow > 0){
        const r = (a.el === "H" ? 0.9 : 1.6) * SC * p.f, g = ctx.createRadialGradient(p.X, p.Y, 0, p.X, p.Y, r);
        g.addColorStop(0, `rgba(255,220,120,${.75 * a.glow})`); g.addColorStop(1, "rgba(255,220,120,0)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.X, p.Y, r, 0, 2 * Math.PI); ctx.fill();
      }
      ball(p.X, p.Y, R_STICK[a.el] * SC * p.f, atomColor(a), a.fade ? .3 : 1);
    }
  }
  ctx.font = "700 13px 'Source Sans 3',system-ui,sans-serif"; ctx.textAlign = "center";   // Beschriftungen
  const label = (txt, col, p, r) => {
    const y = p.Y - (r * SC * p.f + 16);
    ctx.lineWidth = 3; ctx.strokeStyle = "rgba(10,14,24,.85)"; ctx.strokeText(txt, p.X, y);
    ctx.fillStyle = col; ctx.fillText(txt, p.X, y);
  };
  for (let i = 0; i < A.length; i++){
    const a = A[i]; if (a.el === "H" || a.fade) continue;
    if (a.pair >= 0){                                            // NaOH als Formeleinheit, solange Na⁺ und OH⁻ zusammenhängen
      if (a.el === "Na"){ const o = P[a.pair], p = P[i]; label("NaOH", "#e8ecf3", {X:(p.X + o.X) / 2, Y:Math.min(p.Y, o.Y), f:p.f}, R_STICK.Na); }
      continue;
    }
    const k = kind(i);
    if (k === "H2O" && !S.closeup) continue;
    label(LABEL[k], LABEL_COL[k] || "#e8ecf3", P[i], R_STICK[a.el]);
  }
  gizmo();
  if (S.indicator) indicator();
  if (S.flying.length && !S.closeup){
    ctx.font = "700 12px 'Source Sans 3',system-ui,sans-serif"; ctx.textAlign = "right"; ctx.fillStyle = "rgba(255,220,120,.95)";
    ctx.fillText("Zeitlupe", W - 12, S.indicator ? H - 16 : 20);
  }
}

/* ---------- Valenzstrichformeln ---------- */
const T = (x, y, s, cls = "") => `<text x="${x}" y="${y}" font-size="26" text-anchor="middle" dominant-baseline="central"${cls ? ` class="${cls}"` : ""}>${s}</text>`;
const Ln = (x1, y1, x2, y2) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
const BR = (x0, x1, y0, y1, ch) => `<path d="M${x0} ${y0}h-6v${y1 - y0}h6M${x1} ${y0}h6v${y1 - y0}h-6"/>` + T(x1 + 18, y0, ch);
const LEWIS = {
  HCl: (x, y, hp) => T(x, y, "H", hp ? "hp" : "") + Ln(x + 11, y, x + 29, y) + T(x + 46, y, "Cl") +
       Ln(x + 38, y - 17, x + 54, y - 17) + Ln(x + 38, y + 17, x + 54, y + 17) + Ln(x + 64, y - 8, x + 64, y + 8),
  H2O: (x, y, hp) => T(x, y, "O") + Ln(x - 9, y + 7, x - 22, y + 17) + T(x - 31, y + 24, "H") + Ln(x + 9, y + 7, x + 22, y + 17) + T(x + 31, y + 24, "H", hp ? "hp" : "") +
       Ln(x - 17, y - 5, x - 9, y - 16) + Ln(x + 9, y - 16, x + 17, y - 5),
  H3O: (x, y, hp) => T(x, y, "O") + Ln(x - 11, y, x - 25, y) + T(x - 35, y, "H", hp === "l" ? "hp" : "") + Ln(x + 11, y, x + 25, y) + T(x + 35, y, "H", hp === "r" ? "hp" : "") +
       Ln(x, y + 11, x, y + 25) + T(x, y + 36, "H", hp === "b" ? "hp" : "") + Ln(x - 8, y - 16, x + 8, y - 16) + BR(x - 48, x + 48, y - 26, y + 50, "+"),
  Clm: (x, y) => T(x, y, "Cl") + Ln(x - 8, y - 17, x + 8, y - 17) + Ln(x - 8, y + 17, x + 8, y + 17) + Ln(x - 21, y - 8, x - 21, y + 8) + Ln(x + 21, y - 8, x + 21, y + 8) +
       BR(x - 32, x + 32, y - 28, y + 28, "−"),
  OHm: (x, y, hp) => T(x, y, "O") + Ln(x - 8, y - 17, x + 8, y - 17) + Ln(x - 8, y + 17, x + 8, y + 17) + Ln(x - 17, y - 8, x - 17, y + 8) +
       Ln(x + 11, y, x + 25, y) + T(x + 35, y, "H", hp ? "hp" : "") + BR(x - 28, x + 50, y - 28, y + 28, "−"),
  NH3: (x, y) => T(x, y, "N") + Ln(x - 11, y, x - 25, y) + T(x - 35, y, "H") + Ln(x + 11, y, x + 25, y) + T(x + 35, y, "H") +
       Ln(x, y + 11, x, y + 25) + T(x, y + 36, "H") + Ln(x - 8, y - 16, x + 8, y - 16),
  NH4: (x, y, hp) => T(x, y, "N") + Ln(x - 11, y, x - 25, y) + T(x - 35, y, "H") + Ln(x + 11, y, x + 25, y) + T(x + 35, y, "H") +
       Ln(x, y + 11, x, y + 25) + T(x, y + 36, "H") + Ln(x, y - 11, x, y - 25) + T(x, y - 36, "H", hp ? "hp" : "") + BR(x - 48, x + 48, y - 50, y + 50, "+"),
  Nap: (x, y) => T(x, y, "Na") + T(x + 26, y - 16, "+"),
};
const PLUS = (x, y) => T(x, y, "+");
const ARROW = (x, y) => `<path d="M${x - 26} ${y}h52m-10 -7l10 7l-10 7"/>`;
const EQ = (x, y) => `<path d="M${x - 26} ${y - 5}h52l-9 -7M${x + 26} ${y + 5}h-52l9 7"/>`;
function formulaRows(rows, h = 105){                             // rows: [[id, svg-Inhalt (y=0 oben)], …]
  let y = 0, html = "";
  for (const [id, inner] of rows){
    html += `<g class="row" id="${id}"><rect class="bg" x="0" y="${y}" width="760" height="${h}" rx="8"/><g transform="translate(0 ${y})">${inner}</g></g>`;
    y += h + 13;
  }
  html += `<text class="cnt" x="10" y="${y + 6}" id="fcnt"></text>`;
  $("fsvg").setAttribute("viewBox", `0 0 760 ${y + 14}`);
  $("fsvg").innerHTML = html;
}
let flashT = 0;
function flashFormula(id){
  const g = $(id); if (!g) return;
  for (const r of $("fsvg").querySelectorAll(".row")) r.classList.remove("flash");
  g.classList.add("flash"); flashT = 1.2;
}
const dimRow = (id, on) => { const g = $(id); g && g.classList.toggle("dim", on); };

/* ---------- Anzeige ---------- */
function counts(){
  buildLists();
  const n = {H2O:0, "H3O+":0, "OH-":0, HCl:0, "Cl-":0, NH3:0, "NH4+":0, "Na+":0};
  for (let i = 0; i < A.length; i++) if (A[i].el !== "H") n[kind(i)]++;
  return n;
}
const fmt = (x, d = 1) => x.toFixed(d).replace(".", ",");
let lastStatus = "";
function setStatus(s){ if (s !== lastStatus){ $("status").textContent = s; lastStatus = s; } }
const msgNow = () => S.msg && S.t < S.msg.until ? S.msg.text : null;
function updateText(){
  const n = counts(), [readout, status] = PAGE.text(S, n);
  $("readout").textContent = readout;
  setStatus(status);
  PAGE.updateFormula && PAGE.updateFormula(S, n);
}

/* ---------- Bedienung ---------- */
let running = false, speed = 1, sceneId = 1, PAGE = null;
function loadScene(id){
  sceneId = id; seed = 1000 + id * 7919 + Math.floor(Math.random() * 1e6);
  A = []; S = null; S = PAGE.scenes[id](); buildLists();
  if (!S.closeup) equilibrate(1.2);
  S.post && S.post();
  [rotY, rotX] = S.closeup ? [-0.35, 0.28] : [0, 0];              // Kästen beginnen in der Ansicht von vorn
  zoom = 1; running = false;
  $("stepbtn").hidden = !S.PH;
  $("fmwrap").hidden = !!S.closeup;                               // Nahaufnahme: Formel immer sichtbar
  $("formula").hidden = !S.closeup && !$("fmchk").checked;
  for (const b of $("scenes").querySelectorAll("button")) b.setAttribute("aria-checked", String(+b.dataset.scene === id));
  PAGE.formula(S); syncButtons(); syncControls(); updateText(); dirty = true;
}
function syncButtons(){                                          // Knöpfe der Szene (z. B. „HCl zugeben“) zeigen
  for (const b of document.querySelectorAll(".scenebtn")){
    const cfg = S.buttons.find(c => c.id === b.id);
    b.hidden = !cfg;
    if (cfg) b.disabled = (S.added[cfg.key] || 0) >= cfg.max;
  }
}
function syncControls(){
  const done = S.PH && phaseOf(S.t) >= S.PH.length - 2;
  $("playbtn").textContent = running ? "Pause" : (S.t > 0 && !done ? "Weiter" : "Start");
  $("playbtn").disabled = !!done;
  $("stepbtn").disabled = !!done;
}
function bindRadio(id, attr, fn){
  $(id).addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    for (const x of $(id).querySelectorAll("button")) x.setAttribute("aria-checked", String(x === b));
    fn(b.dataset[attr]);
  });
}
const setZoom = z => { zoom = Math.max(0.5, Math.min(3.5, z)); dirty = true; };
function bindControls(){
  bindRadio("scenes", "scene", v => loadScene(+v));
  bindRadio("speedchips", "speed", v => { speed = +v; });
  $("playbtn").addEventListener("click", () => { running = !running; if (S.PH) S.stopAt = null; syncControls(); updateText(); });
  $("stepbtn").addEventListener("click", () => {                 // bis zum Beginn des nächsten Schritts laufen
    const ph = phaseOf(S.t); S.stopAt = S.PH[ph + 1]; running = true; syncControls();
  });
  $("resetbtn").addEventListener("click", () => loadScene(sceneId));
  for (const b of document.querySelectorAll(".scenebtn")) b.addEventListener("click", () => {
    const cfg = S.buttons.find(c => c.id === b.id);
    if (cfg && (S.added[cfg.key] || 0) < cfg.max) cfg.add();
  });
  $("hbchk").addEventListener("change", e => { showHB = e.target.checked; dirty = true; });
  $("fmchk").addEventListener("change", e => { $("formula").hidden = !e.target.checked; });
  // Drehen durch Ziehen (ein Finger) oder Pfeiltasten; Vergrößern mit Mausrad, zwei Fingern oder + / −
  const pts = new Map();
  let drag = null, pinch = null;
  const pinchDist = () => { const [a, b] = [...pts.values()]; return Math.hypot(a.x - b.x, a.y - b.y) || 1; };
  cv.addEventListener("pointerdown", e => {
    pts.set(e.pointerId, {x:e.clientX, y:e.clientY}); cv.setPointerCapture(e.pointerId);
    if (pts.size === 2){ drag = null; pinch = {d:pinchDist(), z:zoom}; }
    else if (pts.size === 1){ drag = {x:e.clientX, y:e.clientY}; cv.classList.add("dragging"); }
  });
  cv.addEventListener("pointermove", e => {
    if (!pts.has(e.pointerId)) return;
    pts.set(e.pointerId, {x:e.clientX, y:e.clientY});
    if (pinch && pts.size === 2){ setZoom(pinch.z * pinchDist() / pinch.d); return; }
    if (!drag) return;
    rotY += (e.clientX - drag.x) * 0.01; rotX = Math.max(-1.4, Math.min(1.4, rotX + (e.clientY - drag.y) * 0.01));
    drag = {x:e.clientX, y:e.clientY}; dirty = true;
  });
  const endDrag = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch = null; if (!pts.size){ drag = null; cv.classList.remove("dragging"); } };
  cv.addEventListener("pointerup", endDrag); cv.addEventListener("pointercancel", endDrag);
  cv.addEventListener("wheel", e => { e.preventDefault(); setZoom(zoom * Math.exp(-e.deltaY * 0.0015)); }, {passive:false});
  $("zin").addEventListener("click", () => setZoom(zoom * 1.25));
  $("zout").addEventListener("click", () => setZoom(zoom / 1.25));
  cv.addEventListener("keydown", e => {
    if (e.key === "+" || e.key === "="){ e.preventDefault(); setZoom(zoom * 1.25); return; }
    if (e.key === "-"){ e.preventDefault(); setZoom(zoom / 1.25); return; }
    const d = {ArrowLeft:[-.1, 0], ArrowRight:[.1, 0], ArrowUp:[0, -.1], ArrowDown:[0, .1]}[e.key];
    if (!d) return;
    e.preventDefault(); rotY += d[0]; rotX = Math.max(-1.4, Math.min(1.4, rotX + d[1])); dirty = true;
  });
}

/* ---------- Schleife ---------- */
let last = 0;
function frame(ts){
  const dt = Math.min(0.05, last ? (ts - last) / 1000 : 0); last = ts;
  if (running){
    let sim = dt * speed;
    if (S.flying.length && !S.closeup) sim *= 0.25;              // Zeitlupe während eines Sprungs
    if (S.PH){
      const ph0 = phaseOf(S.t);
      if (S.stopAt != null && S.t + sim >= S.stopAt) sim = Math.max(0, S.stopAt - S.t);
      const n = Math.max(1, Math.ceil(sim / H_MAX));
      for (let k = 0; k < n && sim > 0; k++) step(sim / n);
      if (S.stopAt != null && S.t >= S.stopAt - 1e-6){ S.t = S.stopAt; running = false; S.stopAt = null; }   // genau auf der Schrittgrenze anhalten
      const ph1 = phaseOf(S.t);
      if (ph1 !== ph0) S.onPhase(ph1);
      if (ph1 >= S.PH.length - 2) running = false;
    } else {
      const n = Math.min(12, Math.ceil(sim / H_MAX));
      for (let k = 0; k < n; k++) step(sim / n);
    }
    if (flashT > 0){ flashT -= dt; if (flashT <= 0) for (const r of $("fsvg").querySelectorAll(".row")) r.classList.remove("flash"); }
    syncControls(); updateText(); dirty = true;
  }
  if (dirty){ draw(); dirty = false; }
  requestAnimationFrame(frame);
}
function boot(page){
  PAGE = page;
  bindControls();
  new ResizeObserver(resize).observe(cv);
  loadScene(1);
  resize();
  requestAnimationFrame(frame);
}
