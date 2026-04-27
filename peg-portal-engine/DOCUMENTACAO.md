# PEG Portal Engine — Documentação

Documento explicativo do sistema: o que faz, como funciona por dentro,
quais decisões de arquitetura foram tomadas e como cada peça se conecta.

---

## 1. O que é o PEG Portal Engine

O **PEG Portal Engine** é um sistema **local** em Python que automatiza a
**configuração inicial** de um WordPress recém-instalado no CloudPanel,
transformando-o em um **portal editorial pronto para uso**.

Ele **não instala** o WordPress.
A instalação continua sendo feita manualmente no CloudPanel.
O PEG entra **depois disso** e cuida da parte chata e repetitiva:

- instalação e ativação dos plugins essenciais
- configuração das opções básicas do WordPress
- aplicação de SEO técnico
- criação das páginas institucionais
- criação das categorias do nicho escolhido
- criação de um post de teste
- geração de um relatório final em Markdown com tudo o que foi feito
  e o que ainda falta configurar manualmente

Tudo isso é controlado por um **painel web local** (Flask + Bootstrap 5)
que roda em `http://127.0.0.1:5000`.

---

## 2. Para que serve

O caso de uso típico é:

1. Você cria um novo site WordPress no CloudPanel (manualmente).
2. Abre o PEG Portal Engine no seu computador.
3. Preenche os dados (URL do WP, SSH do VPS, nicho, nome do portal etc.).
4. Clica em **"Rodar setup completo"**.
5. Em poucos minutos, o site já tem plugins instalados, páginas
   institucionais criadas, categorias do nicho prontas e um relatório
   listando exatamente o que foi feito e o que ainda precisa de
   intervenção humana (como o wizard do Rank Math).

A ideia é eliminar o trabalho repetitivo de configurar dezenas de
portais novos do zero, mantendo um padrão consistente entre todos eles.

---

## 3. Stack e dependências

| Camada           | Ferramenta                          |
|------------------|-------------------------------------|
| Linguagem        | Python 3.12+                        |
| Painel web       | Flask 3                             |
| SSH              | Paramiko                            |
| HTTP / REST      | Requests                            |
| Variáveis        | python-dotenv (`.env`)              |
| UI               | Bootstrap 5 (via CDN)               |
| Persistência     | **Nenhum BD** — apenas arquivos JSON |

**Sem banco de dados.** Toda a configuração estática vive em arquivos
JSON dentro de `config/`.

---

## 4. Estrutura de pastas

```
peg-portal-engine/
├── app.py                    # painel Flask + endpoints AJAX
├── requirements.txt
├── .env.example              # template das variáveis de ambiente
├── README.md                 # guia de instalação rápida
├── DOCUMENTACAO.md           # este arquivo
│
├── config/
│   ├── plugins.json          # lista de plugins (obrigatórios e opcionais)
│   ├── categories.json       # categorias por nicho
│   ├── pages.json            # páginas institucionais
│   └── niches.json           # nichos suportados
│
├── provisioner/
│   ├── __init__.py
│   ├── ssh_client.py         # camada SSH (Paramiko)
│   ├── wpcli.py              # camada WP-CLI (executada via SSH)
│   ├── wp_rest.py            # camada REST API (Application Password)
│   ├── tasks.py              # orquestrador das 14 etapas
│   ├── logger.py             # logger compartilhado
│   └── utils.py              # JSONs + relatório Markdown
│
├── templates/
│   └── index.html            # painel Bootstrap 5
│
├── static/
│   ├── app.js                # AJAX + log em tempo real
│   └── style.css
│
└── logs/                     # logs e relatórios gerados em runtime
```

Cada arquivo do `provisioner/` tem **uma responsabilidade única** e
pode ser usado isoladamente em testes ou scripts.

---

## 5. Como o sistema se comunica com o VPS e o WordPress

O PEG fala com o WordPress por **dois canais distintos**:

