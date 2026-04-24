(() => {
  "use strict";

  const form = document.getElementById("form-config");
  const logArea = document.getElementById("log-area");
  const logStatus = document.getElementById("log-status");
  const btnLimpar = document.getElementById("btn-limpar-log");

  const ENDPOINTS = {
    testar_ssh:        "/api/testar_ssh",
    testar_rest:       "/api/testar_rest",
    validar_wp:        "/api/validar_wp",
    validar_wpcli:     "/api/validar_wpcli",
    verificar_redis:   "/api/verificar_redis",
    instalar_plugins:  "/api/instalar_plugins",
    configurar_wp:     "/api/configurar_wp",
    criar_categorias:  "/api/criar_categorias",
    criar_paginas:     "/api/criar_paginas",
    criar_conteudo:    "/api/criar_conteudo",
    setup_completo:    "/api/setup_completo",
    gerar_relatorio:   "/api/gerar_relatorio",
  };

  const TITULOS = {
    testar_ssh:        "Testar SSH",
    testar_rest:       "Testar REST API",
    validar_wp:        "Validar WordPress",
    validar_wpcli:     "Validar WP-CLI",
    verificar_redis:   "Verificar Redis",
    instalar_plugins:  "Instalar plugins",
    configurar_wp:     "Configurar WordPress",
    criar_categorias:  "Criar categorias",
    criar_paginas:     "Criar paginas",
    criar_conteudo:    "Criar conteudo inicial",
    setup_completo:    "Setup completo",
    gerar_relatorio:   "Gerar relatorio",
  };

  function ts() {
    const d = new Date();
    return d.toLocaleTimeString("pt-BR", { hour12: false });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function appendLog(text, classe = "log-info") {
    const span = document.createElement("span");
    span.className = "log-line " + classe;
    span.innerHTML = "[" + ts() + "] " + escapeHtml(text);
    logArea.appendChild(span);
    logArea.appendChild(document.createTextNode("\n"));
    logArea.scrollTop = logArea.scrollHeight;
  }

  function statusClasse(status) {
    if (status === "ok") return "log-ok";
    if (status === "aviso") return "log-aviso";
    if (status === "erro") return "log-erro";
    return "log-info";
  }

  function coletarPayload() {
    const fd = new FormData(form);
    const payload = {};
    for (const [k, v] of fd.entries()) {
      if (k === "opcionais") continue;
      payload[k] = v;
    }
    payload.opcionais = fd.getAll("opcionais");
    return payload;
  }

  function setBusy(busy) {
    document.querySelectorAll("[data-action]").forEach((b) => {
      b.disabled = busy;
    });
    logStatus.textContent = busy ? "executando…" : "pronto";
  }

  async function executar(action) {
    const url = ENDPOINTS[action];
    if (!url) {
      appendLog("acao desconhecida: " + action, "log-erro");
      return;
    }

    appendLog("▶ " + TITULOS[action], "log-meta");
    setBusy(true);

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(coletarPayload()),
      });

      let data;
      try {
        data = await resp.json();
      } catch (_e) {
        appendLog("Resposta nao-JSON (HTTP " + resp.status + ")", "log-erro");
        return;
      }

      const status = data.status || (resp.ok ? "ok" : "erro");
      const klass = statusClasse(status);
      appendLog(
        "[" + status.toUpperCase() + "] " + (data.message || "(sem mensagem)"),
        klass
      );

      if (data.details) {
        try {
          const det =
            typeof data.details === "string"
              ? data.details
              : JSON.stringify(data.details, null, 2);
          appendLog(det, "log-muted");
        } catch (_e) {
          /* ignore */
        }
      }
    } catch (err) {
      appendLog("Erro de rede: " + (err && err.message ? err.message : err), "log-erro");
    } finally {
      setBusy(false);
    }
  }

  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.getAttribute("data-action");
      executar(action);
    });
  });

  if (btnLimpar) {
    btnLimpar.addEventListener("click", () => {
      logArea.innerHTML = "";
      logStatus.textContent = "log limpo";
    });
  }

  appendLog("Painel pronto. Preencha os campos e clique em uma acao.", "log-meta");
})();
