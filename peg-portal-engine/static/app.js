(() => {
  "use strict";

  const form = document.getElementById("form-config");
  const logArea = document.getElementById("log-area");
  const logStatus = document.getElementById("log-status");
  const btnLimpar = document.getElementById("btn-limpar-log");

  const selectProfile     = document.getElementById("select-profile");
  const btnRecarregarLista = document.getElementById("btn-recarregar-lista");
  const btnNovoProfile    = document.getElementById("btn-novo-profile");
  const btnCarregarProf   = document.getElementById("btn-carregar-profile");
  const btnValidarProf    = document.getElementById("btn-validar-profile");
  const btnSalvarProf     = document.getElementById("btn-salvar-profile");
  const btnExcluirProf    = document.getElementById("btn-excluir-profile");
  const btnSetupProfile   = document.getElementById("btn-setup-profile");
  const profileInfo       = document.getElementById("profile-info");

  const MASCARA_SENSIVEL = "****";
  let profileSlugAtivo = "";
  let streamAtivo = null;

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

  const STEP_FIELDS = [
    ["install_plugins",   "step_install_plugins"],
    ["configure_wp",      "step_configure_wp"],
    ["apply_seo",         "step_apply_seo"],
    ["create_pages",      "step_create_pages"],
    ["create_categories", "step_create_categories"],
    ["create_test_post",  "step_create_test_post"],
    ["generate_report",   "step_generate_report"],
  ];

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
    if (status === "exists") return "log-aviso";
    return "log-info";
  }

  function getVal(name) {
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return "";
    return (el.value || "").toString().trim();
  }

  function getCheck(name) {
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return false;
    return !!el.checked;
  }

  function coletarPayload() {
    // Modo manual: payload achatado para os endpoints legados.
    const fd = new FormData(form);
    const payload = {};
    for (const [k, v] of fd.entries()) {
      if (k === "opcionais") continue;
      payload[k] = v;
    }
    payload.opcionais = fd.getAll("opcionais");
    return payload;
  }

  function coletarStepFlags() {
    const out = {};
    STEP_FIELDS.forEach(([flag, field]) => {
      out[flag] = getCheck(field);
    });
    return out;
  }

  function coletarProfilePayload() {
    // Payload achatado que build_profile_from_payload entende.
    const fd = new FormData(form);
    const get = (k) => (fd.get(k) || "").toString();

    return {
      profile_slug:        get("profile_slug"),
      profile_version:     get("profile_version") || "1.0.0",
      profile_description: get("profile_description"),

      portal_name:     get("portal_name"),
      portal_domain:   get("portal_domain"),
      portal_niche:    get("portal_niche"),
      portal_language: get("portal_language") || "pt-BR",
      portal_timezone: get("portal_timezone") || "America/Sao_Paulo",

      wp_url:          get("wp_url"),
      wp_user:         get("wp_user"),
      wp_app_password: get("wp_app_password"),
      wp_path:         get("wp_path"),
      wpcli_bin:       get("wpcli_bin") || "/usr/local/bin/wp",

      ssh_host:        get("ssh_host"),
      ssh_port:        parseInt(get("ssh_port"), 10) || 22,
      ssh_user:        get("ssh_user"),
      ssh_auth_method: get("ssh_auth_method") || "password",
      ssh_password:    get("ssh_password"),
      ssh_key_path:    get("ssh_key_path"),

      seo_site_title:          get("seo_site_title"),
      seo_tagline:             get("seo_tagline"),
      seo_permalink_structure: get("seo_permalink_structure") || "/%postname%/",
      seo_blog_public:         getCheck("seo_blog_public"),
      seo_comments_enabled:    getCheck("seo_comments_enabled"),
      seo_ping_status:         getCheck("seo_ping_status"),
      seo_rank_math:           getCheck("seo_rank_math"),
      seo_instant_indexing:    getCheck("seo_instant_indexing"),

      plugins_required: get("plugins_required"),
      plugins_optional: get("plugins_optional"),
      plugins_skip:     get("plugins_skip"),

      content_create_pages:      getCheck("content_create_pages"),
      content_create_categories: getCheck("content_create_categories"),
      content_create_test_post:  getCheck("content_create_test_post"),
      content_homepage_slug:     get("content_homepage_slug") || "inicio",

      report_generate_markdown:           getCheck("report_generate_markdown"),
      report_include_manual_pending_tasks: getCheck("report_include_manual_pending_tasks"),
    };
  }

  function setBusy(busy) {
    document.querySelectorAll("[data-action]").forEach((b) => {
      b.disabled = busy;
    });
    [
      btnNovoProfile, btnCarregarProf, btnValidarProf,
      btnSalvarProf, btnExcluirProf, btnSetupProfile,
      btnRecarregarLista,
    ].forEach((b) => { if (b) b.disabled = busy; });
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

      if (data.status === "accepted" && data.job_id) {
          iniciarStream(data.job_id);
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
      // Se for stream, o stream ira desativar o setBusy no done
      if (!streamAtivo || streamAtivo.readyState === EventSource.CLOSED) {
          setBusy(false);
      }
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
  // Site Profiles — helpers para popular o formulario
  // -------------------------------------------------------------------- //
  function setVal(name, value) {
    if (value === undefined || value === null) return;
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return;
    el.value = value;
  }

  function setValSafe(name, value) {
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return;
    if (value === MASCARA_SENSIVEL || value === "" || value == null) {
      el.value = "";
    } else {
      el.value = value;
    }
  }

  function setCheck(name, value) {
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return;
    el.checked = !!value;
  }

  function setSelect(name, value) {
    if (!value) return;
    const sel = form.querySelector(`[name="${name}"]`);
    if (!sel) return;
    const opcao = Array.from(sel.options).find((o) => o.value === value);
    if (opcao) sel.value = value;
  }

  function listToTextarea(arr) {
    return Array.isArray(arr) ? arr.join("\n") : "";
  }

  function aplicarProfileNoForm(profile) {
    if (!profile) return;
    const pr     = profile.profile || {};
    const portal = profile.portal || {};
    const wp     = profile.wordpress || {};
    const ssh    = profile.ssh || {};
    const seo    = profile.seo || {};
    const plgs   = profile.plugins || {};
    const ct     = profile.content || {};
    const rep    = profile.report || {};

    setVal("profile_slug", pr.slug || "");
    setVal("profile_version", pr.version || "1.0.0");
    setVal("profile_description", pr.description || "");

    setVal("portal_name", portal.name);
    setVal("portal_domain", portal.domain);
    setVal("portal_language", portal.language || "pt-BR");
    setVal("portal_timezone", portal.timezone || "America/Sao_Paulo");
    setSelect("portal_niche", portal.niche);

    setVal("wp_url", wp.url);
    setVal("wp_user", wp.admin_user);
    setVal("wp_path", wp.wp_path);
    setVal("wpcli_bin", wp.wp_cli_path || "/usr/local/bin/wp");

    setVal("ssh_host", ssh.host);
    setVal("ssh_port", ssh.port || 22);
    setVal("ssh_user", ssh.user);
    setSelect("ssh_auth_method", ssh.auth_method || "password");

    // Sensiveis: NUNCA preencher mascara
    setValSafe("wp_app_password", wp.application_password);
    setValSafe("ssh_password", ssh.password);
    setValSafe("ssh_key_path", ssh.key_path);

    setVal("seo_site_title", seo.site_title || "");
    setVal("seo_tagline", seo.tagline || "");
    setVal("seo_permalink_structure", seo.permalink_structure || "/%postname%/");
    setCheck("seo_blog_public",      seo.blog_public !== false);
    setCheck("seo_comments_enabled", !!seo.comments_enabled);
    setCheck("seo_ping_status",      !!seo.ping_status);
    setCheck("seo_rank_math",        seo.rank_math !== false);
    setCheck("seo_instant_indexing", seo.instant_indexing !== false);

    setVal("plugins_required", listToTextarea(plgs.required));
    setVal("plugins_optional", listToTextarea(plgs.optional));
    setVal("plugins_skip",     listToTextarea(plgs.skip));

    // Plugins opcionais (modo manual): marca os que vierem em optional
    const optList = Array.isArray(plgs.optional) ? plgs.optional : [];
    document.querySelectorAll('[name="opcionais"]').forEach((cb) => {
      cb.checked = optList.includes(cb.value);
    });

    setCheck("content_create_pages",      ct.create_pages !== false);
    setCheck("content_create_categories", ct.create_categories !== false);
    setCheck("content_create_test_post",  ct.create_test_post !== false);
    setVal("content_homepage_slug",       ct.homepage_slug || "inicio");

    setCheck("report_generate_markdown",            rep.generate_markdown !== false);
    setCheck("report_include_manual_pending_tasks", rep.include_manual_pending_tasks !== false);

    // Steps: defaults a partir do profile
    setCheck("step_install_plugins",   true);
    setCheck("step_configure_wp",      true);
    setCheck("step_apply_seo",         true);
    setCheck("step_create_pages",      ct.create_pages !== false);
    setCheck("step_create_categories", ct.create_categories !== false);
    setCheck("step_create_test_post",  ct.create_test_post !== false);
    setCheck("step_generate_report",   rep.generate_markdown !== false);

    // Resumo
    const partes = [];
    if (pr.slug)       partes.push(`<code>${escapeHtml(pr.slug)}</code>`);
    if (portal.name)   partes.push(`<strong>${escapeHtml(portal.name)}</strong>`);
    if (portal.domain) partes.push(escapeHtml(portal.domain));
    if (portal.niche)  partes.push(`nicho: ${escapeHtml(portal.niche)}`);
    if (seo.tagline)   partes.push(`<em>${escapeHtml(seo.tagline)}</em>`);
    profileInfo.innerHTML =
      partes.length ? partes.join(" — ") : "Profile sem metadados.";
  }

  function coletarOverridesProfile() {
    // Overrides para o setup-from-profile: campos sensiveis + ajustes do form.
    const overrides = {};
    const wp = {}, ssh = {}, portal = {};

    if (getVal("wp_app_password")) wp.application_password = getVal("wp_app_password");
    if (getVal("wp_url"))           wp.url = getVal("wp_url");
    if (getVal("wp_user"))          wp.admin_user = getVal("wp_user");
    if (getVal("wp_path"))          wp.wp_path = getVal("wp_path");
    if (getVal("wpcli_bin"))        wp.wp_cli_path = getVal("wpcli_bin");

    if (getVal("ssh_password")) ssh.password = getVal("ssh_password");
    if (getVal("ssh_key_path")) ssh.key_path = getVal("ssh_key_path");
    if (getVal("ssh_host"))     ssh.host = getVal("ssh_host");
    if (getVal("ssh_user"))     ssh.user = getVal("ssh_user");
    if (getVal("ssh_port"))     ssh.port = parseInt(getVal("ssh_port"), 10) || 22;

    if (getVal("portal_name"))   portal.name = getVal("portal_name");
    if (getVal("portal_domain")) portal.domain = getVal("portal_domain");
    if (getVal("portal_niche"))  portal.niche = getVal("portal_niche");

    if (Object.keys(wp).length)     overrides.wordpress = wp;
    if (Object.keys(ssh).length)    overrides.ssh = ssh;
    if (Object.keys(portal).length) overrides.portal = portal;
    return overrides;
  }

  // -------------------------------------------------------------------- //
  // Listagem
  // -------------------------------------------------------------------- //
  async function carregarListaProfiles(silencioso = false) {
    try {
      const resp = await fetch("/api/site-profiles");
      const data = await resp.json();
      if (!Array.isArray(data.profiles)) return;
      const atual = selectProfile.value;
      selectProfile.innerHTML =
        '<option value="">— escolha um profile —</option>';
      data.profiles.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.slug;
        opt.textContent = `${p.name || p.slug} (${p.slug})`;
        selectProfile.appendChild(opt);
      });
      // mantem selecao se ainda existe
      if (atual) {
        const ainda = Array.from(selectProfile.options).some(
          (o) => o.value === atual
        );
        if (ainda) selectProfile.value = atual;
      }
      if (!silencioso) {
        appendLog(
          `${data.profiles.length} profile(s) disponiveis em config/sites/`,
          "log-meta"
        );
      }
    } catch (err) {
      appendLog("Erro ao listar profiles: " + err, "log-erro");
    }
  }

  // -------------------------------------------------------------------- //
  // Acoes do dashboard de profiles
  // -------------------------------------------------------------------- //
  function novoProfile() {
    form.reset();
    profileSlugAtivo = "";
    if (selectProfile) selectProfile.value = "";
    // Restaura defaults dos checkboxes que nascem marcados
    [
      "seo_blog_public", "seo_rank_math", "seo_instant_indexing",
      "content_create_pages", "content_create_categories",
      "content_create_test_post",
      "report_generate_markdown", "report_include_manual_pending_tasks",
      "step_install_plugins", "step_configure_wp", "step_apply_seo",
      "step_create_pages", "step_create_categories",
      "step_create_test_post", "step_generate_report",
    ].forEach((n) => setCheck(n, true));
    setVal("profile_version", "1.0.0");
    setVal("portal_language", "pt-BR");
    setVal("portal_timezone", "America/Sao_Paulo");
    setVal("seo_permalink_structure", "/%postname%/");
    setVal("wpcli_bin", "/usr/local/bin/wp");
    setVal("content_homepage_slug", "inicio");
    profileInfo.textContent =
      "Novo profile em branco. Preencha os campos e clique em Salvar.";
    appendLog("Novo profile (formulario limpo).", "log-meta");
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
          "Campos preenchidos. Complete senha SSH e Application Password antes de rodar.",
          "log-info"
        );
      }
    } catch (err) {
      appendLog("Erro: " + err, "log-erro");
    } finally {
      setBusy(false);
    }
  }

  async function validarProfile() {
    appendLog("▶ Validar profile", "log-meta");
    setBusy(true);
    try {
      const resp = await fetch("/api/validate-site-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(coletarProfilePayload()),
      });
      const data = await resp.json();
      const status = data.status || "erro";
      appendLog(
        `[${status.toUpperCase()}] ${data.message || ""}`,
        statusClasse(status)
      );
      const det = data.details || {};
      if (Array.isArray(det.errors) && det.errors.length) {
        det.errors.forEach((e) => appendLog("  - " + e, "log-aviso"));
      } else if (status === "ok") {
        appendLog("  estrutura OK; pronto para salvar.", "log-ok");
      }
    } catch (err) {
      appendLog("Erro: " + err, "log-erro");
    } finally {
      setBusy(false);
    }
  }

  async function _salvarRequest(payload, overwrite) {
    const resp = await fetch("/api/save-site-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.assign({}, payload, { overwrite })),
    });
    let data;
    try { data = await resp.json(); } catch (_e) { data = {}; }
    return { resp, data };
  }

  async function salvarProfile() {
    const payload = coletarProfilePayload();
    if (!payload.profile_slug) {
      appendLog("Slug do profile obrigatorio.", "log-erro");
      return;
    }
    appendLog("▶ Salvar profile " + payload.profile_slug, "log-meta");
    setBusy(true);
    try {
      let { resp, data } = await _salvarRequest(payload, false);
      let status = data.status || (resp.ok ? "ok" : "erro");

      if (status === "exists") {
        const slugAlvo =
          (data.details && data.details.slug) || payload.profile_slug;
        const ok = window.confirm(
          `Ja existe um profile '${slugAlvo}.json'. Sobrescrever?`
        );
        if (!ok) {
          appendLog("Operacao cancelada pelo usuario.", "log-aviso");
          return;
        }
        appendLog("  sobrescrevendo arquivo existente…", "log-meta");
        ({ resp, data } = await _salvarRequest(payload, true));
        status = data.status || (resp.ok ? "ok" : "erro");
      }

      appendLog(
        `[${status.toUpperCase()}] ${data.message || ""}`,
        statusClasse(status)
      );
      const det = data.details || {};
      if (Array.isArray(det.errors) && det.errors.length) {
        det.errors.forEach((e) => appendLog("  - " + e, "log-aviso"));
      }
      if (status === "ok") {
        if (det.slug) profileSlugAtivo = det.slug;
        await carregarListaProfiles(true);
        if (det.slug && selectProfile) selectProfile.value = det.slug;
      }
    } catch (err) {
      appendLog("Erro: " + err, "log-erro");
    } finally {
      setBusy(false);
    }
  }

  async function excluirProfile() {
    const slug = (selectProfile.value || profileSlugAtivo || "").trim();
    if (!slug) {
      appendLog("Selecione um profile para excluir.", "log-aviso");
      return;
    }
    const ok = window.confirm(
      `Excluir definitivamente o profile '${slug}.json'? ` +
      `Esta acao nao pode ser desfeita.`
    );
    if (!ok) {
      appendLog("Operacao cancelada pelo usuario.", "log-aviso");
      return;
    }
    appendLog("▶ Excluir profile " + slug, "log-meta");
    setBusy(true);
    try {
      const resp = await fetch("/api/delete-site-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug }),
      });
      const data = await resp.json();
      const status = data.status || (resp.ok ? "ok" : "erro");
      appendLog(
        `[${status.toUpperCase()}] ${data.message || ""}`,
        statusClasse(status)
      );
      if (status === "ok") {
        if (profileSlugAtivo === slug) profileSlugAtivo = "";
        await carregarListaProfiles(true);
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
      appendLog("Carregue ou selecione um profile primeiro.", "log-aviso");
      return;
    }
    const steps = coletarStepFlags();
    const desligadas = Object.entries(steps)
      .filter(([, v]) => !v).map(([k]) => k);
    if (desligadas.length) {
      const ok = window.confirm(
        "As seguintes etapas serao puladas:\n  - " +
        desligadas.join("\n  - ") +
        "\n\nContinuar?"
      );
      if (!ok) {
        appendLog("Setup cancelado pelo usuario.", "log-aviso");
        return;
      }
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
          steps,
        }),
      });
      const data = await resp.json();
      
      if (data.status === "accepted" && data.job_id) {
          iniciarStream(data.job_id);
          return;
      }
      
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
      if (!streamAtivo || streamAtivo.readyState === EventSource.CLOSED) {
          setBusy(false);
      }
    }
  }

  // -------------------------------------------------------------------- //
  // Subir JSON e rodar (caminho rapido)
  // -------------------------------------------------------------------- //
  const inputUploadFile = document.getElementById("upload-profile-file");
  const btnUploadRun    = document.getElementById("btn-upload-run");

  function lerArquivoComoJSON(file) {
    return new Promise((resolve, reject) => {
      const fr = new FileReader();
      fr.onerror = () => reject(new Error("Falha ao ler arquivo."));
      fr.onload = () => {
        try {
          resolve(JSON.parse(String(fr.result || "")));
        } catch (e) {
          reject(new Error("JSON invalido: " + e.message));
        }
      };
      fr.readAsText(file, "utf-8");
    });
  }

  async function uploadEAplicar() {
    if (!inputUploadFile || !inputUploadFile.files || !inputUploadFile.files[0]) {
      appendLog("Selecione um arquivo .json antes de enviar.", "log-aviso");
      return;
    }
    const file = inputUploadFile.files[0];
    let profile;
    try {
      profile = await lerArquivoComoJSON(file);
    } catch (err) {
      appendLog(String(err.message || err), "log-erro");
      return;
    }

    const slug = (profile && profile.profile && profile.profile.slug) || file.name;
    const ok = window.confirm(
      "Rodar setup completo agora usando o JSON '" + slug + "'?\n\n" +
      "As credenciais NAO serao gravadas em disco — sao usadas apenas " +
      "para esta execucao."
    );
    if (!ok) {
      appendLog("Setup cancelado pelo usuario.", "log-aviso");
      return;
    }

    appendLog("▶ Subir e rodar (" + slug + ")", "log-meta");
    setBusy(true);
    try {
      const resp = await fetch("/api/upload-and-run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      const data = await resp.json();
      
      if (data.status === "accepted" && data.job_id) {
          iniciarStream(data.job_id);
          return;
      }
      
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
      if (!streamAtivo || streamAtivo.readyState === EventSource.CLOSED) {
          setBusy(false);
      }
    }
  }

  // -------------------------------------------------------------------- //
  // SSE (Server-Sent Events) Stream
  // -------------------------------------------------------------------- //
  function iniciarStream(jobId) {
      if (streamAtivo) streamAtivo.close();
      setBusy(true);
      appendLog(`Conectando ao stream do job ${jobId}...`, "log-meta");
      
      streamAtivo = new EventSource(`/api/stream/${jobId}`);
      
      streamAtivo.onmessage = function(e) {
          try {
              const event = JSON.parse(e.data);
              
              if (event.type === "step") {
                  const step = event.data;
                  appendLog(`[ETAPA ${step.step_id}] ${step.title} - ${step.status}: ${step.details}`, statusClasse(step.status));
              } 
              else if (event.type === "done") {
                  const res = event.data;
                  const status = res.status || "erro";
                  appendLog(`[FINALIZADO ${status.toUpperCase()}] ${res.message}`, statusClasse(status));
                  streamAtivo.close();
                  setBusy(false);
              }
              else if (event.type === "error") {
                  appendLog(`[ERRO CRITICO] ${event.message}`, "log-erro");
                  streamAtivo.close();
                  setBusy(false);
              }
          } catch(err) {
              appendLog("Erro processando evento SSE: " + err, "log-erro");
          }
      };
      
      streamAtivo.onerror = function() {
          appendLog("Conexao com o servidor perdida ou encerrada.", "log-erro");
          streamAtivo.close();
          setBusy(false);
      };
  }

  // -------------------------------------------------------------------- //
  // Bind dos botoes do dashboard
  // -------------------------------------------------------------------- //
  if (selectProfile)        carregarListaProfiles();
  if (btnRecarregarLista)   btnRecarregarLista.addEventListener("click", () => carregarListaProfiles());
  if (btnNovoProfile)       btnNovoProfile.addEventListener("click", novoProfile);
  if (btnCarregarProf)      btnCarregarProf.addEventListener("click", carregarProfileSelecionado);
  if (btnValidarProf)       btnValidarProf.addEventListener("click", validarProfile);
  if (btnSalvarProf)        btnSalvarProf.addEventListener("click", salvarProfile);
  if (btnExcluirProf)       btnExcluirProf.addEventListener("click", excluirProfile);
  if (btnSetupProfile)      btnSetupProfile.addEventListener("click", rodarSetupPeloProfile);
  if (btnUploadRun)         btnUploadRun.addEventListener("click", uploadEAplicar);

  appendLog("Painel pronto. Preencha os campos e clique em uma acao.", "log-meta");
})();
