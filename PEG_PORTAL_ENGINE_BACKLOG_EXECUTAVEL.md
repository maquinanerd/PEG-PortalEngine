# PEG Portal Engine — Backlog Técnico Executável

Este backlog traduz a visão estratégica do PEG Portal Engine em tarefas técnicas executáveis, organizadas em 6 fases de evolução.

---

## FASE 1 — Hardening imediato
Tarefas urgentes de confiabilidade, evitando que operações falhem silenciosamente ou destruam profiles simultaneamente.

ID: PEG-PORTAL-001
TÍTULO: Configurar Timeout estrito para SSH e REST API
TIPO: HARDENING
PRIORIDADE: P0
CAMADA: SSH / REST API
ARQUIVOS PROVÁVEIS: `provisioner/ssh_client.py`, `provisioner/wp_rest.py`
PROBLEMA: Uma lentidão extrema no VPS de destino pode fazer a requisição HTTP ou SSH travar indefinidamente, derrubando a thread local do Flask.
AÇÃO: Implementar limites de tempo hard-coded explícitos (ex: 30s) tanto nas chamadas de `requests` quanto no socket do `paramiko`.
CRITÉRIO DE ACEITE: O sistema deve abortar conexões e retornar status de erro "Timeout" graciosamente se ultrapassar o limite, sem congelar a aplicação principal.
RISCO SE NÃO FIZER: Travamento em massa de threads no Flask e UX bloqueada.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Primeira tarefa.
PRIORIDADE DE EXECUÇÃO: FASE 1 — Hardening imediato

ID: PEG-PORTAL-002
TÍTULO: Implementar Fail-fast da REST API antes de etapas longas
TIPO: HARDENING
PRIORIDADE: P0
CAMADA: Tasks / Orquestrador
ARQUIVOS PROVÁVEIS: `provisioner/tasks.py`
PROBLEMA: O teste de credenciais da REST API só ocorre de fato (ou comanda parada na UX) tarde demais ou não trava o início das etapas que poderiam ser abortadas cedo.
AÇÃO: Mover a validação real de `Application Password` e autenticação REST para o começo absoluto do `setup_completo`. Se falhar, interromper imediatamente.
CRITÉRIO DE ACEITE: Uma senha REST incorreta aborta a execução inteira no passo 1 ou 2, antes de instalar 15 plugins via WP-CLI.
RISCO SE NÃO FIZER: Desperdício de minutos instalando plugins e configurando WP-CLI para no fim falhar na criação do conteúdo.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Após PEG-PORTAL-001.
PRIORIDADE DE EXECUÇÃO: FASE 1 — Hardening imediato

ID: PEG-PORTAL-003
TÍTULO: Adicionar Retry Policy robusta para WP-CLI
TIPO: HARDENING
PRIORIDADE: P1
CAMADA: WP-CLI
ARQUIVOS PROVÁVEIS: `provisioner/wpcli.py`
PROBLEMA: Instalar plugins via repo público (`wp plugin install`) falha frequentemente devido a oscilações da API do WordPress.org.
AÇÃO: Implementar bloco de retentativas (retry) de 3x com delay exponencial (ex: 5s, 10s) para o comando `instalar_e_ativar`.
CRITÉRIO DE ACEITE: Uma falha aleatória de download de plugin do WP tenta novamente e obtém sucesso na segunda vez, sem marcar como "falha definitiva".
RISCO SE NÃO FIZER: Configurações em lote são abortadas por timeouts externos intermitentes e o operador humano tem que fazer manualmente.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Independente.
PRIORIDADE DE EXECUÇÃO: FASE 1 — Hardening imediato

ID: PEG-PORTAL-004
TÍTULO: Criar File Lock na escrita de Profiles JSON
TIPO: SEGURANÇA
PRIORIDADE: P1
CAMADA: JSON Profiles
ARQUIVOS PROVÁVEIS: `provisioner/utils.py`, `app.py`
PROBLEMA: Dois operadores salvando ou editando o mesmo Profile JSON ao mesmo tempo via dashboard geram condição de corrida (Race Condition), corrompendo o arquivo.
AÇÃO: Implementar lib de lock (ex: `filelock`) ao sobrescrever arquivos `.json` em `config/sites`.
CRITÉRIO DE ACEITE: Teste de stress simultâneo na rota `/api/save-site-profile` garante que a escrita seja atômica.
RISCO SE NÃO FIZER: Corrupção do Profile JSON e perda de todo o template de configuração.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Independente.
PRIORIDADE DE EXECUÇÃO: FASE 1 — Hardening imediato

