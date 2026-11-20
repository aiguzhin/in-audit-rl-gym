/* FinSpector · Python-лаборатория: Pyodide + auditenv в отдельном потоке, чтобы страница не подвисала. */
const BASE = new URL("../py/", self.location.href).href;
const FILES = ["__init__", "money", "config", "generator", "policy", "reference", "matcher", "calculator", "env", "policies", "checks"];
let py = null;
const send = (t, extra) => postMessage(Object.assign({ t }, extra));

async function init() {
  importScripts(BASE + "pyodide/pyodide.js");
  py = await loadPyodide({ indexURL: BASE + "pyodide/" });
  py.FS.mkdirTree("/home/pyodide/auditenv");
  await Promise.all(FILES.map(async f => {
    const r = await fetch(BASE + "auditenv/" + f + ".py");
    if (!r.ok) throw new Error("auditenv/" + f + ".py");
    py.FS.writeFile("/home/pyodide/auditenv/" + f + ".py", await r.text());
  }));
  py.setStdout({ batched: s => send("out", { s: s + "\n" }) });
  py.setStderr({ batched: s => send("err", { s: s + "\n" }) });
  py.runPython('import sys, os; sys.path.insert(0, "/home/pyodide"); os.chdir("/home/pyodide")\nimport auditenv.env, auditenv.policies');
  send("ready", { version: py.version });
}

function cleanTrace(msg) {
  const lines = String(msg).split("\n");
  const out = [];
  let skip = false;
  for (const l of lines) {
    if (/^\s*File "\/lib\/python/.test(l) || /_pyodide/.test(l)) { skip = true; continue; }
    if (skip && /^\s{4}/.test(l)) continue;
    skip = false;
    out.push(l.replace('File "<exec>"', "Ваш код"));
  }
  return out.join("\n").trim() + "\n";
}

const ready = init().catch(e => send("fail", { s: String(e && e.message || e) }));

onmessage = async e => {
  await ready;
  if (!py) return;
  const { code, id } = e.data;
  const ns = py.globals.get("dict")();
  const t0 = performance.now();
  let ok = true;
  try {
    // сбрасываем модули, чтобы правки в auditenv из прошлого запуска не мешали
    await py.runPythonAsync(code, { globals: ns, filename: "<exec>" });
  } catch (err) {
    ok = false;
    send("err", { s: cleanTrace(err.message || err) });
  } finally {
    ns.destroy();
  }
  send("done", { id, ok, ms: Math.round(performance.now() - t0) });
};
