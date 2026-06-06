from flask import Flask
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mongo_uri = app.config["MONGO_URI"]
    client    = MongoClient(mongo_uri)
    db_name   = mongo_uri.rsplit("/", 1)[-1]
    app.db    = client[db_name]

    JWTManager(app)

    from routes.auth import auth_bp
    from routes.reset import reset_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(reset_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)