### 5.1 SSH + WP-CLI (`provisioner/ssh_client.py` + `provisioner/wpcli.py`)

Usado para tarefas que **precisam rodar dentro do servidor**:

- instalar e ativar plugins (`wp plugin install`, `wp plugin activate`)
- atualizar opções do WP (`wp option update`)
- definir homepage (`wp option update show_on_front`)
- regenerar permalinks (`wp rewrite flush`)
- limpar cache (`wp cache flush`)
- verificar disponibilidade do Redis (`redis-cli ping`)
- conferir versão do WordPress e do WP-CLI

A camada SSH suporta **dois modos mutuamente exclusivos**:

1. **Senha** — `SSH_PASSWORD` no `.env` ou no formulário.
2. **Chave privada** — `SSH_KEY_PATH` apontando para um `.pem`/`.ppk`
   no seu computador. Tenta `RSAKey`, depois `Ed25519Key`, `ECDSAKey`
   e `DSSKey`. Chaves protegidas por passphrase **não** são suportadas
   (pelo formulário) — o erro é avisado de forma clara.

A conexão tem **retry automático**: 3 tentativas com 5 segundos de
intervalo. Cada comando tem timeout configurável e nunca lança exceção
não tratada — sempre retorna `{stdout, stderr, exit_code}`.

#### Regras dos comandos WP-CLI

Todo comando WP-CLI é montado com:

- caminho **absoluto** do binário (ex.: `/usr/local/bin/wp`)
- `--path={WP_PATH}` apontando para a raiz do WordPress no VPS
- `--allow-root` adicionado **automaticamente** quando o usuário SSH é `root`
- `--format=json` para comandos que retornam dados (lista de plugins etc.)
- `--skip-themes --skip-plugins` em comandos de verificação (mais rápido)

### 5.2 REST API (`provisioner/wp_rest.py`)

Usado para tarefas que se beneficiam da API HTTP:

- criar páginas institucionais (`POST /wp/v2/pages`)
- criar categorias do nicho (`POST /wp/v2/categories`)
- criar post de teste (`POST /wp/v2/posts`)
- testar autenticação (`GET /wp/v2/users/me`)

Autenticação é feita com **HTTP Basic + Application Password**.
Antes de qualquer requisição, a senha é **validada**:

- espaços em excesso são removidos
- precisa ter **exatamente 24 caracteres alfanuméricos**

Se falhar a validação, **nenhuma requisição é feita** — o erro é
retornado imediatamente.

Antes de criar qualquer página ou categoria, o sistema **busca por slug**
e pula a criação se já existir. Esse comportamento garante que rodar o
setup duas vezes no mesmo site não cria duplicatas.

---

## 6. Configuração via JSON

### `config/niches.json`

Lista os nichos suportados pelo painel.

```json
{
  "opcoes": ["entretenimento", "financas", "imobiliario",
             "tecnologia", "automotivo", "saude",
             "economia", "esportes", "lifestyle"]
}
```

### `config/plugins.json`

Cada item descreve um plugin:

```json
{
  "slug": "seo-by-rank-math",
  "nome": "Rank Math SEO",
  "obrigatorio": true,
  "requer_config_manual": true
}
```

- `obrigatorio: true` → instalado e ativado **sempre** no setup completo.
- `obrigatorio: false` → só é instalado se você marcar o checkbox
  correspondente no painel.
- `requer_config_manual: true` → o plugin é instalado normalmente, mas
  aparece no relatório como **pendência de configuração manual**
  (ex.: Rank Math precisa do wizard).
- `requer_redis: true` → o plugin só é instalado se `redis-cli ping`
  retornar `PONG` no servidor. Caso contrário, vai para o relatório
  como falha com a justificativa "Redis não disponível".

### `config/categories.json`

Mapeia **categorias por nicho**. Cada nicho tem 4 categorias predefinidas
com nome, slug e descrição. Quando você escolhe um nicho no painel, só
as categorias daquele nicho são criadas.

### `config/pages.json`

