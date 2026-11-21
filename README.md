# Raízes do Nordeste · API back-end

API REST do sistema de pedidos da rede Raízes do Nordeste (Recife). Projeto de Back-End, curso de Análise e Desenvolvimento de Sistemas.

**O que a API faz:** cadastro e login de clientes e da equipe (perfis Cliente, Funcionário, Gerente e Matriz), cardápio por unidade com sabores sazonais, criação de pedidos, acompanhamento de status e pagamento desacoplado (o sistema solicita o pagamento a um gateway simulado e registra o resultado recebido dele). São 19 endpoints, 14 tabelas e documentação interativa em Swagger (`/docs`).

**Fora do escopo deste MVP (evolução futura):** fidelização e campanhas, gestão de equipe por API, controle de estoque, relatórios, cancelamento de pedidos e os endpoints `/health` e `/auth/me`.

## Documentação

Na pasta [`docs/`](docs/):

| Arquivo | Conteúdo |
|---|---|
| `DER_Raizes_do_Nordeste_MVP.pdf` | Diagrama entidade-relacionamento (14 tabelas) |
| `Diagrama_de_Classes_MVP.pdf` | Diagrama de classes |
| `Diagrama_Casos_de_Uso_MVP.pdf` | Diagrama de casos de uso |
| `Descricao_dos_Endpoints_API_MVP.pdf` | Descrição dos 19 endpoints, regras e exemplos |
| `Raizes_do_Nordeste_API.postman_collection.json` | Coleção do Postman com 46 requisições e testes automáticos |

**Como usar a coleção:** rode `flask run`, importe o arquivo no Postman e use *Run collection*. Os logins de teste são `cliente@exemplo.com`, `funcionario`, `gerente` e `matriz`, todos com a senha `senha123` (criados pelo `flask seed`).

## Endpoints disponíveis

Base: `/api/v1`

| Método | Rota | Quem acessa | Descrição |
|--------|------|-------------|-----------|
| POST | `/auth/cadastro` | Público | Cadastra cliente (CPF validado, senha com hash, aceite da LGPD obrigatório) |
| POST | `/auth/login` | Público | Login do cliente (e-mail) ou da equipe (login). Devolve o token JWT |
| GET | `/unidades` | Público | Lista unidades. Filtros `?cidade=` e `?regiao=`, paginação `?pagina=&tamanho=` |
| POST | `/unidades` | MATRIZ | Cria unidade (`tipo_cozinha`: COMPLETA ou REDUZIDA) |
| PUT | `/unidades/{id}` | MATRIZ | Atualiza unidade (parcial) |
| GET | `/unidades/{id}/cardapio` | Público | Cardápio da unidade: só o que está disponível ali e na época. `?data=AAAA-MM-DD` simula outra data |
| PUT | `/unidades/{idUnidade}/sabores/{idSabor}` | GERENTE (da unidade), MATRIZ | Define disponibilidade e preço local. Cria o registro se não existir (201) |
| POST | `/produtos` | MATRIZ | Cria produto (ex.: tapioca) |
| POST | `/produtos/{id}/sabores` | MATRIZ | Cria sabor com preço base e período de venda opcional |
| PUT | `/sabores/{id}` | MATRIZ | Atualiza nome, preço base ou período (parcial) |
| POST | `/pedidos` | CLIENTE, FUNCIONARIO, GERENTE | Cria pedido (`canalPedido` obrigatório: APP, TOTEM, BALCAO, PICKUP ou WEB): valida disponibilidade na unidade e na época, grava o preço do momento, calcula o total |
| GET | `/pedidos` | Autenticado | Lista pedidos. Filtros `canalPedido`, `status`, `id_unidade`, `data_inicio`, `data_fim`. Cliente vê só os seus, equipe só a própria unidade |
| GET | `/pedidos/{id}` | Dono, equipe da unidade, MATRIZ | Detalhe com itens e pagamentos |
| GET | `/pedidos/{id}/status` | Dono, equipe da unidade, MATRIZ | Consulta leve para acompanhamento |
| PATCH | `/pedidos/{id}/status` | FUNCIONARIO, GERENTE | Avança: `PRONTO`, depois `RETIRADO` |
| POST | `/pedidos/{id}/pagamentos` | Dono, FUNCIONARIO, GERENTE | Solicita o pagamento ao gateway (202) |
| GET | `/pedidos/{id}/pagamentos` | Dono, equipe da unidade, MATRIZ | Tentativas de pagamento do pedido |
| POST | `/pagamentos/retorno` | Gateway (cabeçalho `X-API-Key`) | Webhook com `APROVADO`, `NEGADO` ou `ERRO`. Idempotente |
| GET | `/auditoria` | GERENTE (da unidade), MATRIZ | Registros de ações sensíveis. Filtros `id_pedido` e `acao` |

