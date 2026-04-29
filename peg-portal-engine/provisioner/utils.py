"""
Utilidades: carga de JSONs, Site Profiles e geracao de relatorio Markdown.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from filelock import FileLock

from .logger import get_logger, sanitize_sensitive_data, get_run_dir


_logger = get_logger()


# ---------------------------------------------------------------------- #
# Carga de configuracao
# ---------------------------------------------------------------------- #
_BASE_DIR = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _BASE_DIR / "config"
_SITES_DIR = _CONFIG_DIR / "sites"
_LOGS_DIR = _BASE_DIR / "logs"


def base_dir() -> Path:
    return _BASE_DIR


def config_dir() -> Path:
    return _CONFIG_DIR


def sites_dir() -> Path:
    _SITES_DIR.mkdir(parents=True, exist_ok=True)
    return _SITES_DIR


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
# Site Profiles (config/sites/*.json)
# ---------------------------------------------------------------------- #
_SENSIVEIS = {
    ("wordpress", "application_password"),
    ("ssh", "password"),
    ("ssh", "key_path"),
}

# Campos sensiveis dentro de listas (group, list_key, item_field).
# Sao zerados em save_site_profile e mascarados em sanitize_site_profile.
_SENSIVEIS_LISTAS = [
    ("users", "users", "password"),
]

_OBRIGATORIOS = [
    ("profile", "slug"),
    ("portal", "name"),
    ("portal", "domain"),
    ("portal", "niche"),
    ("wordpress", "url"),
    ("wordpress", "admin_user"),
    ("wordpress", "wp_path"),
    ("wordpress", "wp_cli_path"),
    ("ssh", "host"),
    ("ssh", "port"),
    ("ssh", "user"),
    ("ssh", "auth_method"),
    ("seo", "site_title"),
    ("seo", "permalink_structure"),
]


def list_site_profiles() -> list[dict]:
    """
    Lista todos os arquivos JSON disponiveis em config/sites/.
    Retorna metadados seguros (slug, name, domain, niche, path relativo).
    Nunca retorna credenciais.
    """
    pasta = sites_dir()
    resultado: list[dict] = []
    for arq in sorted(pasta.glob("*.json")):
        try:
            data = carregar_json(arq)
        except Exception as exc:
            _logger.warning("Profile invalido em %s: %s", arq.name, exc)
            continue
        if not isinstance(data, dict):
            continue
        profile = data.get("profile") or {}
        portal = data.get("portal") or {}
        resultado.append({
            "slug": str(profile.get("slug") or arq.stem),
            "name": str(portal.get("name") or arq.stem),
            "domain": str(portal.get("domain") or ""),
            "niche": str(portal.get("niche") or ""),
            "version": str(profile.get("version") or ""),
            "description": str(profile.get("description") or ""),
            "path": f"config/sites/{arq.name}",
        })
    return resultado


def load_site_profile(slug_or_path: str) -> dict:
    """
    Carrega um profile JSON por slug ou por caminho.
    Aceita 'aeconomia' ou 'config/sites/aeconomia.json'.
    Levanta FileNotFoundError se nao encontrar.
    """
    if not slug_or_path:
        raise ValueError("slug ou caminho do profile vazio")

    candidatos: list[Path] = []
    p = Path(slug_or_path)
    if p.suffix.lower() == ".json":
        if p.is_absolute():
            candidatos.append(p)
        else:
            candidatos.append(_BASE_DIR / p)
            candidatos.append(p)
    else:
        slug_limpo = slug_or_path.strip().replace("/", "_").replace("\\", "_")
        candidatos.append(sites_dir() / f"{slug_limpo}.json")

    for caminho in candidatos:
        if caminho.is_file():
            data = carregar_json(caminho)
            if not isinstance(data, dict):
                raise ValueError(
                    f"Profile {caminho.name} nao contem objeto JSON"
                )
            return data

    raise FileNotFoundError(
        f"Profile nao encontrado: {slug_or_path} "
        f"(procurado em {[str(c) for c in candidatos]})"
    )


def _get_path(d: dict, *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def validate_site_profile(profile: dict) -> tuple[bool, list[str]]:
    """
    Valida estrutura, campos obrigatorios, tipos basicos e nicho.
    Retorna (ok, lista_de_erros).
    """
    erros: list[str] = []
    if not isinstance(profile, dict):
        return False, ["O profile deve ser um objeto JSON."]

    # Obrigatorios
    for caminho in _OBRIGATORIOS:
        valor = _get_path(profile, *caminho)
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            erros.append(f"Campo obrigatorio ausente: {'.'.join(caminho)}")

    # ssh.port deve ser inteiro
    porta = _get_path(profile, "ssh", "port")
    if porta is not None and not isinstance(porta, bool):
        try:
            int(porta)
        except (TypeError, ValueError):
            erros.append("Campo ssh.port deve ser um numero inteiro.")
    elif isinstance(porta, bool):
        erros.append("Campo ssh.port deve ser um numero inteiro.")

    # auth_method
    auth = _get_path(profile, "ssh", "auth_method")
    if auth is not None and auth not in ("password", "key"):
        erros.append("Campo ssh.auth_method deve ser 'password' ou 'key'.")

    # URLs
    for caminho in [("portal", "domain"), ("wordpress", "url")]:
        url = _get_path(profile, *caminho)
        if isinstance(url, str) and url and not (
            url.startswith("http://") or url.startswith("https://")
        ):
            erros.append(
                f"{'.'.join(caminho)} deve comecar com http:// ou https://"
            )

    # Booleans em seo / content / report
    for grupo, chaves in (
        ("seo", ["blog_public", "comments_enabled", "ping_status",
                 "rank_math", "instant_indexing"]),
        ("content", ["create_pages", "create_categories", "create_test_post"]),
        ("report", ["generate_markdown", "include_manual_pending_tasks"]),
    ):
        bloco = profile.get(grupo) or {}
        if not isinstance(bloco, dict):
            erros.append(f"Bloco '{grupo}' deve ser um objeto.")
            continue
        for chave in chaves:
            if chave in bloco and not isinstance(bloco[chave], bool):
                erros.append(f"Campo {grupo}.{chave} deve ser booleano.")

    # Listas de plugins
    plugins = profile.get("plugins") or {}
    if plugins and not isinstance(plugins, dict):
        erros.append("Bloco 'plugins' deve ser um objeto.")
    else:
        for chave in ("required", "optional", "skip"):
            if chave in plugins and not isinstance(plugins[chave], list):
                erros.append(f"Campo plugins.{chave} deve ser uma lista.")

    # Bloco 'users' (lista opcional). Cada item exige login + email.
    users = profile.get("users")
    if users is not None:
        if not isinstance(users, list):
            erros.append("Bloco 'users' deve ser uma lista.")
        else:
            for i, u in enumerate(users):
                if not isinstance(u, dict):
                    erros.append(f"users[{i}] deve ser um objeto.")
                    continue
                if not str(u.get("login") or "").strip():
                    erros.append(f"users[{i}].login obrigatorio")
                if not str(u.get("email") or "").strip():
                    erros.append(f"users[{i}].email obrigatorio")
                role = u.get("role")
                if role is not None and not isinstance(role, str):
                    erros.append(f"users[{i}].role deve ser string")

    # Bloco 'steps' (dict opcional, valores booleanos)
    steps = profile.get("steps")
    if steps is not None:
        if not isinstance(steps, dict):
            erros.append("Bloco 'steps' deve ser um objeto.")
        else:
            for k, v in steps.items():
                if not isinstance(v, bool):
                    erros.append(f"steps.{k} deve ser booleano.")

    # Listas inline em content (todas opcionais)
    content = profile.get("content") or {}
    if isinstance(content, dict):
        for chave in ("pages_inline", "categories_inline", "posts_inline"):
            v = content.get(chave)
            if v is not None and not isinstance(v, list):
                erros.append(f"content.{chave} deve ser uma lista.")

    # Nicho
    niche = _get_path(profile, "portal", "niche")
    if isinstance(niche, str) and niche.strip():
        try:
            disponiveis = carregar_niches()
        except Exception as exc:
            erros.append(f"Falha ao ler niches.json: {exc}")
            disponiveis = []
        if disponiveis and niche not in disponiveis:
            erros.append(
                f"Nicho '{niche}' invalido. "
                f"Disponiveis: {', '.join(disponiveis)}"
            )

    return (len(erros) == 0), erros


def sanitize_site_profile(profile: dict) -> dict:
    """
    Retorna copia segura do profile, mascarando credenciais.
    Campos vazios continuam vazios; campos preenchidos viram '****'.
    Mascara senhas em listas (ex.: users[*].password).
    """
    if not isinstance(profile, dict):
        return {}
    seguro = copy.deepcopy(profile)
    for grupo, chave in _SENSIVEIS:
        bloco = seguro.get(grupo)
        if isinstance(bloco, dict) and bloco.get(chave):
            bloco[chave] = "****"
    for _grupo, list_key, item_field in _SENSIVEIS_LISTAS:
        lista = seguro.get(list_key)
        if isinstance(lista, list):
            for it in lista:
                if isinstance(it, dict) and it.get(item_field):
                    it[item_field] = "****"
    return seguro


def merge_profile_with_payload(profile: dict, payload: dict) -> dict:
    """
    Mescla overrides vindos do formulario com o profile.
    Regra: valores nao-vazios no payload sobrescrevem; valores vazios
    no payload nunca derrubam valores validos do profile.
    Suporta payload no formato aninhado (mesma forma do profile) ou
    no formato achatado (chaves planas tipo 'wp_app_password').
    """
    base = copy.deepcopy(profile) if isinstance(profile, dict) else {}
    if not isinstance(payload, dict) or not payload:
        return base

    # Override aninhado: { "wordpress": {...}, "ssh": {...}, ... }
    for grupo in ("profile", "portal", "wordpress", "ssh",
                  "seo", "plugins", "content", "report", "steps"):
        sub = payload.get(grupo)
        if not isinstance(sub, dict):
            continue
        bloco = base.setdefault(grupo, {})
        if not isinstance(bloco, dict):
            bloco = {}
            base[grupo] = bloco
        for k, v in sub.items():
            if v is None:
                continue
            if isinstance(v, str) and not v.strip():
                continue
            bloco[k] = v

    # Override de listas em raiz (users) — substitui inteiro se enviado
    if isinstance(payload.get("users"), list):
        base["users"] = copy.deepcopy(payload["users"])

    # Override achatado (compatibilidade com o formulario atual).
    achatado_map = {
        "portal_name":    ("portal", "name"),
        "portal_niche":   ("portal", "niche"),
        "portal_domain":  ("portal", "domain"),
        "wp_url":         ("wordpress", "url"),
        "wp_user":        ("wordpress", "admin_user"),
        "wp_app_password": ("wordpress", "application_password"),
        "wp_path":        ("wordpress", "wp_path"),
        "wpcli_bin":      ("wordpress", "wp_cli_path"),
        "ssh_host":       ("ssh", "host"),
        "ssh_port":       ("ssh", "port"),
        "ssh_user":       ("ssh", "user"),
        "ssh_password":   ("ssh", "password"),
        "ssh_key_path":   ("ssh", "key_path"),
    }
    for plana, (grupo, chave) in achatado_map.items():
        if plana not in payload:
            continue
        v = payload.get(plana)
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        base.setdefault(grupo, {})[chave] = v

    return base


def profile_para_cfg(profile: dict, opcionais_extras: Optional[list] = None) -> dict:
    """
    Achata um Site Profile no dict 'cfg' usado pelas tasks atuais.
    Nao valida — use validate_site_profile antes.
    """
    portal = profile.get("portal") or {}
    wp = profile.get("wordpress") or {}
    ssh = profile.get("ssh") or {}
    plugins = profile.get("plugins") or {}

    # Domain pode vir com scheme (https://...). O cfg espera string livre,
    # entao mantemos como esta — o backend nao valida formato do dominio.
    domain = str(portal.get("domain") or "")

    auth = (ssh.get("auth_method") or "password").strip()
    senha_ssh = ssh.get("password") if auth == "password" else ""
    chave_ssh = ssh.get("key_path") if auth == "key" else ""

    cfg = {
        "portal_name":    str(portal.get("name") or "").strip(),
        "portal_niche":   str(portal.get("niche") or "").strip(),
        "portal_domain":  domain.strip(),
        "wp_url":         str(wp.get("url") or "").strip().rstrip("/"),
        "wp_user":        str(wp.get("admin_user") or "").strip(),
        "wp_app_password": wp.get("application_password") or "",
        "ssh_host":       str(ssh.get("host") or "").strip(),
        "ssh_port":       int(ssh.get("port") or 22),
        "ssh_user":       str(ssh.get("user") or "").strip(),
        "ssh_password":   senha_ssh or "",
        "ssh_key_path":   str(chave_ssh or "").strip(),
        "wp_path":        str(wp.get("wp_path") or "").strip(),
        "wpcli_bin":      str(wp.get("wp_cli_path") or "/usr/local/bin/wp").strip(),
    }

    # Conteudo inline e usuarios — passados adiante para acoes_*
    content = profile.get("content") or {}
    if isinstance(content, dict):
        if isinstance(content.get("pages_inline"), list):
            cfg["pages_inline"] = content["pages_inline"]
        if isinstance(content.get("categories_inline"), list):
            cfg["categories_inline"] = content["categories_inline"]
        if isinstance(content.get("posts_inline"), list):
            cfg["posts_inline"] = content["posts_inline"]

    if isinstance(profile.get("users"), list):
        cfg["users"] = profile["users"]

    return cfg


def extrair_profile_meta(profile: dict) -> dict:
    """
    Retorna metadata segura do profile para incluir em log/relatorio.
    Nunca contem credenciais.
    """
    if not isinstance(profile, dict):
        return {}
    pr = profile.get("profile") or {}
    pt = profile.get("portal") or {}
    return {
        "slug":        str(pr.get("slug") or ""),
        "version":     str(pr.get("version") or ""),
        "description": str(pr.get("description") or ""),
        "name":        str(pt.get("name") or ""),
        "domain":      str(pt.get("domain") or ""),
        "niche":       str(pt.get("niche") or ""),
    }


# ---------------------------------------------------------------------- #
# Construcao / persistencia de profiles
# ---------------------------------------------------------------------- #
PROFILES_PROTEGIDOS = {"example"}


def _to_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "yes", "on", "sim"):
            return True
        if s in ("0", "false", "no", "off", "nao", "não", ""):
            return False
    return default


def _to_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _split_lista(v: Any) -> list[str]:
    """Converte string (linhas/virgulas) ou lista em lista de slugs limpos."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        partes: list[str] = []
        for chunk in v.replace(",", "\n").splitlines():
            s = chunk.strip()
            if s:
                partes.append(s)
        return partes
    return []


