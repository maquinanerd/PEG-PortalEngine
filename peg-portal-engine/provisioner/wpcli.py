"""
Camada WP-CLI executada via SSH.

Regras obrigatorias:
- Sempre usar caminho absoluto do binario (WPCLI_BIN)
- Sempre incluir --path={wp_path}
- Detectar SSH user == 'root' e adicionar --allow-root automaticamente
- Usar --format=json em comandos que retornam dados; parsear com json.loads
- --skip-themes --skip-plugins apenas em comandos de verificacao
"""

from __future__ import annotations

import json
import shlex
import time
from typing import Any, Optional

import paramiko

from .logger import get_logger, sanitize_sensitive_data
from .ssh_client import executar


_logger = get_logger()


class WPCLI:
    def __init__(
        self,
        ssh_client: paramiko.SSHClient,
        wpcli_bin: str,
        wp_path: str,
        ssh_user: str,
    ) -> None:
        if ssh_client is None:
            raise ValueError("ssh_client e obrigatorio")
        if not wpcli_bin:
            raise ValueError("wpcli_bin e obrigatorio")
        if not wp_path:
            raise ValueError("wp_path e obrigatorio")

        self.client = ssh_client
        # Caminhos remotos sempre com '/'
        self.wpcli_bin = wpcli_bin.strip()
        self.wp_path = wp_path.strip().rstrip("/") or "/"
        self.allow_root = (ssh_user or "").strip().lower() == "root"

    # ------------------------------------------------------------------ #
    # Construtor de comandos
    # ------------------------------------------------------------------ #
    def _build_cmd(
        self,
        subcommand: str,
        flags: Optional[list] = None,
        json_output: bool = False,
        skip_themes_plugins: bool = False,
    ) -> str:
        parts: list[str] = [
            shlex.quote(self.wpcli_bin),
            subcommand,
            f"--path={shlex.quote(self.wp_path)}",
        ]
        if self.allow_root:
            parts.append("--allow-root")
        if json_output:
            parts.append("--format=json")
        if skip_themes_plugins:
            parts.extend(["--skip-themes", "--skip-plugins"])
        if flags:
            parts.extend(flags)

        return " ".join(parts)

    def _run(self, comando: str, timeout: int = 90) -> dict:
        return executar(self.client, comando, timeout=timeout)

    @staticmethod
    def _safe_json_loads(texto: str) -> Any:
        try:
            return json.loads(texto)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    # ------------------------------------------------------------------ #
    # Verificacoes
    # ------------------------------------------------------------------ #
    def verificar_wpcli(self) -> dict:
        """Retorna versao do WP-CLI."""
        cmd = self._build_cmd("--version")
        res = self._run(cmd, timeout=30)
        if res["exit_code"] == 0:
            versao = res["stdout"].strip()
            return {"ok": True, "versao": versao, "msg": versao}
        return {
            "ok": False,
            "versao": None,
            "msg": f"Falha ao detectar WP-CLI: {sanitize_sensitive_data(res['stderr'].strip() or res['stdout'].strip())}",
        }

    def verificar_wp(self) -> dict:
        """Retorna versao WP, URL do site e status."""
        cmd_versao = self._build_cmd(
            "core version", flags=None, skip_themes_plugins=True
        )
        res_v = self._run(cmd_versao, timeout=30)
        if res_v["exit_code"] != 0:
            return {
                "ok": False,
                "msg": f"WP nao encontrado em {self.wp_path}: "
                       f"{sanitize_sensitive_data(res_v['stderr'].strip() or res_v['stdout'].strip())}",
            }
        versao = res_v["stdout"].strip()

        cmd_url = self._build_cmd(
            "option get siteurl", flags=None, skip_themes_plugins=True
        )
        res_url = self._run(cmd_url, timeout=30)
        siteurl = res_url["stdout"].strip() if res_url["exit_code"] == 0 else None

        return {
            "ok": True,
            "versao": versao,
            "siteurl": siteurl,
            "wp_path": self.wp_path,
            "msg": f"WordPress {versao} em {siteurl or self.wp_path}",
        }

    def verificar_redis(self) -> dict:
        """
        Executa 'redis-cli ping' via SSH e checa por PONG.
        Independe de WP — usa apenas o cliente SSH.
        """
        res = executar(self.client, "redis-cli ping", timeout=15)
        saida = (res["stdout"] or "").strip().upper()
        if res["exit_code"] == 0 and saida == "PONG":
            return {"ok": True, "msg": "Redis disponivel (PONG)"}
        return {
            "ok": False,
            "msg": f"Redis indisponivel: exit={res['exit_code']} "
                   f"stdout={sanitize_sensitive_data(res['stdout'].strip())} stderr={sanitize_sensitive_data(res['stderr'].strip())}",
        }

    # ------------------------------------------------------------------ #
    # Plugins
    # ------------------------------------------------------------------ #
    def listar_plugins_ativos(self) -> list:
        """Lista os slugs dos plugins ativos."""
        cmd = self._build_cmd(
            "plugin list",
            flags=["--status=active", "--field=name"],
            json_output=True,
        )
        res = self._run(cmd, timeout=60)
        if res["exit_code"] != 0:
            _logger.warning(
                "WP-CLI: falha ao listar plugins ativos — %s",
                sanitize_sensitive_data(res["stderr"].strip()),
            )
            return []
        dados = self._safe_json_loads(res["stdout"])
        if isinstance(dados, list):
            return [str(item) for item in dados]
        return []

    def instalar_plugin(self, slug: str) -> dict:
        """Instala um plugin (sem ativar)."""
        if not slug:
            return {"ok": False, "msg": "slug vazio"}
        cmd = self._build_cmd("plugin install", flags=[shlex.quote(slug)])
        res = self._run(cmd, timeout=180)
        if res["exit_code"] == 0:
            return {"ok": True, "msg": f"plugin {slug} instalado"}
        return {
            "ok": False,
            "msg": f"falha ao instalar {slug}: "
                   f"{sanitize_sensitive_data(res['stderr'].strip() or res['stdout'].strip())}",
        }

    def ativar_plugin(self, slug: str) -> dict:
        """Ativa um plugin ja instalado."""
        if not slug:
            return {"ok": False, "msg": "slug vazio"}
        cmd = self._build_cmd("plugin activate", flags=[shlex.quote(slug)])
        res = self._run(cmd, timeout=120)
        if res["exit_code"] == 0:
            return {"ok": True, "msg": f"plugin {slug} ativado"}
        return {
            "ok": False,
            "msg": f"falha ao ativar {slug}: "
                   f"{sanitize_sensitive_data(res['stderr'].strip() or res['stdout'].strip())}",
        }

    def instalar_e_ativar(self, slug: str) -> dict:
        """Instala (se necessario) e ativa um plugin."""
        if not slug:
            return {"ok": False, "msg": "slug vazio"}
        cmd = self._build_cmd(
            "plugin install",
            flags=[shlex.quote(slug), "--activate"],
        )
        
        max_retries = 3
        delays = [5, 10, 15]
        
        res = None
        for attempt in range(max_retries):
            res = self._run(cmd, timeout=240)
            if res["exit_code"] == 0:
                return {"ok": True, "msg": f"plugin {slug} instalado e ativado"}
                
            if attempt < max_retries - 1:
                _logger.warning("Falha ao instalar %s (tentativa %d/%d). Retentando em %ds...", slug, attempt + 1, max_retries, delays[attempt])
                time.sleep(delays[attempt])
                
        return {
            "ok": False,
            "msg": f"falha ao instalar+ativar {slug} (apos {max_retries} tentativas): "
                   f"{sanitize_sensitive_data(res['stderr'].strip() or res['stdout'].strip())}",
        }

    # ------------------------------------------------------------------ #
    # Opcoes / SEO
    # ------------------------------------------------------------------ #
    def atualizar_opcao(self, key: str, value: object) -> dict:
        """Atualiza wp_options via 'wp option update'."""
        if not key:
            return {"ok": False, "msg": "key vazia"}
        valor_str = str(value)
        cmd = self._build_cmd(
            "option update",
            flags=[shlex.quote(key), shlex.quote(valor_str)],
        )
        res = self._run(cmd, timeout=60)
        if res["exit_code"] == 0:
            return {"ok": True, "msg": f"opcao {key} atualizada"}
        return {
            "ok": False,
            "msg": f"falha ao atualizar {key}: "
                   f"{sanitize_sensitive_data(res['stderr'].strip() or res['stdout'].strip())}",
        }

    def configurar_permalink(self, estrutura: str) -> dict:
        """Define a estrutura de permalink (ex: '/%postname%/')."""
        return self.atualizar_opcao("permalink_structure", estrutura)

    def flush_rewrite(self) -> dict:
        """Recria as regras de reescrita."""
        cmd = self._build_cmd("rewrite flush", flags=["--hard"])
        res = self._run(cmd, timeout=60)
        if res["exit_code"] == 0:
            return {"ok": True, "msg": "rewrite rules atualizadas"}
        return {
            "ok": False,
            "msg": f"falha em rewrite flush: "
                   f"{sanitize_sensitive_data(res['stderr'].strip() or res['stdout'].strip())}",
        }

    def flush_cache(self) -> dict:
        """Limpa o object cache do WP."""
        cmd = self._build_cmd("cache flush")
        res = self._run(cmd, timeout=60)
        if res["exit_code"] == 0:
            return {"ok": True, "msg": "cache limpo"}
        return {
            "ok": False,
            "msg": f"falha em cache flush: "
                   f"{sanitize_sensitive_data(res['stderr'].strip() or res['stdout'].strip())}",
        }

    # ------------------------------------------------------------------ #
    # Usuarios
    # ------------------------------------------------------------------ #
    def usuario_existe(self, login_or_email: str) -> bool:
        """Checa se ja existe usuario com aquele login OU email."""
        if not login_or_email:
            return False
        cmd = self._build_cmd(
            "user get",
            flags=[shlex.quote(login_or_email), "--field=ID"],
        )
        res = self._run(cmd, timeout=30)
        return res["exit_code"] == 0 and res["stdout"].strip().isdigit()

    def criar_usuario(
        self,
        login: str,
        email: str,
        role: str = "subscriber",
        password: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> dict:
        """Cria usuario WP via 'wp user create'. Idempotente."""
        if not login or not email:
            return {"ok": False, "msg": "login e email sao obrigatorios"}

        if self.usuario_existe(login) or self.usuario_existe(email):
            return {
                "ok": True,
                "ja_existia": True,
                "msg": f"usuario '{login}' ja existe",
            }

        flags = [
            shlex.quote(login),
            shlex.quote(email),
            f"--role={shlex.quote(role or 'subscriber')}",
            "--porcelain",
        ]
        if password:
            flags.append(f"--user_pass={shlex.quote(password)}")
        if display_name:
            flags.append(f"--display_name={shlex.quote(display_name)}")

        cmd = self._build_cmd("user create", flags=flags)
        res = self._run(cmd, timeout=60)
        if res["exit_code"] == 0:
            uid = res["stdout"].strip()
            return {
                "ok": True,
                "ja_existia": False,
                "id": uid,
                "msg": f"usuario '{login}' criado (id={uid})",
            }
        return {
            "ok": False,
            "msg": f"falha ao criar usuario '{login}': "
                   f"{sanitize_sensitive_data(res['stderr'].strip() or res['stdout'].strip())}",
        }
