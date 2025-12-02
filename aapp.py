from flask import Flask, render_template, jsonify, request, redirect, url_for
import requests
import json
import random 

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui' 

# ============================================
# 🔑 CONSTANTES E CONFIGURAÇÕES
# ============================================
CLIENT_ID = "0lng4xfcer47apzz6gf40oy6a7580a" 
CLIENT_SECRET = "s42xggviazhcmzn8hzvwrsy6lgvuwn" 
TOLKIEN_GAME_NAME = "Dungeons & Dragons" 

JOGOS_POR_PAGINA = 100
IGDB_ENDPOINT = "https://api.igdb.com/v4/games"
HELIX_STREAMS_ENDPOINT = "https://api.twitch.tv/helix/streams" 

# ============================================
# 🔄 FUNÇÕES AUXILIARES DE API (Twitch/IGDB)
# ============================================
def gerar_token():
    """Obtém o Access Token da Twitch."""
    url = "https://id.twitch.tv/oauth2/token"
    params = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
    try:
        resp = requests.post(url, params=params)
        resp.raise_for_status()
        return resp.json().get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter token da Twitch: {e}")
        return None

def obter_nome_jogo_igdb(game_id):
    """Busca o nome de um jogo específico usando seu ID da IGDB."""
    token = gerar_token()
    if not token: return {"name": "Erro"}
    
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }
    body = f"fields name; where id = {game_id};"

    try:
        resp = requests.post(IGDB_ENDPOINT, headers=headers, data=body)
        resp.raise_for_status()
        data = resp.json()
        if data:
            return data[0]
        return {"name": "Jogo Não Encontrado"}
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar nome do jogo na IGDB: {e}")
        return {"name": "Erro de API"}

def obter_detalhes_jogo_igdb(game_id):
    """
    Busca detalhes completos do jogo na IGDB.
    Inclui summary, total_rating, genres, platforms e cover.
    """
    token = gerar_token()
    if not token: return None
    
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }
    fields = "name, summary, total_rating, total_rating_count, genres.name, platforms.name, cover.url"
    body = f"fields {fields}; where id = {game_id};"

    try:
        resp = requests.post(IGDB_ENDPOINT, headers=headers, data=body)
        resp.raise_for_status()
        data = resp.json()
        if data:
            jogo = data[0]
            cover_url_path = jogo.get("cover", {}).get("url")
            if cover_url_path:
                # Substitui 't_thumb' por 't_cover_big' para obter uma imagem maior
                jogo["imagem_url"] = "https:" + cover_url_path.replace("t_thumb", "t_cover_big")
            else:
                jogo["imagem_url"] = "https://via.placeholder.com/300x400?text=Sem+Imagem" 
                
            return jogo
        return None
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar detalhes do jogo na IGDB: {e}")
        return None


def buscar_catalogo_igdb(token, offset_value, game_name=None):
    """Busca jogos na IGDB, usando o offset para paginação e ordenando por nome (Alfabética)."""
    if not token: return []
    
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }
    
    # Se houver um nome de jogo, APLICAMOS APENAS O FILTRO DE PESQUISA (sem restrição de rating).
    if game_name:
        # A IGDB usa o operador '~' para ILIKE (case-insensitive e busca parcial).
        # Para garantir a maior amplitude de resultados, removemos o filtro 'total_rating_count > 10'
        # quando o usuário está buscando um nome específico.
        where_clause = f"name ~ \"*{game_name}*\""
    else:
        # Condição inicial para a listagem padrão (sem pesquisa)
        where_clause = "total_rating_count > 10"

    body = (
        f"fields name, cover.url, id; " 
        f"where {where_clause}; " 
        f"sort name asc; " 
        f"limit {JOGOS_POR_PAGINA};"
        f"offset {offset_value};"
    )

    try:
        resp = requests.post(IGDB_ENDPOINT, headers=headers, data=body)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar catálogo IGDB: {e}")
        return []

