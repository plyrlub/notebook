"""应用入口
最小可运行示例：用 Flask 提供健康检查端点
实际项目按需替换为你的业务代码
"""
import os
from flask import Flask, jsonify


def create_app() -> Flask:
    app = Flask(__name__)
    app_env = os.getenv("APP_ENV", "dev")

    @app.get("/health")
    def health():
        return jsonify(status="ok", env=app_env), 200

    @app.get("/")
    def index():
        return jsonify(
            message="hello from myapp",
            env=app_env,
        ), 200

    return app


# gunicorn 调用入口
app = create_app()


if __name__ == "__main__":
    # 开发模式
    app.run(host="0.0.0.0", port=8080, debug=False)
