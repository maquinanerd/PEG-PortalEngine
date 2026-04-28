# PEG Portal Engine — Documento Mestre

## 1. Resumo Executivo
O PEG Portal Engine é uma ferramenta automatizada de provisionamento e configuração de WordPress baseada em Python (Flask) e execução remota (Paramiko/SSH + REST API). Ele resolve o problema operacional e repetitivo de configurar "na mão" instalações limpas do WordPress, transformando-as em portais editoriais configurados, seguros e otimizados em questão de segundos. 

Ao eliminar a configuração manual de permalinks, criação de páginas essenciais (Sobre, Contato), categorias de nicho e instalação de plugins vitais (SEO, Cache, SMTP), o sistema escala a velocidade de go-to-market de novos portais, garantindo padronização rigorosa sem intervenção humana.

## 2. Papel Dentro do PEG Ecosystem
No PEG Ecosystem, o PEG Portal Engine é a **ponte** entre a infraestrutura "crua" e a operação editorial. Ele não cria o servidor, mas dá "vida e forma" à instalação vazia do WordPress.

A infraestrutura provisiona o WordPress (ex: via CloudPanel). Em seguida, o PEG Portal Engine acessa esse WordPress remotamente (via SSH usando WP-CLI e via HTTP usando REST API) para aplicar os profiles (ex: TheNerd, AEconomia). Com o portal devidamente "formatado" (plugins instalados, categorias certas e SEO on-page ajustado), ele fica pronto para receber a injeção automatizada de conteúdo do MN26, que por sua vez obtém pautas do RSSPRIME. 

**Fluxo de Vida Operacional:**
CloudPanel → WordPress limpo → PEG Portal Engine → Portal configurado → MN26 → Publicação → Indexação → Monetização

O futuro **dashboard central** usará a camada de API do PEG Portal Engine para verificar a saúde dos portais e injetar os "Site Profiles" diretamente, centralizando o comando.

## 3. Inventário Técnico Atual
Atualmente, o sistema conta com:
- **Backend/Framework**: Flask rodando rotas REST para orquestração.
- **Módulos Python Core**: 
  - `provisioner/ssh_client.py`: Camada de SSH com tratamento de retry.
  - `provisioner/wpcli.py`: Executor seguro (shlex) de comandos remotos do WP.
  - `provisioner/wp_rest.py`: Cliente autenticado para uso das Application Passwords (posts, pages, categories).
  - `provisioner/tasks.py`: O orquestrador de setups.
  - `provisioner/logger.py`: Logging formatado para stdout e arquivo seguro.
- **Camada de Configuração (JSON)**: `config/sites/*.json` (Profiles), `config/plugins.json` (Catálogo de plugins permitidos/obrigatórios), `config/niches.json`, `config/categories.json`.
- **Tarefas Automatizadas**: Teste SSH, Teste REST, Validação WP/WP-CLI, Check de Redis, Instalar/Ativar Plugins, Configurar SEO Base, Criar Páginas e Categorias, e Criar Usuários.
- **Relatórios**: Geração de logs do setup (`logs/relatorio_*.md`) com pendências manuais destacadas.

## 4. Arquitetura Atual
O sistema possui uma arquitetura _stateless_, modular e orientada a arquivos (JSON file-based), dividida em 5 camadas lógicas:
1. **Frontend / Dashboard**: Interface web servida por `app.py` (`templates/index.html` e `static/app.js`), que permite entrada de dados e envio de payloads REST.
2. **Backend / API (Flask)**: `app.py` gerencia o input, mescla dados preenchidos com os "Site Profiles" JSON em memória e chama os orquestradores.
3. **Orquestrador (`tasks.py`)**: Valida pré-requisitos, invoca cada etapa do provisionamento na ordem correta, agregando os retornos e mascarando possíveis falhas parciais (para não quebrar toda a execução).
4. **Camada de Transporte e Execução**:
   - **SSH/WP-CLI**: Para ações destrutivas ou em nível de root (instalar plugins, forçar clear-cache, rewrite flush). Usa Paramiko.
   - **REST API (Application Passwords)**: Para ações de criação de conteúdo puro (posts, tags, pages) com validação de regras de negócio do próprio WordPress.
