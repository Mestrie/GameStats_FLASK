from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

# Apenas cria as instâncias. A conexão com o objeto 'app' (init_app)
# será feita no arquivo app.py, quebrando o ciclo de importação.

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

login_manager.login_view = 'login' 
login_manager.login_message_category = 'info'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'