(function () {
  "use strict";
  const assetFetch = window.fetch.bind(window);
  const origin = new URL(location.href);
  const gate = document.createElement("div");
  gate.setAttribute("role", "status");
  gate.style.cssText = "position:fixed;inset:0;background:#f8fafb;z-index:100;display:flex;align-items:center;justify-content:center;padding:24px;text-align:center;white-space:pre-wrap;font:16px Arial;";
  gate.textContent = "Starting offline calculator…\n正在启动离线计算器…";
  document.body.appendChild(gate);
  const localAsset = async path => {
    const response = await assetFetch(new URL(path, location.href));
    if (!response.ok) throw new Error("Missing bundled resource: " + path);
    return response;
  };
  const script = path => new Promise((resolve, reject) => {
    const node = document.createElement("script");
    node.src = path; node.onload = resolve; node.onerror = reject;
    document.body.appendChild(node);
  });

  window.pplOfflineReady = (async () => {
    const python = await loadPyodide({ indexURL: new URL("runtime/", location.href).href });
    await python.loadPackage("numpy");
    python.unpackArchive(await (await localAsset("engine.zip")).arrayBuffer(), "zip", { extractDir: "/ppl" });
    python.runPython("import sys; sys.path.insert(0, '/ppl')\nfrom offline_engine import dispatch");
    const dispatch = python.globals.get("dispatch");
    window.fetch = async (input, options = {}) => {
      const url = new URL(typeof input === "string" ? input : input.url, location.href);
      if (url.protocol !== origin.protocol || url.host !== origin.host || !url.pathname.startsWith("/api/")) {
        throw new Error("Offline mode blocks network requests");
      }
      const isJSON = typeof options.body === "string";
      const values = options.body instanceof FormData ? Object.fromEntries(options.body.entries()) : options.body || "{}";
      const result = JSON.parse(dispatch(url.pathname, options.method || "GET", isJSON ? values : JSON.stringify(values), isJSON));
      return { ok: result.status >= 200 && result.status < 300, status: result.status,
        json: async () => result.body, text: async () => JSON.stringify(result.body) };
    };
    // Separate classic script elements preserve the existing global lexical bindings.
    await script("static/platform.js");
    for (const deferred of document.querySelectorAll('script[type="text/ppl-deferred"]')) {
      const node = document.createElement("script");
      node.textContent = deferred.textContent;
      document.body.appendChild(node);
    }
    await script("static/performance.js");
    await script("static/aircraft.js");
    for (let count = 0; !window.aircraftProfiles; count++) {
      if (count > 300) throw new Error("Aircraft profiles did not initialize");
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    gate.remove();
    document.documentElement.dataset.offlineReady = "true";
    window.webkit?.messageHandlers?.pplReady?.postMessage("ready");
    return true;
  })().catch(error => {
    gate.textContent = "Offline startup failed. Reopen the app or reinstall the complete IPA.\n离线启动失败。请重新打开 App，或安装完整 IPA。\n\n" + error.message;
    document.documentElement.dataset.offlineError = error.message;
    throw error;
  });
})();
