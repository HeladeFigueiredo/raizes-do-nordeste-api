"""Importar todos os modelos aqui garante que o Flask-Migrate enxergue todas as tabelas."""
from app.models.acesso import Equipe, Perfil, Usuario
from app.models.cardapio import Produto, ProdutoUnidade, Sabor, Unidade
from app.models.cliente import Cliente
from app.models.pedido import ItemPedido, Pagamento, Pedido, StatusPagamento, StatusPedido

__all__ = [
    "Equipe", "Perfil", "Usuario",
    "Produto", "ProdutoUnidade", "Sabor", "Unidade",
    "Cliente",
    "ItemPedido", "Pagamento", "Pedido", "StatusPagamento", "StatusPedido",
]