ID: PEG-PORTAL-005
TÍTULO: Validação forte de Schema dos Profiles JSON
TIPO: ARQUITETURA
PRIORIDADE: P2
CAMADA: JSON Profiles
ARQUIVOS PROVÁVEIS: `provisioner/utils.py`
PROBLEMA: Usuários podem imputar arrays em lugares de strings ou pular campos obrigatórios em uploads de perfis manuais, gerando crashes inesperados na hora da execução.
AÇÃO: Utilizar bibliotecas como `Pydantic` ou `jsonschema` para estruturar estritamente a validação da rota de parse do JSON.
CRITÉRIO DE ACEITE: Rejeição limpa no `/api/upload-and-run` ou na leitura local, retornando exatamente o campo que falhou no schema e não stack traces Python.
RISCO SE NÃO FIZER: Erros silenciosos ou "TypeErrors" cripticos durante a etapa 8, corrompendo o WP pela metade.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Após PEG-PORTAL-004.
PRIORIDADE DE EXECUÇÃO: FASE 1 — Hardening imediato

---

## FASE 2 — Logs e histórico de execução
Auditoria em nível forense: se algo deu errado, precisaremos provar "onde" e "por que".

ID: PEG-PORTAL-006
TÍTULO: Centralizar histórico das execuções no diretório /runs
TIPO: LOGS
PRIORIDADE: P1
CAMADA: Logs / Orquestrador
ARQUIVOS PROVÁVEIS: `provisioner/logger.py`, `provisioner/tasks.py`
PROBLEMA: Atualmente logs em texto puro e relatórios `.md` ficam misturados ou limitados.
AÇÃO: Ao final de cada setup, criar uma pasta em `/logs/runs/{slug}_{timestamp}` contendo os artefatos isolados daquela execução.
CRITÉRIO DE ACEITE: Cada "run" gera um diretório exclusivo fácil de isolar e navegar.
RISCO SE NÃO FIZER: Caos e poluição visual ao tentar debugar falhas ocorridas ontem; perda do tracking forense de execuções simultâneas.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Primeira da Fase 2.
PRIORIDADE DE EXECUÇÃO: FASE 2 — Logs e histórico de execução

ID: PEG-PORTAL-007
TÍTULO: Gerar Artifact 'result.json' por execução
TIPO: ARQUITETURA
PRIORIDADE: P2
CAMADA: Orquestrador
ARQUIVOS PROVÁVEIS: `provisioner/tasks.py`
PROBLEMA: O resultado computacional final é apenas renderizado num Markdown, dificultando o consumo por outras máquinas via API.
AÇÃO: No final do `setup_completo`, gravar a variável final do resultado (dictionário contendo flags, acertos, e falhas) no formato `result.json` dentro da pasta de Run.
CRITÉRIO DE ACEITE: Ter um `result.json` persistido contendo dados brutos e serializados da operação que acaba de ocorrer.
RISCO SE NÃO FIZER: Impossibilidade de construir um dashboard central que leia dados históricos em formato de máquina.
DEPENDÊNCIAS: PEG-PORTAL-006
ORDEM DE EXECUÇÃO: Logo após estruturar `/runs`.
PRIORIDADE DE EXECUÇÃO: FASE 2 — Logs e histórico de execução

ID: PEG-PORTAL-008
TÍTULO: Persistir Artefatos Adicionais (report.md e logs.txt) na pasta /runs
TIPO: LOGS
PRIORIDADE: P2
CAMADA: Logs
ARQUIVOS PROVÁVEIS: `provisioner/logger.py`, `provisioner/utils.py`
PROBLEMA: Os logs de aplicação gerais se misturam com as execuções de um portal específico.
AÇÃO: Criar file handlers temporários em Python para que o output daquele domínio específico gere um `logs.txt` individual e o relatório já existente gere o `report.md` no novo repositório isolado da run.
CRITÉRIO DE ACEITE: A pasta da run contém: `result.json`, `report.md` e `logs.txt` perfeitamente pareados para debug.
RISCO SE NÃO FIZER: Dificuldade extrema para engenheiros depurarem falhas em produção.
DEPENDÊNCIAS: PEG-PORTAL-006
ORDEM DE EXECUÇÃO: Imediata.
PRIORIDADE DE EXECUÇÃO: FASE 2 — Logs e histórico de execução