def _slug_seguro(s: str) -> str:
    """Sanitiza slug: minusculas, sem barras, sem espacos."""
    if not isinstance(s, str):
        return ""
    out = s.strip().lower()
    out = out.replace("/", "_").replace("\\", "_")
    out = "".join(c if (c.isalnum() or c in ("-", "_")) else "-" for c in out)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-_") or ""


def build_profile_from_payload(payload: dict) -> dict:
    """
    Monta um profile JSON no schema oficial a partir do payload achatado
    enviado pelo dashboard. Aceita tanto chaves achatadas
    (profile_slug, portal_name, seo_blog_public, ...) quanto chaves
    aninhadas (profile, portal, seo, ...).

    Nao valida — use validate_site_profile na sequencia.
    Sensiveis (application_password, ssh.password, ssh.key_path) sao
    preservados aqui; e save_site_profile que zera antes de gravar.
    """
    if not isinstance(payload, dict):
        payload = {}

    g = lambda k, default="": (
        payload[k] if k in payload and payload[k] is not None else default
    )

    # Permite payload aninhado vindo direto (ex.: ja em formato profile).
    if isinstance(payload.get("profile"), dict) and isinstance(
        payload.get("portal"), dict
    ):
        # Retorna copia profunda; consumidor pode complementar depois.
        return copy.deepcopy(payload)

    profile = {
        "profile": {
            "slug": _slug_seguro(str(g("profile_slug") or g("slug"))),
            "version": str(g("profile_version", "1.0.0")).strip() or "1.0.0",
            "description": str(g("profile_description", "")).strip(),
        },
        "portal": {
            "name":     str(g("portal_name", "")).strip(),
            "domain":   str(g("portal_domain", "")).strip(),
            "niche":    str(g("portal_niche", "")).strip(),
            "language": str(g("portal_language", "pt-BR")).strip() or "pt-BR",
            "timezone": str(g("portal_timezone", "America/Sao_Paulo")).strip()
                        or "America/Sao_Paulo",
        },
        "wordpress": {
            "url":        str(g("wp_url", "")).strip().rstrip("/"),
            "admin_user": str(g("wp_user", "")).strip(),
            "application_password": str(g("wp_app_password", "")),
            "wp_path":    str(g("wp_path", "")).strip(),
            "wp_cli_path": str(g("wpcli_bin", "/usr/local/bin/wp")).strip()
                          or "/usr/local/bin/wp",
        },
        "ssh": {
            "host":        str(g("ssh_host", "")).strip(),
            "port":        _to_int(g("ssh_port", 22), 22),
            "user":        str(g("ssh_user", "")).strip(),
            "auth_method": (str(g("ssh_auth_method", "password")).strip().lower()
                            or "password"),
            "password":    str(g("ssh_password", "")),
            "key_path":    str(g("ssh_key_path", "")).strip(),
        },
        "seo": {
            "site_title":          str(g("seo_site_title", "")).strip(),
            "tagline":             str(g("seo_tagline", "")).strip(),
            "permalink_structure": str(g("seo_permalink_structure",
                                         "/%postname%/")).strip()
                                   or "/%postname%/",
            "blog_public":         _to_bool(g("seo_blog_public", True), True),
            "comments_enabled":    _to_bool(g("seo_comments_enabled", False),
                                            False),
            "ping_status":         _to_bool(g("seo_ping_status", False), False),
            "rank_math":           _to_bool(g("seo_rank_math", True), True),
            "instant_indexing":    _to_bool(g("seo_instant_indexing", True),
                                            True),
        },
        "plugins": {
            "required": _split_lista(g("plugins_required", [])),
            "optional": _split_lista(g("plugins_optional", [])),
            "skip":     _split_lista(g("plugins_skip", [])),
        },
        "content": {
            "create_pages":      _to_bool(g("content_create_pages", True), True),
            "create_categories": _to_bool(g("content_create_categories", True),
                                          True),
            "create_test_post":  _to_bool(g("content_create_test_post", True),
                                          True),
            "homepage_slug":     str(g("content_homepage_slug", "inicio")).strip()
                                 or "inicio",
        },
        "report": {
            "generate_markdown": _to_bool(g("report_generate_markdown", True),
                                          True),
            "include_manual_pending_tasks": _to_bool(
                g("report_include_manual_pending_tasks", True), True
            ),
        },
    }

    # Default seo.site_title = portal.name se vazio
    if not profile["seo"]["site_title"]:
        profile["seo"]["site_title"] = profile["portal"]["name"]

    return profile


