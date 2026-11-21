API_PREFIXO = "/api/v1"


def registrar_rotas(app):
    from app.routes.auditoria import bp as auditoria_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.pagamentos import bp as pagamentos_bp
    from app.routes.pedidos import bp as pedidos_bp
    from app.routes.produtos import bp as produtos_bp
    from app.routes.unidades import bp as unidades_bp

    from flask import Response, jsonify

    from app.openapi import PAGINA_DOCS, construir_spec

    @app.get("/openapi.json")
    def openapi_json():
        return jsonify(construir_spec())

    @app.get("/docs")
    def swagger_ui():
        return Response(PAGINA_DOCS, mimetype="text/html")

    for bp in (auth_bp, unidades_bp, produtos_bp, pedidos_bp, pagamentos_bp, auditoria_bp):
        app.register_blueprint(bp, url_prefix=API_PREFIXO)
