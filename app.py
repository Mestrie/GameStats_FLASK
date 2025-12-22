from flask import Flask, render_template, jsonify, request, redirect, url_for, flash 
import json
import random 
import time
import os
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from datetime import timedelta
from flask_login import login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask import render_template
from python.utilidades import get_or_fetch_game
from python.models import User, Game, Review
from sqlalchemy import func
from flask import abort
from datetime import datetime
from python.utilidades import cadastrar_usuario





#Funções para geração e verificação de tokens de reset de senha
def gerar_token_reset(user_id, expires_sec=3600):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(user_id, salt='reset-senha-salt')

def verificar_token_reset(token, expires_sec=3600):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token, salt='reset-senha-salt', max_age=expires_sec)
    except:
        return None
    return user_id

# 🔑 IMPORTAÇÕES ESSENCIAIS DO FLASK-LOGIN
from flask_login import current_user, login_user, logout_user, login_required 

# 🔑 IMPORTA AS INSTÂNCIAS DAS EXTENSÕES
from python.extensions import db, bcrypt, login_manager 

# Carrega as variáveis do arquivo .env
load_dotenv() 

# 🎯 Importa de 'python.utilidades'
from python.utilidades import (
    JOGOS_POR_PAGINA,
    gerar_token, buscar_catalogo_igdb, obter_detalhes_jogo_igdb, 
    obter_nome_jogo_igdb, realizar_analise_dashboards, buscar_sugestoes_igdb, buscar_filtros_botoes
)

# Configuração da aplicação Flask
app = Flask(__name__)

# ----------------------------------------------------
# 📌 CONFIGURAÇÕES E CONEXÃO DAS EXTENSÕES (Init Step)
# ----------------------------------------------------
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'chave_de_desenvolvimento_insegura')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 1. CONECTA TODAS AS INSTÂNCIAS AO OBJETO 'app'
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.session_protection = "strong"  # Melhorar proteção da sessão
login_manager.remember_cookie_duration = timedelta(minutes=30)  # Expira a sessão depois de 30 minutos



# ----------------------------------------------------
# 2. IMPORTAÇÃO E ATRIBUIÇÃO CRUCIAL DO USER_LOADER
# ----------------------------------------------------
# ATENÇÃO: Foi importado os modelos (que dependem de 'db' inicializado)
# e atribuímos o loader IMEDIATAMENTE após a inicialização do 'login_manager'.
from python.models import User, load_user

# 3. ATRIBUIÇÃO DA FUNÇÃO OBRIGATÓRIA (CRUCIAL!)

# ============================================
# ROTAS PRINCIPAIS (Front-end)
# ============================================

@app.route('/')
def index():
    """Página de apresentação."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de Login (Lógica REAL com DB)."""
    # Se o usuário já estiver logado, redireciona
    if current_user.is_authenticated:
        flash('Você já está logado!', 'info')
        return redirect(url_for('listagem'))  # Redireciona para a listagem se já estiver logado

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login bem-sucedido!', 'success')
            next_page = request.args.get('next')  # Para redirecionar para a página que o usuário queria acessar
            return redirect(next_page) if next_page else redirect(url_for('listagem'))  # Redireciona para a listagem

        flash('Login falhou. Verifique e-mail e senha.', 'danger')
    return render_template('login.html')


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    # Evita acesso à página de cadastro por usuários autenticados
    if current_user.is_authenticated:
        flash('Você já está logado.', 'info')
        return redirect(url_for('listagem'))

    if request.method == 'POST':
        # Dados do formulário
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        # Geração do hash da senha
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        # Criação do usuário (valida duplicidade e trata erro de integridade)
        sucesso, mensagem = cadastrar_usuario(
            email=email,
            username=username,
            password_hash=password_hash
        )

        # Feedback ao usuário
        flash(mensagem, 'success' if sucesso else 'danger')

        # Redirecionamento pós-cadastro
        if sucesso:
            return redirect(url_for('login'))

    # Renderização inicial ou em caso de erro
    return render_template('cadastro.html')