Lista as 11 páginas institucionais padrão (Início, Sobre, Quem Somos,
Contato, Política de Privacidade, Termos de Uso, Política Editorial,
Expediente, Anuncie, Correções, Mapa do Site). O conteúdo aceita
placeholders:

- `{portal_name}` → substituído pelo nome do portal
- `{niche}` → substituído pelo nicho escolhido

A substituição acontece **em runtime**, antes de criar a página.

---

## 7. As 14 etapas do setup completo

Quando você clica em **"Rodar setup completo"**, o orquestrador
(`provisioner/tasks.py::setup_completo`) executa em ordem:

| # | Etapa                          | Falha aborta tudo? |
|---|--------------------------------|--------------------|
| 1 | Testar conexão SSH             | **Sim**            |
| 2 | Validar instalação WordPress   | **Sim**            |
| 3 | Validar WP-CLI                 | **Sim**            |
| 4 | Verificar Redis disponível     | Não (vira aviso)   |
| 5 | Instalar plugins obrigatórios  | Não                |
| 6 | Instalar `redis-cache` (se Redis) | Não             |
| 7 | Configurar opções do WP        | Não                |
| 8 | SEO técnico (permalink, indexação, homepage) | Não  |
| 9 | Testar REST API                | Não (mas pula 10–12) |
| 10 | Criar categorias do nicho     | Não                |
| 11 | Criar páginas institucionais  | Não                |
| 12 | Criar post de teste (rascunho) | Não               |
| 13 | Flush rewrite + cache         | Não                |
| 14 | Gerar relatório Markdown      | —                  |

Etapas não-críticas que falham viram **avisos**: o processo continua e
tudo é registrado no relatório final.

---

## 8. SEO técnico aplicado

Configurado via `wp option update`:

- `blogname` — título do site
- `blogdescription` — descrição base ("Portal de notícias sobre {niche}")
- `permalink_structure` — `/%postname%/`
- `blog_public` — `1` (indexação ativa)
- `timezone_string` — `America/Sao_Paulo`
- `date_format` / `time_format` — formato BR
- `default_comment_status` / `default_ping_status` — `closed`

Após criar a página "Início", o sistema também define:

- `show_on_front=page`
- `page_on_front=<id da página Início>`

O **wizard do Rank Math** não pode ser automatizado e fica registrado
como pendência manual no relatório, com link direto para
`/wp-admin/admin.php?page=rank-math`.

---

## 9. Painel web (Flask)

### Endereço

`http://127.0.0.1:5000`

### Layout

Coluna esquerda: formulário com todas as variáveis de configuração
(portal, WordPress, SSH, VPS, plugins opcionais).

Coluna direita: botões de ação agrupados em três blocos:

- **Validações** — Testar SSH, REST, WP, WP-CLI, Redis
- **Provisionamento granular** — instalar plugins, configurar WP,
  criar categorias, criar páginas, criar conteúdo
- **Tudo de uma vez** — Setup completo + Gerar relatório

Abaixo dos botões há uma **área de log preto/colorido** que recebe a
resposta de cada chamada AJAX em tempo real, sem reload da página.

### Endpoints

Cada botão dispara um POST `/api/<acao>` com o payload do formulário.
Toda resposta segue o mesmo formato:

```json
{
  "status": "ok | aviso | erro | exists",
  "message": "texto curto para o usuário",
  "details": { ... ou lista, ou null ... }
}
```

#### Endpoints do dashboard de profiles

| Método | Rota                          | Função                                     |
|--------|-------------------------------|--------------------------------------------|
| GET    | `/api/site-profiles`          | lista profiles existentes                  |
| POST   | `/api/load-site-profile`      | lê um profile pelo `slug`                  |
| POST   | `/api/validate-site-profile`  | valida payload (achatado ou aninhado)      |
| POST   | `/api/save-site-profile`      | persiste profile (HTTP 409 se já existir)  |
| POST   | `/api/delete-site-profile`    | remove profile (`example` é protegido)     |
| POST   | `/api/setup-from-profile`     | roda setup pelo profile + `steps` (flags)  |