Exemplos (PowerShell ou Linux/macOS com `curl`):

```bash
curl -X POST http://127.0.0.1:5000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"login\":\"gerente\",\"senha\":\"senha123\"}"
curl http://127.0.0.1:5000/api/v1/pedidos -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:5000/api/v1/unidades/2/cardapio?data=2026-06-15"
```

No cardápio, o bolo de milho junino só aparece entre 01/06 e 31/07, e o quiosque (cozinha reduzida) não oferece ovo com queijo nem cuscuz. Sem `preco_local`, vale o preço base do sabor.

## Arquitetura em camadas

| Camada | Onde fica | Responsabilidade |
|--------|-----------|------------------|
| API (interface) | `app/routes/`, `app/schemas/`, `app/security.py`, `app/openapi.py` | Rotas, validação de entrada, autenticação, permissões e documentação |
| Aplicação | `app/services/` | Casos de uso: criar pedido, solicitar pagamento, registrar retorno, avançar status, auditar |
| Domínio | `app/models/`, `app/constants.py` | Entidades, status e transições permitidas |
| Infraestrutura | `app/extensions.py`, `migrations/`, `app/services/gateway.py` | Banco (ORM e migrações) e integração de pagamento simulada |

## LGPD e segurança

- **Dados coletados e finalidade:** nome, CPF, e-mail, data de nascimento e cidade, usados só para identificar o cliente, registrar pedidos e pagamentos.
- **Consentimento:** o cadastro exige `consentimento_lgpd: true`, e a data do aceite fica gravada.
- **Minimização:** a resposta nunca devolve a senha e o CPF sai mascarado.
- **Senha:** guardada com hash (Werkzeug), nunca em texto.
- **Acesso:** autenticação por token JWT e autorização por perfil (Cliente, Funcionário, Gerente, Matriz), com escopo por unidade. O cliente só enxerga os próprios pedidos.
- **Auditoria:** criação de pedido, mudança de status e pagamento geram registro em `auditoria`, consultável em `GET /auditoria`.
- **Retenção (proposta):** dados de cliente inativo seriam anonimizados após prazo definido pela empresa. Não implementado no MVP.

## Fluxo do pedido e do pagamento

```
Aguardando pagamento --(gateway aprova)--> Em produção --(equipe)--> Pronto --(equipe)--> Retirado
```

1. O cliente cria o pedido (`POST /pedidos`). Itens fora do cardápio da unidade ou fora da época dão 422 listando todos os problemas.
2. Solicita o pagamento (`POST /pedidos/{id}/pagamentos`). O sistema **não processa** pagamento: pede ao gateway e guarda a tentativa.
3. O gateway avisa o resultado em `POST /pagamentos/retorno`. Aprovado: o pedido entra em produção sozinho. Negado ou erro: o pedido continua aguardando e o cliente pode tentar de novo.
4. A equipe avança o pedido até a retirada.

O gateway é **simulado** (`app/services/gateway.py`). Para simular o retorno em desenvolvimento ou no Postman:

```bash
curl -X POST http://127.0.0.1:5000/api/v1/pagamentos/retorno -H "Content-Type: application/json" -H "X-API-Key: chave-do-gateway-dev" -d "{\"id_transacao_externa\":\"SIM-XXXX\",\"resultado\":\"APROVADO\"}"
```

Se o gateway estiver fora do ar, a solicitação responde 502, a tentativa fica registrada com erro e pode ser repetida.

