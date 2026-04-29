"""
Orquestrador de tarefas do PEG Portal Engine.

Cada acao publica retorna um dicionario padronizado:
    {"status": "ok"|"erro"|"aviso", "message": str, "details": dict|list|None}

A funcao 'setup_completo' executa as 15 etapas em sequencia, parando apenas
em erros criticos (SSH ou WP invalidos) e registrando os demais como avisos.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Callable

from . import ssh_client
from .logger import get_logger, setup_run_logger, teardown_run_logger, get_run_dir
from .wp_rest import WPRest
from .wpcli import WPCLI
from .utils import (
    aplicar_placeholders,
    carregar_categorias,
    carregar_paginas,
    carregar_plugins,
    gerar_relatorio,
)


_logger = get_logger()


# ---------------------------------------------------------------------- #
# Helpers de SSH/WPCLI/REST a partir do payload do formulario
# ---------------------------------------------------------------------- #
def _ssh_kwargs(cfg: dict) -> dict:
    return {
        "host": (cfg.get("ssh_host") or "").strip(),
        "port": int(cfg.get("ssh_port") or 22),
        "user": (cfg.get("ssh_user") or "").strip(),
        "password": cfg.get("ssh_password") or None,
        "key_path": cfg.get("ssh_key_path") or None,
    }


def _abrir_ssh(cfg: dict):
    kwargs = _ssh_kwargs(cfg)
    return ssh_client.conectar(**kwargs)


def _abrir_wpcli(cfg: dict, client) -> WPCLI:
    return WPCLI(
        ssh_client=client,
        wpcli_bin=(cfg.get("wpcli_bin") or "/usr/local/bin/wp").strip(),
        wp_path=(cfg.get("wp_path") or "").strip(),
        ssh_user=(cfg.get("ssh_user") or "").strip(),
    )


def _abrir_rest(cfg: dict) -> WPRest:
    return WPRest(
        wp_url=(cfg.get("wp_url") or "").strip(),
        wp_user=(cfg.get("wp_user") or "").strip(),
        app_password=cfg.get("wp_app_password") or "",
    )


def _resp(status: str, message: str, details=None) -> dict:
    return {"status": status, "message": message, "details": details}


# ---------------------------------------------------------------------- #
# Acoes individuais (chamadas pelos botoes)
# ---------------------------------------------------------------------- #
def acao_testar_ssh(cfg: dict) -> dict:
    kwargs = _ssh_kwargs(cfg)
    res = ssh_client.testar_conexao(**kwargs)
    return _resp("ok" if res["ok"] else "erro", res["msg"])


def acao_testar_rest(cfg: dict) -> dict:
    try:
        rest = _abrir_rest(cfg)
    except Exception as exc:
        return _resp("erro", f"Falha ao inicializar REST: {exc}")
    res = rest.testar_api()
    return _resp("ok" if res.get("ok") else "erro", res.get("msg", ""), res)


def acao_validar_wp(cfg: dict) -> dict:
    try:
        client = _abrir_ssh(cfg)
    except Exception as exc:
        return _resp("erro", f"SSH falhou: {exc}")
    try:
        wp = _abrir_wpcli(cfg, client)
        res = wp.verificar_wp()
        return _resp("ok" if res["ok"] else "erro", res["msg"], res)
    finally:
        ssh_client.fechar(client)


def acao_validar_wpcli(cfg: dict) -> dict:
    try:
        client = _abrir_ssh(cfg)
    except Exception as exc:
        return _resp("erro", f"SSH falhou: {exc}")
    try:
        wp = _abrir_wpcli(cfg, client)
        res = wp.verificar_wpcli()
        return _resp("ok" if res["ok"] else "erro", res["msg"], res)
    finally:
        ssh_client.fechar(client)

def acao_gerar_app_password(cfg: dict) -> dict:
    try:
        client = _abrir_ssh(cfg)
    except Exception as exc:
        return _resp("erro", f"SSH falhou: {exc}")
    try:
        wp = _abrir_wpcli(cfg, client)
        app_name = f"PEG-Engine-{int(time.time())}"
        cmd = f"user application-password create {cfg.get('wp_user')} {app_name} --porcelain"
        ok, out, err = wp._run_cmd(cmd)
        if ok and out:
            password = out.strip()
            cfg["wp_app_password"] = password
            return _resp("ok", f"Application Password '{app_name}' gerada com sucesso", {"password": password})
        else:
            return _resp("erro", f"Falha ao gerar Application Password via WP-CLI: {err}")
    finally:
        ssh_client.fechar(client)


def acao_verificar_redis(cfg: dict) -> dict:
    try:
        client = _abrir_ssh(cfg)
    except Exception as exc:
        return _resp("erro", f"SSH falhou: {exc}")
    try:
        wp = _abrir_wpcli(cfg, client)
        res = wp.verificar_redis()
        return _resp("ok" if res["ok"] else "aviso", res["msg"], res)
    finally:
        ssh_client.fechar(client)


def acao_instalar_plugins(
    cfg: dict,
    opcionais_extras: Optional[list] = None,
    pular_plugins: Optional[list] = None,
) -> dict:
    """
    Instala todos os plugins obrigatorios + qualquer plugin opcional listado
    em opcionais_extras (lista de slugs).
    Slugs em pular_plugins sao ignorados (mesmo se obrigatorios em plugins.json).
    Retorna detalhes por plugin.
    """
    opcionais_extras = opcionais_extras or []
    pular_plugins = set(pular_plugins or [])
    try:
        plugins = carregar_plugins()
    except Exception as exc:
        return _resp("erro", f"Falha ao ler plugins.json: {exc}")

    try:
        client = _abrir_ssh(cfg)
    except Exception as exc:
        return _resp("erro", f"SSH falhou: {exc}")

    try:
        wp = _abrir_wpcli(cfg, client)
        redis_disp: Optional[bool] = None  # avalia sob demanda

        sucesso: list = []
        falhas: list = []
        manuais: list = []

        for p in plugins:
            slug = p.get("slug")
            if not slug:
                continue

            if slug in pular_plugins:
                _logger.info("Plugin %s na lista de skip — pulando", slug)
                continue

            obrigatorio = bool(p.get("obrigatorio"))
            requer_redis = bool(p.get("requer_redis"))
            requer_manual = bool(p.get("requer_config_manual"))

            if not obrigatorio and slug not in opcionais_extras:
                _logger.info("Plugin opcional nao selecionado: %s — pulando", slug)
                continue

            if requer_redis:
                if redis_disp is None:
                    redis_res = wp.verificar_redis()
                    redis_disp = bool(redis_res.get("ok"))
                if not redis_disp:
                    motivo = "Redis nao disponivel — redis-cache nao instalado"
                    falhas.append({"slug": slug, "motivo": motivo})
                    _logger.warning("Plugin %s: %s", slug, motivo)
                    continue

            res = wp.instalar_e_ativar(slug)
            if res["ok"]:
                sucesso.append(slug)
                if requer_manual:
                    manuais.append({"slug": slug, "nome": p.get("nome", slug)})
            else:
                falhas.append({"slug": slug, "motivo": res["msg"]})

        return _resp(
            "ok" if not falhas else "aviso",
            f"Plugins: {len(sucesso)} ok, {len(falhas)} falha(s)",
            {"sucesso": sucesso, "falhas": falhas, "config_manual": manuais},
        )
    finally:
        ssh_client.fechar(client)


def acao_configurar_wordpress(cfg: dict) -> dict:
    """Aplica as opcoes basicas via WP-CLI + flush rewrite + flush cache."""
    portal_name = (cfg.get("portal_name") or "Meu Portal").strip()
    niche = (cfg.get("portal_niche") or "geral").strip()

    opcoes = {
        "blogname":               portal_name,
        "blogdescription":        f"Portal de noticias sobre {niche}",
        "permalink_structure":    "/%postname%/",
        "timezone_string":        "America/Sao_Paulo",
        "date_format":            "d/m/Y",
        "time_format":            "H:i",
        "blog_public":            "1",
        "default_comment_status": "closed",
        "default_ping_status":    "closed",
        "default_pingback_flag":  "0",
    }

    try:
        client = _abrir_ssh(cfg)
    except Exception as exc:
        return _resp("erro", f"SSH falhou: {exc}")

    try:
        wp = _abrir_wpcli(cfg, client)
        sucesso: list = []
        falhas: list = []
        for chave, valor in opcoes.items():
            res = wp.atualizar_opcao(chave, valor)
            if res["ok"]:
                sucesso.append(chave)
            else:
                falhas.append({"opcao": chave, "motivo": res["msg"]})

        wp.flush_rewrite()
        wp.flush_cache()

        status = "ok" if not falhas else "aviso"
        return _resp(
            status,
            f"WordPress configurado ({len(sucesso)} opcoes ok, {len(falhas)} falhas)",
            {"sucesso": sucesso, "falhas": falhas},
        )
    finally:
        ssh_client.fechar(client)


def acao_criar_categorias(cfg: dict) -> dict:
    inline = cfg.get("categories_inline")
    if isinstance(inline, list) and inline:
        categorias = inline
        origem = "inline (profile)"
    else:
        niche = (cfg.get("portal_niche") or "").strip()
        try:
            categorias = carregar_categorias(niche)
        except Exception as exc:
            return _resp("erro", f"Falha ao ler categories.json: {exc}")
        origem = f"categories.json (nicho '{niche}')"

    if not categorias:
        return _resp("aviso", f"Nenhuma categoria configurada (fonte: {origem})")

    try:
        rest = _abrir_rest(cfg)
    except Exception as exc:
        return _resp("erro", f"REST init falhou: {exc}")

    teste = rest.testar_api()
    if not teste.get("ok"):
        return _resp("erro", f"REST nao autenticada: {teste.get('msg')}")

    criadas: list = []
    falhas: list = []
    for c in categorias:
        nome = c.get("nome")
        slug = c.get("slug")
        descricao = c.get("descricao", "")
        if not nome or not slug:
            falhas.append({"categoria": str(c), "motivo": "nome/slug vazio"})
            continue
        res = rest.criar_categoria(nome, slug, descricao)
        if res.get("ok"):
            criadas.append(
                {"nome": nome, "slug": slug, "ja_existia": bool(res.get("ja_existia"))}
            )
        else:
            falhas.append({"categoria": slug, "motivo": res.get("msg", "")})

    status = "ok" if not falhas else "aviso"
    return _resp(
        status,
        f"Categorias: {len(criadas)} ok, {len(falhas)} falha(s)",
        {"criadas": criadas, "falhas": falhas},
    )


def acao_criar_paginas(cfg: dict) -> dict:
    portal_name = (cfg.get("portal_name") or "Meu Portal").strip()
    niche = (cfg.get("portal_niche") or "geral").strip()

    inline = cfg.get("pages_inline")
    if isinstance(inline, list) and inline:
        paginas = inline
    else:
        try:
            paginas = carregar_paginas()
        except Exception as exc:
            return _resp("erro", f"Falha ao ler pages.json: {exc}")

    try:
        rest = _abrir_rest(cfg)
    except Exception as exc:
        return _resp("erro", f"REST init falhou: {exc}")

    teste = rest.testar_api()
    if not teste.get("ok"):
        return _resp("erro", f"REST nao autenticada: {teste.get('msg')}")

    criadas: list = []
    falhas: list = []
    for p in paginas:
        titulo = p.get("titulo")
        slug = p.get("slug")
        status_pag = p.get("status", "publish")
        conteudo = aplicar_placeholders(p.get("conteudo", ""), portal_name, niche)
        titulo_render = aplicar_placeholders(titulo, portal_name, niche)
        if not titulo:
            falhas.append({"pagina": "?", "motivo": "titulo vazio"})
            continue
        res = rest.criar_pagina(titulo_render, conteudo, status=status_pag, slug=slug)
        if res.get("ok"):
            criadas.append(
                {
                    "titulo": titulo,
                    "slug": slug,
                    "id": res.get("id"),
                    "ja_existia": bool(res.get("ja_existia")),
                }
            )
        else:
            falhas.append({"pagina": slug or titulo, "motivo": res.get("msg", "")})

    status = "ok" if not falhas else "aviso"
    return _resp(
        status,
        f"Paginas: {len(criadas)} ok, {len(falhas)} falha(s)",
        {"criadas": criadas, "falhas": falhas},
    )


def acao_criar_conteudo_inicial(cfg: dict) -> dict:
    """
    Se cfg['posts_inline'] for lista nao-vazia, cria todos os posts ali
    definidos. Senao, cria um unico post de teste (rascunho) na primeira
    categoria do nicho (comportamento legado).

    Cada item de posts_inline aceita:
        {"titulo": str, "conteudo": str, "status": "draft"|"publish",
         "categoria_slug": str, "categoria_ids": [int]}
    """
    portal_name = (cfg.get("portal_name") or "Meu Portal").strip()
    niche = (cfg.get("portal_niche") or "").strip()

    try:
        rest = _abrir_rest(cfg)
    except Exception as exc:
        return _resp("erro", f"REST init falhou: {exc}")

    teste = rest.testar_api()
    if not teste.get("ok"):
        return _resp("erro", f"REST nao autenticada: {teste.get('msg')}")

    posts_inline = cfg.get("posts_inline")
    usar_inline = isinstance(posts_inline, list) and len(posts_inline) > 0

    # Mapa slug->id (preenchido sob demanda)
    cache_cat: dict = {}

    def _resolver_categoria_ids(item: dict) -> list:
        ids = item.get("categoria_ids")
        if isinstance(ids, list) and ids:
            try:
                return [int(x) for x in ids if x]
            except (TypeError, ValueError):
                pass
        slug = (item.get("categoria_slug") or "").strip()
        if not slug:
            return []
        if slug in cache_cat:
            return [cache_cat[slug]] if cache_cat[slug] else []
        cid = None
        for cat in rest.listar_categorias():
            if cat.get("slug") == slug:
                cid = cat.get("id")
                break
        cache_cat[slug] = cid
        return [cid] if cid else []

    if usar_inline:
        criados: list = []
        falhas: list = []
        for item in posts_inline:
            if not isinstance(item, dict):
                falhas.append({"post": str(item), "motivo": "entrada invalida"})
                continue
            titulo = aplicar_placeholders(
                item.get("titulo", ""), portal_name, niche
            )
            conteudo = aplicar_placeholders(
                item.get("conteudo", ""), portal_name, niche
            )
            status_p = item.get("status") or "draft"
            cats = _resolver_categoria_ids(item)
            if not titulo:
                falhas.append({"post": "?", "motivo": "titulo vazio"})
                continue
            res = rest.criar_post(
                titulo, conteudo, status=status_p, categoria_ids=cats or None
            )
            if res.get("ok"):
                criados.append({"titulo": titulo, "id": res.get("id")})
            else:
                falhas.append({"post": titulo, "motivo": res.get("msg", "")})

        status = "ok" if not falhas else "aviso"
        return _resp(
            status,
            f"Posts: {len(criados)} criados, {len(falhas)} falha(s)",
            {"criados": criados, "falhas": falhas},
        )

    # ---------- Comportamento legado: 1 post de teste ----------
    try:
        categorias_cfg = carregar_categorias(niche)
    except Exception as exc:
        return _resp("erro", f"Falha ao ler categories.json: {exc}")

    cat_id: Optional[int] = None
    if categorias_cfg:
        primeiro_slug = categorias_cfg[0].get("slug")
        if primeiro_slug:
            existentes = rest.listar_categorias()
            for cat in existentes:
                if cat.get("slug") == primeiro_slug:
                    cat_id = cat.get("id")
                    break

    titulo = f"Post de teste — {portal_name}"
    conteudo = "Este e um post de teste criado automaticamente pelo PEG Portal Engine."
    res = rest.criar_post(
        titulo,
        conteudo,
        status="draft",
        categoria_ids=[cat_id] if cat_id else None,
    )
    return _resp(
        "ok" if res.get("ok") else "aviso",
        res.get("msg", ""),
        res,
    )


def acao_criar_usuarios(cfg: dict) -> dict:
    """
    Cria usuarios WP a partir de cfg['users'] (lista de objetos).
    Cada item: {login, email, role?, password?, display_name?}.
    Idempotente: usuarios ja existentes nao sao recriados.
    """
    usuarios = cfg.get("users") or []
    if not isinstance(usuarios, list) or not usuarios:
        return _resp("aviso", "Nenhum usuario configurado")

    try:
        client = _abrir_ssh(cfg)
    except Exception as exc:
        return _resp("erro", f"SSH falhou: {exc}")

    try:
        wp = _abrir_wpcli(cfg, client)
        criados: list = []
        ja_existiam: list = []
        falhas: list = []

        for u in usuarios:
            if not isinstance(u, dict):
                falhas.append({"usuario": str(u), "motivo": "entrada invalida"})
                continue
            login = (u.get("login") or "").strip()
            email = (u.get("email") or "").strip()
            role = (u.get("role") or "subscriber").strip()
            password = u.get("password") or None
            display = (u.get("display_name") or "").strip() or None
            if not login or not email:
                falhas.append({
                    "usuario": login or email or "?",
                    "motivo": "login/email vazio",
                })
                continue
            res = wp.criar_usuario(
                login, email, role=role,
                password=password, display_name=display,
            )
            if res.get("ok"):
                if res.get("ja_existia"):
                    ja_existiam.append(login)
                else:
                    criados.append({"login": login, "id": res.get("id")})
            else:
                falhas.append({"usuario": login, "motivo": res.get("msg", "")})

        status = "ok" if not falhas else "aviso"
        return _resp(
            status,
            f"Usuarios: {len(criados)} criados, "
            f"{len(ja_existiam)} ja existiam, {len(falhas)} falha(s)",
            {
                "criados": criados,
                "ja_existiam": ja_existiam,
                "falhas": falhas,
            },
        )
    finally:
        ssh_client.fechar(client)


def acao_gerar_relatorio(cfg: dict, contexto_extra: Optional[dict] = None) -> dict:
    """Gera relatorio com dados minimos quando chamado isoladamente."""
    contexto = {
        "portal_name": cfg.get("portal_name") or "",
        "dominio": cfg.get("portal_domain") or "",
        "niche": cfg.get("portal_niche") or "",
        "wp_url": cfg.get("wp_url") or "",
        "iniciado_em": datetime.now(),
        "duracao_segundos": 0,
        "wp": {},
        "plugins_ok": [],
        "plugins_falha": [],
        "paginas_criadas": [],
        "categorias_criadas": [],
        "seo": {},
        "pendencias_manuais": [],
        "erros": [],
    }
    if contexto_extra:
        contexto.update(contexto_extra)

    try:
        caminho = gerar_relatorio(contexto)
        return _resp("ok", f"Relatorio gerado em {caminho}", {"path": str(caminho)})
    except Exception as exc:
        return _resp("erro", f"Falha ao gerar relatorio: {exc}")


# ---------------------------------------------------------------------- #
# Setup completo (15 etapas)
# ---------------------------------------------------------------------- #
@dataclass
class StepResult:
    step_id: int
    title: str
    status: str
    details: str
    critical: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

def _etapa(num: int, nome: str, status: str, detalhes: str, critical: bool = False) -> dict:
    return StepResult(step_id=num, title=nome, status=status, details=detalhes, critical=critical).to_dict()


_STEP_FLAGS_DEFAULT = {
    "install_plugins":   True,
    "configure_wp":      True,
    "apply_seo":         True,
    "create_users":      True,
    "create_pages":      True,
    "create_categories": True,
    "create_test_post":  True,
    "generate_report":   True,
}


def _normalize_step_flags(
    step_flags: Optional[dict],
    content_flags: Optional[dict],
) -> dict:
    """Funde step_flags (novo) + content_flags (legado) com defaults."""
    flags = dict(_STEP_FLAGS_DEFAULT)
    if isinstance(content_flags, dict):
        for k in ("create_pages", "create_categories", "create_test_post"):
            if k in content_flags:
                flags[k] = bool(content_flags[k])
    if isinstance(step_flags, dict):
        for k in flags:
            if k in step_flags:
                flags[k] = bool(step_flags[k])
    return flags


def setup_completo(
    cfg: dict,
    opcionais_extras: Optional[list] = None,
    pular_plugins: Optional[list] = None,
    content_flags: Optional[dict] = None,
    profile_meta: Optional[dict] = None,
    step_flags: Optional[dict] = None,
    on_progress: Optional[Callable[[dict], None]] = None,
    job_id: Optional[str] = None,
) -> dict:
    """
    Executa todas as etapas em sequencia. Erros nao criticos viram avisos
    no log. Erros criticos (SSH/WP invalidos) abortam o processo.

    step_flags (dict) controla execucao por etapa:
        install_plugins, configure_wp, apply_seo,
        create_pages, create_categories, create_test_post,
        generate_report
    Defaults = todos True. content_flags (legado) ainda e respeitado para
    compatibilidade com o modo manual.
    """
    opcionais_extras = opcionais_extras or []
    pular_plugins = pular_plugins or []
    flags = _normalize_step_flags(step_flags, content_flags)
    install_plugins   = flags["install_plugins"]
    configure_wp      = flags["configure_wp"]
    apply_seo         = flags["apply_seo"]
    create_users      = flags["create_users"]
    create_pages      = flags["create_pages"]
    create_categories = flags["create_categories"]
    create_test_post  = flags["create_test_post"]
    generate_report   = flags["generate_report"]

    slug_portal = cfg.get("portal_name", "portal")
    setup_run_logger(slug_portal, job_id=job_id)

    inicio = time.monotonic()
    iniciado_em = datetime.now()
    etapas: list[dict] = []
    erros: list[dict] = []

    def add_etapa(e: dict):
        etapas.append(e)
        if on_progress:
            on_progress({"type": "step", "data": e})

    contexto_relatorio: dict = {
        "portal_name": cfg.get("portal_name") or "",
        "dominio": cfg.get("portal_domain") or "",
        "niche": cfg.get("portal_niche") or "",
        "wp_url": cfg.get("wp_url") or "",
        "iniciado_em": iniciado_em,
        "duracao_segundos": 0,
        "wp": {},
        "plugins_ok": [],
        "plugins_falha": [],
        "paginas_criadas": [],
        "categorias_criadas": [],
        "seo": {
            "permalink": False,
            "permalink_estrutura": "/%postname%/",
            "indexacao": False,
            "homepage": False,
        },
        "pendencias_manuais": [],
        "erros": [],
    }
    if profile_meta:
        contexto_relatorio["profile"] = profile_meta
        contexto_relatorio["profile_aplicado"] = {
            "seo_aplicado": False,  # atualizado depois
            "plugins_required": list(profile_meta.get("plugins_required") or []),
            "plugins_optional": list(profile_meta.get("plugins_optional") or []),
            "plugins_skip": list(pular_plugins),
            "create_users": create_users,
            "create_pages": create_pages,
            "create_categories": create_categories,
            "create_test_post": create_test_post,
        }

    # Listas resumo das etapas (entrarao no relatorio Markdown)
    etapas_exec_nomes: list[str] = []
    etapas_pul_nomes: list[str] = []

    def _registrar(nome: str, executou: bool) -> None:
        (etapas_exec_nomes if executou else etapas_pul_nomes).append(nome)

    contexto_relatorio["etapas_executadas"] = etapas_exec_nomes
    contexto_relatorio["etapas_puladas"] = etapas_pul_nomes
    contexto_relatorio["step_flags"] = dict(flags)

    # ---------------- Etapa 1: SSH ----------------
    res_ssh = acao_testar_ssh(cfg)
    add_etapa(_etapa(1, "Testar SSH", res_ssh["status"], res_ssh["message"], critical=True))
    _logger.info("[1/15] Testar SSH: %s — %s", res_ssh["status"], res_ssh["message"])
    if res_ssh["status"] == "erro":
        erros.append({"etapa": 1, "mensagem": res_ssh["message"]})
        return _finalizar(cfg, contexto_relatorio, etapas, erros, inicio,
                          critico=True)

    # ---------------- Etapa 2: validar WP ----------------
    res_wp = acao_validar_wp(cfg)
    add_etapa(_etapa(2, "Validar WordPress", res_wp["status"], res_wp["message"], critical=True))
    _logger.info("[2/15] Validar WP: %s — %s", res_wp["status"], res_wp["message"])
    if res_wp["status"] == "erro":
        erros.append({"etapa": 2, "mensagem": res_wp["message"]})
        return _finalizar(cfg, contexto_relatorio, etapas, erros, inicio,
                          critico=True)

    detalhes_wp = res_wp.get("details") or {}
    contexto_relatorio["wp"] = {
        "versao": detalhes_wp.get("versao"),
        "siteurl": detalhes_wp.get("siteurl"),
        "permalink": "/%postname%/",
    }

    # ---------------- Etapa 3: validar WP-CLI ----------------
    res_wpcli = acao_validar_wpcli(cfg)
    add_etapa(_etapa(3, "Validar WP-CLI", res_wpcli["status"], res_wpcli["message"], critical=True))
    _logger.info("[3/15] WP-CLI: %s — %s", res_wpcli["status"], res_wpcli["message"])
    if res_wpcli["status"] == "erro":
        erros.append({"etapa": 3, "mensagem": res_wpcli["message"]})
        # WP-CLI invalido tambem e critico — sem ele plugins/opcoes nao rodam
        return _finalizar(cfg, contexto_relatorio, etapas, erros, inicio,
                          critico=True)

    # ---------------- Etapa 3.5: gerar App Password (se faltar) ----------------
    if not (cfg.get("wp_app_password") or "").strip():
        res_app_pass = acao_gerar_app_password(cfg)
        add_etapa(_etapa(3, "Gerar App Password", res_app_pass["status"], res_app_pass["message"]))
        _logger.info("[3.5/15] App Password: %s — %s", res_app_pass["status"], res_app_pass["message"])
        if res_app_pass["status"] == "erro":
            erros.append({"etapa": 3, "mensagem": res_app_pass["message"]})
        else:
            contexto_relatorio["wp"]["application_password_gerada"] = res_app_pass["details"]["password"]

    # ---------------- Etapa 4: Validacao Critica REST API (Fail-Fast) ----------------
    res_rest_fast = acao_testar_rest(cfg)
    add_etapa(_etapa(4, "Testar REST API (Fail-Fast)", res_rest_fast["status"], res_rest_fast["message"], critical=True))
    _logger.info("[4/15] REST API Fail-Fast: %s — %s", res_rest_fast["status"], res_rest_fast["message"])
    if res_rest_fast["status"] == "erro":
        erros.append({"etapa": 4, "mensagem": res_rest_fast["message"]})
        # Aborta setup antes de mexer em plugins e conteudos
        return _finalizar(cfg, contexto_relatorio, etapas, erros, inicio,
                          critico=True)

    rest_ok = True  # Foi testado como OK acima

    # ---------------- Etapa 4.5: Redis ----------------
    res_redis = acao_verificar_redis(cfg)
    add_etapa(_etapa(4, "Verificar Redis", res_redis["status"], res_redis["message"]))
    _logger.info("[4.5/15] Redis: %s — %s", res_redis["status"], res_redis["message"])

    # ---------------- Etapa 5/6: Plugins ----------------
    if not install_plugins:
        add_etapa(_etapa(5, "Instalar plugins", "aviso",
                             "desativado pela flag install_plugins=false"))
        _logger.info("[5-6/15] Plugins: pulado pela flag")
        _registrar("Instalar plugins", False)
    else:
        res_plugins = acao_instalar_plugins(
            cfg,
            opcionais_extras=opcionais_extras,
            pular_plugins=pular_plugins,
        )
        add_etapa(_etapa(5, "Instalar plugins", res_plugins["status"], res_plugins["message"]))
        _logger.info("[5-6/15] Plugins: %s — %s", res_plugins["status"], res_plugins["message"])
        detalhes_plugins = res_plugins.get("details") or {}
        contexto_relatorio["plugins_ok"] = list(detalhes_plugins.get("sucesso", []))
        contexto_relatorio["plugins_falha"] = list(detalhes_plugins.get("falhas", []))
        if res_plugins["status"] == "aviso":
            for f in detalhes_plugins.get("falhas", []):
                erros.append({"etapa": 5, "mensagem": f"{f.get('slug')}: {f.get('motivo')}"})
        _registrar("Instalar plugins", True)

    # Pendencias manuais a partir do plugins.json
    try:
        for p in carregar_plugins():
            slug = p.get("slug")
            if not slug:
                continue
            if not p.get("requer_config_manual"):
                continue
            if slug in contexto_relatorio["plugins_ok"]:
                wp_url = (cfg.get("wp_url") or "").rstrip("/")
                url = ""
                if slug == "seo-by-rank-math":
                    url = f"{wp_url}/wp-admin/admin.php?page=rank-math"
                elif slug == "wp-mail-smtp":
                    url = f"{wp_url}/wp-admin/admin.php?page=wp-mail-smtp"
                elif slug == "site-kit-by-google":
                    url = f"{wp_url}/wp-admin/admin.php?page=googlesitekit-splash"
                else:
                    url = f"{wp_url}/wp-admin/plugins.php"
                contexto_relatorio["pendencias_manuais"].append(
                    {"plugin": p.get("nome", slug), "url": url}
                )
    except Exception as exc:
        _logger.warning("Falha ao montar pendencias manuais: %s", exc)

    # ---------------- Etapa 7: configurar WP ----------------
    if not configure_wp:
        add_etapa(_etapa(7, "Configurar WordPress", "aviso",
                             "desativado pela flag configure_wp=false"))
        _logger.info("[7/15] Configurar WP: pulado pela flag")
        _registrar("Configurar WordPress", False)
    else:
        res_cfg = acao_configurar_wordpress(cfg)
        add_etapa(_etapa(7, "Configurar WordPress", res_cfg["status"], res_cfg["message"]))
        _logger.info("[7/15] Configurar WP: %s — %s", res_cfg["status"], res_cfg["message"])
        if res_cfg["status"] != "erro":
            contexto_relatorio["seo"]["permalink"] = True
            contexto_relatorio["seo"]["indexacao"] = True
            if profile_meta and "profile_aplicado" in contexto_relatorio:
                contexto_relatorio["profile_aplicado"]["seo_aplicado"] = True
        else:
            erros.append({"etapa": 7, "mensagem": res_cfg["message"]})
        _registrar("Configurar WordPress", True)

    # ---------------- Etapa 8: SEO tecnico (homepage definida adiante) ----------------
    if not apply_seo:
        add_etapa(_etapa(8, "SEO tecnico (base)", "aviso",
                             "desativado pela flag apply_seo=false "
                             "(homepage nao sera definida apos paginas)"))
        _registrar("SEO tecnico", False)
    else:
        add_etapa(_etapa(8, "SEO tecnico (base)", "ok",
                             "permalink + indexacao aplicados; "
                             "homepage sera definida apos paginas"))
        _registrar("SEO tecnico", True)

    # ---------------- Etapa 9: REST API (Re-teste legado) ----------------
    # Apenas para compatibilidade se algo foi feito, mas ja validamos no fail-fast
    res_rest = acao_testar_rest(cfg)
    add_etapa(_etapa(9, "Re-testar REST API", res_rest["status"], res_rest["message"]))
    _logger.info("[9/15] REST (Re-teste): %s — %s", res_rest["status"], res_rest["message"])
    rest_ok = res_rest["status"] == "ok"
    if not rest_ok:
        erros.append({"etapa": 9, "mensagem": res_rest["message"]})

    # ---------------- Etapa 10: categorias ----------------
    if not create_categories:
        add_etapa(_etapa(10, "Criar categorias", "aviso",
                             "desativado pela flag create_categories=false"))
        _registrar("Criar categorias", False)
    elif rest_ok:
        res_cats = acao_criar_categorias(cfg)
        add_etapa(_etapa(10, "Criar categorias", res_cats["status"], res_cats["message"]))
        _logger.info("[10/15] Categorias: %s — %s", res_cats["status"], res_cats["message"])
        det = res_cats.get("details") or {}
        for c in det.get("criadas", []):
            contexto_relatorio["categorias_criadas"].append(c)
        for f in det.get("falhas", []):
            erros.append({"etapa": 10, "mensagem": f"{f.get('categoria')}: {f.get('motivo')}"})
        _registrar("Criar categorias", True)
    else:
        add_etapa(_etapa(10, "Criar categorias", "aviso", "REST nao disponivel — pulado"))
        _registrar("Criar categorias", False)

    # ---------------- Etapa 11: paginas ----------------
    paginas_criadas: list = []
    if not create_pages:
        add_etapa(_etapa(11, "Criar paginas", "aviso",
                             "desativado pela flag create_pages=false"))
        _registrar("Criar paginas", False)
    elif rest_ok:
        res_pag = acao_criar_paginas(cfg)
        add_etapa(_etapa(11, "Criar paginas", res_pag["status"], res_pag["message"]))
        _logger.info("[11/15] Paginas: %s — %s", res_pag["status"], res_pag["message"])
        det = res_pag.get("details") or {}
        for p in det.get("criadas", []):
            contexto_relatorio["paginas_criadas"].append(p)
            paginas_criadas.append(p)
        for f in det.get("falhas", []):
            erros.append({"etapa": 11, "mensagem": f"{f.get('pagina')}: {f.get('motivo')}"})
        _registrar("Criar paginas", True)

        # Configurar homepage (etapa 8, parte 2) — depende de apply_seo
        if apply_seo:
            try:
                inicio_pag = next(
                    (p for p in paginas_criadas if (p.get("slug") or "") == "inicio"), None
                )
                if inicio_pag and inicio_pag.get("id"):
                    client = _abrir_ssh(cfg)
                    try:
                        wp = _abrir_wpcli(cfg, client)
                        wp.atualizar_opcao("show_on_front", "page")
                        wp.atualizar_opcao("page_on_front", inicio_pag["id"])
                        contexto_relatorio["seo"]["homepage"] = True
                        _logger.info(
                            "Homepage definida como pagina ID=%s (Inicio)",
                            inicio_pag["id"],
                        )
                    finally:
                        ssh_client.fechar(client)
            except Exception as exc:
                erros.append(
                    {"etapa": 8, "mensagem": f"falha ao definir homepage: {exc}"}
                )
    else:
        add_etapa(_etapa(11, "Criar paginas", "aviso", "REST nao disponivel — pulado"))
        _registrar("Criar paginas", False)

    # ---------------- Etapa 12: criar usuarios ----------------
    if not create_users:
        add_etapa(_etapa(12, "Criar usuarios", "aviso",
                             "desativado pela flag create_users=false"))
        _registrar("Criar usuarios", False)
    else:
        usuarios_cfg = cfg.get("users") or []
        if not isinstance(usuarios_cfg, list) or not usuarios_cfg:
            add_etapa(_etapa(12, "Criar usuarios", "aviso",
                                 "nenhum usuario definido em users[]"))
            _logger.info("[12/15] Usuarios: nenhum configurado")
            _registrar("Criar usuarios", False)
        else:
            res_users = acao_criar_usuarios(cfg)
            add_etapa(_etapa(12, "Criar usuarios", res_users["status"],
                                 res_users["message"]))
            _logger.info("[12/15] Usuarios: %s — %s",
                         res_users["status"], res_users["message"])
            if res_users["status"] == "aviso":
                det = res_users.get("details") or {}
                for f in det.get("falhas", []):
                    erros.append({
                        "etapa": 12,
                        "mensagem": f"{f.get('usuario')}: {f.get('motivo')}",
                    })
            elif res_users["status"] == "erro":
                erros.append({"etapa": 12, "mensagem": res_users["message"]})
            _registrar("Criar usuarios", True)

    # ---------------- Etapa 13: conteudo inicial ----------------
    if not create_test_post:
        add_etapa(_etapa(13, "Criar conteudo inicial", "aviso",
                             "desativado pela flag create_test_post=false"))
        _registrar("Criar conteudo inicial", False)
    elif rest_ok:
        res_post = acao_criar_conteudo_inicial(cfg)
        add_etapa(_etapa(13, "Criar conteudo inicial", res_post["status"],
                             res_post["message"]))
        _logger.info("[13/15] Conteudo: %s — %s", res_post["status"], res_post["message"])
        if res_post["status"] == "erro":
            erros.append({"etapa": 13, "mensagem": res_post["message"]})
        _registrar("Criar conteudo inicial", True)
    else:
        add_etapa(_etapa(13, "Criar conteudo inicial", "aviso",
                             "REST nao disponivel — pulado"))
        _registrar("Criar conteudo inicial", False)

    # ---------------- Etapa 14: flush rewrite + cache ----------------
    try:
        client = _abrir_ssh(cfg)
        try:
            wp = _abrir_wpcli(cfg, client)
            wp.flush_rewrite()
            wp.flush_cache()
            add_etapa(_etapa(14, "Flush rewrite + cache", "ok",
                                 "rewrite rules e object cache atualizados"))
            _logger.info("[14/15] Flush rewrite/cache: ok")
            _registrar("Flush rewrite + cache", True)
        finally:
            ssh_client.fechar(client)
    except Exception as exc:
        add_etapa(_etapa(14, "Flush rewrite + cache", "aviso", str(exc)))
        erros.append({"etapa": 14, "mensagem": str(exc)})
        _registrar("Flush rewrite + cache", False)

    # ---------------- Etapa 15: relatorio ----------------
    resultado = _finalizar(
        cfg, contexto_relatorio, etapas, erros, inicio,
        critico=False, generate_report=generate_report,
    )
    if on_progress:
        on_progress({"type": "done", "data": resultado})
    return resultado


def _finalizar(
    cfg: dict,
    contexto_relatorio: dict,
    etapas: list,
    erros: list,
    inicio: float,
    critico: bool,
    generate_report: bool = True,
    add_etapa: Optional[Callable[[dict], None]] = None,
) -> dict:
    contexto_relatorio["duracao_segundos"] = time.monotonic() - inicio
    contexto_relatorio["erros"] = list(erros)

    relatorio_path: Optional[str] = None
    
    def _safe_add(e: dict):
        if add_etapa:
            add_etapa(e)
        else:
            etapas.append(e)

    if not generate_report:
        _safe_add(_etapa(15, "Gerar relatorio", "aviso",
                             "desativado pela flag generate_report=false"))
        # Se houver lista de etapas executadas, registra que esta foi pulada
        pul = contexto_relatorio.get("etapas_puladas")
        if isinstance(pul, list):
            pul.append("Gerar relatorio")
    else:
        try:
            caminho = gerar_relatorio(contexto_relatorio)
            relatorio_path = str(caminho)
            _safe_add(_etapa(15, "Gerar relatorio", "ok", f"gerado em {caminho}"))
            exec_list = contexto_relatorio.get("etapas_executadas")
            if isinstance(exec_list, list):
                exec_list.append("Gerar relatorio")
        except Exception as exc:
            _safe_add(_etapa(15, "Gerar relatorio", "erro", str(exc)))
            erros.append({"etapa": 15, "mensagem": str(exc)})

    if critico:
        msg = "Setup interrompido por erro critico"
        status = "erro"
    elif erros:
        msg = f"Setup concluido com {len(erros)} aviso(s)/erro(s)"
        status = "aviso"
    else:
        msg = "Setup concluido com sucesso"
        status = "ok"

    resultado_final = _resp(
        status,
        msg,
        {
            "etapas": etapas,
            "erros": erros,
            "relatorio": relatorio_path,
            "duracao_segundos": round(contexto_relatorio["duracao_segundos"], 2),
        },
    )
    
    # Grava result.json
    try:
        run_dir = get_run_dir()
        if run_dir:
            json_path = run_dir / "result.json"
            json_path.write_text(json.dumps(resultado_final, indent=2, ensure_ascii=False), encoding="utf-8")
    finally:
        teardown_run_logger()
        
    return resultado_final
