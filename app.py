# app.py (No topo)
from flask import Flask, render_template, jsonify, request, redirect, url_for
# ...
import json
import random 
import time
import os # ⬅️ ADICIONE ESTE
from dotenv import load_dotenv # ⬅️ ADICIONE ESTE

# Carrega as variáveis do arquivo .env
load_dotenv() # ⬅️ ADICIONE ESTE

# 🎯 Importa de 'python.utilidades'
from python.utilidades import (
    # CLIENT_ID, CLIENT_SECRET FORAM REMOVIDOS DAQUI
    JOGOS_POR_PAGINA,
    gerar_token, buscar_catalogo_igdb, obter_detalhes_jogo_igdb,
    obter_nome_jogo_igdb, realizar_analise_dashboards, buscar_sugestoes_igdb
)

# Configuração da aplicação Flask
app = Flask(__name__)
# AGORA LÊ DO AMBIENTE (FLASK_SECRET_KEY)
# O segundo argumento ('chave_de_desenvolvimento_insegura') é um valor de fallback.
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'chave_de_desenvolvimento_insegura')

# ============================================
# 🗺️ ROTAS PRINCIPAIS (Front-end)
# ============================================

@app.route('/')
def index():
    """Página de apresentação."""
    return render_template('index.html') 

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de Login (Simulação)."""
    if request.method == 'POST':
        # Simulação de login
        return redirect(url_for('listagem')) 
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Página de Cadastro (Simulação)."""
    if request.method == 'POST':
        # Simulação de cadastro
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/listagem')
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
    app.run(debug=True)