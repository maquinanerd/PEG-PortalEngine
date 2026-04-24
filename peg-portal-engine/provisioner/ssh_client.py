"""
Camada SSH baseada em Paramiko.

Suporta dois modos de autenticacao mutuamente exclusivos:
1. Senha (ssh_password)
2. Chave privada (ssh_key_path) — RSA, com possivel passphrase

Toda funcao trata erros e retorna dicionarios padronizados.
Nunca loga senhas ou chaves.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import paramiko
from paramiko.ssh_exception import (
    AuthenticationException,
    BadHostKeyException,
    NoValidConnectionsError,
    PasswordRequiredException,
    SSHException,
)

from .logger import get_logger


_logger = get_logger()

_MAX_RETRIES = 3
_RETRY_INTERVAL_SEC = 5


def _carregar_chave(key_path: str) -> paramiko.PKey:
    """Carrega uma chave privada RSA a partir de um caminho local."""
    caminho = Path(key_path).expanduser()
    if not caminho.is_file():
        raise FileNotFoundError(f"Chave privada nao encontrada: {caminho}")

    try:
        return paramiko.RSAKey.from_private_key_file(str(caminho))
    except PasswordRequiredException as exc:
        raise PasswordRequiredException(
            "A chave privada esta protegida por passphrase, "
            "que nao e suportada via formulario."
        ) from exc
    except SSHException:
        # Tenta outros tipos de chave comuns
        for klass in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey):
            try:
                return klass.from_private_key_file(str(caminho))
            except PasswordRequiredException as exc:
                raise PasswordRequiredException(
                    "A chave privada esta protegida por passphrase."
                ) from exc
            except Exception:
                continue
        raise


def conectar(
    host: str,
    port: int,
    user: str,
    password: Optional[str] = None,
    key_path: Optional[str] = None,
    timeout: int = 30,
) -> paramiko.SSHClient:
    """
    Abre uma conexao SSH com retry automatico (3 tentativas, 5s de intervalo).
    Retorna o cliente conectado ou levanta a ultima excecao.
    """
    if not host or not user:
        raise ValueError("host e user sao obrigatorios para conexao SSH")

    use_key = bool(key_path) and not password
    chave_obj: Optional[paramiko.PKey] = None
    if use_key:
        chave_obj = _carregar_chave(key_path)  # pode levantar

    ultima_excecao: Optional[BaseException] = None

    for tentativa in range(1, _MAX_RETRIES + 1):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            _logger.info(
                "SSH: conectando em %s@%s:%s (tentativa %s/%s, modo=%s)",
                user,
                host,
                port,
                tentativa,
                _MAX_RETRIES,
                "chave" if use_key else "senha",
            )
            if use_key:
                client.connect(
                    hostname=host,
                    port=int(port),
                    username=user,
                    pkey=chave_obj,
                    timeout=timeout,
                    auth_timeout=timeout,
                    banner_timeout=timeout,
                    look_for_keys=False,
                    allow_agent=False,
                )
            else:
                client.connect(
                    hostname=host,
                    port=int(port),
                    username=user,
                    password=password or "",
                    timeout=timeout,
                    auth_timeout=timeout,
                    banner_timeout=timeout,
                    look_for_keys=False,
                    allow_agent=False,
                )
            _logger.info("SSH: conexao estabelecida com %s", host)
            return client
        except (
            AuthenticationException,
            BadHostKeyException,
            NoValidConnectionsError,
            SSHException,
            OSError,
        ) as exc:
            ultima_excecao = exc
            _logger.warning(
                "SSH: falha na tentativa %s/%s — %s",
                tentativa,
                _MAX_RETRIES,
                exc,
            )
            try:
                client.close()
            except Exception:
                pass
            if tentativa < _MAX_RETRIES:
                time.sleep(_RETRY_INTERVAL_SEC)
        except Exception as exc:  # pragma: no cover
            ultima_excecao = exc
            _logger.error("SSH: erro inesperado — %s", exc)
            try:
                client.close()
            except Exception:
                pass
            break

    assert ultima_excecao is not None
    raise ultima_excecao


def executar(client: paramiko.SSHClient, comando: str, timeout: int = 60) -> dict:
    """
    Executa um comando remoto e retorna {stdout, stderr, exit_code}.
    Nunca lanca excecao: erros sao retornados em campos do dict.
    """
    if client is None:
        return {
            "stdout": "",
            "stderr": "Cliente SSH invalido (None)",
            "exit_code": -1,
        }

    if not comando or not comando.strip():
        return {
            "stdout": "",
            "stderr": "Comando vazio",
            "exit_code": -1,
        }

    # Log seguro: nao loga conteudo de variaveis sensiveis
    _logger.debug("SSH exec: %s", comando)

    try:
        stdin, stdout, stderr = client.exec_command(comando, timeout=timeout)
        try:
            stdin.close()
        except Exception:
            pass

        out_bytes = stdout.read()
        err_bytes = stderr.read()
        exit_code = stdout.channel.recv_exit_status()

        return {
            "stdout": out_bytes.decode("utf-8", errors="replace"),
            "stderr": err_bytes.decode("utf-8", errors="replace"),
            "exit_code": int(exit_code),
        }
    except SSHException as exc:
        _logger.error("SSH exec erro: %s", exc)
        return {"stdout": "", "stderr": f"SSHException: {exc}", "exit_code": -1}
    except Exception as exc:
        _logger.error("SSH exec erro inesperado: %s", exc)
        return {"stdout": "", "stderr": f"Erro: {exc}", "exit_code": -1}


def fechar(client: Optional[paramiko.SSHClient]) -> None:
    """Fecha a conexao SSH (idempotente)."""
    if client is None:
        return
    try:
        client.close()
        _logger.debug("SSH: conexao fechada")
    except Exception as exc:  # pragma: no cover
        _logger.warning("SSH: erro ao fechar conexao — %s", exc)


def testar_conexao(
    host: str,
    port: int,
    user: str,
    password: Optional[str] = None,
    key_path: Optional[str] = None,
) -> dict:
    """
    Testa SSH e retorna {ok, msg}. Nunca lanca excecao.
    """
    client = None
    try:
        client = conectar(host, port, user, password=password, key_path=key_path)
        # Comando trivial para validar shell
        resultado = executar(client, "echo PEG_OK", timeout=15)
        if resultado["exit_code"] == 0 and "PEG_OK" in resultado["stdout"]:
            return {"ok": True, "msg": f"Conexao SSH OK em {user}@{host}:{port}"}
        return {
            "ok": False,
            "msg": f"Conexao aberta, mas comando teste falhou: "
                   f"exit={resultado['exit_code']} stderr={resultado['stderr'].strip()}",
        }
    except FileNotFoundError as exc:
        return {"ok": False, "msg": str(exc)}
    except PasswordRequiredException as exc:
        return {"ok": False, "msg": str(exc)}
    except AuthenticationException:
        return {"ok": False, "msg": "Falha de autenticacao SSH (usuario/senha/chave)."}
    except NoValidConnectionsError as exc:
        return {"ok": False, "msg": f"Nao foi possivel conectar: {exc}"}
    except SSHException as exc:
        return {"ok": False, "msg": f"Erro SSH: {exc}"}
    except Exception as exc:
        return {"ok": False, "msg": f"Erro inesperado: {exc}"}
    finally:
        fechar(client)