5. **Logs & Relatórios**: Cada execução loga localmente na pasta `/logs/` e emite um arquivo final `.md` auditável. As senhas **nunca** são gravadas.

## 5. Fluxo Operacional Completo
Quando a execução (`/api/setup_completo`) é disparada, a seguinte máquina de estados acontece:

1. **01_validar_ssh**: Testa conexão bruta Paramiko. *Objetivo*: Garantir handshake TCP/SSH e auth. *Risco*: Timeout de firewall, auth key errada. **Crítica** (aborta se falhar).
2. **02_validar_wpcli**: Roda `wp --version`. *Objetivo*: Conferir se WP-CLI existe. *Risco*: Binário inexistente ou path errado. **Crítica**.
3. **03_validar_wordpress**: Roda `wp core version`. *Objetivo*: Garantir que a pasta alvo seja um WP. *Risco*: Caminho errado. **Crítica**.
4. **04_validar_rest_api**: *Esta etapa testa o payload da REST, embora na esteira da `tasks.py` ela atue validando a API antes de criar o conteúdo de páginas e posts.* *Objetivo*: Testar a Application Password. *Risco*: Senha inválida ou faltante. **Crítica para conteúdo**.
5. **05_configurar_core**: Via WP-CLI `option update`, configura timezone, blogname, comments=closed. *Objetivo*: Higienizar o core. *Risco*: Permissão de BD. **Não Crítica**.
6. **06_configurar_permalink**: Aplica estrutura `/%postname%/` e roda `rewrite flush`. *Objetivo*: SEO básico. *Risco*: `.htaccess` restrito no servidor. **Não Crítica**.
7. **07_instalar_plugins**: Lê `plugins.json` e instala obrigatórios+opcionais. *Objetivo*: Turbocharger do site. *Risco*: Repositório do WP.org cair, limite de disco. **Não Crítica** (vira Aviso e anota no log).
8. **08_criar_categorias**: Via REST, injeta a árvore de editorias. *Objetivo*: Estruturar a taxonomia. *Risco*: Conflito de slug. **Não Crítica**.
9. **09_criar_paginas**: Via REST, cria 'Sobre', 'Contato', etc. *Objetivo*: Institucional pronto. *Risco*: IDs/slugs duplicados. **Não Crítica**.
10. **10_criar_post_teste**: Via REST, publica post "draft". *Objetivo*: Validar pipeline. **Não Crítica**.
11. **11_gerar_relatorio**: Agrupa as etapas e gera um `relatorio_dominio_timestamp.md`. *Objetivo*: Auditoria final. **Não Crítica**.

## 6. Pontos Fortes
- **Segurança de Senhas**: A aplicação não persiste chaves (`application_password` e `ssh_password`) nos profiles JSON. Tudo roda apenas em memória.
- **Portabilidade & Ausência de Banco**: Pode ser compactada num zip e rodada em qualquer máquina sem dependência de MySQL/Postgres. O uso de JSONs garante reprodutibilidade.
- **Separação de Responsabilidades**: Foi extremamente bem pensada a divisão entre WP-CLI (para infra/plugins) e REST API (para conteúdo). Executar criação de posts via REST é mais limpo, e instalar plugins via CLI é mais rápido.
- **Segurança Operacional**: A utilização sistemática de `shlex.quote` em `wpcli.py` previne injeção de comandos Bash remotos via input mal-intencionado (Shell Injection).
- **Simplicidade (KISS)**: O painel em Flask atende exatamente a necessidade com rotas simples.

## 7. Fragilidades e Riscos
- **Timeout em Requisições Longas**: A rota `/api/setup_completo` retém a requisição HTTP. Um setup longo (baixando muitos plugins num servidor lento) pode resultar em erro HTTP 504 no browser, mesmo que o backend continue.
- **Ausência de Lock nos Profiles**: Edições simultâneas do mesmo profile JSON pelo dashboard sobreescreverão o dado sem verificação de concorrência.
- **Falta de Histórico Centralizado e Ausência de Fila**: Não há um agendador (`Celery`, `RQ`); tudo roda de forma síncrona, não mantendo uma fila recuperável em caso de queda local do Flask.
- **Falhas Parciais de Plugins sem Rollback**: Se um plugin falhar na ativação, ele fica inativo ou quebrado. Falta modo "Dry-Run" ou Rollback reverso.
- **Dependência Crítica do WP-CLI Remoto**: Se o provider de VPS alterar o path do binário do wp ou restringir sua execução, o processo inteiro é inutilizado.

