from flask_login import UserMixin
from python.extensions import db, login_manager


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)   # IGDB ID
    name = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text)
    rating = db.Column(db.Float)
    rating_count = db.Column(db.Integer)
    genres = db.Column(db.Text)        # "RPG, Action"
    platforms = db.Column(db.Text)     # "PS4, PC"
    game_modes = db.Column(db.Text)    # "Single-player"
    developers = db.Column(db.Text)
    release_date = db.Column(db.Date)
    image_url = db.Column(db.String(300))
    updated_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        onupdate=db.func.now()
    )

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    rating = db.Column(db.Integer, nullable=False)  # 0 a 100
    comment = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=db.func.now())

    # 🔗 Relacionamentos
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)

    # 🔒 Um usuário só pode avaliar um jogo uma vez
    __table_args__ = (
        db.UniqueConstraint('user_id', 'game_id', name='unique_user_game_review'),
    )

    user = db.relationship('User', backref='reviews')
    game = db.relationship('Game', backref='reviews')

class Filtro(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    igdb_id = db.Column(db.Integer, nullable=False)   # ID original da IGDB
    tipo = db.Column(db.String(50), nullable=False)   # platform | genre | mode | developer
    nome = db.Column(db.String(200), nullable=False)

    updated_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        onupdate=db.func.now()
    )

    __table_args__ = (
        db.UniqueConstraint('igdb_id', 'tipo', name='unique_igdb_filter'),
    )

    def __repr__(self):
        return f"<Filtro {self.tipo}: {self.nome}>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
