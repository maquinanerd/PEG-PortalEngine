# PEG Portal Engine

Sistema local em Python para provisionar e configurar automaticamente
instalacoes WordPress ja criadas manualmente no CloudPanel.

O sistema **nao instala** WordPress. Ele transforma um WordPress recem-criado
em um portal editorial pronto para uso (plugins essenciais, paginas
institucionais, categorias por nicho, SEO tecnico e relatorio de pendencias).

---

## Pre-requisitos

- **Python 3.12+** instalado localmente (Windows, macOS ou Linux)
- **WP-CLI** ja instalado no VPS (geralmente em `/usr/local/bin/wp`)
- Acesso SSH ao VPS (senha **ou** chave privada)
- WordPress acessivel via HTTPS
- **Application Password** gerada em
  `WordPress -> Usuarios -> Perfil -> Senhas de aplicativo`
  (formato: `xxxx xxxx xxxx xxxx xxxx xxxx`, 24 caracteres alfanumericos)

---

## Instalacao (Windows + VS Code)

1. Clone ou copie esta pasta `peg-portal-engine/` para sua maquina.
2. Abra a pasta no VS Code.
3. Crie um virtualenv:
   ```bat
   python -m venv venv
   ```
4. Ative o virtualenv:
   ```bat
   venv\Scripts\activate
   ```
   No Linux/macOS:
   ```bash
   source venv/bin/activate
   ```
5. Instale as dependencias:
   ```bat
   pip install -r requirements.txt
   ```
6. Copie `.env.example` para `.env` e preencha com seus dados (opcional —
   tambem da para preencher pelo formulario web):
   ```bat
   copy .env.example .env
   ```
7. Rode o painel:
   ```bat
   python app.py
   ```
8. Acesse no navegador: http://127.0.0.1:5000

---

## Como usar

1. Preencha o formulario com:
   - Nome do portal, nicho e dominio
   - URL do WordPress, usuario e Application Password
   - Dados de SSH (host, porta, usuario, senha **ou** caminho da chave)
   - Caminho do WordPress no VPS (ex.: `/var/www/meusite/htdocs`)
   - Caminho do binario WP-CLI no VPS (padrao: `/usr/local/bin/wp`)

2. Use os botoes para validar cada peca:
   - **Testar SSH** — confirma acesso ao VPS
   - **Testar REST API** — confirma a Application Password
   - **Validar WordPress** — confere instalacao via WP-CLI
   - **Validar WP-CLI** — confere a versao
   - **Verificar Redis** — checa `redis-cli ping` no servidor

3. Provisionamento granular (opcional):
   - **Instalar plugins**, **Configurar WordPress**, **Criar categorias**,
     **Criar paginas**, **Criar conteudo inicial**

4. **Rodar setup completo** — executa as 14 etapas em sequencia e gera
   relatorio em `logs/relatorio_<dominio>_<timestamp>.md`.

---

## Usando Site Profiles JSON

Para evitar repreencher o formulario a cada portal, voce pode criar um
**Site Profile** por portal — um arquivo JSON declarativo dentro de
`config/sites/`.

### Onde criar

```
config/sites/
├── example.json       # template (duplique este)
├── aeconomia.json
├── thenerd.json
└── achouimovel.json
```

### Como criar um profile novo

1. Duplique `config/sites/example.json` com o nome do seu portal:
   ```bat
   copy config\sites\example.json config\sites\meusite.json
   ```
2. Edite os campos:
   - `profile.slug`, `profile.description`
   - `portal.name`, `portal.domain`, `portal.niche`
   - `wordpress.url`, `wordpress.admin_user`, `wordpress.wp_path`
   - `ssh.host`, `ssh.port`, `ssh.user`, `ssh.auth_method`
   - `seo.site_title`, `seo.tagline`
   - `plugins.required`, `plugins.optional`, `plugins.skip`
   - `content.create_pages`, `content.create_categories`,
     `content.create_test_post`

### Quais credenciais ficam fora do JSON

Por seguranca, deixe estes campos **vazios** no profile:

- `wordpress.application_password`
- `ssh.password`
- `ssh.key_path`

Voce preenche esses campos no painel a cada execucao. Eles ficam apenas
em memoria — nunca sao gravados no disco nem enviados de volta para o
frontend (sao mascarados como `****` em qualquer resposta).

### Como carregar e rodar pelo painel

1. Rode `python app.py` e abra <http://127.0.0.1:5000>.
2. No card **Profile JSON do Portal** (topo da coluna esquerda):
   - escolha o profile no select;
   - clique em **Carregar** — todos os campos do formulario sao preenchidos
     automaticamente, exceto as senhas;
   - preencha **SSH password** (ou `key_path`) e **Application Password**;
   - clique em **Rodar setup** para executar as 14 etapas direto pelo profile.
3. O relatorio final inclui uma secao "Profile utilizado" com slug,
   versao e configuracoes aplicadas.

### Modo manual continua funcionando

Os botoes antigos (Testar SSH, Validar WP, Setup completo, etc.) continuam
exatamente como antes. O suporte a profile e **adicional**, nao substitui
o modo manual.

---

## Dashboard de gerenciamento de profiles

