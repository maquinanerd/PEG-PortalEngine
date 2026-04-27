(() => {
  "use strict";

  const form = document.getElementById("form-config");
  const logArea = document.getElementById("log-area");
  const logStatus = document.getElementById("log-status");
  const btnLimpar = document.getElementById("btn-limpar-log");

  const selectProfile     = document.getElementById("select-profile");
  const btnCarregarProf   = document.getElementById("btn-carregar-profile");
  const btnSetupProfile   = document.getElementById("btn-setup-profile");
  const profileInfo       = document.getElementById("profile-info");

  const MASCARA_SENSIVEL = "****";
  let profileSlugAtivo = "";

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

  // -------------------------------------------------------------------- //
  // Site Profiles
  // -------------------------------------------------------------------- //
  function setVal(name, value) {
    if (value === undefined || value === null) return;
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return;
    el.value = value;
  }

  function setValSafe(name, value) {
    // Para campos sensiveis: nunca preencher mascara, sempre limpar.
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return;
    if (value === MASCARA_SENSIVEL || value === "" || value == null) {
      el.value = "";
    } else {
      el.value = value;
    }
  }

  function aplicarProfileNoForm(profile) {
    if (!profile) return;
    const portal = profile.portal || {};
    const wp     = profile.wordpress || {};
    const ssh    = profile.ssh || {};
    const seo    = profile.seo || {};

    setVal("portal_name", portal.name);
    setVal("portal_domain", portal.domain);
    setVal("wp_url", wp.url);
    setVal("wp_user", wp.admin_user);
    setVal("wp_path", wp.wp_path);
    setVal("wpcli_bin", wp.wp_cli_path);
    setVal("ssh_host", ssh.host);
    setVal("ssh_port", ssh.port);
    setVal("ssh_user", ssh.user);

    // Nicho: select — atualiza so se valor existir
    if (portal.niche) {
      const sel = form.querySelector('[name="portal_niche"]');
      if (sel) {
        const opcao = Array.from(sel.options).find(
          (o) => o.value === portal.niche
        );
        if (opcao) sel.value = portal.niche;
      }
    }

    // Sensiveis: nunca auto-preencher mascara
    setValSafe("wp_app_password", wp.application_password);
    setValSafe("ssh_password", ssh.password);
    setValSafe("ssh_key_path", ssh.key_path);

    // Plugins opcionais: marcar checkboxes do profile
    const pluginsBlock = profile.plugins || {};
    const optList = Array.isArray(pluginsBlock.optional)
      ? pluginsBlock.optional : [];
    document.querySelectorAll('[name="opcionais"]').forEach((cb) => {
      cb.checked = optList.includes(cb.value);
    });

    // Mostra info resumida
    const partes = [];
    if (portal.name) partes.push(`<strong>${escapeHtml(portal.name)}</strong>`);
    if (portal.domain) partes.push(escapeHtml(portal.domain));
    if (portal.niche) partes.push(`nicho: ${escapeHtml(portal.niche)}`);
    if (seo.tagline) partes.push(`<em>${escapeHtml(seo.tagline)}</em>`);
    profileInfo.innerHTML =
      partes.length ? partes.join(" — ") : "Profile sem metadados.";
  }

  function coletarOverridesProfile() {
    // Pega valores preenchidos no formulario que devem complementar/sobrepor o profile.
    const fd = new FormData(form);
    const get = (k) => (fd.get(k) || "").toString().trim();
    const overrides = {};
    const wp = {}, ssh = {}, portal = {};

    if (get("wp_app_password")) wp.application_password = get("wp_app_password");
    if (get("wp_url"))           wp.url = get("wp_url");
    if (get("wp_user"))          wp.admin_user = get("wp_user");
    if (get("wp_path"))          wp.wp_path = get("wp_path");
    if (get("wpcli_bin"))        wp.wp_cli_path = get("wpcli_bin");

    if (get("ssh_password")) ssh.password = get("ssh_password");
    if (get("ssh_key_path")) ssh.key_path = get("ssh_key_path");
    if (get("ssh_host"))     ssh.host = get("ssh_host");
    if (get("ssh_user"))     ssh.user = get("ssh_user");
    if (get("ssh_port"))     ssh.port = parseInt(get("ssh_port"), 10) || 22;

    if (get("portal_name"))   portal.name = get("portal_name");
    if (get("portal_domain")) portal.domain = get("portal_domain");
    if (get("portal_niche"))  portal.niche = get("portal_niche");

    if (Object.keys(wp).length)    overrides.wordpress = wp;
    if (Object.keys(ssh).length)   overrides.ssh = ssh;
    if (Object.keys(portal).length) overrides.portal = portal;
    return overrides;
  }

  async function carregarListaProfiles() {
    try {
      const resp = await fetch("/api/site-profiles");
      const data = await resp.json();
      if (!Array.isArray(data.profiles)) return;
      // Limpa exceto o placeholder
      selectProfile.innerHTML =
        '<option value="">— escolha um profile —</option>';
      data.profiles.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.slug;
        opt.textContent = `${p.name} (${p.slug})`;
        selectProfile.appendChild(opt);
      });
      appendLog(
        `${data.profiles.length} profile(s) disponiveis em config/sites/`,
        "log-meta"
      );
    } catch (err) {
      appendLog("Erro ao listar profiles: " + err, "log-erro");
    }
  }

  async function carregarProfileSelecionado() {
    const slug = (selectProfile.value || "").trim();
    if (!slug) {
      appendLog("Escolha um profile no select.", "log-aviso");
      return;
    }
    appendLog("▶ Carregar profile " + slug, "log-meta");
    setBusy(true);
    try {
      const resp = await fetch("/api/load-site-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug }),
      });
      const data = await resp.json();
      const status = data.status || "erro";
      appendLog(
        `[${status.toUpperCase()}] ${data.message || ""}`,
        statusClasse(status)
      );

      if (Array.isArray(data.errors) && data.errors.length) {
        data.errors.forEach((e) => appendLog("  - " + e, "log-aviso"));
      }

      if (data.profile) {
        aplicarProfileNoForm(data.profile);
        profileSlugAtivo = (data.meta && data.meta.slug) || slug;
        appendLog(
          "Campos preenchidos. Complete senha SSH e Application Password.",
          "log-info"
        );
      }
    } catch (err) {
      appendLog("Erro: " + err, "log-erro");
    } finally {
      setBusy(false);
    }
  }

  async function rodarSetupPeloProfile() {
    const slug = (selectProfile.value || profileSlugAtivo || "").trim();
    if (!slug) {
      appendLog("Carregue um profile primeiro.", "log-aviso");
      return;
    }
    appendLog("▶ Setup pelo profile " + slug, "log-meta");
    setBusy(true);
    try {
      const resp = await fetch("/api/setup-from-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug,
          overrides: coletarOverridesProfile(),
        }),
      });
      const data = await resp.json();
      const status = data.status || "erro";
      appendLog(
        `[${status.toUpperCase()}] ${data.message || ""}`,
        statusClasse(status)
      );
      if (data.details) {
        try {
          const det = typeof data.details === "string"
            ? data.details
            : JSON.stringify(data.details, null, 2);
          appendLog(det, "log-muted");
        } catch (_e) { /* ignore */ }
      }
    } catch (err) {
      appendLog("Erro: " + err, "log-erro");
    } finally {
      setBusy(false);
    }
  }

  if (selectProfile)   carregarListaProfiles();
  if (btnCarregarProf) btnCarregarProf.addEventListener("click", carregarProfileSelecionado);
  if (btnSetupProfile) btnSetupProfile.addEventListener("click", rodarSetupPeloProfile);

  appendLog("Painel pronto. Preencha os campos e clique em uma acao.", "log-meta");
})();