## 8. Roadmap Técnico Priorizado

### Fase 1 — Hardening sem mudar arquitetura
- Tratamento de Timeout nos sockets SSH e timeout prolongado de REST requests.
- Fail-fast (Early Return) na autenticação REST antes de iniciar as longas etapas de SSH para plugins.
- Adicionar retry policies robustas nas instalações via WP-CLI.

### Fase 2 — Execução observável
- Salvar todos os retornos brutos em `/runs/` (relatório rico contendo não só os logs de warning mas a resposta do STDOUT inteiro para auditoria).

### Fase 3 — UX operacional
- Implementação de **Server-Sent Events (SSE)** ou WebSockets para feedback Real-time de progresso no dashboard ("Etapa 3 de 11: Instalando SEO Rank Math...").
- Dashboard interno para leitura e download retroativo de logs `.md`.

### Fase 4 — Profiles multi-nicho
- Arquitetar e armazenar os profiles mestre finais para as marcas do grupo: `thenerd.json`, `aeconomia.json`, `achouimovel.json`.
- Suporte para injeção customizada de links de menus já pré-configurados no profile.

### Fase 5 — Integração com o ecossistema
- Fornecimento automatizado de credenciais geradas para os motores **MN26** e **RSSPRIME**.
- Criação de endpoints Webhook de *health check* para que um dashboard centralizado global invoque os engines remotamente.

### Fase 6 — Escala e governança
- Migração opcional da persistência local para um banco **SQLite/Postgres**, suportando auditoria de quem modificou cada Site Profile (Logs de auditoria de usuário).
- RBAC (Role-Based Access Control) na interface local: Administradores validam Profiles, Estagiários apenas executam setups limitados.

## 9. Modelo Ideal de Profile JSON

```json
{
  "profile": {
    "site_name": "Portal the Nerd",
    "site_url": "https://thenerd.com.br",
    "language": "pt-BR",
    "timezone": "America/Sao_Paulo",
    "niche": "geek",
    "description": "Cultura pop, filmes, quadrinhos e tecnologia."
  },
  "infrastructure": {
    "wp_path": "/var/www/thenerd.com.br/htdocs"
  },
  "plugins": {
    "required": ["seo-by-rank-math", "redis-cache", "instant-indexing"],
    "optional": ["site-kit-by-google"]
  },
  "content": {
    "categories": [
      {"name": "Cinema", "slug": "cinema", "description": "Lançamentos e críticas"},
      {"name": "Tecnologia", "slug": "tecnologia", "description": "Hardware e reviews"}
    ],
    "pages": [
      {"title": "Sobre Nós", "slug": "sobre", "status": "publish"},
      {"title": "Termos de Uso", "slug": "termos", "status": "publish"}
    ],
    "editorial_pages": true,
    "legal_pages": true,
    "menus": [
      {"name": "Principal", "locations": ["primary"]}
    ],
    "default_author": "redacao"
  },
  "seo_settings": {
    "rank_math_settings": {"titles_and_meta": true, "sitemap": true},
    "analytics_pending": true
  },
  "report_config": {
    "generate_markdown": true,
    "include_manual_pending_tasks": true
  }
}
```

## 10. Modelo Ideal de Relatório de Execução

Um relatório em `.md` não deve ser apenas um dump de logs, mas sim um *Dossiê Operacional Auditável*.