def buscar_sugestoes_igdb(token, query):
    """Busca um número pequeno de jogos (10) para sugestões de autocomplete, incluindo o URL da capa."""
    if not token or not query:
        return []

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    # CRUCIAL: Adicionar 'cover.url' aos campos solicitados
    body = (
        f"fields name, id, cover.url; " 
        f"where name ~ \"*{query}*\"; "
        f"sort total_rating_count desc; " 
        f"limit 10;"
    )

    try:
        resp = requests.post(IGDB_ENDPOINT, headers=headers, data=body)
        resp.raise_for_status()
        
        # Processa os resultados para incluir a URL da capa formatada
        sugestoes_formatadas = []
        for jogo in resp.json():
            cover_url_path = jogo.get("cover", {}).get("url")
            
            # Formata o URL da imagem, usando um placeholder se não houver capa
            if cover_url_path:
                # Substitui 't_thumb' por 't_cover_small' (ou 't_micro') para o ícone de autocomplete
                imagem_url = "https:" + cover_url_path.replace("t_thumb", "t_cover_small")
            else:
                # Placeholder simples
                imagem_url = "https://via.placeholder.com/30x30?text=I" 
            
            sugestoes_formatadas.append({
                "name": jogo.get("name"),
                "id": jogo.get("id"),
                "image": imagem_url
            })
            
        # Retorna lista de dicionários com {name, id, image}
        return sugestoes_formatadas
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar sugestões IGDB: {e}")
        return []


# ATENÇÃO: A rota /api/sugestoes deve ser atualizada para usar a saída desta função
# ESTA ROTA SUBSTITUI A SUA VERSÃO ANTIGA. Ela chama a função acima e retorna o resultado completo.
@app.route('/api/sugestoes')
def api_sugestoes():
    """Endpoint para busca assíncrona de sugestões de nomes de jogos."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    token = gerar_token()
    
    # A função buscar_sugestoes_igdb JÁ RETORNA OS DADOS NO FORMATO CORRETO (com 'image').
    # Basta retornar esse resultado diretamente para o JavaScript.
    sugestoes = buscar_sugestoes_igdb(token, query) 
    
    return jsonify(sugestoes)

def buscar_streams_por_id(token, game_id):
    """Busca streams ativas na Twitch usando o ID do Jogo (IGDB ID)."""
    if not token: return []
    
    url = HELIX_STREAMS_ENDPOINT
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {token}"}
    params = {
        "game_id": game_id,  
        "first": 8           
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar streams da Twitch por ID: {e}")
        return []


# ============================================
# 📊 FUNÇÃO DE ANÁLISE E PROCESSAMENTO
# ============================================
def realizar_analise_dashboards(game_id, game_name):
    """Processa dados do Twitch Helix para o dashboard de um jogo específico."""
    token = gerar_token()
    
    streams = buscar_streams_por_id(token, game_id) 

    nomes = []
    visualizadores = []
    avaliacoes_simuladas = []
    
    for stream in streams:
        nomes.append(stream.get("title", "Stream Sem Título"))
        visualizadores.append(stream.get("viewer_count", 0))
        
        # Simula a avaliação do usuário
        avaliacao = round(random.uniform(3.0, 5.0), 1)
        avaliacoes_simuladas.append(avaliacao)

    dados_analise = {
        "labels": nomes,
        "data_avaliacoes": avaliacoes_simuladas,
        "data_visualizadores": visualizadores,
        "titulo": f"Streams Ativas de: {game_name}"
    }
    return dados_analise


# ============================================
# 🗺️ ROTAS PRINCIPAIS
# ============================================

@app.route('/')
def index():
    """Página de apresentação."""
    return render_template('index.html') 

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de Login (Simulação)."""
    if request.method == 'POST':
        return redirect(url_for('listagem')) 
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Página de Cadastro (Simulação)."""
    if request.method == 'POST':
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/listagem')
def listagem():
    """
    Rota que busca e renderiza a listagem de jogos com paginação (IGDB).
    Garante que os termos de pesquisa sejam capturados e usados.
    """
    
    # Captura o termo de pesquisa e a página. O termo_pesquisa é crucial para o filtro.
    termo_pesquisa = request.args.get('pesquisa', '').strip()
    pagina_atual = request.args.get('pagina', 1, type=int)
    
    offset = (pagina_atual - 1) * JOGOS_POR_PAGINA
    
    token = gerar_token()
    
    # Chama a função de busca com o termo de pesquisa
    jogos_brutos = buscar_catalogo_igdb(token, offset, termo_pesquisa)

    jogos_listagem = []
    for jogo in jogos_brutos:
        # PONTO CRUCIAL: Trata a falta da capa de forma segura
        cover_url_path = jogo.get("cover", {}).get("url")
        
        # Se um jogo não tiver capa ou ID, ele deve ser ignorado para evitar erros de exibição.
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
        
    proxima_pagina_existe = len(jogos_brutos) == JOGOS_POR_PAGINA # Usa jogos_brutos para verificar se há mais páginas
        
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
    Busca detalhes completos do jogo na IGDB e renderiza detalhes.html,
    passando o game_id e o objeto 'detalhes' necessário.
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

# ROTA DE API: Chamada pelo JavaScript no frontend 
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
    print(f"Iniciando servidor para a categoria: {TOLKIEN_GAME_NAME}")
    app.run(debug=True)