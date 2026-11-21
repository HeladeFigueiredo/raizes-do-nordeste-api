"""Documentação OpenAPI 3 da API, servida em /openapi.json e exibida em /docs (Swagger UI).

A especificação é escrita aqui, em Python, e um teste automatizado (tests/test_openapi.py) confere que
cada rota da API está documentada e vice-versa. Assim a documentação reflete o contrato real.
"""

ERRO_EXEMPLO = {"erro": "DADOS_INVALIDOS", "mensagem": "Há campos inválidos na requisição.",
                "detalhes": [{"campo": "quantidade", "mensagem": "A quantidade deve ser entre 1 e 50."}]}

STATUS_PEDIDO = ["AGUARDANDO_PAGAMENTO", "EM_PRODUCAO", "PRONTO", "RETIRADO", "CANCELADO_CLIENTE", "CANCELADO_EMPRESA"]
CANAIS = ["APP", "TOTEM", "BALCAO", "PICKUP", "WEB"]


def _corpo(schema, exemplo):
    return {"required": True, "content": {"application/json": {"schema": schema, "example": exemplo}}}


def _resp(descricao, schema=None, exemplo=None):
    r = {"description": descricao}
    if schema is not None:
        r["content"] = {"application/json": {"schema": schema, **({"example": exemplo} if exemplo is not None else {})}}
    return r


def _erro(descricao, codigo, mensagem):
    return _resp(descricao, {"$ref": "#/components/schemas/Erro"}, {"erro": codigo, "mensagem": mensagem})


E400 = _resp("Dados inválidos", {"$ref": "#/components/schemas/Erro"}, ERRO_EXEMPLO)
E401 = _erro("Não autenticado (token ausente, inválido ou expirado)", "NAO_AUTENTICADO", "Autenticação necessária.")
E403 = _erro("Sem permissão para esta operação", "SEM_PERMISSAO", "Você não tem permissão para esta operação.")
E404 = _erro("Não encontrado", "NAO_ENCONTRADO", "Recurso não encontrado.")
JWT = [{"bearerAuth": []}]


def _pagina(item_ref):
    return {"type": "object", "properties": {
        "itens": {"type": "array", "items": {"$ref": item_ref}}, "pagina": {"type": "integer"},
        "tamanho": {"type": "integer"}, "total": {"type": "integer"}}}


def _param(nome, onde, descricao, tipo="string", obrigatorio=None, enum=None):
    esquema = {"type": tipo}
    if enum:
        esquema["enum"] = enum
    return {"name": nome, "in": onde, "description": descricao, "required": onde == "path" if obrigatorio is None else obrigatorio,
            "schema": esquema}


PAGINACAO = [_param("pagina", "query", "Página (começa em 1)", "integer"),
             _param("tamanho", "query", "Itens por página (1 a 100, padrão 20)", "integer")]
ID_PEDIDO = _param("id_pedido", "path", "Identificador do pedido", "integer")

UNIDADE_EX = {"id": 1, "nome": "Raízes Boa Viagem", "cidade": "Recife", "regiao": "Litoral", "tipo_cozinha": "COMPLETA"}
SABOR_EX = {"id": 12, "id_produto": 5, "nome": "Doce", "preco_base": 7.5, "data_inicio_venda": None, "data_fim_venda": None}
PAGAMENTO_EX = {"id": 1, "id_pedido": 1, "status": "Processando pagamento", "status_codigo": "PROCESSANDO", "valor": 10.0,
                "id_transacao_externa": "SIM-108A5BD44745", "data_retorno": None}
PEDIDO_EX = {
    "id": 1, "id_cliente": 1, "id_unidade": 1, "canalPedido": "APP",
    "status": "Aguardando liberação do pagamento", "status_codigo": "AGUARDANDO_PAGAMENTO",
    "valor_total": 10.0, "data_pedido": "2026-11-21T13:06:13Z",
    "itens": [{"id_sabor": 1, "produto": "Tapioca", "sabor": "Queijo", "quantidade": 2, "preco_unitario": 5.0, "subtotal": 10.0}],
    "pagamentos": [],
}