ID: PEG-PORTAL-009
TÍTULO: Revisão do mascaramento absoluto de senhas em STDOUT e Arquivos
TIPO: SEGURANÇA
PRIORIDADE: P0
CAMADA: Logs / SSH / REST API
ARQUIVOS PROVÁVEIS: `provisioner/logger.py`, `provisioner/wpcli.py`
PROBLEMA: Existe o risco iminente de flags passadas no bash (ex: `--user_pass=`) ou no body da REST API caírem acidentalmente no `logging.debug()` ou no stderr do paramiko gravado nos logs locais.
AÇÃO: Implementar regex (filtro de sanitização) global no `provisioner/logger.py` garantindo que strings de senha nunca sejam persistidas nem por tabela.
CRITÉRIO DE ACEITE: Nenhum password impresso no arquivo `logs.txt`, nem na interface, mesmo se o WP-CLI retornar erro envolvendo o parâmetro.
RISCO SE NÃO FIZER: Vazamento de chaves SSH corporativas e senhas de administradores em disco plain text.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Alta urgência (fazer logo no início da Fase 2 ou fim da Fase 1).
PRIORIDADE DE EXECUÇÃO: FASE 2 — Logs e histórico de execução

ID: PEG-PORTAL-010
TÍTULO: Melhoria e enriquecimento semântico do relatório final
TIPO: UX / DOCUMENTAÇÃO
PRIORIDADE: P2
CAMADA: Orquestrador / Frontend
ARQUIVOS PROVÁVEIS: `provisioner/utils.py`, `provisioner/tasks.py`
PROBLEMA: O relatório Markdown atual é cru e carece de dados de inventário vitais para governança.
AÇÃO: Refatorar o renderizador do Markdown para incluir tabela de auditoria de etapas, inventário de infraestrutura (versão do PHP, versão WP-CLI), e destacar em bloco visual (checklists `[ ]`) as pendências manuais.
CRITÉRIO DE ACEITE: O documento final `.md` deve ser legível o suficiente para um Diretor revisar sem precisar de conhecimentos de Python.
RISCO SE NÃO FIZER: Falsa sensação de sucesso ("deu tudo certo"), sendo que passos críticos foram pulados (ex. Wizard SEO).
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Fim da Fase 2.
PRIORIDADE DE EXECUÇÃO: FASE 2 — Logs e histórico de execução

ID: PEG-PORTAL-011
TÍTULO: Adicionar Modo Dry-Run (Simulação)
TIPO: ARQUITETURA
PRIORIDADE: P3
CAMADA: Tasks / WP-CLI / REST API
ARQUIVOS PROVÁVEIS: `provisioner/tasks.py`, `provisioner/wpcli.py`
PROBLEMA: Não há como testar a validade inteira de um Profile sem acidentalmente injetar dados de verdade em um WordPress remoto.
AÇÃO: Criar flag `--dry-run` ou via UI que executa o `setup_completo`, testa conectividade REST/SSH, gera o profile mockado, mas ignora comandos que alterem estado do servidor remoto (mutáveis).
CRITÉRIO DE ACEITE: Sistema roda todas as 11 etapas e gera o `report.md` atestando que os dados passariam, porém sem sujar o banco de dados do WP destino.
RISCO SE NÃO FIZER: Operadores inexperientes destruindo portais de produção testando perfis com erros de digitação.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Última da Fase 2.
PRIORIDADE DE EXECUÇÃO: FASE 2 — Logs e histórico de execução

---

## FASE 3 — UX e progresso em tempo real
Resolver o congelamento e cegueira operacional do usuário.

ID: PEG-PORTAL-012
TÍTULO: Avaliação e implementação de Server-Sent Events (SSE) ou WebSockets
TIPO: UX
PRIORIDADE: P1
CAMADA: Flask / Frontend
ARQUIVOS PROVÁVEIS: `app.py`, `static/app.js`
PROBLEMA: Ao clicar em "Rodar Setup", a UX fica presa aguardando o retorno monolítico de 15 passos da requisição HTTP bloqueante.
AÇÃO: Alterar a arquitetura da rota para devolver "Job Aceito" e abrir um canal SSE ou polling curto. O backend emite eventos a cada step (`"etapa": 1, "status": "ok"`).
CRITÉRIO DE ACEITE: Na tela do navegador, a barra de progresso enche gradualmente conforme as etapas no backend Python acontecem em tempo real.
RISCO SE NÃO FIZER: Timeouts de Gateway (ex: Nginx, Cloudflare), frustração do operador com falso feedback de travamento.
DEPENDÊNCIAS: Flask suporta SSE nativamente com decorators em yield ou Redis PubSub.
ORDEM DE EXECUÇÃO: Independente dentro da Fase 3.
PRIORIDADE DE EXECUÇÃO: FASE 3 — UX e progresso em tempo real

---

## FASE 4 — Profiles multi-nicho
O sistema só brilha se houver templates para usar.

