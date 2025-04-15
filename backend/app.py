from flask import Flask, jsonify
from flask_cors import CORS
from auth.routes import auth_bp
from transactions.routes import transactions_bp
from ai.routes import ai_bp
import config
import logging

# Configure logging
logging.basicConfig(
    filename=config.LOG_FILE,
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Configure CORS
CORS(app, resources={r"/api/*": {"origins": config.CORS_ALLOWED_ORIGINS}})
# Register blueprints
app.register_blueprint(auth_bp, url_prefix=config.AUTH_ENDPOINT)
app.register_blueprint(transactions_bp, url_prefix=config.TRANSACTIONS_ENDPOINT)
app.register_blueprint(ai_bp, url_prefix=config.AI_ENDPOINT)

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)