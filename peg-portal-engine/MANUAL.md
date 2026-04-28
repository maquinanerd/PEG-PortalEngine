# PEG Portal Engine — Manual Tecnico Completo

Documento unico que descreve o produto, arquitetura, todos os arquivos e
cada funcao publica do projeto **PEG Portal Engine**.

> Versao do manual: gerada a partir do estado do repositorio em 2026-04-27.
> Para visao rapida, ver `README.md`. Para detalhes operacionais, ver
> `DOCUMENTACAO.md`.

---

## Sumario

1. [Visao geral do produto](#1-visao-geral-do-produto)
2. [Stack e dependencias](#2-stack-e-dependencias)
3. [Arquitetura e ciclo de uma requisicao](#3-arquitetura-e-ciclo-de-uma-requisicao)
4. [Estrutura de pastas](#4-estrutura-de-pastas)
5. [Configuracao: `.env` e `config/*.json`](#5-configuracao-env-e-configjson)
6. [Schema do Site Profile (`config/sites/*.json`)](#6-schema-do-site-profile)
7. [Walkthrough dos arquivos Python](#7-walkthrough-dos-arquivos-python)
   - [7.1 `app.py`](#71-apppy)
   - [7.2 `provisioner/__init__.py`](#72-provisioner__init__py)
   - [7.3 `provisioner/logger.py`](#73-provisionerloggerpy)
   - [7.4 `provisioner/ssh_client.py`](#74-provisionerssh_clientpy)
   - [7.5 `provisioner/wpcli.py`](#75-provisionerwpclipy)
   - [7.6 `provisioner/wp_rest.py`](#76-provisionerwp_restpy)
   - [7.7 `provisioner/utils.py`](#77-provisionerutilspy)
   - [7.8 `provisioner/tasks.py`](#78-provisionertaskspy)
8. [Frontend: HTML, CSS e JavaScript](#8-frontend-html-css-e-javascript)
9. [Endpoints HTTP — referencia completa](#9-endpoints-http--referencia-completa)
10. [As 14 etapas do `setup_completo`](#10-as-14-etapas-do-setup_completo)
11. [Step flags — controle granular do setup](#11-step-flags--controle-granular-do-setup)
12. [Seguranca: sensiveis nunca persistidos](#12-seguranca-sensiveis-nunca-persistidos)
13. [Logs e relatorio Markdown](#13-logs-e-relatorio-markdown)
14. [Como rodar localmente](#14-como-rodar-localmente)
15. [Troubleshooting comum](#15-troubleshooting-comum)
16. [Glossario](#16-glossario)

---

## 1. Visao geral do produto

**PEG Portal Engine** e um pequeno servidor Flask em Python 3.12 que
**provisiona e configura instalacoes WordPress que ja existem em um VPS
CloudPanel**. Ele NAO instala WordPress, NAO cria banco de dados e NAO
mexe em DNS — assume que tudo isso ja foi feito (manualmente ou por outro
script). O foco e a etapa seguinte: deixar o WP pronto para producao com
SEO, plugins, paginas, categorias e indexacao corretos.

O produto resolve tres dores:

1. **Padronizar** o setup de varios portais (sempre o mesmo conjunto de
   plugins, mesma estrutura de permalink, mesma homepage, etc.).
2. **Reaproveitar** configuracoes via Site Profiles JSON
   (`config/sites/*.json`), sem banco de dados.
3. **Auditar** cada execucao com log estruturado e relatorio Markdown.

O painel web tem dois modos:

- **Manual:** voce preenche o formulario e clica em cada acao individual
  (Testar SSH, Instalar plugins, Criar paginas, etc.).
- **Por profile:** voce carrega um arquivo `*.json` salvo em
  `config/sites/`, completa as senhas em runtime, escolhe quais etapas
  rodar e clica em **Rodar setup**.

E projetado para rodar **localmente** no Windows do usuario com VS Code.
Nao depende de Replit, Docker, banco ou cloud.

---

## 2. Stack e dependencias

| Camada       | Tecnologia                                              |
|--------------|---------------------------------------------------------|
| Linguagem    | Python 3.12+                                            |
| Web          | Flask (servidor + Jinja2 templates)                     |
| SSH          | Paramiko                                                |
| HTTP cliente | Requests                                                |
| Env          | python-dotenv                                           |
| Frontend     | Bootstrap 5 (via CDN) + JS vanilla                      |
| Persistencia | Arquivos JSON em `config/` (sem banco)                  |

`requirements.txt`:

```
flask
paramiko
requests
python-dotenv
```

---

## 3. Arquitetura e ciclo de uma requisicao

```
                 +------------------------+
   navegador --> |  Flask  (app.py)       |
                 |  - servir templates    |
                 |  - 18 endpoints /api/* |
                 +-----------+------------+
                             |
                             v
                 +------------------------+
                 |  provisioner/tasks.py  |  <-- orquestra acoes
                 +-----+------+-----+-----+
                       |      |     |
              +--------+      |     +-------------+
              v               v                   v
       ssh_client.py     wpcli.py            wp_rest.py
       (Paramiko)        (WP-CLI via SSH)    (REST API)
              |               |                   |
              v               v                   v
       +-------------+  +-------------+   +---------------+
       |   VPS SSH   |  | shell remoto|   | WordPress     |
       | (CloudPanel)|  | + WP-CLI    |   | wp-json/wp/v2 |
       +-------------+  +-------------+   +---------------+
```

Cada clique no painel:

1. JavaScript (`static/app.js`) coleta o formulario.
2. Faz `POST /api/<acao>` em JSON.
3. `app.py` valida payload, monta `cfg` (dicionario plano com tudo) e
   delega para uma funcao `acao_*` em `provisioner/tasks.py`.
4. A funcao em `tasks.py` abre conexoes SSH/REST conforme necessario,
   executa a etapa, registra no log e retorna
   `{"status", "message", "details"}`.
5. `app.py` devolve esse dict como JSON.
6. JS exibe o resultado no log preto do painel.

---

## 4. Estrutura de pastas

```
peg-portal-engine/
|-- app.py                          # painel Flask + 18 endpoints
|-- requirements.txt                # 4 deps Python
|-- .env.example                    # template de variaveis sensiveis
|-- README.md                       # visao rapida + getting started
|-- DOCUMENTACAO.md                 # documentacao operacional detalhada
|-- MANUAL.md                       # este documento
|
|-- provisioner/                    # nucleo do produto
|   |-- __init__.py                 # marca como pacote
|   |-- logger.py                   # logger duplo (stdout + arquivo)
|   |-- ssh_client.py               # wrapper Paramiko
|   |-- wpcli.py                    # classe WPCLI (executa wp via SSH)
|   |-- wp_rest.py                  # classe WPRest (REST API)
|   |-- utils.py                    # JSON loaders, profiles, relatorio
|   |-- tasks.py                    # acao_* + setup_completo (14 etapas)
|
|-- config/
|   |-- niches.json                 # lista de nichos suportados
|   |-- plugins.json                # plugins obrigatorios + opcionais
|   |-- categories.json             # categorias por nicho
|   |-- pages.json                  # paginas institucionais padrao
|   |-- sites/
|       |-- example.json            # profile de exemplo (protegido)
|       |-- aeconomia.json          # profile real
|       |-- achouimovel.json        # profile real
|       |-- thenerd.json            # profile real
|
|-- templates/
|   |-- index.html                  # painel unica pagina
|
|-- static/
|   |-- app.js                      # logica do painel (vanilla JS)
|   |-- style.css                   # cores do log
|
|-- logs/                           # criado em runtime (gitignored)
|-- reports/                        # relatorios .md (gitignored)
```

---

## 5. Configuracao: `.env` e `config/*.json`

### 5.1 `.env`

Carregado automaticamente por `python-dotenv` no inicio de `app.py`.
Template em `.env.example`:

| Variavel        | Uso                                              |
|-----------------|--------------------------------------------------|
| `SESSION_SECRET`| Secret do Flask (qualquer string longa)          |
| `LOG_LEVEL`     | `DEBUG`/`INFO`/`WARNING`/`ERROR` (default INFO)  |
| `PORTAL_NAME`   | Nome padrao para preencher o formulario          |
| `PORTAL_DOMAIN` | Dominio padrao                                   |
| `PORTAL_NICHE`  | Nicho padrao                                     |
| `WP_URL`        | URL do WP padrao                                 |
| `WP_USER`       | Usuario WP padrao                                |
| `WP_APP_PASSWORD` | Application Password padrao                    |
| `SSH_HOST`      | Host SSH padrao                                  |
| `SSH_PORT`      | Porta SSH (22)                                   |
| `SSH_USER`      | Usuario SSH padrao (`root`)                      |
| `SSH_PASSWORD`  | Senha SSH padrao                                 |
| `SSH_KEY_PATH`  | Caminho da chave SSH alternativa                 |
| `WP_PATH`       | Caminho do WP no VPS                             |
| `WPCLI_BIN`     | Path do binario `wp` (`/usr/local/bin/wp`)       |

Esses valores **populam o formulario** ao carregar `index.html`. Tudo
pode ser editado em runtime — o `.env` e so um conforto, nao e a fonte
da verdade.

### 5.2 `config/niches.json`

Lista plana de nichos disponiveis no `<select>` do dashboard:

```json
["tecnologia", "imoveis", "economia", "saude"]
```

### 5.3 `config/plugins.json`

Lista de plugins com metadata. Estrutura:

```json
[
  {
    "slug": "seo-by-rank-math",
    "nome": "Rank Math SEO",
    "obrigatorio": true,
    "requer_config_manual": true
  },
  ...
]
```

- `obrigatorio: true` -> sempre instalado pelo modo manual.
- `obrigatorio: false` -> aparece como checkbox em "Plugins opcionais".
- `requer_config_manual: true` -> entra na secao "Pendencias manuais"
  do relatorio com a URL da pagina de configuracao no wp-admin.

### 5.4 `config/categories.json`

Categorias por nicho:

```json
{
  "tecnologia": ["Hardware", "Software", "Mobile"],
  "imoveis":    ["Comprar", "Alugar", "Mercado"]
}
```

### 5.5 `config/pages.json`

Paginas institucionais padrao criadas em todo portal:

```json
[
  { "slug": "inicio",        "titulo": "Inicio",        "conteudo": "..." },
  { "slug": "sobre",         "titulo": "Sobre {portal}", "conteudo": "..." },
  { "slug": "contato",       "titulo": "Contato",       "conteudo": "..." },
  { "slug": "politica",      "titulo": "Politica de Privacidade", "conteudo": "..." }
]
```

Placeholders `{portal}` e `{nicho}` sao substituidos pela funcao
`aplicar_placeholders` (utils.py).

---

## 6. Schema do Site Profile

Cada arquivo em `config/sites/<slug>.json` segue este schema. Veja
exemplo completo em `config/sites/example.json`.

```json
{
  "profile": {
    "slug":        "meusite",
    "version":     "1.0.0",
    "description": "Profile do meu portal"
  },
  "portal": {
    "name":     "Meu Site",
    "domain":   "https://meusite.com.br",
    "niche":    "tecnologia",
    "language": "pt-BR",
    "timezone": "America/Sao_Paulo"
  },
  "wordpress": {
    "url":                 "https://meusite.com.br",
    "admin_user":          "admin",
    "application_password": "",
    "wp_path":             "/home/site/htdocs/meusite.com.br",
    "wp_cli_path":         "/usr/local/bin/wp"
  },
  "ssh": {
    "host":        "1.2.3.4",
    "port":        22,
    "user":        "root",
    "auth_method": "password",
    "password":    "",
    "key_path":    ""
  },
  "seo": {
    "site_title":          "Meu Site",
    "tagline":             "Subtitulo curto",
    "permalink_structure": "/%postname%/",
    "blog_public":         true,
    "comments_enabled":    false,
    "ping_status":         false,
    "rank_math":           true,
    "instant_indexing":    true
  },
  "plugins": {
    "required": ["seo-by-rank-math", "instant-indexing", "classic-editor"],
    "optional": ["redis-cache"],
    "skip":     []
  },
  "content": {
    "create_pages":      true,
    "create_categories": true,
    "create_test_post":  true,
    "homepage_slug":     "inicio"
  },
  "report": {
    "generate_markdown":            true,
    "include_manual_pending_tasks": true
  }
}
```

### Campos sensiveis (NUNCA persistidos)

`save_site_profile` zera **antes de gravar**:

- `wordpress.application_password`
- `ssh.password`
- `ssh.key_path`

Esses valores so existem em runtime — formulario, `.env` ou parametro
`overrides` do endpoint `/api/setup-from-profile`.

---

## 7. Walkthrough dos arquivos Python

Para cada modulo abaixo, listo o **proposito**, as **funcoes/classes
publicas** e o **proposito de cada uma**.

### 7.1 `app.py`

**Proposito:** ponto de entrada Flask. Carrega `.env`, instancia logger,
registra todas as rotas, valida payloads e delega trabalho para
`provisioner/tasks.py`.

#### Helpers internos

| Funcao | O que faz |
|--------|-----------|
| `_payload_para_cfg(payload)` | Converte o JSON plano vindo do formulario em `cfg` (dicionario com chaves `wp_url`, `ssh_host`, etc.) que `tasks.py` consome. |
| `_opcionais(payload)` | Extrai a lista `opcionais` (plugins extras marcados no modo manual). |
| `_erro_json(msg, status_http=400)` | Helper para resposta JSON de erro padronizada. |
| `_executar(handler, payload)` | Wrapper que captura excecoes do handler e devolve JSON `{status:"erro"}` em caso de falha. |
| `_profile_do_payload(payload)` | Aceita payload **achatado** (`profile_slug`, `portal_name`, ...) ou **aninhado** (`profile`, `portal`, ...) e retorna sempre o profile no schema oficial (chama `build_profile_from_payload` quando achatado). |

#### Rotas

| Metodo | Rota                          | Handler                       |
|--------|-------------------------------|-------------------------------|
| GET    | `/`                           | `index()` — renderiza `index.html` com nichos, plugins opcionais e env atual |
| POST   | `/api/testar_ssh`             | `api_testar_ssh()`            |
| POST   | `/api/testar_rest`            | `api_testar_rest()`           |
| POST   | `/api/validar_wp`             | `api_validar_wp()`            |
| POST   | `/api/validar_wpcli`          | `api_validar_wpcli()`         |
| POST   | `/api/verificar_redis`        | `api_verificar_redis()`       |
| POST   | `/api/instalar_plugins`       | `api_instalar_plugins()`      |
| POST   | `/api/configurar_wp`          | `api_configurar_wp()`         |
| POST   | `/api/criar_categorias`       | `api_criar_categorias()`      |
| POST   | `/api/criar_paginas`          | `api_criar_paginas()`         |
| POST   | `/api/criar_conteudo`         | `api_criar_conteudo()`        |
| POST   | `/api/setup_completo`         | `api_setup_completo()`        |
| POST   | `/api/gerar_relatorio`        | `api_gerar_relatorio()`       |
| GET    | `/api/site-profiles`          | `api_site_profiles()` — lista profiles em `config/sites/` |
| POST   | `/api/load-site-profile`      | `api_load_site_profile()` — le um profile, sanitiza e devolve |
| POST   | `/api/setup-from-profile`     | `api_setup_from_profile()` — roda setup pelo profile + `steps` |
| POST   | `/api/validate-site-profile`  | `api_validate_site_profile()` — valida payload contra o schema |
| POST   | `/api/save-site-profile`      | `api_save_site_profile()` — grava em `config/sites/<slug>.json` |
| POST   | `/api/delete-site-profile`    | `api_delete_site_profile()` — remove arquivo (`example` protegido) |

Detalhes completos de payloads/responses em
[Endpoints HTTP](#9-endpoints-http--referencia-completa).

---

### 7.2 `provisioner/__init__.py`

Vazio. Apenas marca a pasta como pacote Python.

---

### 7.3 `provisioner/logger.py`

**Proposito:** logger unico, reutilizavel, com **dois handlers** (stdout
+ arquivo timestamped em `logs/peg_<timestamp>.log`).

| Simbolo | O que faz |
|---------|-----------|
| `_resolve_level(level_name)` | Converte string ("DEBUG", "INFO"…) para constante `logging.*`. |
| `_logs_dir()` | Garante que `logs/` exista; retorna `Path`. |
| `get_logger()` | Retorna o logger singleton ja configurado com handlers stdout + arquivo. Idempotente (nao adiciona handlers em chamadas repetidas). |
| `get_log_file_path()` | Retorna o caminho do arquivo de log atual (ou `None`). |
| `log_credencial_segura(_valor)` | Helper para mascarar credenciais — sempre devolve `"****"`. Use ao logar valores sensiveis. |

Formato: `[YYYY-MM-DD HH:MM:SS] [NIVEL] mensagem`.

---

### 7.4 `provisioner/ssh_client.py`

**Proposito:** abstrair Paramiko. Conecta via senha **ou** chave privada
(mutuamente exclusivos), executa comandos remotos, fecha conexao com
seguranca.

| Funcao | O que faz |
|--------|-----------|
| `_carregar_chave(key_path)` | Tenta carregar chave RSA, depois ED25519, depois ECDSA. Levanta `ValueError` se nao for nenhuma. **Nao suporta passphrase.** |
| `conectar(host, port, user, auth_method, password, key_path, timeout)` | Abre uma `SSHClient` Paramiko. Valida que **so um** entre `password` e `key_path` foi fornecido (`auth_method` decide qual). Devolve o client conectado. |
| `executar(client, comando, timeout=60)` | Executa um comando, captura `stdout`, `stderr`, `exit_status`. Devolve `{"stdout","stderr","exit_status","ok"}`. |
| `fechar(client)` | Fecha a conexao; ignora `None` e excecoes. |
| `testar_conexao(host, port, user, ...)` | Conecta + executa `whoami` + fecha. Retorna `{status, message}` para a etapa 1. |

Toda log de comando passa por `get_logger()`. Senhas e chaves nunca
aparecem no log — so o nome do metodo e o host.

---

### 7.5 `provisioner/wpcli.py`

**Proposito:** wrapper em torno do binario `wp` rodando via SSH no VPS.
Cada metodo monta um comando WP-CLI, executa pelo `ssh_client.executar`,
faz parse do output (texto ou JSON) e devolve dict padronizado.

#### Classe `WPCLI`

| Metodo | O que faz |
|--------|-----------|
| `__init__(client, wp_path, wp_cli_path)` | Guarda referencias ao SSH client, ao caminho do WP no VPS e ao binario `wp`. |
| `_build_cmd(args, json_output)` | Monta a string `wp <args> --path=<wp_path> [--format=json]`. |
| `_run(comando, timeout=90)` | Chama `ssh_client.executar`. Loga o comando (sem dados sensiveis). |
| `_safe_json_loads(texto)` | `json.loads` defensivo — devolve `None` se nao parsear. |
| `verificar_wpcli()` | `wp --info` — confirma que o binario existe e versao do WP-CLI. |
| `verificar_wp()` | `wp core version --extra` — confirma que ha um WP instalado em `wp_path`. Retorna versao + URL. |
| `verificar_redis()` | `wp redis status` (se plugin Redis Object Cache estiver presente) — opcional, devolve aviso se nao instalado. |
| `listar_plugins_ativos()` | `wp plugin list --status=active --format=json`. |
| `instalar_plugin(slug)` | `wp plugin install <slug>`. Idempotente: se ja instalado, retorna ok. |
| `ativar_plugin(slug)` | `wp plugin activate <slug>`. |
| `instalar_e_ativar(slug)` | Combina os dois acima; usado por `acao_instalar_plugins`. |
| `atualizar_opcao(key, value)` | `wp option update <key> <value>` — usa `--format=json` se valor for dict/list. |
| `configurar_permalink(estrutura)` | `wp rewrite structure '<estrutura>' --hard`. |
| `flush_rewrite()` | `wp rewrite flush --hard`. |
| `flush_cache()` | `wp cache flush`. |

---

### 7.6 `provisioner/wp_rest.py`

**Proposito:** cliente HTTP para a REST API do WordPress
(`/wp-json/wp/v2/`). Usado para criar conteudo (categorias, paginas,
posts) sem precisar entrar no admin.

#### Funcoes-modulo

| Funcao | O que faz |
|--------|-----------|
| `_normalizar_app_password(senha)` | Remove espacos extras da Application Password. |
| `_validar_app_password(senha)` | Verifica formato `xxxx xxxx xxxx xxxx xxxx xxxx`. Devolve `(bool, motivo)`. |

#### Classe `WPRest`

| Metodo | O que faz |
|--------|-----------|
| `__init__(wp_url, wp_user, app_password)` | Valida e normaliza credenciais. Configura HTTP Basic Auth. |
| `_check_auth()` | Devolve dict de erro se faltam credenciais; `None` se ok. |
| `_url(caminho)` | Concatena `wp_url + /wp-json/wp/v2/ + caminho`. |
| `_request(metodo, caminho, json=None, params=None, timeout=20)` | Executa request com auth, trata 4xx/5xx, devolve JSON parseado ou `{"erro": ...}`. |
| `testar_api()` | `GET /users/me` — confirma que credenciais funcionam e usuario tem permissoes. |
| `listar_categorias()` | `GET /categories?per_page=100`. |
| `categoria_existe(slug)` | True se ja ha categoria com aquele slug. |
| `criar_categoria(nome, slug=None, descricao=None)` | `POST /categories`. Idempotente: se ja existe, devolve ok. |
| `listar_paginas()` | `GET /pages?per_page=100&status=publish,draft`. |
| `pagina_existe(slug)` | True/False. |
| `buscar_pagina_por_slug(slug)` | Devolve dict da pagina (com `id`) ou `None`. |
| `criar_pagina(titulo, slug, conteudo, status="publish")` | `POST /pages`. Idempotente. |
| `criar_post(titulo, conteudo, slug=None, status="publish", categorias=None)` | `POST /posts`. |

---

### 7.7 `provisioner/utils.py`

**Proposito:** utilitarios cross-cutting — carga de JSONs do `config/`,
schema/CRUD de Site Profiles, geracao de relatorio Markdown.

#### Helpers de path

| Funcao | O que faz |
|--------|-----------|
| `base_dir()` | Diretorio raiz do projeto (`peg-portal-engine/`). |
| `config_dir()` | `<base>/config`. |
| `sites_dir()` | `<base>/config/sites`. Cria se nao existir. |
| `logs_dir()` | `<base>/logs`. Cria se nao existir. |

#### Carga de JSONs do `config/`

| Funcao | O que faz |
|--------|-----------|
| `carregar_json(caminho)` | `json.loads` defensivo com mensagem clara se o arquivo nao existir ou for invalido. |
| `carregar_niches()` | Le `config/niches.json`. |
| `carregar_plugins()` | Le `config/plugins.json`. |
| `carregar_categorias(nicho)` | Le `config/categories.json` e devolve a lista do nicho (ou `[]`). |
| `carregar_paginas()` | Le `config/pages.json`. |
| `aplicar_placeholders(texto, portal_name, niche)` | Substitui `{portal}` e `{nicho}` em strings de pagina. |

#### Site Profiles — leitura e validacao

| Funcao | O que faz |
|--------|-----------|
| `list_site_profiles()` | Varre `config/sites/*.json`, devolve lista de dicts `{slug, name, domain, version}`. |
| `load_site_profile(slug_or_path)` | Carrega um profile pelo slug (ou caminho absoluto). Levanta `FileNotFoundError` se nao existir. |
| `_get_path(d, *keys)` | Helper interno: `_get_path(prof, "portal", "name")`. |
| `validate_site_profile(profile)` | Verifica todos os campos obrigatorios do schema. Retorna `(bool, [erros])`. |
| `sanitize_site_profile(profile)` | Devolve copia do profile com sensiveis mascarados como `"****"`. Usado no `/api/load-site-profile` para nao trafegar senhas pelo wire (mesmo que ja sejam vazias). |
| `merge_profile_with_payload(profile, payload)` | Funde overrides do formulario sobre o profile (campos vazios nao sobrescrevem). |
| `profile_para_cfg(profile, opcionais_extras=None)` | Converte profile aninhado em `cfg` plano que `tasks.py` consome. |
| `extrair_profile_meta(profile)` | Devolve dict resumo `{slug, version, description, name, domain, niche}` para o relatorio. |

#### Site Profiles — escrita (CRUD)

| Funcao | O que faz |
|--------|-----------|
| `_to_bool(v, default)` | Coercao tolerante: aceita `True/False`, `"1"/"0"`, `"sim"/"nao"`, etc. |
| `_to_int(v, default)` | `int(v)` defensivo. |
| `_split_lista(v)` | Converte `"a,b\nc"` ou `["a","b"]` em `["a","b","c"]` (limpo, sem vazios). |
| `_slug_seguro(s)` | Sanitiza slug: minusculas, sem barras, sem espacos, so `[a-z0-9_-]`. |
| `build_profile_from_payload(payload)` | Recebe payload **achatado** do dashboard (`profile_slug`, `portal_name`, `seo_blog_public`, …) e devolve profile no schema oficial. Default `seo.site_title` = `portal.name` se vazio. |
| `save_site_profile(profile, *, overwrite=False)` | Valida (`validate_site_profile`), zera os 3 sensiveis, grava em `config/sites/<slug>.json` (indent=2, ensure_ascii=False). Devolve `{"status":"ok"|"exists"|"erro", "message", "path", "slug", "errors"}`. Status `"exists"` quando arquivo ja existe e `overwrite=False`. |
| `delete_site_profile(slug)` | Remove o arquivo. **Bloqueia** slugs em `PROFILES_PROTEGIDOS = {"example"}`. Devolve `{"status","message","path"}`. |

`PROFILES_PROTEGIDOS` (constante de modulo) garante que o profile de
demonstracao nunca seja apagado por engano.

#### Relatorio Markdown

| Funcao | O que faz |
|--------|-----------|
| `_check(b)` | Devolve `[x]` ou `[ ]` para listas Markdown. |
| `gerar_relatorio(contexto)` | Escreve `reports/relatorio_<timestamp>.md` com: portal, profile usado, **etapas executadas**, **etapas puladas**, status WP, plugins (ok/falhas), SEO, paginas e categorias criadas, pendencias manuais, erros e duracao. Retorna `Path` do arquivo. |

---

### 7.8 `provisioner/tasks.py`

**Proposito:** orquestracao. Cada acao do painel tem uma funcao
`acao_*(cfg)`. O `setup_completo(cfg, ..., step_flags)` encadeia 14
etapas com gating por flag.

#### Helpers de conexao

| Funcao | O que faz |
|--------|-----------|
| `_ssh_kwargs(cfg)` | Extrai os parametros de SSH do `cfg`. |
| `_abrir_ssh(cfg)` | `ssh_client.conectar(...)` com kwargs prontos. |
| `_abrir_wpcli(cfg, client)` | Instancia `WPCLI(client, wp_path, wp_cli_path)`. |
| `_abrir_rest(cfg)` | Instancia `WPRest(wp_url, wp_user, app_password)`. |
| `_resp(status, message, details=None)` | Constroi a resposta padrao `{status, message, details}`. |
| `_etapa(num, nome, status, detalhes)` | Constroi o item da lista de etapas no relatorio. |

#### Acoes individuais (uma por botao)

| Funcao | Etapa(s) | O que faz |
|--------|----------|-----------|
| `acao_testar_ssh(cfg)` | 1 | Conecta SSH, roda `whoami`, fecha. |
| `acao_testar_rest(cfg)` | 9 | `WPRest.testar_api()`. |
| `acao_validar_wp(cfg)` | 2 | `WPCLI.verificar_wp()` — versao + URL. |
| `acao_validar_wpcli(cfg)` | 3 | `WPCLI.verificar_wpcli()` — versao do binario. |
| `acao_verificar_redis(cfg)` | 4 | `WPCLI.verificar_redis()` — opcional. |
| `acao_instalar_plugins(cfg, opcionais_extras, pular_plugins)` | 5-6 | Le `plugins.json`, instala obrigatorios + opcionais marcados, ignora `pular`. Devolve `{sucesso:[...], falhas:[...]}`. |
| `acao_configurar_wordpress(cfg)` | 7 | Aplica `permalink_structure`, `blog_public`, `default_comment_status`, `default_ping_status`, `timezone_string`, `wp_lang`. |
| `acao_criar_categorias(cfg)` | 10 | Le `categories.json` para o nicho, cria via REST. |
| `acao_criar_paginas(cfg)` | 11 | Le `pages.json`, aplica placeholders, cria via REST. |
| `acao_criar_conteudo_inicial(cfg)` | 12 | Cria post de teste "Bem-vindo ao <portal>". |
| `acao_gerar_relatorio(cfg, contexto_extra=None)` | 14 | Reune o `cfg` em `contexto` minimo e chama `gerar_relatorio`. |

#### Setup completo

| Funcao | O que faz |
|--------|-----------|
| `_normalize_step_flags(step_flags, content_flags)` | Funde flags do dashboard + flags legadas (`content_flags`) com `_STEP_FLAGS_DEFAULT` (todos `True`). |
| `acao_criar_usuarios(cfg)` | Le `cfg["users"]` e cria cada usuario via `wp user create` (idempotente — usuarios existentes por login OU email sao mantidos). Aceita `{login,email,role?,password?,display_name?}`. |
| `setup_completo(cfg, opcionais_extras=None, pular_plugins=None, content_flags=None, profile_meta=None, step_flags=None)` | Orquestra todas as 15 etapas. Cada etapa:<br>1. Verifica a flag correspondente.<br>2. Se desligada, registra `_etapa(..., "aviso", "desativado pela flag…")` e adiciona a `etapas_puladas`.<br>3. Se ligada, executa a `acao_*` e adiciona a `etapas_executadas`.<br>4. Erros nao criticos viram avisos; erros criticos (SSH/WP invalidos) abortam.<br>Devolve `{"status","message","details":{etapas, contexto_relatorio, relatorio_path}}`. |
| `_finalizar(cfg, contexto_relatorio, etapas, erros, inicio, critico, generate_report=True)` | Calcula duracao, anexa erros, e (se `generate_report=True`) chama `gerar_relatorio` (etapa 15). |

`_STEP_FLAGS_DEFAULT` (constante):

```python
{
  "install_plugins":   True,
  "configure_wp":      True,
  "apply_seo":         True,
  "create_users":      True,   # NEW (etapa 12)
  "create_pages":      True,
  "create_categories": True,
  "create_test_post":  True,
  "generate_report":   True,
}
```

**Ordem das 15 etapas:** 1=SSH, 2=Validar WP, 3=WP-CLI, 4=Redis, 5-6=Plugins,
7=Configurar WP, 8=SEO base, 9=REST, 10=Categorias, 11=Paginas, 12=Usuarios,
13=Conteudo inicial, 14=Flush rewrite/cache, 15=Relatorio.

**Conteudo inline:** se `cfg["pages_inline"]`, `cfg["categories_inline"]` ou
`cfg["posts_inline"]` forem listas nao-vazias, as acoes `acao_criar_paginas`,
`acao_criar_categorias` e `acao_criar_conteudo_inicial` usam essas listas em
vez de ler `pages.json` / `categories.json` / criar 1 post fixo.

---

### 7.9 Endpoint `POST /api/upload-and-run` (novo)

Caminho rapido: o usuario sobe **um unico JSON** com TUDO preenchido
(credenciais, usuarios, paginas, categorias, posts, etapas) e o setup roda
imediatamente, sem persistir nada em disco.

- Aceita `multipart/form-data` com arquivo `profile_file` OU `application/json`
  com o profile no corpo.
- Valida via `validate_site_profile`, exige `wordpress.application_password`
  e `ssh.password`/`ssh.key_path` preenchidos no JSON.
- Honra automaticamente `profile.steps` para selecionar etapas.
- Resposta identica a `/api/setup-from-profile`, com `details.origem="upload-and-run"`.

Bloco `users[]` no profile (cada item):
```json
{"login": "editor1", "email": "ed@x.com", "role": "editor",
 "password": "...", "display_name": "Editor"}
```

Bloco `steps` no profile (chaves opcionais, todas booleanas):
```json
{"install_plugins": true, "configure_wp": true, "apply_seo": true,
 "create_users": true, "create_categories": true, "create_pages": true,
 "create_test_post": true, "generate_report": true}
```

Bloco `content.{pages,categories,posts}_inline` no profile: listas opcionais
que substituem os JSONs estaticos quando preenchidas.

**Seguranca:** `users[*].password` e listado em `_SENSIVEIS_LISTAS` —
`save_site_profile` zera essas senhas antes de gravar e
`sanitize_site_profile` mascara como `****`.

---

## 8. Frontend: HTML, CSS e JavaScript

### 8.1 `templates/index.html`

Pagina unica, layout em duas colunas (Bootstrap 5 via CDN):

- **Coluna esquerda — formulario de Configuracao** com secoes:
  Profile, Portal, WordPress, SSH, VPS/WP-CLI, SEO, Plugins (3
  textareas + checkboxes legados), Conteudo, Relatorio.
- **Coluna direita — Acoes manuais** (12 botoes, cada um com
  `data-action="<nome>"`) + **Log de execucao** preto.
- **Card "Gerenciar Portal / Profile"** no topo da esquerda, com:
  select de profiles, botoes Novo / Carregar / Validar / Salvar /
  Excluir / Rodar setup, e 7 checkboxes de **Etapas a executar no
  setup**.

Variaveis Jinja2 usadas (passadas por `app.index()`):

- `niches` — lista de nichos para o `<select>`.
- `plugins_opcionais` — lista de plugins nao-obrigatorios (modo manual).
- `env` — dict com defaults vindos do `.env`.

### 8.2 `static/style.css`

17 linhas. Cores das classes de log:

- `.log-info` (cinza claro)
- `.log-meta` (azul)
- `.log-ok` (verde)
- `.log-aviso` (amarelo)
- `.log-erro` (vermelho)
- `.log-muted` (cinza escuro, para JSON expandido)

### 8.3 `static/app.js`

Tudo em vanilla JS dentro de uma IIFE. Sem framework, sem build step.

#### Constantes / mapeamentos

- `ENDPOINTS` — mapa `acao -> rota`.
- `TITULOS` — mapa `acao -> titulo amigavel para o log`.
- `STEP_FIELDS` — pares `[flag_backend, name_input]` para os 7 checkboxes.
- `MASCARA_SENSIVEL = "****"` — usada para detectar e nao restaurar valores mascarados vindos do servidor.

#### Helpers de UI

| Funcao | O que faz |
|--------|-----------|
| `ts()` | Timestamp HH:MM:SS para o log. |
| `escapeHtml(s)` | Escape de HTML basico. |
| `appendLog(text, classe)` | Adiciona linha colorida ao `<pre id="log-area">`. |
| `statusClasse(status)` | Mapeia `ok/aviso/erro/exists` -> classe CSS do log. |
| `setBusy(busy)` | Desabilita/habilita botoes durante uma chamada. |
| `getVal(name)` / `getCheck(name)` / `setVal(name,v)` / `setCheck(name,v)` / `setSelect(name,v)` / `setValSafe(name,v)` | Acesso tipado ao formulario. `setValSafe` ignora a string `"****"` para nao restaurar mascaras. |
| `listToTextarea(arr)` | `["a","b"]` -> `"a\nb"`. |

#### Coleta de payloads

| Funcao | O que faz |
|--------|-----------|
| `coletarPayload()` | Payload achatado para os endpoints **legados** (`/api/testar_ssh`, `/api/setup_completo`, etc.). |
| `coletarStepFlags()` | Le os 7 checkboxes e devolve o dict `{install_plugins, configure_wp, ...}`. |
| `coletarProfilePayload()` | Payload achatado completo para `build_profile_from_payload` (inclui SEO, plugins, content, report). |
| `coletarOverridesProfile()` | Apenas os campos preenchidos (sensiveis + ajustes) que sobrescrevem o profile salvo no `/api/setup-from-profile`. |
| `aplicarProfileNoForm(profile)` | Recebe profile aninhado e popula **todos** os campos do formulario (exceto sensiveis). |

#### Acoes do dashboard de profiles

| Funcao | Botao | O que faz |
|--------|-------|-----------|
| `carregarListaProfiles(silencioso)` | (auto + recarregar) | `GET /api/site-profiles` e popula o `<select>`. |
| `novoProfile()` | Novo profile | Reseta o formulario, marca defaults, limpa selecao. |
| `carregarProfileSelecionado()` | Carregar | `POST /api/load-site-profile` com `slug`. |
| `validarProfile()` | Validar | `POST /api/validate-site-profile` com payload do form. |
| `_salvarRequest(payload, overwrite)` | (interno) | Helper de fetch para `/api/save-site-profile`. |
| `salvarProfile()` | Salvar profile | Chama save com `overwrite:false`. Se o servidor responder `status:"exists"`, `confirm()` no usuario e re-chama com `overwrite:true`. Em sucesso, recarrega a lista e re-seleciona o slug. |
| `excluirProfile()` | Excluir | `confirm()` + `POST /api/delete-site-profile`. |
| `rodarSetupPeloProfile()` | Rodar setup | Coleta steps, se houver alguma desligada faz `confirm()` listando quais. Envia `{slug, overrides, steps}` para `/api/setup-from-profile`. |

#### Acoes manuais

`executar(action)` faz `POST` para o endpoint correspondente com
`coletarPayload()` e exibe o resultado no log.

Bind: cada elemento `[data-action]` tem seu listener no DOMContentLoaded.

---

## 9. Endpoints HTTP — referencia completa

Formato de resposta padrao para todos os endpoints `/api/*`:

```json
{
  "status":  "ok | aviso | erro | exists",
  "message": "texto curto para o usuario",
  "details": { ... ou lista, ou null ... }
}
```

### 9.1 Acoes individuais (modo manual)

Todas aceitam o **mesmo payload** — o JSON achatado do formulario.

| Endpoint                  | O que executa                                  |
|---------------------------|------------------------------------------------|
| `POST /api/testar_ssh`    | `acao_testar_ssh`                              |
| `POST /api/testar_rest`   | `acao_testar_rest`                             |
| `POST /api/validar_wp`    | `acao_validar_wp`                              |
| `POST /api/validar_wpcli` | `acao_validar_wpcli`                           |
| `POST /api/verificar_redis` | `acao_verificar_redis`                       |
| `POST /api/instalar_plugins` | `acao_instalar_plugins(opcionais, [])`      |
| `POST /api/configurar_wp` | `acao_configurar_wordpress`                    |
| `POST /api/criar_categorias` | `acao_criar_categorias`                     |
| `POST /api/criar_paginas` | `acao_criar_paginas`                           |
| `POST /api/criar_conteudo` | `acao_criar_conteudo_inicial`                 |
| `POST /api/setup_completo` | `setup_completo(cfg, opcionais, [])`          |
| `POST /api/gerar_relatorio` | `acao_gerar_relatorio`                       |

### 9.2 Profiles

#### `GET /api/site-profiles`

```json
{ "profiles": [
  { "slug": "aeconomia", "name": "A Economia", "domain": "...", "version": "1.0.0" },
  ...
]}
```

#### `POST /api/load-site-profile`

Request:

```json
{ "slug": "aeconomia" }
```

Response:

```json
{
  "status":  "ok",
  "message": "Profile 'aeconomia' carregado.",
  "profile": { ...schema completo, com sensiveis = "****"... },
  "meta":    { "slug":"aeconomia", "version":"1.0.0", ... },
  "errors":  []
}
```

#### `POST /api/validate-site-profile`

Request: payload achatado **ou** profile aninhado.

Response:

```json
{
  "status": "ok | erro",
  "message": "Profile valido. | N erro(s) de validacao.",
  "details": {
    "valid":  true,
    "errors": ["wordpress.url ausente", ...],
    "profile": { ...sanitizado... }
  }
}
```

#### `POST /api/save-site-profile`

Request:

```json
{
  "profile_slug": "meusite",
  "portal_name":  "Meu Site",
  ...todos os campos achatados...
  "overwrite": false
}
```

(Tambem aceita payload aninhado em `{"profile_obj": {...}}` ou direto
`{"profile": {...}, "portal": {...}, ...}`.)

Responses:

- `200 OK` — `status:"ok"`, salvo com sucesso.
- `409 Conflict` — `status:"exists"`, `details.overwrite_required=true`. O
  painel pergunta antes de re-enviar com `overwrite:true`.
- `400 Bad Request` — `status:"erro"`, `details.errors` lista o que falta.

#### `POST /api/delete-site-profile`

Request: `{ "slug": "meusite" }`

Responses:

- `200 OK` — removido.
- `400` — slug invalido **ou** slug protegido (`example`) **ou** arquivo
  inexistente.

#### `POST /api/setup-from-profile`

Request:

```json
{
  "slug": "meusite",
  "overrides": {
    "wordpress": { "application_password": "xxxx xxxx xxxx xxxx xxxx xxxx" },
    "ssh":       { "password": "..." }
  },
  "steps": {
    "install_plugins":   true,
    "configure_wp":      true,
    "apply_seo":         true,
    "create_pages":      true,
    "create_categories": true,
    "create_test_post":  false,
    "generate_report":   true
  }
}
```

Response (mesmo do `/api/setup_completo`):

```json
{
  "status":  "ok | aviso | erro",
  "message": "Setup completo: 13 etapas (12 ok, 1 aviso) em 47s",
  "details": {
    "etapas": [ {"etapa":1, "nome":"Testar SSH", "status":"ok", "detalhes":"..."}, ... ],
    "relatorio_path": "/.../reports/relatorio_2026-04-27_18-30.md",
    "profile":  { "slug":"meusite", "name":"Meu Site", "version":"1.0.0" },
    "step_flags": { ...as flags efetivas usadas... }
  }
}
```

---

## 10. As 14 etapas do `setup_completo`

| #  | Nome                          | Componente                | Flag controladora |
|----|-------------------------------|---------------------------|-------------------|
| 1  | Testar SSH                    | `ssh_client`              | (sempre roda)     |
| 2  | Validar WordPress             | `wpcli.verificar_wp`      | (sempre)          |
| 3  | Validar WP-CLI                | `wpcli.verificar_wpcli`   | (sempre)          |
| 4  | Verificar Redis               | `wpcli.verificar_redis`   | (sempre, opc.)    |
| 5-6 | Instalar plugins (obrig+opc) | `acao_instalar_plugins`   | `install_plugins` |
| 7  | Configurar WordPress          | `acao_configurar_wordpress` | `configure_wp`  |
| 8  | SEO tecnico (base)            | inline                    | `apply_seo`       |
| 9  | Testar REST API               | `wp_rest.testar_api`      | (sempre)          |
| 10 | Criar categorias              | `acao_criar_categorias`   | `create_categories` |
| 11 | Criar paginas + homepage      | `acao_criar_paginas` + `wp.atualizar_opcao` | `create_pages` (homepage tambem precisa de `apply_seo`) |
| 12 | Criar conteudo inicial        | `acao_criar_conteudo_inicial` | `create_test_post` |
| 13 | Flush rewrite + cache         | `wpcli.flush_rewrite/cache` | (sempre)        |
| 14 | Gerar relatorio Markdown      | `gerar_relatorio`         | `generate_report` |

Etapas marcadas "(sempre)" nao sao gateadas por flags pois sao
**verificacoes baratas e nao destrutivas** ou pre-requisitos
operacionais (SSH, REST). Etapas 5-12 e 14 sao gateaveis.

---

## 11. Step flags — controle granular do setup

```python
_STEP_FLAGS_DEFAULT = {
  "install_plugins":   True,   # etapas 5-6
  "configure_wp":      True,   # etapa 7
  "apply_seo":         True,   # etapa 8 + homepage da etapa 11
  "create_pages":      True,   # etapa 11
  "create_categories": True,   # etapa 10
  "create_test_post":  True,   # etapa 12
  "generate_report":   True,   # etapa 14
}
```

Chegam ao backend de duas formas:

1. **Dashboard** — 7 checkboxes em "Etapas a executar no setup".
   `coletarStepFlags()` no JS monta o dict e envia em
   `setup-from-profile`.
2. **Programaticamente** — qualquer caller pode passar
   `step_flags={...}` direto para `tasks.setup_completo`.

Etapas desligadas:

- aparecem como `_etapa(num, nome, "aviso", "desativado pela flag X=false")`;
- entram em `contexto_relatorio["etapas_puladas"]`;
- sao listadas na secao **"Etapas puladas"** do relatorio Markdown.

Etapas ligadas e executadas entram em `etapas_executadas` e na secao
**"Etapas executadas"**.

---

## 12. Seguranca: sensiveis nunca persistidos

Tres campos nunca sao gravados em disco:

- `wordpress.application_password`
- `ssh.password`
- `ssh.key_path`

Garantias:

1. `save_site_profile(profile, ...)` **zera** esses campos numa copia
   profunda antes do `json.dump`. Mesmo que o caller envie credenciais,
   elas nunca chegam ao arquivo.
2. `sanitize_site_profile(profile)` substitui esses campos por `"****"`
   antes de devolver pelo `/api/load-site-profile`, evitando trafegar
   valores reais (mesmo que sejam vazios).
3. O frontend (`setValSafe`) detecta `"****"` e **nao restaura** no
   formulario — voce sempre precisa redigitar a credencial em runtime.
4. O logger nunca recebe a credencial: ha `log_credencial_segura()`
   helper que sempre devolve `"****"`.
5. Profiles em `config/sites/` podem ser commitados em git com seguranca
   — o `example.json` ja vem com esses campos vazios.

O profile `example` esta em `PROFILES_PROTEGIDOS = {"example"}` e
**nao pode ser excluido** pelo endpoint de delete.

---

## 13. Logs e relatorio Markdown

### Logs de runtime

- `logs/peg_<timestamp>.log` (UTF-8) e duplicado em **stdout**.
- Nivel via `LOG_LEVEL` no `.env` (`DEBUG/INFO/WARNING/ERROR`).
- Formato: `[2026-04-27 18:30:12] [INFO] [5-6/14] Plugins: ok — 8 instalados`.
- Cada acao tem prefixo de etapa quando faz parte do setup completo.

### Relatorio Markdown

Gerado em `reports/relatorio_<timestamp>.md` pela `gerar_relatorio()`.
Estrutura:

1. **Cabecalho** — portal, dominio, nicho, duracao, data.
2. **Profile utilizado** (se houver) — slug, versao, descricao.
3. **Etapas executadas** — checklist marcado.
4. **Etapas puladas** — checklist desmarcado.
5. **WordPress** — versao, URL, permalink.
6. **Plugins** — lista de ok + falhas com motivos.
7. **SEO** — flags aplicadas (permalink, indexacao, homepage).
8. **Categorias criadas / Paginas criadas** — listas.
9. **Pendencias manuais** — links wp-admin para plugins que precisam de
   configuracao manual (Rank Math, Instant Indexing, etc.).
10. **Erros** — lista crua dos erros nao-fatais por etapa.

---

## 14. Como rodar localmente

Pre-requisitos: Python 3.12+, Git, VS Code (recomendado).

```bash
# 1. clonar
git clone <repo>
cd peg-portal-engine

# 2. ambiente virtual
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # Linux/Mac

# 3. dependencias
pip install -r requirements.txt

# 4. variaveis de ambiente
copy .env.example .env           # Windows
# cp .env.example .env           # Linux/Mac
# editar .env com valores padrao do seu portal

# 5. rodar
python app.py
# -> http://127.0.0.1:5000
```

No painel:

- Modo manual: preencha o formulario, clique acoes individuais.
- Modo profile: selecione um `.json` em `config/sites/`, clique
  Carregar, complete senhas, clique Rodar setup.

Para criar profiles novos pelo painel: clique **Novo profile**,
preencha tudo, clique **Validar** (opcional) e **Salvar profile**.

---

## 15. Troubleshooting comum

| Sintoma | Causa provavel | Solucao |
|---------|----------------|---------|
| `auth_method='password' requer senha SSH` | Profile salvo sem senha (correto!), mas voce nao preencheu o campo no formulario antes de rodar. | Digite a senha no campo SSH password e clique Rodar setup novamente. |
| `Application Password do WordPress nao informada` | Mesmo problema acima, com a senha de aplicacao. | Preencha o campo e tente de novo. |
| `Profile invalido: ...` no Validar | Algum campo obrigatorio esta vazio (slug, name, niche, etc.). | Veja a lista de erros no log e preencha. |
| `Ja existe '<slug>.json'. Confirme sobrescrita.` | Voce tentou salvar um slug que ja tem arquivo. | O painel ja mostra um confirm. Aceite para sobrescrever. |
| `Profile 'example' e protegido e nao pode ser excluido.` | Por design. | Nao ha como deletar — esta na constante `PROFILES_PROTEGIDOS`. |
| `Erro ao executar wp ...` (exit_status != 0) | WP-CLI no VPS retornou erro. | Veja o `stderr` no log; teste o mesmo comando manualmente via SSH. |
| `REST nao disponivel — pulado` | Etapa 9 falhou (Application Password errada ou wp-json bloqueado). | Verifique a senha e que a REST API nao esta restrita por plugin de seguranca. |
| Plugins falham com `404` | Slug nao existe no repositorio do WordPress. | Confira o slug em wordpress.org/plugins/. |

---

## 16. Glossario

- **Site Profile / Profile** — arquivo JSON em `config/sites/<slug>.json`
  que descreve um portal completo.
- **`cfg`** — dicionario plano consumido por `tasks.py`. Nao confundir
  com profile (que e aninhado).
- **Step flag** — uma das 7 chaves booleanas que controlam quais etapas
  rodam.
- **Application Password** — senha gerada pelo WordPress em
  *Usuarios -> Perfil -> Application Passwords*, no formato
  `xxxx xxxx xxxx xxxx xxxx xxxx`.
- **WP-CLI** — binario `wp` no VPS, usado para configurar o WordPress
  via SSH sem entrar no admin.
- **Rank Math** — plugin de SEO que substitui o Yoast.
- **Instant Indexing** — plugin que pinga Google/Bing/IndexNow ao
  publicar conteudo.
- **PROFILES_PROTEGIDOS** — set em `utils.py` que lista slugs imunes a
  delete (`{"example"}`).

---

*Fim do manual.*