ID: PEG-PORTAL-013
TÍTULO: Criação de Profiles Mestre: TheNerd, AEconomia e AchouImovel
TIPO: CONFIG
PRIORIDADE: P1
CAMADA: JSON Profiles
ARQUIVOS PROVÁVEIS: `config/sites/thenerd.json`, `aeconomia.json`, `achouimovel.json`
PROBLEMA: O PEG Portal Engine está vazio. Precisamos de baselines reais para a frota.
AÇÃO: Descrever os schemas complexos com as taxonomias de categorias de cinema/tecnologia para o TheNerd, finanças para AEconomia e mercado imobiliário para AchouImovel.
CRITÉRIO DE ACEITE: Ter ao menos 3 arquivos JSON que passem 100% no validador de schemas da Fase 1 e possuam 5+ categorias definidas.
RISCO SE NÃO FIZER: Software inútil operacionalmente por não espelhar as marcas da empresa.
DEPENDÊNCIAS: Validação forte de Schema (Fase 1).
ORDEM DE EXECUÇÃO: Início da Fase 4.
PRIORIDADE DE EXECUÇÃO: FASE 4 — Profiles multi-nicho

---

## FASE 5 — Integração MN26/RSSPRIME
Sincronizar a terraplanagem com as fábricas de conteúdo.

ID: PEG-PORTAL-014
TÍTULO: Preparação da Infra para MN26 (Usuário e App Passwords)
TIPO: INTEGRAÇÃO
PRIORIDADE: P0
CAMADA: WP-CLI / Tasks
ARQUIVOS PROVÁVEIS: `provisioner/tasks.py`, `provisioner/wpcli.py`
PROBLEMA: O MN26 precisa conectar nesse WordPress logo após o provisionamento, mas não possui credencial programática definida.
AÇÃO: O PEG Portal Engine deve ser instruído (via profile) a criar nativamente um usuário `bot_mn26`, gerar-lhe uma Application Password dedicada via comando WP-CLI e guardar essa credencial no relatório ou dispará-la a um Webhook secreto do cofre do MN26.
CRITÉRIO DE ACEITE: WP provisionado possui usuário autônomo bot, sem precisar de clique humano em "Gerar Senha de Aplicativo" na dashboard do wp-admin.
RISCO SE NÃO FIZER: Quebra de esteira automatizada. O humano continua sendo o gargalo gerando senhas no WP.
DEPENDÊNCIAS: Nenhum.
ORDEM DE EXECUÇÃO: Imediata na fase de integração.
PRIORIDADE DE EXECUÇÃO: FASE 5 — Integração MN26/RSSPRIME

ID: PEG-PORTAL-015
TÍTULO: Suporte a Topic Mapping / Integração RSSPRIME
TIPO: INTEGRAÇÃO / CONFIG
PRIORIDADE: P2
CAMADA: JSON Profiles
ARQUIVOS PROVÁVEIS: `config/sites/*.json`
PROBLEMA: O RSSPRIME agrupa matérias com tags universais que podem não bater com os slugs gerados aleatoriamente nos sites.
AÇÃO: Padronizar e unificar o dicionário de Categorias (sluge) da etapa 8 (Criar Categorias) para corresponder ao contrato do "Topic Mapper" do RSSPRIME.
CRITÉRIO DE ACEITE: O JSON Profile aceitar uma diretriz do tipo `feed_mapping: ["rss-finance-1", "rss-cripto-2"]` e montar as categorias.
RISCO SE NÃO FIZER: O conteúdo do agregador não acha gavetas para cair, resultando em "Uncategorized" nos sites WP.
DEPENDÊNCIAS: Criação de Profiles Mestre (Fase 4).
ORDEM DE EXECUÇÃO: Pós-Profiles.
PRIORIDADE DE EXECUÇÃO: FASE 5 — Integração MN26/RSSPRIME

---

## FASE 6 — Governança e escala
Protegendo a máquina interna e tornando-a corporativa.

ID: PEG-PORTAL-016
TÍTULO: Autenticação no painel Flask e Endpoints
TIPO: SEGURANÇA
PRIORIDADE: P0
CAMADA: Flask / Segurança
ARQUIVOS PROVÁVEIS: `app.py`
PROBLEMA: O Flask está exposto em localhost livre. Se exposto externamente ou num docker aberto, torna-se um buraco de segurança grave para RCE (Remote Code Execution em VPS de terceiros).
AÇÃO: Proteger todas as rotas (Web e API) com Basic Auth, JWT ou session token atrelado a usuário.
CRITÉRIO DE ACEITE: Impossível ler, abrir ou engatilhar comandos na porta :5000 sem credencial de operador.
RISCO SE NÃO FIZER: Risco crítico 10/10 de sequestro de infraestrutura.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: OBRIGATÓRIA antes de deploy em núvem.
PRIORIDADE DE EXECUÇÃO: FASE 6 — Governança e escala

