"""
Camada REST API do WordPress.

- Auth: HTTP Basic com Application Password
- Validacao do app password antes de qualquer requisicao
- Deduplicacao por slug (categorias e paginas)
"""

from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth

from .logger import get_logger, sanitize_sensitive_data


_logger = get_logger()
_HTTP_TIMEOUT = int(os.environ.get("PEG_ENGINE_REST_TIMEOUT", "30"))


def _normalizar_app_password(senha: str) -> str:
    """Remove espacos em excesso e mantem apenas alfanumerico."""
    if not senha:
        return ""
    return re.sub(r"\s+", "", senha)


def _validar_app_password(senha: str) -> tuple[bool, str]:
    """Application Password deve ter exatamente 24 caracteres alfanumericos."""
    limpo = _normalizar_app_password(senha)
    if not limpo:
        return False, "Application Password vazia"
    if len(limpo) != 24:
        return (
            False,
            f"Application Password invalida: esperado 24 caracteres alfanumericos, "
            f"recebido {len(limpo)}",
        )
    if not re.fullmatch(r"[A-Za-z0-9]{24}", limpo):
        return False, "Application Password contem caracteres invalidos"
    return True, ""


class WPRest:
    def __init__(self, wp_url: str, wp_user: str, app_password: str) -> None:
        if not wp_url:
            raise ValueError("wp_url e obrigatorio")
        if not wp_user:
            raise ValueError("wp_user e obrigatorio")

        self.wp_url = wp_url.rstrip("/")
        self.wp_user = wp_user

        ok, msg = _validar_app_password(app_password)
        self._auth_valida = ok
        self._auth_msg = msg
        if ok:
            self._auth = HTTPBasicAuth(self.wp_user, _normalizar_app_password(app_password))
        else:
            self._auth = None
            _logger.error("WP REST: %s", msg)

        self.base = self.wp_url + "/wp-json/"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _check_auth(self) -> Optional[dict]:
        if not self._auth_valida:
            return {"ok": False, "msg": self._auth_msg}
        return None

    def _url(self, caminho: str) -> str:
        if caminho.startswith("/"):
            caminho = caminho[1:]
        return urljoin(self.base, caminho)

    def _request(
        self,
        metodo: str,
        caminho: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
        timeout: int = _HTTP_TIMEOUT,
    ) -> dict:
        """
        Wrapper unico para todas as chamadas REST.
        Retorna {ok, status, data, msg, raw_text}.
        """
        check = self._check_auth()
        if check:
            return {
                "ok": False,
                "status": 0,
                "data": None,
                "msg": check["msg"],
                "raw_text": "",
            }

        url = self._url(caminho)
        try:
            resp = requests.request(
                metodo.upper(),
                url,
                params=params,
                json=json_body,
                auth=self._auth,
                timeout=timeout,
            )
        except requests.exceptions.SSLError as exc:
            return {"ok": False, "status": 0, "data": None,
                    "msg": f"SSL error: {exc}", "raw_text": ""}
        except requests.exceptions.ConnectionError as exc:
            return {"ok": False, "status": 0, "data": None,
                    "msg": f"Connection error: {exc}", "raw_text": ""}
        except requests.exceptions.Timeout:
            return {"ok": False, "status": 0, "data": None,
                    "msg": f"Timeout apos {timeout}s", "raw_text": ""}
        except requests.exceptions.RequestException as exc:
            return {"ok": False, "status": 0, "data": None,
                    "msg": f"Erro requests: {exc}", "raw_text": ""}

        try:
            data = resp.json()
            if isinstance(data, dict):
                # Sanitiza os valores em string do JSON apenas nas chaves principais
                for k, v in data.items():
                    if isinstance(v, str):
                        data[k] = sanitize_sensitive_data(v)
        except ValueError:
            data = None

        ok = 200 <= resp.status_code < 300
        msg_erro = ""
        if not ok and isinstance(data, dict):
            msg_erro = data.get("message") or data.get("code") or ""

        return {
            "ok": ok,
            "status": resp.status_code,
            "data": data,
            "msg": msg_erro or f"HTTP {resp.status_code}",
            "raw_text": sanitize_sensitive_data(resp.text[:500]),
        }

    # ------------------------------------------------------------------ #
    # Teste / discovery
    # ------------------------------------------------------------------ #
    def testar_api(self) -> dict:
        """Testa /wp-json/ e /wp-json/wp/v2/users/me."""
        check = self._check_auth()
        if check:
            return check

        # GET / (publico)
        try:
            r1 = requests.get(self.base, timeout=_HTTP_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            return {"ok": False, "msg": f"Falha ao acessar {self.base}: {exc}"}

        if r1.status_code != 200:
            return {
                "ok": False,
                "msg": f"GET {self.base} retornou {r1.status_code}",
            }

        # GET users/me (autenticado)
        r2 = self._request("GET", "wp/v2/users/me")
        if not r2["ok"]:
            return {
                "ok": False,
                "msg": f"Auth falhou em users/me: HTTP {r2['status']} — {r2['msg']}",
            }

        usuario = r2["data"] or {}
        return {
            "ok": True,
            "msg": f"REST OK — autenticado como '{usuario.get('name') or self.wp_user}'",
            "user_id": usuario.get("id"),
        }

    # ------------------------------------------------------------------ #
    # Categorias
    # ------------------------------------------------------------------ #
    def listar_categorias(self) -> list:
        """Lista todas as categorias (paginado, ate 100/pag)."""
        resultados: list = []
        pagina = 1
        while True:
            res = self._request(
                "GET",
                "wp/v2/categories",
                params={"per_page": 100, "page": pagina},
            )
            if not res["ok"]:
                _logger.warning("REST: falha ao listar categorias — %s", res["msg"])
                break
            dados = res["data"]
            if not isinstance(dados, list) or not dados:
                break
            resultados.extend(dados)
            if len(dados) < 100:
                break
            pagina += 1
            if pagina > 20:  # salvaguarda
                break
        return resultados

    def categoria_existe(self, slug: str) -> bool:
        if not slug:
            return False
        res = self._request(
            "GET",
            "wp/v2/categories",
            params={"slug": slug},
        )
        if not res["ok"]:
            return False
        dados = res["data"]
        return isinstance(dados, list) and len(dados) > 0

    def criar_categoria(
        self,
        nome: str,
        slug: str,
        descricao: str = "",
        parent_id: Optional[int] = None,
    ) -> dict:
        if not nome or not slug:
            return {"ok": False, "msg": "nome e slug sao obrigatorios"}

        if self.categoria_existe(slug):
            _logger.info("REST: categoria '%s' ja existe — pulando", slug)
            return {"ok": True, "ja_existia": True, "msg": f"categoria '{slug}' ja existe"}

        body: dict = {"name": nome, "slug": slug, "description": descricao or ""}
        if parent_id:
            body["parent"] = int(parent_id)

        res = self._request("POST", "wp/v2/categories", json_body=body)
        if res["ok"] and isinstance(res["data"], dict):
            return {
                "ok": True,
                "ja_existia": False,
                "id": res["data"].get("id"),
                "msg": f"categoria '{slug}' criada (id={res['data'].get('id')})",
            }
        return {"ok": False, "msg": f"falha ao criar categoria '{slug}': {res['msg']}"}

    # ------------------------------------------------------------------ #
    # Paginas
    # ------------------------------------------------------------------ #
    def listar_paginas(self) -> list:
        resultados: list = []
        pagina = 1
        while True:
            res = self._request(
                "GET",
                "wp/v2/pages",
                params={"per_page": 100, "page": pagina, "status": "any"},
            )
            if not res["ok"]:
                _logger.warning("REST: falha ao listar paginas — %s", res["msg"])
                break
            dados = res["data"]
            if not isinstance(dados, list) or not dados:
                break
            resultados.extend(dados)
            if len(dados) < 100:
                break
            pagina += 1
            if pagina > 20:
                break
        return resultados

    def pagina_existe(self, slug: str) -> bool:
        if not slug:
            return False
        res = self._request(
            "GET",
            "wp/v2/pages",
            params={"slug": slug, "status": "any"},
        )
        if not res["ok"]:
            return False
        dados = res["data"]
        return isinstance(dados, list) and len(dados) > 0

    def buscar_pagina_por_slug(self, slug: str) -> Optional[dict]:
        res = self._request(
            "GET",
            "wp/v2/pages",
            params={"slug": slug, "status": "any"},
        )
        if not res["ok"]:
            return None
        dados = res["data"]
        if isinstance(dados, list) and dados:
            return dados[0]
        return None

    def criar_pagina(
        self,
        titulo: str,
        conteudo: str,
        status: str = "publish",
        slug: Optional[str] = None,
    ) -> dict:
        if not titulo:
            return {"ok": False, "msg": "titulo obrigatorio"}

        if slug and self.pagina_existe(slug):
            _logger.info("REST: pagina '%s' ja existe — pulando", slug)
            existente = self.buscar_pagina_por_slug(slug) or {}
            return {
                "ok": True,
                "ja_existia": True,
                "id": existente.get("id"),
                "msg": f"pagina '{slug}' ja existe (id={existente.get('id')})",
            }

        body: dict = {
            "title": titulo,
            "content": conteudo or "",
            "status": status or "publish",
        }
        if slug:
            body["slug"] = slug

        res = self._request("POST", "wp/v2/pages", json_body=body)
        if res["ok"] and isinstance(res["data"], dict):
            return {
                "ok": True,
                "ja_existia": False,
                "id": res["data"].get("id"),
                "msg": f"pagina '{titulo}' criada (id={res['data'].get('id')})",
            }
        return {"ok": False, "msg": f"falha ao criar pagina '{titulo}': {res['msg']}"}

    # ------------------------------------------------------------------ #
    # Posts
    # ------------------------------------------------------------------ #
    def criar_post(
        self,
        titulo: str,
        conteudo: str,
        status: str = "draft",
        categoria_ids: Optional[list] = None,
    ) -> dict:
        if not titulo:
            return {"ok": False, "msg": "titulo obrigatorio"}

        body: dict = {
            "title": titulo,
            "content": conteudo or "",
            "status": status or "draft",
        }
        if categoria_ids:
            try:
                body["categories"] = [int(cid) for cid in categoria_ids if cid]
            except (TypeError, ValueError):
                pass

        res = self._request("POST", "wp/v2/posts", json_body=body)
        if res["ok"] and isinstance(res["data"], dict):
            return {
                "ok": True,
                "id": res["data"].get("id"),
                "msg": f"post criado (id={res['data'].get('id')})",
            }
        return {"ok": False, "msg": f"falha ao criar post: {res['msg']}"}