**A Estrutura Ideal:**
- **Cabeçalho:** Data, Hora da Run, URL alvo, VPS Alvo.
- **Status da Run:** SUCESSO ABSOLUTO ou SUCESSO COM ALERTAS.
- **Tabela de Auditoria de Etapas:** Etapa | Status | Duração | Resumo da Resposta.
- **Diagnóstico Infra & Plugins:** Redis [Ativo/Inativo], Cache, e Tabela de Plugins Instalados x Plugins Falhos.
- **Criação de Conteúdo Base:** Quantidade de Categorias e Páginas inseridas na Base de Dados.
- **⚠️ Pendências Manuais Restantes:** Destaque em formato Check-Box para o Operador Humano atuar (Ex: `[ ] Configurar Wizard do Rank Math em wp-admin`, `[ ] Conectar Google Account`).
- **Ponto de Entrega (Handoff):** Orientações literais de repasse para a integração com o próximo nó do sistema.

## 11. Integração Futura com MN26
O PEG Portal Engine atua como a esteira de terraplanagem para receber a casa (o **MN26**).
- O Engine gerará **Usuários Editoriais de Aplicação** e gerenciará suas Application Passwords.
- Os *slugs* gerados antecipadamente nas etapas de categorias (8) deverão respeitar as definições de clusterização base do pipeline do MN26. Ex: O MN26 dispara post no slug `/tecnologia`, logo, o Engine garante a pré-existência desta taxonomia exata.
- Configurando o plugin Rank Math logo no início, assegura-se que os posts automáticos injetados pelo MN26 herdem Schemas JSON-LD formatados, habilitando tráfego orgânico via "Google Discover" ou "News" muito mais rápido.

## 12. Integração Futura com RSSPRIME
Sendo o RSSPRIME responsável por curadoria e agrupamento, a sintonia deve focar no *Topic Mapping*.
- Os Profiles JSON dos Portais importarão taxonomias correspondentes com as tags nativas filtradas pelo RSSPRIME na raiz. Se o RSSPRIME agrupa artigos do nicho imobiliário, os JSON profiles carregam slugs de categoria como `credito`, `arquitetura`.

## 13. Integração Futura com Dashboard Central
O *PEG Dashboard* tratará esta aplicação não mais como painel, mas sim como uma API invisível e poderosa.
- Exibirá graficamente o **Status de Provisionamento** dos portais em grid (Online, Failed, Provisioning...).
- Obterá do Engine as atualizações da **Saúde do WordPress** baseada em comandos nativos via SSH injetados pela rotina.
- Controlará num único plano visual as pendências operacionais em lote ("Nós temos 4 Portais onde o Setup do Mail SMTP ainda está pendente de intervenção humana").

## 14. Checklist de Produção

### Segurança
- [ ] Adicionar JWT/Basic Auth nas chamadas internas do Flask para que ele fique invisível se operado via web externa.
- [ ] Implementar leitura de `.pem` local via secrets management ou Docker Env sem depender de mount de arquivos vulneráveis na máquina do Operador.

### UX (Interface Operacional)
- [ ] Trocar requisição síncrona que congela o frontend por Server-Sent Events (SSE) reportando o Progresso Barra-a-Barra.

### Logs
- [ ] Arquivar os relatórios de execução diários em formato persistente (ex: push pra um S3/Bucket ou banco local com interface visual histórica).

### Perfomance & Testes
- [ ] Criação de testes TDD/Mockados testando resiliência ao timeout de rede do VPS via Github Actions na base de código.

## 15. Conclusão Executiva
Atualmente, o PEG Portal Engine é inegavelmente uma **Ferramenta Interna Madura e Operacional**. Ele se descolou de ser um mero script bash solto e atingiu um status profissional, provando sua arquitetura através das validações corretas (uso agnóstico de JSON, divisão CLI/REST, shlex).

**O que falta para se tornar o Núcleo Perfeito do Ecossistema PEG?**
Mudar a topologia da comunicação da UX. A ausência de execuções assíncronas observáveis em tempo real (congelar o input do usuário e devolver uma resposta gigante em HTTP no final do processamento SSH longo) é o gargalo limitador de sua escalabilidade multi-operador. Quando ele ganhar o modelo Assíncrono/Real-time e atuar como Worker de uma Fila central, ele estará preparado para operar não 10, mas 1.000 portais de maneira orquestrada.