O card **Gerenciar Portal / Profile** (topo da coluna esquerda) traz um CRUD
completo dos arquivos `config/sites/*.json`, sem banco de dados.

### Botoes

- **Novo profile** — limpa o formulario e prepara um profile em branco.
- **Carregar** — le o profile selecionado e preenche todos os campos do
  formulario (incluindo SEO, plugins, conteudo e relatorio). Senhas
  **nunca** sao restauradas — voce digita em runtime.
- **Validar** — envia o conteudo atual do formulario para
  `POST /api/validate-site-profile` e mostra erros de schema.
- **Salvar profile** — chama `POST /api/save-site-profile`. Se o arquivo
  ja existir, o painel pergunta antes de sobrescrever.
- **Excluir** — chama `POST /api/delete-site-profile` apos confirmacao.
  O profile `example` e protegido e nao pode ser removido.
- **Rodar setup** — chama `POST /api/setup-from-profile` enviando o
  dicionario de etapas (veja abaixo).

### Etapas controlaveis pelo dashboard

Os checkboxes **Etapas a executar no setup** controlam, por execucao:

| Flag                | Padrao | O que controla                          |
|---------------------|--------|------------------------------------------|
| `install_plugins`   | on     | etapas 5-6 (instalar plugins)            |
| `configure_wp`      | on     | etapa 7 (permalink, indexacao, opcoes)   |
| `apply_seo`         | on     | etapa 8 + definicao de homepage          |
| `create_pages`      | on     | etapa 11 (paginas institucionais)        |
| `create_categories` | on     | etapa 10 (categorias do nicho)           |
| `create_test_post`  | on     | etapa 12 (post de teste)                 |
| `generate_report`   | on     | etapa 14 (relatorio Markdown)            |

Etapas desligadas viram avisos no log e aparecem na secao
**"Etapas puladas"** do relatorio. Etapas executadas aparecem em
**"Etapas executadas"**.

### Sensiveis nunca persistidos

Antes de gravar em disco, `save_site_profile` **zera** sempre:

- `wordpress.application_password`
- `ssh.password`
- `ssh.key_path`

Os campos sensiveis ficam apenas em memoria (formulario / `.env`) e podem
ser passados via `overrides` no `setup-from-profile`.

---

## Estrutura do projeto

```
peg-portal-engine/
├── app.py                    # painel Flask
├── requirements.txt
├── .env.example
├── README.md
├── DOCUMENTACAO.md
├── config/
│   ├── plugins.json
│   ├── categories.json       # categorias por nicho
│   ├── pages.json            # paginas institucionais
│   ├── niches.json
│   └── sites/                # profiles por portal (JSON)
│       ├── example.json
│       ├── aeconomia.json
│       ├── thenerd.json
│       └── achouimovel.json
├── provisioner/
│   ├── ssh_client.py         # paramiko (senha ou chave)
│   ├── wpcli.py              # WP-CLI via SSH
│   ├── wp_rest.py            # REST API (Application Password)
│   ├── tasks.py              # orquestracao das 14 etapas
│   ├── logger.py             # logging em tela + arquivo
│   └── utils.py              # JSONs + relatorio Markdown
├── templates/index.html
├── static/{app.js, style.css}
└── logs/                     # logs e relatorios gerados em runtime
```

---

## Plugins instalados

Definidos em `config/plugins.json`. Os marcados como `obrigatorio: true` sao
sempre instalados e ativados:

- Rank Math SEO (precisa de wizard manual depois)
- Instant Indexing
- Classic Editor
- Redirection
- WP Super Cache
- WP Mail SMTP (precisa de configuracao SMTP manual)

Plugins opcionais (so se marcados no formulario):

- Redis Object Cache (so instala se `redis-cli ping` retornar `PONG`)
- Site Kit by Google (precisa de conexao manual com Google)

---

## Pendencias manuais conhecidas

Os plugins abaixo sao instalados/ativados, mas precisam de configuracao
manual no painel do WordPress:

- **Rank Math SEO** — completar wizard em
  `/wp-admin/admin.php?page=rank-math`
- **WP Mail SMTP** — configurar servidor de e-mail em
  `/wp-admin/admin.php?page=wp-mail-smtp`
- **Site Kit by Google** — conectar conta Google em
  `/wp-admin/admin.php?page=googlesitekit-splash`

Tudo isso aparece listado no relatorio final.

---

## Notas tecnicas

- **Portavel**: nao usa nada exclusivo do Replit; roda em qualquer maquina
  com Python 3.12+.
- **Sem banco de dados**: configuracoes via arquivos JSON.
- **Caminhos remotos** (no VPS) sao montados com `/` literal — nunca com
  `os.path.join` — para garantir compatibilidade com SSH a partir do Windows.
- **Caminhos locais** usam `pathlib.Path`.
- **Credenciais nunca aparecem nos logs ou no relatorio** (mascaradas via
  `log_credencial_segura`).
- Application Password e validada (24 caracteres alfanumericos) **antes**
  de qualquer requisicao REST.
- Categorias e paginas sao **deduplicadas por slug** antes de serem criadas.
- Cada comando WP-CLI usa caminho absoluto do binario, `--path={wp_path}`
  e `--allow-root` quando o usuario SSH for `root`.
