from flask import Flask, render_template, jsonify, request, redirect, url_for, flash 
import json
import random 
import time
import os
from dotenv import load_dotenv

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
    obter_nome_jogo_igdb, realizar_analise_dashboards, buscar_sugestoes_igdb
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

# ----------------------------------------------------
# 2. IMPORTAÇÃO E ATRIBUIÇÃO CRUCIAL DO USER_LOADER
# ----------------------------------------------------
# ATENÇÃO: Importamos os modelos (que dependem de 'db' inicializado)
# e atribuímos o loader IMEDIATAMENTE após a inicialização do 'login_manager'.
from python.models import User, load_user

# 3. ATRIBUIÇÃO DA FUNÇÃO OBRIGATÓRIA (CRUCIAL!)

# ============================================
# 🗺️ ROTAS PRINCIPAIS (Front-end)
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
        return redirect(url_for('listagem'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # 1. Checa se o usuário existe E se o hash da senha confere
        if user and bcrypt.check_password_hash(user.password, password):
            # 2. Login bem-sucedido
            login_user(user, remember=True)
            flash('Login bem-sucedido!', 'success')
            
            # Redireciona para a próxima página ou listagem
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('listagem'))
        else:
            # 3. Falha no login
            flash('Login falhou. Verifique e-mail e senha.', 'danger')
            
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Página de Cadastro (Lógica REAL com DB)."""
    # Se o usuário já estiver logado, redireciona
    if current_user.is_authenticated:
        flash('Você já está logado!', 'info')
        return redirect(url_for('listagem'))

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 1. Validação (Email já existe)
        if User.query.filter_by(email=email).first():
            flash('Este e-mail já está cadastrado. Tente fazer login.', 'danger')
            return render_template('cadastro.html')
        
        # 2. Criação Segura do HASH
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # 3. Criação do Usuário e Salva no Banco
        novo_usuario = User(email=email, username=username, password=hashed_password)
        db.session.add(novo_usuario)
        db.session.commit()
        
        flash(f'Conta criada com sucesso para {username}! Faça login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('index'))

@app.route('/listagem')
@login_required #
def listagem():
    """
    Rota que busca e renderiza a listagem de jogos com paginação (IGDB).
    Usa funções importadas de python.utilidades.
    """
    
    # Captura o termo de pesquisa e a página.
    termo_pesquisa = request.args.get('pesquisa', '').strip()
    pagina_atual = request.args.get('pagina', 1, type=int)
    
    offset = (pagina_atual - 1) * JOGOS_POR_PAGINA
    
    token = gerar_token()
    
    # Chama a função de busca com o termo de pesquisa
    jogos_brutos = buscar_catalogo_igdb(token, offset, termo_pesquisa)

    jogos_listagem = []
    for jogo in jogos_brutos:
        cover_url_path = jogo.get("cover", {}).get("url")
        
        if not jogo.get("id"):
            continue

        if cover_url_path:
            # Substitui 't_thumb' por 't_cover_big' para melhor qualidade visual
            imagem_url = "https:" + cover_url_path.replace("t_thumb", "t_cover_big")
        else:
            # URL de placeholder caso a capa não exista
            imagem_url = "https://via.placeholder.com/300x400?text=Sem+Imagem" 
        
        jogos_listagem.append({
            "id": jogo.get("id"),
            "titulo": jogo.get("name", "Jogo Sem Nome"),
            "imagem_url": imagem_url 
        })
        
    proxima_pagina_existe = len(jogos_brutos) == JOGOS_POR_PAGINA 
        
    return render_template(
        'listagem.html', 
        jogos=jogos_listagem,
        pagina_atual=pagina_atual,
        proxima_pagina_existe=proxima_pagina_existe,
        termo_pesquisa=termo_pesquisa 
    )

# ROTA DINÂMICA: Exibe os Detalhes do Jogo
@app.route('/dashboards/<game_id>')
@login_required
def dashboards_detalhes(game_id):
    
    """
    Busca detalhes completos do jogo na IGDB e renderiza o template de detalhes.
    """
    
    detalhes_jogo = obter_detalhes_jogo_igdb(game_id)
    
    if not detalhes_jogo:
        return "Jogo não encontrado ou erro na API.", 404

    game_name = detalhes_jogo.get("name", "Jogo Desconhecido")
    
    return render_template(
        'detalhes.html',  
        game_id=game_id, 
        game_name=game_name,
        detalhes=detalhes_jogo 
    )


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


# ============================================
# 🚀 INICIALIZAÇÃO DO FLASK
# ============================================
if __name__ == '__main__':
    print("Iniciando servidor Flask...")
    
    # ⚠️ BLOCO DE CRIAÇÃO DE TABELAS (Execute APENAS uma vez!)
    with app.app_context():
        # DESCOMENTE A LINHA ABAIXO, RODE 'python app.py' E COMENTE-A NOVAMENTE!
        #db.create_all() 
        print("Verificação: O banco de dados está pronto para uso.")
        
    app.run(debug=True)