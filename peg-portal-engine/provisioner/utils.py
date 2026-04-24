"""
Utilidades: carga de JSONs e geracao de relatorio Markdown.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .logger import get_logger


_logger = get_logger()


# ---------------------------------------------------------------------- #
# Carga de configuracao
# ---------------------------------------------------------------------- #
_BASE_DIR = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _BASE_DIR / "config"
_LOGS_DIR = _BASE_DIR / "logs"


def base_dir() -> Path:
    return _BASE_DIR


def config_dir() -> Path:
    return _CONFIG_DIR


def logs_dir() -> Path:
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return _LOGS_DIR


def carregar_json(caminho: Path) -> Any:
    """Carrega JSON com tratamento de erros explicito."""
    try:
        with caminho.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        _logger.error("JSON nao encontrado: %s", caminho)
        raise
    except json.JSONDecodeError as exc:
        _logger.error("JSON invalido em %s: %s", caminho, exc)
        raise


def carregar_niches() -> list:
    dados = carregar_json(_CONFIG_DIR / "niches.json")
    if isinstance(dados, dict) and isinstance(dados.get("opcoes"), list):
        return [str(x) for x in dados["opcoes"]]
    return []


def carregar_plugins() -> list:
    dados = carregar_json(_CONFIG_DIR / "plugins.json")
    return dados if isinstance(dados, list) else []


def carregar_categorias(nicho: str) -> list:
    dados = carregar_json(_CONFIG_DIR / "categories.json")
    if isinstance(dados, dict):
        lista = dados.get(nicho)
        if isinstance(lista, list):
            return lista
    return []


def carregar_paginas() -> list:
    dados = carregar_json(_CONFIG_DIR / "pages.json")
    return dados if isinstance(dados, list) else []


def aplicar_placeholders(texto: str, portal_name: str, niche: str) -> str:
    if not isinstance(texto, str):
        return texto
    return texto.replace("{portal_name}", portal_name or "").replace(
        "{niche}", niche or ""
    )


# ---------------------------------------------------------------------- #
# Relatorio Markdown
# ---------------------------------------------------------------------- #
def _check(b: bool) -> str:
    return "[x]" if b else "[ ]"


def gerar_relatorio(contexto: dict) -> Path:
    """
    Gera o relatorio em Markdown a partir do dicionario 'contexto'.

    Estrutura esperada do contexto:
    {
        "portal_name": str,
        "dominio": str,
        "niche": str,
        "wp_url": str,
        "iniciado_em": datetime,
        "duracao_segundos": float,
        "wp": {"versao": str|None, "siteurl": str|None, "permalink": str|None},
        "plugins_ok": [slug, ...],
        "plugins_falha": [{"slug": str, "motivo": str}, ...],
        "paginas_criadas": [{"titulo": str, "id": int|None, "ja_existia": bool}, ...],
        "categorias_criadas": [{"nome": str, "slug": str, "ja_existia": bool}, ...],
        "seo": {"permalink": bool, "indexacao": bool, "homepage": bool},
        "pendencias_manuais": [{"plugin": str, "url": str}, ...],
        "erros": [{"etapa": int|str, "mensagem": str}, ...],
    }
    """
    portal_name = contexto.get("portal_name") or "Portal"
    dominio = contexto.get("dominio") or "dominio-desconhecido"
    niche = contexto.get("niche") or "geral"
    wp_url = contexto.get("wp_url") or ""
    iniciado_em: Optional[datetime] = contexto.get("iniciado_em")
    duracao = float(contexto.get("duracao_segundos") or 0)

    wp_info = contexto.get("wp") or {}
    plugins_ok = contexto.get("plugins_ok") or []
    plugins_falha = contexto.get("plugins_falha") or []
    paginas = contexto.get("paginas_criadas") or []
    categorias = contexto.get("categorias_criadas") or []
    seo = contexto.get("seo") or {}
    pendencias = contexto.get("pendencias_manuais") or []
    erros = contexto.get("erros") or []

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_dominio = (dominio or "site").replace("/", "_").replace(":", "_")
    caminho = logs_dir() / f"relatorio_{safe_dominio}_{timestamp}.md"

    data_hora = (iniciado_em or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    linhas: list[str] = []
    linhas.append("# Relatorio PEG Portal Engine")
    linhas.append(f"**Portal:** {portal_name}")
    linhas.append(f"**Dominio:** {dominio}")
    linhas.append(f"**Nicho:** {niche}")
    linhas.append(f"**Data:** {data_hora}")
    linhas.append(f"**Duracao total:** {duracao:.1f}s")
    linhas.append("")

    # WordPress
    linhas.append("## WordPress")
    linhas.append(f"- Versao: {wp_info.get('versao') or 'desconhecida'}")
    linhas.append(f"- URL: {wp_info.get('siteurl') or wp_url or 'desconhecida'}")
    linhas.append(f"- Permalink: {wp_info.get('permalink') or 'nao definido'}")
    linhas.append("")

    # Plugins OK
    linhas.append("## Plugins Instalados e Ativos")
    if plugins_ok:
        for slug in plugins_ok:
            linhas.append(f"- [x] {slug}")
    else:
        linhas.append("- (nenhum)")
    linhas.append("")

    # Plugins falha
    linhas.append("## Plugins com Falha")
    if plugins_falha:
        for item in plugins_falha:
            slug = item.get("slug", "?")
            motivo = item.get("motivo", "sem detalhes")
            linhas.append(f"- [ ] {slug} — Motivo: {motivo}")
    else:
        linhas.append("- (nenhuma falha registrada)")
    linhas.append("")

    # Paginas
    linhas.append("## Paginas Criadas")
    if paginas:
        for p in paginas:
            titulo = p.get("titulo", "?")
            pid = p.get("id")
            sufixo = " (ja existia)" if p.get("ja_existia") else ""
            id_txt = f" (ID: {pid})" if pid else ""
            linhas.append(f"- [x] {titulo}{id_txt}{sufixo}")
    else:
        linhas.append("- (nenhuma)")
    linhas.append("")

    # Categorias
    linhas.append("## Categorias Criadas")
    if categorias:
        for c in categorias:
            nome = c.get("nome", "?")
            sufixo = " (ja existia)" if c.get("ja_existia") else ""
            linhas.append(f"- [x] {nome}{sufixo}")
    else:
        linhas.append("- (nenhuma)")
    linhas.append("")

    # SEO
    linhas.append("## SEO Aplicado")
    linhas.append(
        f"- {_check(bool(seo.get('permalink')))} Permalink configurado: "
        f"{seo.get('permalink_estrutura') or '/%postname%/'}"
    )
    linhas.append(f"- {_check(bool(seo.get('indexacao')))} Indexacao ativa")
    linhas.append(f"- {_check(bool(seo.get('homepage')))} Homepage definida")
    linhas.append("")

    # Pendencias manuais
    linhas.append("## ⚠️ Pendencias de Configuracao Manual")
    if pendencias:
        for i, p in enumerate(pendencias, start=1):
            plugin = p.get("plugin", "?")
            url = p.get("url", "")
            linhas.append(f"{i}. **{plugin}** — Configurar em: {url}")
    else:
        linhas.append("- (nenhuma)")
    linhas.append("")

    # Erros
    linhas.append("## Erros Encontrados")
    if erros:
        for e in erros:
            etapa = e.get("etapa", "?")
            msg = e.get("mensagem", "")
            linhas.append(f"- Etapa {etapa}: {msg}")
    else:
        linhas.append("- (nenhum)")
    linhas.append("")

    # Proximos passos
    linhas.append("## Proximos Passos")
    linhas.append("1. Completar pendencias listadas acima")
    linhas.append("2. Configurar tema")
    linhas.append("3. Criar usuario editor")
    linhas.append("4. Configurar DNS e SSL se necessario")
    linhas.append("5. Publicar primeiros artigos")
    linhas.append("")

    try:
        caminho.write_text("\n".join(linhas), encoding="utf-8")
        _logger.info("Relatorio gerado: %s", caminho)
    except OSError as exc:
        _logger.error("Falha ao gravar relatorio em %s: %s", caminho, exc)
        raise

    return caminho
