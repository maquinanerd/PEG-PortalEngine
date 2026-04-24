"""
Orquestrador de tarefas do PEG Portal Engine.

Cada acao publica retorna um dicionario padronizado:
    {"status": "ok"|"erro"|"aviso", "message": str, "details": dict|list|None}

A funcao 'setup_completo' executa as 14 etapas em sequencia, parando apenas
em erros criticos (SSH ou WP invalidos) e registrando os demais como avisos.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from . import ssh_client
from .logger import get_logger
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


def acao_instalar_plugins(cfg: dict, opcionais_extras: Optional[list] = None) -> dict:
    """
    Instala todos os plugins obrigatorios + qualquer plugin opcional listado
    em opcionais_extras (lista de slugs).
    Retorna detalhes por plugin.
    """
    opcionais_extras = opcionais_extras or []
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
    niche = (cfg.get("portal_niche") or "").strip()
    try:
        categorias = carregar_categorias(niche)
    except Exception as exc:
        return _resp("erro", f"Falha ao ler categories.json: {exc}")

    if not categorias:
        return _resp("aviso", f"Nenhuma categoria configurada para nicho '{niche}'")

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
    """Cria post de teste (rascunho) na primeira categoria do nicho."""
    portal_name = (cfg.get("portal_name") or "Meu Portal").strip()
    niche = (cfg.get("portal_niche") or "").strip()

    try:
        rest = _abrir_rest(cfg)
    except Exception as exc:
        return _resp("erro", f"REST init falhou: {exc}")

    teste = rest.testar_api()
    if not teste.get("ok"):
        return _resp("erro", f"REST nao autenticada: {teste.get('msg')}")

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
# Setup completo (14 etapas)
# ---------------------------------------------------------------------- #
def _etapa(num: int, nome: str, status: str, detalhes: str) -> dict:
    return {"etapa": num, "nome": nome, "status": status, "detalhes": detalhes}


def setup_completo(cfg: dict, opcionais_extras: Optional[list] = None) -> dict:
    """
    Executa todas as etapas em sequencia. Erros nao criticos viram avisos
    no log. Erros criticos (SSH/WP invalidos) abortam o processo.
    """
    opcionais_extras = opcionais_extras or []
    inicio = time.monotonic()
    iniciado_em = datetime.now()
    etapas: list[dict] = []
    erros: list[dict] = []

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

    # ---------------- Etapa 1: SSH ----------------
    res_ssh = acao_testar_ssh(cfg)
    etapas.append(_etapa(1, "Testar SSH", res_ssh["status"], res_ssh["message"]))
    _logger.info("[1/14] Testar SSH: %s — %s", res_ssh["status"], res_ssh["message"])
    if res_ssh["status"] == "erro":
        erros.append({"etapa": 1, "mensagem": res_ssh["message"]})
        return _finalizar(cfg, contexto_relatorio, etapas, erros, inicio,
                          critico=True)

    # ---------------- Etapa 2: validar WP ----------------
    res_wp = acao_validar_wp(cfg)
    etapas.append(_etapa(2, "Validar WordPress", res_wp["status"], res_wp["message"]))
    _logger.info("[2/14] Validar WP: %s — %s", res_wp["status"], res_wp["message"])
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
    etapas.append(_etapa(3, "Validar WP-CLI", res_wpcli["status"], res_wpcli["message"]))
    _logger.info("[3/14] WP-CLI: %s — %s", res_wpcli["status"], res_wpcli["message"])
    if res_wpcli["status"] == "erro":
        erros.append({"etapa": 3, "mensagem": res_wpcli["message"]})
        # WP-CLI invalido tambem e critico — sem ele plugins/opcoes nao rodam
        return _finalizar(cfg, contexto_relatorio, etapas, erros, inicio,
                          critico=True)

    # ---------------- Etapa 4: Redis ----------------
    res_redis = acao_verificar_redis(cfg)
    etapas.append(_etapa(4, "Verificar Redis", res_redis["status"], res_redis["message"]))
    _logger.info("[4/14] Redis: %s — %s", res_redis["status"], res_redis["message"])

    # ---------------- Etapa 5/6: Plugins ----------------
    res_plugins = acao_instalar_plugins(cfg, opcionais_extras=opcionais_extras)
    etapas.append(_etapa(5, "Instalar plugins", res_plugins["status"], res_plugins["message"]))
    _logger.info("[5-6/14] Plugins: %s — %s", res_plugins["status"], res_plugins["message"])
    detalhes_plugins = res_plugins.get("details") or {}
    contexto_relatorio["plugins_ok"] = list(detalhes_plugins.get("sucesso", []))
    contexto_relatorio["plugins_falha"] = list(detalhes_plugins.get("falhas", []))
    if res_plugins["status"] == "aviso":
        for f in detalhes_plugins.get("falhas", []):
            erros.append({"etapa": 5, "mensagem": f"{f.get('slug')}: {f.get('motivo')}"})

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
    res_cfg = acao_configurar_wordpress(cfg)
    etapas.append(_etapa(7, "Configurar WordPress", res_cfg["status"], res_cfg["message"]))
    _logger.info("[7/14] Configurar WP: %s — %s", res_cfg["status"], res_cfg["message"])
    if res_cfg["status"] != "erro":
        contexto_relatorio["seo"]["permalink"] = True
        contexto_relatorio["seo"]["indexacao"] = True
    else:
        erros.append({"etapa": 7, "mensagem": res_cfg["message"]})

    # ---------------- Etapa 8: SEO tecnico (homepage definida adiante) ----------------
    # Permalink e indexacao ja vieram da etapa 7. Homepage e definida apos paginas (etapa 11).
    etapas.append(_etapa(8, "SEO tecnico (base)", "ok",
                         "permalink + indexacao aplicados; homepage sera definida apos paginas"))

    # ---------------- Etapa 9: REST API ----------------
    res_rest = acao_testar_rest(cfg)
    etapas.append(_etapa(9, "Testar REST API", res_rest["status"], res_rest["message"]))
    _logger.info("[9/14] REST: %s — %s", res_rest["status"], res_rest["message"])
    rest_ok = res_rest["status"] == "ok"
    if not rest_ok:
        erros.append({"etapa": 9, "mensagem": res_rest["message"]})

    # ---------------- Etapa 10: categorias ----------------
    if rest_ok:
        res_cats = acao_criar_categorias(cfg)
        etapas.append(_etapa(10, "Criar categorias", res_cats["status"], res_cats["message"]))
        _logger.info("[10/14] Categorias: %s — %s", res_cats["status"], res_cats["message"])
        det = res_cats.get("details") or {}
        for c in det.get("criadas", []):
            contexto_relatorio["categorias_criadas"].append(c)
        for f in det.get("falhas", []):
            erros.append({"etapa": 10, "mensagem": f"{f.get('categoria')}: {f.get('motivo')}"})
    else:
        etapas.append(_etapa(10, "Criar categorias", "aviso", "REST nao disponivel — pulado"))

    # ---------------- Etapa 11: paginas ----------------
    paginas_criadas: list = []
    if rest_ok:
        res_pag = acao_criar_paginas(cfg)
        etapas.append(_etapa(11, "Criar paginas", res_pag["status"], res_pag["message"]))
        _logger.info("[11/14] Paginas: %s — %s", res_pag["status"], res_pag["message"])
        det = res_pag.get("details") or {}
        for p in det.get("criadas", []):
            contexto_relatorio["paginas_criadas"].append(p)
            paginas_criadas.append(p)
        for f in det.get("falhas", []):
            erros.append({"etapa": 11, "mensagem": f"{f.get('pagina')}: {f.get('motivo')}"})

        # Configurar homepage (etapa 8, parte 2)
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
                        "Homepage definida como pagina ID=%s (Inicio)", inicio_pag["id"]
                    )
                finally:
                    ssh_client.fechar(client)
        except Exception as exc:
            erros.append({"etapa": 8, "mensagem": f"falha ao definir homepage: {exc}"})
    else:
        etapas.append(_etapa(11, "Criar paginas", "aviso", "REST nao disponivel — pulado"))

    # ---------------- Etapa 12: conteudo inicial ----------------
    if rest_ok:
        res_post = acao_criar_conteudo_inicial(cfg)
        etapas.append(_etapa(12, "Criar conteudo inicial", res_post["status"],
                             res_post["message"]))
        _logger.info("[12/14] Conteudo: %s — %s", res_post["status"], res_post["message"])
        if res_post["status"] == "erro":
            erros.append({"etapa": 12, "mensagem": res_post["message"]})
    else:
        etapas.append(_etapa(12, "Criar conteudo inicial", "aviso",
                             "REST nao disponivel — pulado"))

    # ---------------- Etapa 13: flush rewrite + cache ----------------
    try:
        client = _abrir_ssh(cfg)
        try:
            wp = _abrir_wpcli(cfg, client)
            wp.flush_rewrite()
            wp.flush_cache()
            etapas.append(_etapa(13, "Flush rewrite + cache", "ok",
                                 "rewrite rules e object cache atualizados"))
            _logger.info("[13/14] Flush rewrite/cache: ok")
        finally:
            ssh_client.fechar(client)
    except Exception as exc:
        etapas.append(_etapa(13, "Flush rewrite + cache", "aviso", str(exc)))
        erros.append({"etapa": 13, "mensagem": str(exc)})

    # ---------------- Etapa 14: relatorio ----------------
    return _finalizar(cfg, contexto_relatorio, etapas, erros, inicio, critico=False)


def _finalizar(
    cfg: dict,
    contexto_relatorio: dict,
    etapas: list,
    erros: list,
    inicio: float,
    critico: bool,
) -> dict:
    contexto_relatorio["duracao_segundos"] = time.monotonic() - inicio
    contexto_relatorio["erros"] = list(erros)

    relatorio_path: Optional[str] = None
    try:
        caminho = gerar_relatorio(contexto_relatorio)
        relatorio_path = str(caminho)
        etapas.append(_etapa(14, "Gerar relatorio", "ok", f"gerado em {caminho}"))
    except Exception as exc:
        etapas.append(_etapa(14, "Gerar relatorio", "erro", str(exc)))
        erros.append({"etapa": 14, "mensagem": str(exc)})

    if critico:
        msg = "Setup interrompido por erro critico"
        status = "erro"
    elif erros:
        msg = f"Setup concluido com {len(erros)} aviso(s)/erro(s)"
        status = "aviso"
    else:
        msg = "Setup concluido com sucesso"
        status = "ok"

    return _resp(
        status,
        msg,
        {
            "etapas": etapas,
            "erros": erros,
            "relatorio": relatorio_path,
            "duracao_segundos": round(contexto_relatorio["duracao_segundos"], 2),
        },
    )
