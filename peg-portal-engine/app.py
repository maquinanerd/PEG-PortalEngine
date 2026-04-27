"""
PEG Portal Engine — painel local em Flask.

Rodar localmente em http://127.0.0.1:5000
Comando: python app.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from provisioner import tasks
from provisioner.logger import get_logger
from provisioner.utils import (
    carregar_niches,
    carregar_plugins,
    extrair_profile_meta,
    list_site_profiles,
    load_site_profile,
    merge_profile_with_payload,
    profile_para_cfg,
    sanitize_site_profile,
    validate_site_profile,
)


# Carrega .env (se existir) ANTES de iniciar logger/Flask, para que LOG_LEVEL
# e demais defaults estejam disponiveis.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.is_file():
    load_dotenv(_ENV_PATH)

_logger = get_logger()

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)
app.config["JSON_SORT_KEYS"] = False


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #
def _payload_para_cfg(payload: dict) -> dict:
    """Normaliza o payload do front em um dict aceito pelas tasks."""
    if not isinstance(payload, dict):
        return {}
    cfg = {
        "portal_name":    (payload.get("portal_name") or "").strip(),
        "portal_niche":   (payload.get("portal_niche") or "").strip(),
        "portal_domain":  (payload.get("portal_domain") or "").strip(),
        "wp_url":         (payload.get("wp_url") or "").strip().rstrip("/"),
        "wp_user":        (payload.get("wp_user") or "").strip(),
        "wp_app_password": payload.get("wp_app_password") or "",
        "ssh_host":       (payload.get("ssh_host") or "").strip(),
        "ssh_port":       int(payload.get("ssh_port") or 22),
        "ssh_user":       (payload.get("ssh_user") or "").strip(),
        "ssh_password":   payload.get("ssh_password") or "",
        "ssh_key_path":   (payload.get("ssh_key_path") or "").strip(),
        "wp_path":        (payload.get("wp_path") or "").strip(),
        "wpcli_bin":      (payload.get("wpcli_bin") or "/usr/local/bin/wp").strip(),
    }
    return cfg


def _opcionais(payload: dict) -> list:
    val = payload.get("opcionais") if isinstance(payload, dict) else None
    if isinstance(val, list):
        return [str(x) for x in val if x]
    if isinstance(val, str) and val:
        return [val]
    return []


def _erro_json(msg: str, status_http: int = 400):
    return jsonify({"status": "erro", "message": msg, "details": None}), status_http


def _executar(handler: Callable[[dict], dict], payload: dict) -> Any:
    try:
        cfg = _payload_para_cfg(payload)
        resultado = handler(cfg)
        return jsonify(resultado)
    except Exception as exc:
        _logger.exception("Erro nao tratado em handler: %s", exc)
        return _erro_json(f"Erro interno: {exc}", status_http=500)


# ---------------------------------------------------------------------- #
# Rota principal
# ---------------------------------------------------------------------- #
@app.route("/")
def index():
    try:
        niches = carregar_niches()
    except Exception as exc:
        _logger.error("Falha ao carregar niches.json: %s", exc)
        niches = []

    try:
        plugins = carregar_plugins()
    except Exception as exc:
        _logger.error("Falha ao carregar plugins.json: %s", exc)
        plugins = []

    plugins_opcionais = [p for p in plugins if not p.get("obrigatorio")]

    env_view = {
        "PORTAL_NAME":     os.getenv("PORTAL_NAME", ""),
        "PORTAL_NICHE":    os.getenv("PORTAL_NICHE", ""),
        "PORTAL_DOMAIN":   os.getenv("PORTAL_DOMAIN", ""),
        "WP_URL":          os.getenv("WP_URL", ""),
        "WP_USER":         os.getenv("WP_USER", ""),
        "WP_APP_PASSWORD": "",  # NUNCA pre-preencher senha por padrao
        "SSH_HOST":        os.getenv("SSH_HOST", ""),
        "SSH_PORT":        os.getenv("SSH_PORT", "22"),
        "SSH_USER":        os.getenv("SSH_USER", "root"),
        "SSH_PASSWORD":    "",  # idem
        "SSH_KEY_PATH":    os.getenv("SSH_KEY_PATH", ""),
        "WP_PATH":         os.getenv("WP_PATH", ""),
        "WPCLI_BIN":       os.getenv("WPCLI_BIN", "/usr/local/bin/wp"),
    }

    return render_template(
        "index.html",
        niches=niches,
        plugins_opcionais=plugins_opcionais,
        env=env_view,
    )


# ---------------------------------------------------------------------- #
# API endpoints
# ---------------------------------------------------------------------- #
@app.post("/api/testar_ssh")
def api_testar_ssh():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_testar_ssh, payload)


@app.post("/api/testar_rest")
def api_testar_rest():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_testar_rest, payload)


@app.post("/api/validar_wp")
def api_validar_wp():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_validar_wp, payload)


@app.post("/api/validar_wpcli")
def api_validar_wpcli():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_validar_wpcli, payload)


@app.post("/api/verificar_redis")
def api_verificar_redis():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_verificar_redis, payload)


@app.post("/api/instalar_plugins")
def api_instalar_plugins():
    payload = request.get_json(silent=True) or {}
    opcionais = _opcionais(payload)
    try:
        cfg = _payload_para_cfg(payload)
        return jsonify(tasks.acao_instalar_plugins(cfg, opcionais_extras=opcionais))
    except Exception as exc:
        _logger.exception("Erro em instalar_plugins: %s", exc)
        return _erro_json(f"Erro interno: {exc}", status_http=500)


@app.post("/api/configurar_wp")
def api_configurar_wp():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_configurar_wordpress, payload)


@app.post("/api/criar_categorias")
def api_criar_categorias():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_criar_categorias, payload)


@app.post("/api/criar_paginas")
def api_criar_paginas():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_criar_paginas, payload)


@app.post("/api/criar_conteudo")
def api_criar_conteudo():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_criar_conteudo_inicial, payload)


@app.post("/api/setup_completo")
def api_setup_completo():
    payload = request.get_json(silent=True) or {}
    opcionais = _opcionais(payload)
    try:
        cfg = _payload_para_cfg(payload)
        return jsonify(tasks.setup_completo(cfg, opcionais_extras=opcionais))
    except Exception as exc:
        _logger.exception("Erro em setup_completo: %s", exc)
        return _erro_json(f"Erro interno: {exc}", status_http=500)


@app.post("/api/gerar_relatorio")
def api_gerar_relatorio():
    payload = request.get_json(silent=True) or {}
    return _executar(tasks.acao_gerar_relatorio, payload)


# ---------------------------------------------------------------------- #
# Site Profiles
# ---------------------------------------------------------------------- #
@app.get("/api/site-profiles")
def api_site_profiles():
    try:
        profiles = list_site_profiles()
        return jsonify({
            "status": "ok",
            "message": f"{len(profiles)} profile(s) encontrado(s)",
            "profiles": profiles,
        })
    except Exception as exc:
        _logger.exception("Erro ao listar profiles: %s", exc)
        return _erro_json(f"Erro ao listar profiles: {exc}", status_http=500)


@app.post("/api/load-site-profile")
def api_load_site_profile():
    payload = request.get_json(silent=True) or {}
    slug = (payload.get("slug") or payload.get("path") or "").strip()
    if not slug:
        return _erro_json("Informe 'slug' ou 'path' do profile.")

    try:
        profile = load_site_profile(slug)
    except FileNotFoundError as exc:
        return _erro_json(str(exc), status_http=404)
    except Exception as exc:
        _logger.exception("Erro ao carregar profile '%s': %s", slug, exc)
        return _erro_json(f"Erro ao carregar profile: {exc}", status_http=500)

    ok, erros = validate_site_profile(profile)
    seguro = sanitize_site_profile(profile)
    meta = extrair_profile_meta(profile)

    return jsonify({
        "status": "ok" if ok else "erro",
        "message": (
            f"Profile '{meta.get('slug') or slug}' carregado"
            if ok else "Profile carregado com erros de validacao"
        ),
        "profile": seguro,
        "meta": meta,
        "valid": ok,
        "errors": erros,
    })


@app.post("/api/setup-from-profile")
def api_setup_from_profile():
    payload = request.get_json(silent=True) or {}
    slug = (payload.get("slug") or payload.get("path") or "").strip()
    if not slug:
        return _erro_json("Informe 'slug' do profile.")

    overrides = payload.get("overrides") or {}

    try:
        profile = load_site_profile(slug)
    except FileNotFoundError as exc:
        return _erro_json(str(exc), status_http=404)
    except Exception as exc:
        _logger.exception("Erro ao carregar profile '%s': %s", slug, exc)
        return _erro_json(f"Erro ao carregar profile: {exc}", status_http=500)

    profile_merged = merge_profile_with_payload(profile, overrides)

    ok, erros = validate_site_profile(profile_merged)
    if not ok:
        return jsonify({
            "status": "erro",
            "message": "Profile invalido: " + "; ".join(erros),
            "details": {"errors": erros},
        }), 400

    # Validar credenciais necessarias
    auth = (profile_merged.get("ssh") or {}).get("auth_method")
    ssh_block = profile_merged.get("ssh") or {}
    if auth == "password" and not (ssh_block.get("password") or "").strip():
        return _erro_json(
            "auth_method='password' requer senha SSH no profile, "
            "no formulario ou no .env."
        )
    if auth == "key" and not (ssh_block.get("key_path") or "").strip():
        return _erro_json(
            "auth_method='key' requer caminho da chave SSH no profile, "
            "no formulario ou no .env."
        )

    wp_block = profile_merged.get("wordpress") or {}
    if not (wp_block.get("application_password") or "").strip():
        return _erro_json(
            "Application Password do WordPress nao informada "
            "(profile ou formulario)."
        )

    cfg = profile_para_cfg(profile_merged)

    plugins_cfg = profile_merged.get("plugins") or {}
    required = list(plugins_cfg.get("required") or [])
    optional = list(plugins_cfg.get("optional") or [])
    skip = list(plugins_cfg.get("skip") or [])
    # required + optional viram opcionais_extras (forca instalacao)
    opcionais_extras = sorted(set(required) | set(optional))

    content_cfg = profile_merged.get("content") or {}
    content_flags = {
        "create_pages":     bool(content_cfg.get("create_pages", True)),
        "create_categories": bool(content_cfg.get("create_categories", True)),
        "create_test_post": bool(content_cfg.get("create_test_post", True)),
    }

    profile_meta = extrair_profile_meta(profile_merged)
    profile_meta["plugins_required"] = required
    profile_meta["plugins_optional"] = optional

    try:
        resultado = tasks.setup_completo(
            cfg,
            opcionais_extras=opcionais_extras,
            pular_plugins=skip,
            content_flags=content_flags,
            profile_meta=profile_meta,
        )
        # Anexa identificador do profile na resposta
        if isinstance(resultado, dict):
            resultado.setdefault("details", {})
            if isinstance(resultado["details"], dict):
                resultado["details"]["profile"] = {
                    "slug": profile_meta.get("slug"),
                    "name": profile_meta.get("name"),
                    "version": profile_meta.get("version"),
                }
        return jsonify(resultado)
    except Exception as exc:
        _logger.exception("Erro em setup-from-profile: %s", exc)
        return _erro_json(f"Erro interno: {exc}", status_http=500)


# ---------------------------------------------------------------------- #
# Entry point
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    _logger.info("Iniciando PEG Portal Engine em http://127.0.0.1:5000")
    # debug=False para evitar reload duplo (importante em Windows + Paramiko)
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