def save_site_profile(
    profile: dict,
    *,
    overwrite: bool = False,
) -> dict:
    """
    Persiste um profile em config/sites/<slug>.json.

    Regras:
    - Valida estrutura antes de gravar (validate_site_profile).
    - Zera credenciais sensiveis (NUNCA grava senha real em disco).
    - Slug e obrigatorio e deve ser seguro para nome de arquivo.
    - Se o arquivo ja existir e overwrite=False, retorna 'exists' sem gravar.
    - Indent 2, ensure_ascii=False.

    Retorna dict:
      {"status": "ok"|"exists"|"erro", "message": str,
       "path": str|None, "slug": str|None, "errors": [str]}
    """
    if not isinstance(profile, dict):
        return {"status": "erro", "message": "Profile invalido (nao e objeto).",
                "path": None, "slug": None, "errors": []}

    # Validar primeiro
    valido, erros = validate_site_profile(profile)
    if not valido:
        return {
            "status": "erro",
            "message": "Profile invalido: " + "; ".join(erros),
            "path": None,
            "slug": None,
            "errors": erros,
        }

    slug_bruto = ((profile.get("profile") or {}).get("slug") or "").strip()
    slug = _slug_seguro(slug_bruto)
    if not slug:
        return {
            "status": "erro",
            "message": "profile.slug ausente ou invalido.",
            "path": None, "slug": None, "errors": ["profile.slug invalido"],
        }

    # Copia segura: zera credenciais antes de gravar
    seguro = copy.deepcopy(profile)
    wp = seguro.setdefault("wordpress", {})
    ssh = seguro.setdefault("ssh", {})
    if not isinstance(wp, dict):
        wp = {}
        seguro["wordpress"] = wp
    if not isinstance(ssh, dict):
        ssh = {}
        seguro["ssh"] = ssh
    wp["application_password"] = ""
    ssh["password"] = ""
    # key_path: tambem nunca persistido (caminho local de chave privada)
    ssh["key_path"] = ""

    # Senhas em listas (users[*].password) — nunca persistir
    for _grupo, list_key, item_field in _SENSIVEIS_LISTAS:
        lista = seguro.get(list_key)
        if isinstance(lista, list):
            for it in lista:
                if isinstance(it, dict) and item_field in it:
                    it[item_field] = ""

    # Garante que profile.slug salvo seja o sanitizado
    pr = seguro.setdefault("profile", {})
    if isinstance(pr, dict):
        pr["slug"] = slug

    destino = sites_dir() / f"{slug}.json"
    if destino.exists() and not overwrite:
        return {
            "status": "exists",
            "message": (
                f"Ja existe '{destino.name}'. Confirme sobrescrita "
                "(overwrite=true)."
            ),
            "path": str(destino),
            "slug": slug,
            "errors": [],
        }

    try:
        lock_path = destino.with_suffix(".json.lock")
        with FileLock(str(lock_path), timeout=10):
            destino.write_text(
                json.dumps(seguro, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        _logger.info("Profile salvo: %s", destino)
    except OSError as exc:
        _logger.error("Falha ao gravar profile %s: %s", destino, exc)
        return {"status": "erro",
                "message": f"Falha ao gravar arquivo: {exc}",
                "path": None, "slug": slug, "errors": [str(exc)]}
    except Exception as exc:
        _logger.error("Falha de concorrência ou FileLock no profile %s: %s", destino, exc)
        return {"status": "erro",
                "message": f"Falha de concorrencia ao gravar arquivo: {exc}",
                "path": None, "slug": slug, "errors": [str(exc)]}

    return {
        "status": "ok",
        "message": f"Profile '{slug}' salvo em {destino.name}",
        "path": str(destino),
        "slug": slug,
        "errors": [],
    }


def delete_site_profile(slug: str) -> dict:
    """
    Remove config/sites/<slug>.json.
    Protege slugs em PROFILES_PROTEGIDOS (ex.: 'example').

    Retorna dict:
      {"status": "ok"|"erro", "message": str, "path": str|None}
    """
    s = _slug_seguro(slug or "")
    if not s:
        return {"status": "erro", "message": "Slug ausente ou invalido.",
                "path": None}
    if s in PROFILES_PROTEGIDOS:
        return {"status": "erro",
                "message": f"Profile '{s}' e protegido e nao pode ser excluido.",
                "path": None}

    destino = sites_dir() / f"{s}.json"
    if not destino.exists():
        return {"status": "erro",
                "message": f"Profile '{s}.json' nao encontrado.",
                "path": str(destino)}

    try:
        destino.unlink()
        _logger.info("Profile removido: %s", destino)
    except OSError as exc:
        _logger.error("Falha ao remover %s: %s", destino, exc)
        return {"status": "erro",
                "message": f"Falha ao remover arquivo: {exc}",
                "path": str(destino)}

    return {"status": "ok",
            "message": f"Profile '{s}' removido.",
            "path": str(destino)}


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
    profile_meta = contexto.get("profile") or {}
    profile_aplicado = contexto.get("profile_aplicado") or {}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_dominio = (dominio or "site").replace("/", "_").replace(":", "_")
    
    run_dir = get_run_dir()
    if run_dir:
        caminho = run_dir / "report.md"
    else:
        caminho = logs_dir() / f"relatorio_{safe_dominio}_{timestamp}.md"

    data_hora = (iniciado_em or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    linhas: list[str] = []
    linhas.append("# Relatorio de Provisionamento")
    linhas.append("")
    linhas.append("## Metadados da Execucao")
    linhas.append(f"- **Portal:** {portal_name}")
    linhas.append(f"- **Dominio:** {dominio}")
    linhas.append(f"- **Nicho:** {niche}")
    linhas.append(f"- **Data:** {data_hora}")
    linhas.append(f"- **Duracao total:** {duracao:.1f}s")
    linhas.append("")

    # Profile (se houver)
    if profile_meta:
        linhas.append("## Profile utilizado")
        linhas.append(f"- Slug: {profile_meta.get('slug') or '-'}")
        linhas.append(f"- Nome: {profile_meta.get('name') or '-'}")
        linhas.append(f"- Dominio: {profile_meta.get('domain') or '-'}")
        linhas.append(f"- Nicho: {profile_meta.get('niche') or '-'}")
        linhas.append(
            f"- Versao do profile: {profile_meta.get('version') or '-'}"
        )
        if profile_meta.get("description"):
            linhas.append(f"- Descricao: {profile_meta['description']}")
        linhas.append("")

        if profile_aplicado:
            linhas.append("## Configuracoes aplicadas via profile")
            seo_ok = profile_aplicado.get("seo_aplicado")
            linhas.append(
                "- SEO tecnico: "
                + ("aplicado" if seo_ok else "nao aplicado")
            )
            req = profile_aplicado.get("plugins_required") or []
            opt = profile_aplicado.get("plugins_optional") or []
            skip = profile_aplicado.get("plugins_skip") or []
            linhas.append(
                "- Plugins obrigatorios: "
                + (", ".join(req) if req else "(nenhum extra)")
            )
            linhas.append(
                "- Plugins opcionais: "
                + (", ".join(opt) if opt else "(nenhum)")
            )
            if skip:
                linhas.append("- Plugins pulados: " + ", ".join(skip))
            linhas.append(
                "- Paginas institucionais: "
                + ("criadas" if profile_aplicado.get("create_pages")
                   else "puladas")
            )
            linhas.append(
                "- Categorias do nicho: "
                + ("criadas" if profile_aplicado.get("create_categories")
                   else "puladas")
            )
            linhas.append(
                "- Post de teste: "
                + ("criado" if profile_aplicado.get("create_test_post")
                   else "pulado")
            )
            linhas.append("")

    # Etapas executadas/puladas (controle por step_flags)
    etapas_exec = contexto.get("etapas_executadas") or []
    etapas_pul = contexto.get("etapas_puladas") or []
    if etapas_exec or etapas_pul:
        linhas.append("## Etapas executadas")
        if etapas_exec:
            for e in etapas_exec:
                linhas.append(f"- [x] {e}")
        else:
            linhas.append("- (nenhuma)")
        linhas.append("")
        linhas.append("## Etapas puladas")
        if etapas_pul:
            for e in etapas_pul:
                linhas.append(f"- [ ] {e}")
        else:
            linhas.append("- (nenhuma)")
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
        conteudo_sanitizado = sanitize_sensitive_data("\n".join(linhas))
        caminho.write_text(conteudo_sanitizado, encoding="utf-8")
        _logger.info("Relatorio gerado: %s", caminho)
    except OSError as exc:
        _logger.error("Falha ao gravar relatorio em %s: %s", caminho, exc)
        raise

    return caminho