`save-site-profile` aceita `{ overwrite: true|false }`. Quando o arquivo já
existe e `overwrite=false`, retorna `status="exists"` + HTTP 409 e
`details.overwrite_required=true`. O painel pergunta antes de sobrescrever.

`setup-from-profile` aceita um campo `steps` (dict) com as 7 flags abaixo
para gatear etapas em runtime sem editar o JSON:

```json
{
  "slug": "meusite",
  "overrides": { "wordpress": { "application_password": "..." } },
  "steps": {
    "install_plugins":   true,
    "configure_wp":      true,
    "apply_seo":         true,
    "create_pages":      true,
    "create_categories": true,
    "create_test_post":  true,
    "generate_report":   true
  }
}
```

Etapas desligadas viram avisos e aparecem na seção **"Etapas puladas"**
do relatório Markdown. Etapas executadas aparecem em
**"Etapas executadas"**.

#### Sensíveis nunca persistidos

`save_site_profile` zera, antes de gravar:

- `wordpress.application_password`
- `ssh.password`
- `ssh.key_path`

Esses três campos vivem apenas em memória (formulário, `.env`) e podem
ser injetados em runtime via `overrides` do `setup-from-profile`.

---

## 10. Logs e segurança

- **Logger duplo:** stdout (console) + arquivo `logs/peg_<timestamp>.log`.
- Nível configurável via `LOG_LEVEL` no `.env` (padrão `INFO`).
- Formato: `[YYYY-MM-DD HH:MM:SS] [NIVEL] mensagem`.
- **Credenciais nunca são logadas.** Senhas SSH, Application Passwords e
  caminhos de chaves não aparecem no log nem no relatório. Existe um
  helper `log_credencial_segura(valor)` que sempre retorna `"****"`.
- O comando WP-CLI é logado, mas argumentos sensíveis nunca são
  inseridos via comando (sempre via opção do WP).

---

## 11. Relatório final

Cada execução do setup gera um arquivo:

```
logs/relatorio_<dominio>_<timestamp>.md
```

O relatório inclui:

- **Cabeçalho:** portal, domínio, nicho, data e duração
- **WordPress:** versão, URL, permalink
- **Plugins instalados** (com checkboxes marcados)
- **Plugins com falha** e motivo (ex.: Redis indisponível)
- **Páginas criadas** com ID e marca de "já existia" quando aplicável
- **Categorias criadas** com a mesma lógica
- **SEO aplicado** (permalink, indexação, homepage)
- **Pendências de configuração manual** com link direto para o admin
- **Erros encontrados** com a etapa de origem
- **Próximos passos** sugeridos (tema, usuário editor, DNS/SSL, conteúdo)

---

## 12. Portabilidade

- **Não usa nada exclusivo do Replit.** Roda em Windows, macOS e Linux
  com qualquer Python 3.12+.
- **Caminhos locais:** sempre `pathlib.Path` (compatível com Windows).
- **Caminhos remotos no VPS:** sempre strings com `/` literal — nunca
  `os.path.join`, que quebraria ao rodar a partir do Windows.
- **Sem dependências nativas pesadas:** apenas Flask, Paramiko, Requests
  e python-dotenv.

---

## 13. Tratamento de erros

Toda função que faz I/O (SSH, HTTP, leitura de arquivo) tem try/except
explícito e nunca propaga exceção crua para o frontend. O painel sempre
recebe uma resposta JSON estruturada — mesmo quando o servidor está
fora do ar ou a senha é inválida.

A filosofia é: **errar barulhento, mas nunca silenciosamente.**

- SSH inválido → erro crítico, aborta o setup.
- WP/WP-CLI inválido → erro crítico, aborta o setup.
- Plugin individual falhou → log + entrada no relatório, continua.
- REST API fora do ar → pula etapas 10/11/12 mas ainda gera relatório.
- Categoria/página já existe → log "já existe", segue em frente.