Observações: datas e horas são gravadas e devolvidas em UTC (sufixo `Z`). O SQLite roda com chaves estrangeiras ligadas para se comportar como o PostgreSQL.

## Perfis e permissões

O token JWT carrega o perfil: `CLIENTE`, `FUNCIONARIO`, `GERENTE` ou `MATRIZ`.
Nas próximas rotas, use os decoradores de `app/security.py`:

```python
@bp.get("/algo")
@perfis_permitidos("GERENTE", "MATRIZ")   # gerente herda o que o funcionário pode fazer
def algo():
    exigir_unidade(id_unidade)            # gerente e funcionário só acessam a própria unidade
```

Sem token: 401. Perfil sem permissão ou unidade de outro: 403.

## Tecnologias

Python 3.10+, Flask, Flask-SQLAlchemy (SQLAlchemy 2), Flask-Migrate (Alembic), SQLite em desenvolvimento e PostgreSQL em produção, pytest.

## Como rodar

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate            # Windows (PowerShell ou CMD)
# source .venv/bin/activate       # Linux ou macOS

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Configurar as variáveis de ambiente
copy .env.example .env            # Windows  (Linux/macOS: cp .env.example .env)

# 4. Criar o banco (aplica as migrações) e popular com dados iniciais
flask db upgrade
flask seed

# 5. Subir a API
flask run
```

A API sobe em `http://127.0.0.1:5000`. Teste: `http://127.0.0.1:5000/api/v1/unidades`.

**Swagger (documentação interativa):** `http://127.0.0.1:5000/docs`. A especificação OpenAPI em JSON está em `http://127.0.0.1:5000/openapi.json`. Para testar rotas protegidas, faça `POST /auth/login`, copie o `access_token` e clique em *Authorize*. A página do Swagger carrega os arquivos visuais da internet (CDN), então precisa de conexão.

No PyCharm: em *Settings > Project > Python Interpreter*, aponte para o `.venv` do projeto.
Se o `flask` não for reconhecido no terminal, use `python -m flask ...`.

## Dados de exemplo (`flask seed`)

Cria os 6 status de pedido, os 5 status de pagamento, os 3 perfis, 2 unidades (uma com cozinha completa, uma reduzida), produtos, sabores (inclusive um sazonal do período junino) e usuários de teste.

| Quem | Login | Senha |
|------|-------|-------|
| Funcionário | `funcionario` | `senha123` |
| Gerente | `gerente` | `senha123` |
| Matriz | `matriz` | `senha123` |
| Cliente | `cliente@exemplo.com` | `senha123` |

Essas senhas são só para desenvolvimento. Troque `SEED_PASSWORD` no `.env`. Para criar só status e perfis: `flask seed --sem-exemplos`.

## Testes

```bash
python -m pytest -q
```

São 180+ testes automatizados (autenticação, permissões, cardápio, pedidos, pagamento, auditoria e conferência da documentação OpenAPI contra as rotas reais). A coleção do Postman (`docs/`) tem 46 requisições com testes embutidos.

## Estrutura

```
app/
  __init__.py      fábrica da aplicação (create_app)
  config.py        configurações por ambiente
  constants.py     status, transições, canais e perfis
  errors.py        padrão único de erro (JSON)
  security.py      JWT, perfis e escopo por unidade
  validacao.py     leitura e validação do corpo JSON
  cli.py           comando "flask seed"
  models/          tabelas (cardapio, cliente, pedido, acesso e auditoria)
  schemas/         validação das entradas (Marshmallow)
  services/        regras de negócio (cardápio, pedidos, pagamento, auditoria, gateway simulado)
  openapi.py       especificação OpenAPI (Swagger) em /docs
  routes/          endpoints (blueprints), finos: validam, chamam o serviço e respondem
  utils/           CPF e outros utilitários
migrations/        histórico versionado do banco
tests/             testes automatizados
```

## Migrações: fluxo de trabalho

Ao alterar um modelo (ex.: nova coluna):

```bash
flask db migrate -m "descrição da mudança"
flask db upgrade
```

Os arquivos gerados em `migrations/versions/` vão para o Git junto com o código.

## Padrão de erro

```json
{ "erro": "CODIGO", "mensagem": "texto legível", "detalhes": [] }
```
