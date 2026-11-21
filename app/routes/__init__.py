API_PREFIXO = "/api/v1"


def registrar_rotas(app):
    from app.routes.auth import bp as auth_bp
    from app.routes.pagamentos import bp as pagamentos_bp
    from app.routes.pedidos import bp as pedidos_bp
    from app.routes.produtos import bp as produtos_bp
    from app.routes.unidades import bp as unidades_bp

    for bp in (auth_bp, unidades_bp, produtos_bp, pedidos_bp, pagamentos_bp):
        app.register_blueprint(bp, url_prefix=API_PREFIXO)