---

## 14. Pré-requisitos no VPS

Para o sistema funcionar, o servidor precisa ter:

- WordPress instalado e acessível via HTTPS
- WP-CLI instalado (testado em `/usr/local/bin/wp`)
- Acesso SSH liberado (porta 22 ou outra) com senha **ou** chave RSA
- Permissões adequadas para o usuário SSH operar o WordPress
- Redis (opcional — só necessário se quiser usar `redis-cache`)
- Application Password gerada no WordPress
  (`Usuários → Perfil → Senhas de Aplicativo`)

---

## 15. Limites conhecidos

- **Não instala WordPress.** É premissa do projeto: WordPress já existe.
- **Não automatiza wizards de plugins** (Rank Math, WP Mail SMTP, Site Kit).
  São listados como pendências manuais no relatório.
- **Chaves SSH com passphrase não são suportadas** pelo formulário.
- **Não troca o tema nem cria usuário editor.** Aparece nos "próximos
  passos" do relatório como tarefa manual.
- **Não toca em DNS, SSL ou certificados.** Isso continua sendo
  responsabilidade do CloudPanel ou do administrador.

---

## 16. Como rodar localmente

Resumido (passo-a-passo completo no `README.md`):

```bat
cd peg-portal-engine
python -m venv venv
venv\Scripts\activate           :: Windows
pip install -r requirements.txt
copy .env.example .env          :: e edite .env, opcionalmente
python app.py
```

Abrir no navegador: <http://127.0.0.1:5000>.

---

## 17. Site Profiles JSON

Para padronizar e versionar a configuracao por portal, o sistema suporta
**Site Profiles**: arquivos JSON declarativos dentro de `config/sites/`,
um por portal. Cada profile contem todos os dados necessarios para
transformar uma instalacao WordPress em portal editorial.

### Conceito

- Um profile = **um portal**.
- O arquivo e versionavel (pode ir pro Git **sem** as senhas).
- Senhas e chaves **nao** ficam no JSON. Sao preenchidas no painel a cada
  execucao e ficam apenas em memoria.
- O modo manual continua funcionando exatamente como antes — profiles
  sao um modo opcional adicional.

### Schema completo

```json
{
  "profile": {
    "slug": "aeconomia",
    "version": "1.0.0",
    "description": "Profile do portal A Economia"
  },
  "portal": {
    "name": "A Economia",
    "domain": "https://aeconomia.online",
    "niche": "financas",
    "language": "pt-BR",
    "timezone": "America/Sao_Paulo"
  },
  "wordpress": {
    "url": "https://aeconomia.online",
    "admin_user": "editor_aeconomia",
    "application_password": "",
    "wp_path": "/home/aeconomia/htdocs/aeconomia.online",
    "wp_cli_path": "/usr/local/bin/wp"
  },
  "ssh": {
    "host": "000.000.000.000",
    "port": 22,
    "user": "aeconomia",
    "auth_method": "password",
    "password": "",
    "key_path": ""
  },
  "seo": {
    "site_title": "A Economia",
    "tagline": "Noticias sobre economia, financas e mercado",
    "permalink_structure": "/%postname%/",
    "blog_public": true,
    "comments_enabled": false,
    "ping_status": false,
    "rank_math": true,
    "instant_indexing": true
  },
  "plugins": {
    "required": ["seo-by-rank-math", "instant-indexing", "classic-editor"],
    "optional": ["redis-cache", "site-kit-by-google"],
    "skip": []
  },
  "content": {
    "create_pages": true,
    "create_categories": true,
    "create_test_post": true,
    "homepage_slug": "inicio"
  },
  "report": {
    "generate_markdown": true,
    "include_manual_pending_tasks": true
  }
}
```

### Campos obrigatorios