'''
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('index'))
'''
@app.route("/alterar_senha", methods=["GET", "POST"])
@login_required
def alterar_senha():
    if request.method == "POST":
        # Obtém a senha atual e a nova senha do formulário
        atual = request.form["senha_atual"]
        nova = request.form["nova_senha"]

        # Verifica se a senha atual corresponde ao hash armazenado (Flask-Bcrypt)
        if not bcrypt.check_password_hash(current_user.password, atual):
            # Exibe mensagem de erro caso a senha atual esteja incorreta
            flash("Senha atual incorreta.", "danger")
            return redirect(url_for("alterar_senha"))

        # Gera o hash da nova senha e armazena no objeto do usuário
        current_user.password = bcrypt.generate_password_hash(nova).decode("utf-8")
        # Salva alterações no banco de dados
        db.session.commit()

        # Exibe mensagem de sucesso e redireciona para o perfil
        flash("Senha atualizada com sucesso!", "success")
        return redirect(url_for("perfil"))

    # Renderiza a página de alteração de senha
    return render_template("alterar_senha.html")



@app.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = gerar_token_reset(user.id)
            link_reset = url_for('reset_senha', token=token, _external=True)
            # Aqui  envia o email com link_reset
            print("Link de reset (teste):", link_reset)
        flash('Se o email existir no sistema, você receberá um link para reset de senha.', 'info')
    return render_template('esqueci_senha.html')

@app.route('/reset_senha/<token>', methods=['GET', 'POST'])
def reset_senha(token):
    user_id = verificar_token_reset(token)
    if not user_id:
        flash('O link de reset é inválido ou expirou.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if request.method == 'POST':
        nova_senha = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(nova_senha).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Sua senha foi atualizada com sucesso!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_senha.html')

PLATFORM_MAP = {
    "PS4": "PlayStation 4",
    "PC": "PC (Microsoft Windows)",
    "XBOX ONE": "Xbox One",
    "Switch": "Nintendo Switch"
}

@app.route('/listagem')
@login_required
def listagem():
    # ----------------------------
    # 📝 Parâmetros da URL
    # ----------------------------
    termo_pesquisa = request.args.get('pesquisa', '').strip()
    platform_filter = request.args.get('platform')   # filtro de plataforma
    genre_filter = request.args.get('genre')         # filtro de gênero
    year_filter = request.args.get('year')           # filtro de ano
    developer_filter = request.args.get('developer') # filtro de desenvolvedora
    mode_filter = request.args.get('mode')           # filtro de modo
    pagina_atual = request.args.get('pagina', 1, type=int)

    offset = (pagina_atual - 1) * JOGOS_POR_PAGINA
    token = gerar_token()

    # ----------------------------
    # 🔘 Filtros para botões
    # ----------------------------
    filtros = buscar_filtros_botoes(token)

    # ----------------------------
    # 🎮 Busca dos jogos na IGDB
    # ----------------------------
    jogos_brutos = buscar_catalogo_igdb(
        token=token,
        offset=offset,
        termo_pesquisa=termo_pesquisa,
        platform=platform_filter,
        genre=genre_filter,
        year=year_filter,
        developer=developer_filter,
        mode=mode_filter
    )

    # ----------------------------
    # 🗂️ Processamento e filtros adicionais
    # ----------------------------
    jogos_listagem = []
    for jogo in jogos_brutos:
        # 🖼️ Capa
        cover_url_path = jogo.get("cover", {}).get("url")
        imagem_url = (
            "https:" + cover_url_path.replace("t_thumb", "t_cover_big")
            if cover_url_path
            else "https://via.placeholder.com/300x400?text=Sem+Imagem"
        )

        # ----------------------------
        # 🔧 Filtros extras de segurança
        # ----------------------------
        # Plataforma
        if platform_filter and platform_filter not in ", ".join([p["name"] for p in jogo.get("platforms", [])]):
            continue

        # Gênero
        if genre_filter and genre_filter not in ", ".join([g["name"] for g in jogo.get("genres", [])]):
            continue

        # Ano
        if year_filter:
            release_ts = jogo.get("first_release_date")
            if not release_ts:
                continue
            ano_jogo = datetime.utcfromtimestamp(release_ts).year
            if str(ano_jogo) != year_filter:
                continue

        # Desenvolvedora
        if developer_filter:
            developers_list = [c["company"]["name"] for c in jogo.get("involved_companies", []) if c.get("developer")]
            if developer_filter not in ", ".join(developers_list):
                continue

        # Modo
        if mode_filter and mode_filter not in ", ".join([m["name"] for m in jogo.get("game_modes", [])]):
            continue

        # ----------------------------
        # 📌 Adiciona jogo à lista final
        # ----------------------------
        jogos_listagem.append({
            "id": jogo.get("id"),
            "titulo": jogo.get("name", "Jogo Sem Nome"),
            "imagem_url": imagem_url
        })

    # ----------------------------
    # 🔜 Paginação
    # ----------------------------
    proxima_pagina_existe = len(jogos_brutos) == JOGOS_POR_PAGINA

    # ----------------------------
    # 📤 Renderiza template
    # ----------------------------
    return render_template(
        'listagem.html',
        jogos=jogos_listagem,
        pagina_atual=pagina_atual,
        proxima_pagina_existe=proxima_pagina_existe,
        termo_pesquisa=termo_pesquisa,
        platform_filter=platform_filter,
        genre_filter=genre_filter,
        year_filter=year_filter,
        developer_filter=developer_filter,
        mode_filter=mode_filter,
        filtros=filtros
    )




@app.route('/dashboards/<int:game_id>')
@login_required
def dashboards_detalhes(game_id):

    detalhes_jogo = get_or_fetch_game(game_id)
    if not detalhes_jogo:
        abort(404)

    review_usuario = Review.query.filter_by(
        user_id=current_user.id,
        game_id=game_id
    ).first()

    # 📊 Média das notas
    media_usuarios = db.session.query(
        func.avg(Review.rating)
    ).filter_by(game_id=game_id).scalar()

    # 👥 Quantidade de usuários que avaliaram
    quantidade_usuarios = db.session.query(
        func.count(Review.id)
    ).filter_by(game_id=game_id).scalar()

    reviews = Review.query.filter_by(game_id=game_id).all()

    return render_template(
        "detalhes.html",
        detalhes=detalhes_jogo,
        game_id=game_id,
        review_usuario=review_usuario,
        media_usuarios=media_usuarios,
        quantidade_usuarios=quantidade_usuarios,  # ⬅️ AQUI
        reviews=reviews
    )




@app.route("/perfil")
@login_required
def perfil():
    return render_template("perfil.html", user=current_user)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for('login'))

