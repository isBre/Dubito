// Pyodide backend for the static GitHub Pages build of the Dubito web game.
//
// Defines window.dubitoLocalApi(path, method, body) -> {status, data}, which
// templates/index.html's api() prefers over fetch() when present. The Python
// engine (web_session.handle_api and everything below it) runs entirely in
// this browser tab; build_static.py packs it into engine.zip next to this
// file and injects both script tags into the page.
(() => {
  const startBtn = () => document.getElementById('btn-start');

  function status(text, disabled) {
    const btn = startBtn();
    if (!btn) return;
    btn.disabled = disabled;
    btn.textContent = text;
  }

  const engineReady = (async () => {
    status('LOADING ENGINE…', true);
    const pyodide = await loadPyodide();
    status('DEALING THE DECK…', true);
    const resp = await fetch('engine.zip');
    if (!resp.ok) throw new Error(`engine.zip: HTTP ${resp.status}`);
    pyodide.unpackArchive(await resp.arrayBuffer(), 'zip');
    const handleApi = pyodide.pyimport('web_session').handle_api;
    status('START GAME', false);
    return (path, method, body) =>
      JSON.parse(handleApi(path, method, body == null ? null : JSON.stringify(body)));
  })();

  engineReady.catch((e) => {
    console.error('Dubito engine failed to load:', e);
    status('ENGINE FAILED — RELOAD PAGE', true);
  });

  window.dubitoLocalApi = async (path, method, body) => {
    const call = await engineReady;
    return call(path, method, body);
  };
})();