ID: PEG-PORTAL-017
TÍTULO: Criação de Endpoint de Health Check
TIPO: INTEGRAÇÃO / MONITORAMENTO
PRIORIDADE: P1
CAMADA: Flask
ARQUIVOS PROVÁVEIS: `app.py`
PROBLEMA: O Dashboard Central, e serviços como UptimeRobot, não conseguem saber se o PEG Engine está em pé.
AÇÃO: Criar rota `/api/health` retornando `200 OK` e dados vitais em JSON (`{"status":"online", "workers_free": 1}`).
CRITÉRIO DE ACEITE: Requisição GET devolve imediatamente status de serviço sem travar.
RISCO SE NÃO FIZER: Ferramentas de CI/CD e Dashboards ficarem cegos.
DEPENDÊNCIAS: Nenhuma.
ORDEM DE EXECUÇÃO: Independente.
PRIORIDADE DE EXECUÇÃO: FASE 6 — Governança e escala

ID: PEG-PORTAL-018
TÍTULO: Preparação de rotas API para Dashboard Central
TIPO: INTEGRAÇÃO
PRIORIDADE: P1
CAMADA: Flask
ARQUIVOS PROVÁVEIS: `app.py`
PROBLEMA: O Dashboard corporativo do ecossistema PEG vai precisar "puxar" histórico e "injetar" comandos remotamente via Webhooks ou APIs REST ao invés do usuário preencher a tela HTML do Flask local.
AÇÃO: Expor e documentar Swagger/OpenAPI ou contratos fixos para injetar `POST /api/upload-and-run` e `GET /api/history`.
CRITÉRIO DE ACEITE: O Dashboard Central conseguir mandar um comando completo de provisionamento e o PEG Portal agir como um "Worker Silencioso" e devolver 201 Created.
RISCO SE NÃO FIZER: Isolamento tecnológico do projeto, virando ferramenta apenas local.
DEPENDÊNCIAS: FASE 2 e FASE 3 prontas.
ORDEM DE EXECUÇÃO: Intermediária na Fase 6.
PRIORIDADE DE EXECUÇÃO: FASE 6 — Governança e escala

ID: PEG-PORTAL-019
TÍTULO: Refatoração: Criar Testes Mockados de SSH e REST API
TIPO: TESTES / ARQUITETURA
PRIORIDADE: P2
CAMADA: Testes
ARQUIVOS PROVÁVEIS: `tests/test_ssh.py`, `tests/test_rest.py`, `tests/test_tasks.py`
PROBLEMA: Ausência de suíte de testes (TDD). Qualquer refatoração futura pode quebrar as regexp ou parsing JSON de saídas SSH (ex: WP-CLI versão).
AÇÃO: Implementar pytest simulando (mocking) Paramiko SSH channels (retornando stdout predefinido) e calls requests para o WP.
CRITÉRIO DE ACEITE: `$ pytest` executa em 2 segundos cobrindo as mecânicas cruciais de `wpcli.py` e `wp_rest.py` sem tocar na internet ou criar chaves reais.
RISCO SE NÃO FIZER: Deterioração rápida do código e Medo de refatorar (Technical Debt).
DEPENDÊNCIAS: Nenhuma arquitetural, mas essencial para engenharia de software madura.
ORDEM DE EXECUÇÃO: Recomendável finalização da Fase 6.
PRIORIDADE DE EXECUÇÃO: FASE 6 — Governança e escala

ID: PEG-PORTAL-020
TÍTULO: Refatoração: Criar Testes end-to-end do setup_completo (Integração)
TIPO: TESTES
PRIORIDADE: P2
CAMADA: Testes
ARQUIVOS PROVÁVEIS: `tests/test_setup_completo.py`
PROBLEMA: A prova de fogo da orquestração nunca roda até que um operador clique em "Executar" na tela.
AÇÃO: Usar um conteiner Docker provisório via `testcontainers-python` ou apenas mocks de alto-nível para testar se a rotina engole exceções de forma correta e não derruba a si própria no passo `setup_completo`.
CRITÉRIO DE ACEITE: Suite de teste de orquestração atesta que a lista retorna 11 chaves de relatório contendo erros suaves ou sucessos completos.
RISCO SE NÃO FIZER: Orquestrador frágil.
DEPENDÊNCIAS: PEG-PORTAL-019.
ORDEM DE EXECUÇÃO: Fim da esteira.
PRIORIDADE DE EXECUÇÃO: FASE 6 — Governança e escala