def _op(resumo, descricao, tags, respostas, seguranca=None, corpo=None, parametros=None):
    op = {"summary": resumo, "description": descricao, "tags": tags, "responses": respostas}
    if seguranca is not None:
        op["security"] = seguranca
    if corpo:
        op["requestBody"] = corpo
    if parametros:
        op["parameters"] = parametros
    return op


def construir_spec() -> dict:
    ref = lambda nome: {"$ref": f"#/components/schemas/{nome}"}
    paths = {
        "/auth/cadastro": {"post": _op(
            "Cadastrar cliente", "Cria o cliente. Exige o aceite do tratamento de dados (LGPD), que é registrado com data e hora. "
            "A senha é guardada com hash e o CPF volta mascarado.", ["Autenticação"],
            {"201": _resp("Cliente criado", ref("Cliente"), {
                "id": 1, "nome": "Maria da Silva", "email": "maria@exemplo.com", "cpf": "***.982.247-**",
                "data_nascimento": "1998-03-10", "idade": 28, "cidade": "Olinda",
                "consentimento_lgpd": True, "data_consentimento": "2026-11-21T13:00:00Z"}),
             "400": E400, "409": _erro("CPF ou e-mail já cadastrado", "EMAIL_JA_CADASTRADO", "Já existe um cadastro com este e-mail.")},
            seguranca=[], corpo=_corpo(ref("CadastroCliente"), {
                "nome": "Maria da Silva", "cpf": "529.982.247-25", "email": "maria@exemplo.com", "senha": "senhaforte1",
                "data_nascimento": "1998-03-10", "cidade": "Olinda", "consentimento_lgpd": True}))},
        "/auth/login": {"post": _op(
            "Login", "Cliente entra com o e-mail e a equipe com o login. Devolve o token JWT. A resposta é a mesma para qualquer falha.",
            ["Autenticação"],
            {"200": _resp("Token gerado", ref("Token"), {"access_token": "eyJhbGciOi...", "token_type": "Bearer", "expires_in": 3600, "perfil": "CLIENTE"}),
             "400": E400, "401": _erro("Credenciais inválidas", "CREDENCIAIS_INVALIDAS", "Login ou senha inválidos.")},
            seguranca=[], corpo=_corpo(ref("Login"), {"login": "cliente@exemplo.com", "senha": "senha123"}))},
        "/unidades": {
            "get": _op("Listar unidades", "Lista paginada, com filtros opcionais por cidade e região.", ["Unidades"],
                       {"200": _resp("Lista de unidades", _pagina("#/components/schemas/Unidade"),
                                     {"itens": [UNIDADE_EX], "pagina": 1, "tamanho": 20, "total": 1})},
                       seguranca=[], parametros=[_param("cidade", "query", "Filtra pela cidade"), _param("regiao", "query", "Filtra pela região")] + PAGINACAO),
            "post": _op("Criar unidade", "Somente a MATRIZ.", ["Unidades"],
                        {"201": _resp("Unidade criada", ref("Unidade"), UNIDADE_EX), "400": E400, "401": E401, "403": E403},
                        seguranca=JWT, corpo=_corpo(ref("UnidadeEntrada"), {"nome": "Raízes Olinda", "cidade": "Olinda", "regiao": "Litoral", "tipo_cozinha": "REDUZIDA"}))},
        "/unidades/{id_unidade}": {"put": _op(
            "Atualizar unidade", "Somente a MATRIZ.", ["Unidades"],
            {"200": _resp("Unidade atualizada", ref("Unidade"), UNIDADE_EX), "400": E400, "401": E401, "403": E403, "404": E404},
            seguranca=JWT, parametros=[_param("id_unidade", "path", "Identificador da unidade", "integer")],
            corpo=_corpo(ref("UnidadeEntrada"), {"nome": "Raízes Olinda Centro", "cidade": "Olinda", "regiao": "Litoral", "tipo_cozinha": "COMPLETA"}))},
        "/unidades/{id_unidade}/cardapio": {"get": _op(
            "Cardápio da unidade", "Só aparecem os sabores disponíveis na unidade e dentro da época de venda (sazonalidade) na data de hoje.",
            ["Unidades"],
            {"200": _resp("Cardápio", ref("Cardapio"), {
                "unidade": UNIDADE_EX, "data_referencia": "2026-11-21",
                "itens": [{"id_produto": 3, "produto": "Bolo de macaxeira", "descricao": "Bolo tradicional de macaxeira",
                           "sabores": [{"id_sabor": 5, "sabor": "Tradicional", "preco": 6.0}]}]}),
             "404": E404}, seguranca=[], parametros=[_param("id_unidade", "path", "Identificador da unidade", "integer")])},
        "/unidades/{id_unidade}/sabores/{id_sabor}": {"put": _op(
            "Definir disponibilidade e preço local de um sabor", "GERENTE da própria unidade ou MATRIZ. Sem preco_local vale o preço base. Cria o registro se ainda não existir (201).",
            ["Unidades"],
            {"200": _resp("Atualizado", ref("Disponibilidade"), {"id_unidade": 1, "id_sabor": 5, "esta_disponivel": True, "preco_local": None, "preco_vigente": 6.0}),
             "201": _resp("Criado", ref("Disponibilidade")), "400": E400, "401": E401, "403": E403, "404": E404},
            seguranca=JWT, parametros=[_param("id_unidade", "path", "Identificador da unidade", "integer"), _param("id_sabor", "path", "Identificador do sabor", "integer")],
            corpo=_corpo(ref("DisponibilidadeEntrada"), {"esta_disponivel": True, "preco_local": 6.5}))},
        "/produtos": {"post": _op(
            "Criar produto", "Somente a MATRIZ.", ["Produtos"],
            {"201": _resp("Produto criado", ref("Produto"), {"id": 5, "nome": "Pamonha", "descricao": "Pamonha doce e salgada"}),
             "400": E400, "401": E401, "403": E403, "409": _erro("Produto já existe", "PRODUTO_JA_EXISTE", "Já existe um produto com este nome.")},
            seguranca=JWT, corpo=_corpo(ref("ProdutoEntrada"), {"nome": "Pamonha", "descricao": "Pamonha doce e salgada"}))},
        "/produtos/{id_produto}/sabores": {"post": _op(
            "Criar sabor", "Somente a MATRIZ. Datas de início e fim definem a sazonalidade (opcionais).", ["Produtos"],
            {"201": _resp("Sabor criado", ref("Sabor"), SABOR_EX), "400": E400, "401": E401, "403": E403, "404": E404},
            seguranca=JWT, parametros=[_param("id_produto", "path", "Identificador do produto", "integer")],
            corpo=_corpo(ref("SaborEntrada"), {"nome": "Doce", "preco_base": 7.5, "data_inicio_venda": None, "data_fim_venda": None}))},
        "/sabores/{id_sabor}": {"put": _op(
            "Atualizar sabor", "Somente a MATRIZ.", ["Produtos"],
            {"200": _resp("Sabor atualizado", ref("Sabor"), SABOR_EX), "400": E400, "401": E401, "403": E403, "404": E404},
            seguranca=JWT, parametros=[_param("id_sabor", "path", "Identificador do sabor", "integer")],
            corpo=_corpo(ref("SaborEntrada"), {"nome": "Doce tradicional", "preco_base": 8.0}))},
        "/pedidos": {
            "post": _op(
                "Criar pedido", "CLIENTE ou equipe. O canalPedido é obrigatório. O servidor valida a disponibilidade, grava o preço do momento e calcula o total. "
                "O canal BALCAO é exclusivo da equipe. O pedido nasce aguardando pagamento.", ["Pedidos"],
                {"201": _resp("Pedido criado", ref("Pedido"), PEDIDO_EX), "400": E400, "401": E401, "403": E403,
                 "422": _resp("Item indisponível", ref("Erro"), {"erro": "ITEM_INDISPONIVEL", "mensagem": "Há itens indisponíveis neste pedido.",
                                                                  "detalhes": [{"id_sabor": 99, "motivo": "SABOR_INEXISTENTE"}]})},
                seguranca=JWT, corpo=_corpo(ref("PedidoEntrada"), {"id_unidade": 1, "canalPedido": "APP", "itens": [{"id_sabor": 1, "quantidade": 2}]})),
            "get": _op(
                "Listar pedidos", "Mais recentes primeiro. Cliente vê só os seus, equipe vê a própria unidade, matriz vê tudo.", ["Pedidos"],
                {"200": _resp("Lista de pedidos", _pagina("#/components/schemas/PedidoResumo"), {"itens": [{k: v for k, v in PEDIDO_EX.items() if k not in ("itens", "pagamentos")}], "pagina": 1, "tamanho": 20, "total": 1}),
                 "400": _erro("Parâmetro inválido", "PARAMETRO_INVALIDO", "canalPedido inválido."), "401": E401},
                seguranca=JWT, parametros=[
                    _param("canalPedido", "query", "Filtra pelo canal de origem", enum=CANAIS),
                    _param("status", "query", "Filtra pelo status", enum=STATUS_PEDIDO),
                    _param("id_unidade", "query", "Filtra pela unidade", "integer"),
                    _param("data_inicio", "query", "Data inicial (AAAA-MM-DD)"), _param("data_fim", "query", "Data final (AAAA-MM-DD, inclusiva)")] + PAGINACAO)},
        "/pedidos/{id_pedido}": {"get": _op(
            "Consultar pedido", "Detalhe com itens e pagamentos.", ["Pedidos"],
            {"200": _resp("Pedido", ref("Pedido"), PEDIDO_EX), "401": E401, "403": E403, "404": E404}, seguranca=JWT, parametros=[ID_PEDIDO])},
        "/pedidos/{id_pedido}/status": {
            "get": _op("Consultar status do pedido", "Consulta leve usada no acompanhamento pelo app.", ["Pedidos"],
                       {"200": _resp("Status", ref("StatusPedido"), {"id": 1, "status": "Em produção", "status_codigo": "EM_PRODUCAO", "pagamento": PAGAMENTO_EX}),
                        "401": E401, "403": E403, "404": E404}, seguranca=JWT, parametros=[ID_PEDIDO]),
            "patch": _op("Atualizar status do pedido", "Equipe da unidade avança EM_PRODUCAO → PRONTO → RETIRADO. Não é possível pular o pagamento nem voltar etapas (409).",
                         ["Pedidos"],
                         {"200": _resp("Status atualizado", ref("StatusPedido"), {"id": 1, "status": "Pedido pronto, pode retirar", "status_codigo": "PRONTO"}),
                          "400": E400, "401": E401, "403": E403, "404": E404,
                          "409": _erro("Transição inválida", "TRANSICAO_INVALIDA", "O pedido entra em produção sozinho quando o pagamento é confirmado.")},
                         seguranca=JWT, parametros=[ID_PEDIDO], corpo=_corpo(ref("StatusEntrada"), {"status": "PRONTO"}))},
        "/pedidos/{id_pedido}/pagamentos": {
            "post": _op("Solicitar pagamento", "Pede a cobrança ao gateway (simulado). O resultado chega depois em POST /pagamentos/retorno.", ["Pagamentos"],
                        {"202": _resp("Pagamento em processamento", ref("Pagamento"), PAGAMENTO_EX), "401": E401, "403": E403, "404": E404,
                         "409": _erro("Pedido não aguarda pagamento ou já há pagamento em andamento", "PAGAMENTO_EM_ANDAMENTO", "Já existe um pagamento em andamento para este pedido."),
                         "502": _erro("Gateway indisponível", "GATEWAY_INDISPONIVEL", "O gateway de pagamento está indisponível. Tente novamente em instantes.")},
                        seguranca=JWT, parametros=[ID_PEDIDO]),
            "get": _op("Listar pagamentos do pedido", "Tentativas de pagamento do pedido.", ["Pagamentos"],
                       {"200": _resp("Pagamentos", {"type": "object", "properties": {"itens": {"type": "array", "items": ref("Pagamento")}}}, {"itens": [PAGAMENTO_EX]}),
                        "401": E401, "403": E403, "404": E404}, seguranca=JWT, parametros=[ID_PEDIDO])},
        "/pagamentos/retorno": {"post": _op(
            "Retorno do gateway (webhook)", "Chamado pelo gateway, autenticado pela chave de API no cabeçalho X-API-Key (sem JWT). Idempotente: repetir o mesmo resultado não muda nada. "
            "APROVADO leva o pedido para EM_PRODUCAO. NEGADO ou ERRO mantêm o pedido aguardando pagamento.", ["Pagamentos"],
            {"200": _resp("Resultado registrado", ref("RetornoPagamento"), {
                "id_pedido": 1, "status_pagamento": "Pagamento efetuado", "status_pagamento_codigo": "EFETUADO",
                "status_pedido": "Em produção", "status_pedido_codigo": "EM_PRODUCAO", "ja_processado": False}),
             "400": E400, "401": _erro("Chave de API inválida", "CHAVE_INVALIDA", "Chave de API inválida ou ausente (cabeçalho X-API-Key)."),
             "404": _erro("Transação não encontrada", "TRANSACAO_NAO_ENCONTRADA", "Transação não encontrada."),
             "409": _erro("Transação já finalizada com outro resultado", "RETORNO_CONFLITANTE", "Esta transação já foi finalizada com outro resultado.")},
            seguranca=[{"gatewayKey": []}],
            corpo=_corpo(ref("RetornoEntrada"), {"id_transacao_externa": "SIM-108A5BD44745", "resultado": "APROVADO"}))},
        "/auditoria": {"get": _op(
            "Consultar auditoria", "GERENTE (somente a própria unidade) ou MATRIZ. Registros de ações sensíveis: PEDIDO_CRIADO, STATUS_ALTERADO, PAGAMENTO_SOLICITADO e PAGAMENTO_RETORNO.",
            ["Auditoria"],
            {"200": _resp("Registros", _pagina("#/components/schemas/Auditoria"), {"itens": [{
                "id": 2, "tipo_ator": "EQUIPE", "id_ator": 1, "id_pedido": 1, "acao": "STATUS_ALTERADO",
                "detalhe": "EM_PRODUCAO -> PRONTO", "data_acao": "2026-11-21T13:10:00Z"}], "pagina": 1, "tamanho": 20, "total": 1}),
             "400": _erro("Parâmetro inválido", "PARAMETRO_INVALIDO", "'id_pedido' deve ser um número inteiro."), "401": E401, "403": E403},
            seguranca=JWT, parametros=[_param("id_pedido", "query", "Filtra pelo pedido", "integer"), _param("acao", "query", "Filtra pela ação")] + PAGINACAO)},
    }

    num = {"type": "number", "format": "float"}
    schemas = {
        "Erro": {"type": "object", "description": "Formato único de erro de toda a API.", "properties": {
            "erro": {"type": "string", "description": "Código estável do erro"}, "mensagem": {"type": "string"},
            "detalhes": {"type": "array", "items": {"type": "object"}}}, "required": ["erro", "mensagem"]},
        "CadastroCliente": {"type": "object", "required": ["nome", "cpf", "email", "senha", "data_nascimento", "consentimento_lgpd"], "properties": {
            "nome": {"type": "string", "minLength": 3, "maxLength": 120}, "cpf": {"type": "string"}, "email": {"type": "string", "format": "email"},
            "senha": {"type": "string", "minLength": 8, "maxLength": 72}, "data_nascimento": {"type": "string", "format": "date"},
            "cidade": {"type": "string"}, "consentimento_lgpd": {"type": "boolean", "description": "Precisa ser true"}}},
        "Cliente": {"type": "object", "properties": {
            "id": {"type": "integer"}, "nome": {"type": "string"}, "email": {"type": "string"}, "cpf": {"type": "string", "description": "Mascarado"},
            "data_nascimento": {"type": "string", "format": "date"}, "idade": {"type": "integer"}, "cidade": {"type": "string"},
            "consentimento_lgpd": {"type": "boolean"}, "data_consentimento": {"type": "string", "format": "date-time"}}},
        "Login": {"type": "object", "required": ["login", "senha"], "properties": {"login": {"type": "string"}, "senha": {"type": "string"}}},
        "Token": {"type": "object", "properties": {"access_token": {"type": "string"}, "token_type": {"type": "string"},
                                                    "expires_in": {"type": "integer"}, "perfil": {"type": "string", "enum": ["CLIENTE", "FUNCIONARIO", "GERENTE", "MATRIZ"]}}},
        "UnidadeEntrada": {"type": "object", "required": ["nome", "cidade", "regiao", "tipo_cozinha"], "properties": {
            "nome": {"type": "string"}, "cidade": {"type": "string"}, "regiao": {"type": "string"}, "tipo_cozinha": {"type": "string", "enum": ["COMPLETA", "REDUZIDA"]}}},
        "Unidade": {"type": "object", "properties": {"id": {"type": "integer"}, "nome": {"type": "string"}, "cidade": {"type": "string"},
                                                      "regiao": {"type": "string"}, "tipo_cozinha": {"type": "string"}}},
        "Cardapio": {"type": "object", "properties": {"unidade": ref("Unidade"), "data_referencia": {"type": "string", "format": "date"},
                                                       "itens": {"type": "array", "items": {"type": "object"}}}},
        "DisponibilidadeEntrada": {"type": "object", "required": ["esta_disponivel"], "properties": {"esta_disponivel": {"type": "boolean"}, "preco_local": {**num, "nullable": True}}},
        "Disponibilidade": {"type": "object", "properties": {"id_unidade": {"type": "integer"}, "id_sabor": {"type": "integer"}, "esta_disponivel": {"type": "boolean"},
                                                              "preco_local": {**num, "nullable": True}, "preco_vigente": num}},
        "ProdutoEntrada": {"type": "object", "required": ["nome"], "properties": {"nome": {"type": "string"}, "descricao": {"type": "string"}}},
        "Produto": {"type": "object", "properties": {"id": {"type": "integer"}, "nome": {"type": "string"}, "descricao": {"type": "string"}}},
        "SaborEntrada": {"type": "object", "required": ["nome", "preco_base"], "properties": {
            "nome": {"type": "string"}, "preco_base": num, "data_inicio_venda": {"type": "string", "format": "date", "nullable": True},
            "data_fim_venda": {"type": "string", "format": "date", "nullable": True}}},
        "Sabor": {"type": "object", "properties": {"id": {"type": "integer"}, "id_produto": {"type": "integer"}, "nome": {"type": "string"}, "preco_base": num,
                                                    "data_inicio_venda": {"type": "string", "nullable": True}, "data_fim_venda": {"type": "string", "nullable": True}}},
        "PedidoEntrada": {"type": "object", "required": ["id_unidade", "canalPedido", "itens"], "properties": {
            "id_unidade": {"type": "integer"}, "canalPedido": {"type": "string", "enum": CANAIS},
            "id_cliente": {"type": "integer", "description": "Opcional, usado pela equipe no balcão"},
            "itens": {"type": "array", "minItems": 1, "maxItems": 30, "items": {"type": "object", "required": ["id_sabor", "quantidade"], "properties": {
                "id_sabor": {"type": "integer"}, "quantidade": {"type": "integer", "minimum": 1, "maximum": 50}}}}}},
        "PedidoResumo": {"type": "object", "properties": {"id": {"type": "integer"}, "id_cliente": {"type": "integer", "nullable": True}, "id_unidade": {"type": "integer"},
                                                           "canalPedido": {"type": "string", "enum": CANAIS}, "status": {"type": "string"},
                                                           "status_codigo": {"type": "string", "enum": STATUS_PEDIDO}, "valor_total": num, "data_pedido": {"type": "string", "format": "date-time"}}},
        "Pedido": {"allOf": [ref("PedidoResumo"), {"type": "object", "properties": {
            "itens": {"type": "array", "items": {"type": "object"}}, "pagamentos": {"type": "array", "items": ref("Pagamento")}}}]},
        "StatusEntrada": {"type": "object", "required": ["status"], "properties": {"status": {"type": "string", "enum": STATUS_PEDIDO}}},
        "StatusPedido": {"type": "object", "properties": {"id": {"type": "integer"}, "status": {"type": "string"}, "status_codigo": {"type": "string", "enum": STATUS_PEDIDO},
                                                           "pagamento": {"allOf": [ref("Pagamento")], "nullable": True}}},
        "Pagamento": {"type": "object", "properties": {"id": {"type": "integer"}, "id_pedido": {"type": "integer"}, "status": {"type": "string"}, "status_codigo": {"type": "string"},
                                                        "valor": num, "id_transacao_externa": {"type": "string"}, "data_retorno": {"type": "string", "nullable": True}}},
        "RetornoEntrada": {"type": "object", "required": ["id_transacao_externa", "resultado"], "properties": {
            "id_transacao_externa": {"type": "string"}, "resultado": {"type": "string", "enum": ["APROVADO", "NEGADO", "ERRO"]}}},
        "RetornoPagamento": {"type": "object", "properties": {"id_pedido": {"type": "integer"}, "status_pagamento": {"type": "string"}, "status_pagamento_codigo": {"type": "string"},
                                                               "status_pedido": {"type": "string"}, "status_pedido_codigo": {"type": "string"}, "ja_processado": {"type": "boolean"}}},
        "Auditoria": {"type": "object", "properties": {"id": {"type": "integer"}, "tipo_ator": {"type": "string", "enum": ["CLIENTE", "EQUIPE", "GATEWAY"]},
                                                        "id_ator": {"type": "integer", "nullable": True}, "id_pedido": {"type": "integer", "nullable": True},
                                                        "acao": {"type": "string"}, "detalhe": {"type": "string"}, "data_acao": {"type": "string", "format": "date-time"}}},
    }
    return {
        "openapi": "3.0.3",
        "info": {"title": "Raízes do Nordeste · API", "version": "1.0.0",
                 "description": "API REST de pedidos da rede Raízes do Nordeste (MVP). Faça login em POST /auth/login, copie o access_token, "
                                "clique em Authorize e informe o token. Logins de teste (senha senha123): cliente@exemplo.com, funcionario, gerente, matriz."},
        "servers": [{"url": "/api/v1"}],
        "tags": [{"name": n} for n in ("Autenticação", "Unidades", "Produtos", "Pedidos", "Pagamentos", "Auditoria")],
        "paths": paths,
        "components": {
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                                "gatewayKey": {"type": "apiKey", "in": "header", "name": "X-API-Key"}},
            "schemas": schemas},
    }


PAGINA_DOCS = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Raízes do Nordeste · Swagger</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"></head>
<body><div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>window.ui = SwaggerUIBundle({url: "/openapi.json", dom_id: "#swagger-ui", persistAuthorization: true});</script>
</body></html>"""