- `profile.slug`
- `portal.name`, `portal.domain`, `portal.niche`
- `wordpress.url`, `wordpress.admin_user`, `wordpress.wp_path`,
  `wordpress.wp_cli_path`
- `ssh.host`, `ssh.port`, `ssh.user`, `ssh.auth_method`
  (`password` ou `key`)
- `seo.site_title`, `seo.permalink_structure`

`portal.niche` precisa existir em `config/niches.json`. Se nao existir,
o erro de validacao mostra a lista de nichos disponiveis.

### Endpoints novos

| Metodo | Rota                       | Funcao                                                     |
|--------|----------------------------|------------------------------------------------------------|
| GET    | `/api/site-profiles`       | Lista profiles em `config/sites/` (sem credenciais)        |
| POST   | `/api/load-site-profile`   | Carrega 1 profile, valida e devolve sanitizado             |
| POST   | `/api/setup-from-profile`  | Roda o setup completo (14 etapas) usando profile + overrides |

Payloads:

```jsonc
// POST /api/load-site-profile
{ "slug": "aeconomia" }

// POST /api/setup-from-profile
{
  "slug": "aeconomia",
  "overrides": {
    "wordpress": { "application_password": "xxxx xxxx xxxx xxxx xxxx xxxx" },
    "ssh":       { "password": "minha-senha-ssh" }
  }
}
```

### Regras de seguranca

- `wordpress.application_password`, `ssh.password` e `ssh.key_path`
  **nunca** sao retornados em texto claro pelo `/api/load-site-profile`.
  Quando preenchidos no JSON, viram `****` na resposta.
- O frontend nao auto-preenche campos de senha mesmo que o profile tenha
  valor — o usuario sempre redigita no painel.
- Os arquivos de exemplo (`example.json`, `aeconomia.json`,
  `thenerd.json`, `achouimovel.json`) **nao** contem credenciais reais.
- Logs nao registram nenhum valor sensivel — o helper `extrair_profile_meta`
  garante que apenas dados nao-sensiveis (slug, nome, dominio, nicho,
  versao) cheguem ao log e ao relatorio.

### Fluxo operacional

1. Voce cria `config/sites/meusite.json` (duplique `example.json`).
2. Edita os campos do portal, WP, SSH, SEO, plugins e content.
3. Abre o painel em `http://127.0.0.1:5000`.
4. Escolhe o profile no select **"Profile JSON do Portal"**.
5. Clica em **Carregar** — formulario e preenchido (menos as senhas).
6. Preenche **SSH password** (ou `key_path`) e **Application Password**.
7. Clica em **Rodar setup** — as 14 etapas rodam usando o profile.
8. O relatorio gerado em `logs/` traz:
   - secao **"Profile utilizado"** (slug, nome, versao, dominio, nicho);
   - secao **"Configuracoes aplicadas via profile"** (SEO, plugins
     required/optional/skip, paginas, categorias, post de teste).

### Funcoes Python por tras dos endpoints

Em `provisioner/utils.py`:

- `list_site_profiles()` — varre `config/sites/`, devolve metadados seguros.
- `load_site_profile(slug_or_path)` — aceita slug ou caminho relativo.
- `validate_site_profile(profile)` — checa obrigatorios, tipos, URLs,
  booleans, listas e nicho.
- `sanitize_site_profile(profile)` — copia mascarando credenciais.
- `merge_profile_with_payload(profile, payload)` — mescla overrides do
  formulario; aceita payload aninhado (`{wordpress:{...}}`) ou achatado
  (`{wp_app_password:"..."}`).
- `profile_para_cfg(profile)` — achata o profile no `cfg` plano que as
  tasks atuais ja consomem.
- `extrair_profile_meta(profile)` — devolve so os dados nao-sensiveis
  para log e relatorio.

---

## 18. Resumo em uma linha

> **PEG Portal Engine = um botão "Tornar este WordPress em portal" para
> qualquer instalação WordPress que você acabou de criar no CloudPanel,
> com relatório no final dizendo o que foi feito e o que falta.**
