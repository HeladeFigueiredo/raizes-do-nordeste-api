# Raízes do Nordeste · API back-end

API REST do sistema de pedidos da rede Raízes do Nordeste (Recife). Projeto de Back-End, curso de Análise e Desenvolvimento de Sistemas.

**Estado atual (fatias 1 a 4):** estrutura, modelos das 13 tabelas, migrações, dados iniciais, autenticação com perfis, cardápio por unidade (com sazonalidade), pedidos e pagamento desacoplado.
Fora do escopo deste MVP (evolução futura): fidelização, consentimentos LGPD, gestão de equipe, controle de estoque, auditoria, relatórios, cancelamento de pedidos, endpoints `/health` e `/auth/me`.

**Se você já tinha rodado uma versão anterior**, apague o arquivo do banco em `instance/` e rode `flask db upgrade` e `flask seed` de novo (o histórico de migrações foi reunido em uma única migração inicial). Se o seu `.env` for antigo, acrescente a linha `GATEWAY_API_KEY=chave-do-gateway-dev` (sem ela, esse mesmo valor é usado por padrão).

## Endpoints disponíveis

Base: `/api/v1`

| Método | Rota | Quem acessa | Descrição |
|--------|------|-------------|-----------|
| POST | `/auth/cadastro` | Público | Cadastra cliente (CPF validado, senha com hash) |
| POST | `/auth/login` | Público | Login do cliente (e-mail) ou da equipe (login). Devolve o token JWT |
| GET | `/unidades` | Público | Lista unidades. Filtros `?cidade=` e `?regiao=`, paginação `?pagina=&tamanho=` |
| POST | `/unidades` | MATRIZ | Cria unidade (`tipo_cozinha`: COMPLETA ou REDUZIDA) |
| PUT | `/unidades/{id}` | MATRIZ | Atualiza unidade (parcial) |
| GET | `/unidades/{id}/cardapio` | Público | Cardápio da unidade: só o que está disponível ali e na época. `?data=AAAA-MM-DD` simula outra data |
| PUT | `/unidades/{idUnidade}/sabores/{idSabor}` | GERENTE (da unidade), MATRIZ | Define disponibilidade e preço local. Cria o registro se não existir (201) |
| POST | `/produtos` | MATRIZ | Cria produto (ex.: tapioca) |
| POST | `/produtos/{id}/sabores` | MATRIZ | Cria sabor com preço base e período de venda opcional |
| PUT | `/sabores/{id}` | MATRIZ | Atualiza nome, preço base ou período (parcial) |
| POST | `/pedidos` | CLIENTE, FUNCIONARIO, GERENTE | Cria pedido: valida disponibilidade na unidade e na época, grava o preço do momento, calcula o total |
| GET | `/pedidos` | Autenticado | Lista pedidos. Filtros `id_unidade`, `status`, `data_inicio`, `data_fim`. Cliente vê só os seus, equipe só a própria unidade |
| GET | `/pedidos/{id}` | Dono, equipe da unidade, MATRIZ | Detalhe com itens e pagamentos |
| GET | `/pedidos/{id}/status` | Dono, equipe da unidade, MATRIZ | Consulta leve para acompanhamento |
| PATCH | `/pedidos/{id}/status` | FUNCIONARIO, GERENTE | Avança: `PRONTO`, depois `RETIRADO` |
| POST | `/pedidos/{id}/pagamentos` | Dono, FUNCIONARIO, GERENTE | Solicita o pagamento ao gateway (202) |
| GET | `/pedidos/{id}/pagamentos` | Dono, equipe da unidade, MATRIZ | Tentativas de pagamento do pedido |
| POST | `/pagamentos/retorno` | Gateway (cabeçalho `X-API-Key`) | Webhook com `APROVADO`, `NEGADO` ou `ERRO`. Idempotente |

Exemplos (PowerShell ou Linux/macOS com `curl`):

```bash
curl -X POST http://127.0.0.1:5000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"login\":\"gerente\",\"senha\":\"senha123\"}"
curl http://127.0.0.1:5000/api/v1/pedidos -H "Authorization: Bearer <token>"
curl "http://127.0.0.1:5000/api/v1/unidades/2/cardapio?data=2026-06-15"
```

No cardápio, o bolo de milho junino só aparece entre 01/06 e 31/07, e o quiosque (cozinha reduzida) não oferece ovo com queijo nem cuscuz. Sem `preco_local`, vale o preço base do sabor.

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
  models/          tabelas (cardapio, cliente, pedido, acesso)
  schemas/         validação das entradas (Marshmallow)
  services/        regras de negócio (cardápio, pedidos, pagamento, gateway simulado)
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
