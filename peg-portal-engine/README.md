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

## Estrutura do projeto

```
peg-portal-engine/
├── app.py                    # painel Flask
├── requirements.txt
├── .env.example
├── README.md
├── config/
│   ├── plugins.json
│   ├── categories.json       # categorias por nicho
│   ├── pages.json            # paginas institucionais
│   └── niches.json
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