# ============================================
# 🖥️ ROTAS DE API (Retornam JSON)
# ============================================

@app.route('/api/sugestoes')
def api_sugestoes():
    """Endpoint para busca assíncrona de sugestões de nomes de jogos (autocomplete)."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    token = gerar_token()
    
    # A função buscar_sugestoes_igdb já retorna os dados no formato correto (com 'image').
    sugestoes = buscar_sugestoes_igdb(token, query) 
    
    return jsonify(sugestoes)


@app.route('/api/analises/<game_id>')
def api_analises_filtrada(game_id):
    """Retorna dados de análise (Twitch Helix) filtrados por ID do Jogo."""
    
    game_info = obter_nome_jogo_igdb(game_id)
    game_name = game_info.get("name", "Jogo Desconhecido")
    
    dados = realizar_analise_dashboards(game_id, game_name)
    return jsonify(dados)

@app.route('/review/<int:game_id>', methods=['POST'])
@login_required
def salvar_review(game_id):
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')

    # Verifica se já existe review
    review_existente = Review.query.filter_by(
        user_id=current_user.id,
        game_id=game_id
    ).first()

    if review_existente:
        review_existente.rating = rating
        review_existente.comment = comment
    else:
        nova_review = Review(
            rating=rating,
            comment=comment,
            user_id=current_user.id,
            game_id=game_id
        )
        db.session.add(nova_review)

    db.session.commit()
    flash('Review salva com sucesso!', 'success')

    return redirect(url_for('dashboards_detalhes', game_id=game_id))

# ============================================
# 🚀 INICIALIZAÇÃO DO FLASK
# ============================================
if __name__ == '__main__':
    print("Iniciando servidor Flask...")
    
    # ⚠️ BLOCO DE CRIAÇÃO DE TABELAS (Execute APENAS uma vez!)
    with app.app_context():
        # DESCOMENTE A LINHA ABAIXO, RODE 'python app.py' E COMENTE-A NOVAMENTE!
        db.create_all() 
        print("Verificação: O banco de dados está pronto para uso.")
        
    app.run(debug=True)