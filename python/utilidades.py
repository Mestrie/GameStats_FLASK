import requests
import time 
import random 
import os 
from dotenv import load_dotenv 
from python.models import Game
from python.extensions import db
from datetime import datetime, timedelta
from python.traducao import traduzir_texto
from python.models import Filtro




# Carrega as variáveis do arquivo .env
load_dotenv() 

# ============================================
# 🔑 CONSTANTES E CONFIGURAÇÕES
# ============================================
# AGORA LÊ DO ARQUIVO .env
CLIENT_ID = os.getenv("CLIENT_ID") 
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    print("🚨 ERRO CRÍTICO: CLIENT_ID ou CLIENT_SECRET não foram carregados do .env.")
    print("Verifique se o arquivo .env está na raiz e se os nomes das chaves estão corretos.")
    # Você pode até interromper a aplicação se eles estiverem vazios
    # raise EnvironmentError("Credenciais de API não encontradas.")
# Fim das variáveis de ambiente

TOLKIEN_GAME_NAME = "Dungeons & Dragons" 
JOGOS_POR_PAGINA = 500

IGDB_ENDPOINT = "https://api.igdb.com/v4/games"
HELIX_STREAMS_ENDPOINT = "https://api.twitch.tv/helix/streams" 
TOKEN_ENDPOINT = "https://id.twitch.tv/oauth2/token"

# ... o restante do arquivo segue igual
# Variável global simples para cache do token
_token_cache = {"token": None, "expires_at": 0}


 
# ============================================
# 🔄 FUNÇÕES AUXILIARES DE API (Twitch/IGDB)
# ============================================

def gerar_token():
    """Gera ou renova o token de acesso à Twitch/IGDB se ele estiver expirado."""
    agora = time.time()

    if _token_cache["token"] is None or _token_cache["expires_at"] < agora:
        try:
            params = {
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'grant_type': 'client_credentials'
            }
            response = requests.post(TOKEN_ENDPOINT, params=params)
            response.raise_for_status() 
            
            data = response.json()
            token = data['access_token']
            expires_in = data['expires_in']
            
            _token_cache["token"] = token
            # Define a expiração com um buffer de 60 segundos
            _token_cache["expires_at"] = agora + expires_in - 60 
            
            return token
        
        except requests.exceptions.RequestException as e:
            print(f"Erro ao obter token da Twitch: {e}")
            return None
    else:
        return _token_cache["token"]

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
    fields = "name, summary, total_rating, total_rating_count, genres.name, game_modes.name, platforms.name, cover.url, first_release_date, involved_companies.company.name, involved_companies.developer"
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


# python/utilidades.py (Função buscar_catalogo_igdb)

def buscar_catalogo_igdb(
    token,
    offset,
    termo_pesquisa=None,
    platform=None,
    genre=None,
    year=None,
    developer=None,
    mode=None
):
    if not token:
        return []

    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {token}"}

    # ----------------------------
    # Verifica se existe algum filtro ativo
    # ----------------------------
    filtros_ativos = any([platform, genre, year, developer, mode])

    if termo_pesquisa:
        # 🔍 PESQUISA — sem sort (IGDB não aceita), sem where
        termo_pesquisa = termo_pesquisa.replace('"', '')
        
        query = f'''
            search "{termo_pesquisa}";
            fields name, cover.url, total_rating, aggregated_rating,
                   platforms.name, genres.name, game_modes.name,
                   first_release_date, involved_companies.company.name;
            limit {JOGOS_POR_PAGINA};
            offset {offset};
        '''
    else:
        # ----------------------------
        # Monta filtros dinamicamente apenas se existirem
        # ----------------------------
        where_clauses = []

        if platform:
            where_clauses.append(f'platforms.name = "{platform}"')

        if genre:
            where_clauses.append(f'genres.name = "{genre}"')

        if mode:
            where_clauses.append(f'game_modes.name = "{mode}"')

        if developer:
            where_clauses.append(f'involved_companies.company.name = "{developer}"')

        if year:
            from datetime import datetime

            # Converte o início e fim do ano em timestamps Unix
            start_ts = int(datetime(int(year), 1, 1, 0, 0, 0).timestamp())
            end_ts = int(datetime(int(year), 12, 31, 23, 59, 59).timestamp())

            # Adiciona a cláusula where usando os timestamps
            where_clauses.append(f'first_release_date >= {start_ts} & first_release_date <= {end_ts}')


        # ----------------------------
        # Caso NÃO haja filtros → usa a listagem padrão
        # ----------------------------
        if not filtros_ativos:
            query = f'''
                fields name, cover.url, total_rating, aggregated_rating,
                       platforms.name, genres.name, game_modes.name,
                       first_release_date, involved_companies.company.name;
                where total_rating != null | aggregated_rating != null;
                sort name asc;
                limit {JOGOS_POR_PAGINA};
                offset {offset};
            '''
        else:
            # ----------------------------
            # Caso HAJA filtros → aplica where dinâmico
            # ----------------------------
            where_query = " & ".join(where_clauses)

            query = f'''
                fields name, cover.url, total_rating, aggregated_rating,
                       platforms.name, genres.name, game_modes.name,
                       first_release_date, involved_companies.company.name;
                where {where_query};
                sort name asc;
                limit {JOGOS_POR_PAGINA};
                offset {offset};
            '''

    try:
        resp = requests.post(IGDB_ENDPOINT, headers=headers, data=query)
        resp.raise_for_status()
        jogos = resp.json()

        # 🧹 FILTRAR NA PESQUISA TAMBÉM (opcional mas RECOMENDADO)
        if termo_pesquisa:
            jogos = [j for j in jogos if j.get("total_rating") or j.get("aggregated_rating")]
            jogos = sorted(jogos, key=lambda x: x.get("name", "").lower())

        return jogos

    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar catálogo IGDB: {e}")
        return []


# ============================================
# 🔄 Funções de Filtros para botões
 
def buscar_filtros_botoes(token):
    # 🎯 Busca filtros para botões
    # Primeiro tenta buscar do banco de dados
    # Se não existir, busca da IGDB e salva

    if not token:
        return {}

    filtros = {
        "platforms": [],
        "genres": [],
        "modes": [],
        "developers": []
        
    }

    # 🔎 Busca filtros já salvos no banco
    filtros_db = Filtro.query.all()

    if filtros_db:
        for f in filtros_db:
            if f.tipo == "platform":
                filtros["platforms"].append(f.nome)
            elif f.tipo == "genre":
                filtros["genres"].append(f.nome)
            elif f.tipo == "mode":
                filtros["modes"].append(f.nome)
            elif f.tipo == "developer":
                filtros["developers"].append(f.nome)


        return filtros

    # 🌐 Se não existir no banco, busca da IGDB
    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    endpoints = {
        "platform": "platforms",
        "genre": "genres",
        "mode": "game_modes",
        "developer": "companies"
    }

    for tipo, endpoint in endpoints.items():
        query = """
            fields id, name;
            limit 200;
        """

        resp = requests.post(
            f"https://api.igdb.com/v4/{endpoint}",
            headers=headers,
            data=query
        )

        if resp.status_code == 200:
            dados = resp.json()

            for item in dados:
                igdb_id = item.get("id")
                nome = item.get("name")

                if igdb_id and nome:
                    # 💾 Salva o filtro no banco
                    db.session.add(
                        Filtro(
                            igdb_id=igdb_id,
                            tipo=tipo,
                            nome=nome
                        )
                    )

                    # 📌 Adiciona também no retorno
                    if tipo == "platform":
                        filtros["platforms"].append(nome)
                    elif tipo == "genre":
                        filtros["genres"].append(nome)
                    elif tipo == "mode":
                        filtros["modes"].append(nome)
                    elif tipo == "developer":
                        filtros["developers"].append(nome)

    db.session.commit()

    return filtros





def buscar_sugestoes_igdb(token, query):
    """Busca um número pequeno de jogos (10) para sugestões de autocomplete, incluindo o URL da capa."""
    if not token or not query:
        return []

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    body = (
        f"fields name, id, cover.url; " 
        f"where name ~ \"*{query}*\"; "
        f"sort total_rating_count desc; " 
        f"limit 10;"
    )

    try:
        resp = requests.post(IGDB_ENDPOINT, headers=headers, data=body)
        resp.raise_for_status()
        
        sugestoes_formatadas = []
        for jogo in resp.json():
            cover_url_path = jogo.get("cover", {}).get("url")
            
            if cover_url_path:
                # Substitui 't_thumb' por 't_cover_small' para o ícone de autocomplete
                imagem_url = "https:" + cover_url_path.replace("t_thumb", "t_cover_small")
            else:
                imagem_url = "https://via.placeholder.com/30x30?text=I" 
            
            sugestoes_formatadas.append({
                "name": jogo.get("name"),
                "id": jogo.get("id"),
                "image": imagem_url
            })
            
        return sugestoes_formatadas
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar sugestões IGDB: {e}")
        return []

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
# 🔄 Função “get or fetch” (cache inteligente)
# ============================================



def get_or_fetch_game(game_id, max_age_days=7):
    """
    Busca o jogo no banco de dados.
    Se não existir ou estiver desatualizado, busca na IGDB e salva.
    """

    # 1️⃣ Tenta pegar do banco
    jogo = Game.query.get(game_id)

    # 2️⃣ Se existir e ainda for recente, retorna direto
    if jogo and jogo.updated_at:
        limite = datetime.utcnow() - timedelta(days=max_age_days)
        if jogo.updated_at >= limite:
            return jogo

    # 3️⃣ Se não existe ou está velho, busca na API
    dados = obter_detalhes_jogo_igdb(game_id)
    if not dados:
        return None

    # 4️⃣ Se não existia, cria
    if not jogo:
        jogo = Game(id=game_id)

    # 5️⃣ Atualiza dados
    jogo.name = dados.get("name")
    summary_en = dados.get("summary")
    jogo.summary = traduzir_texto(summary_en) if summary_en else None
    jogo.rating = dados.get("total_rating") or 0
    jogo.rating_count = dados.get("total_rating_count")
    jogo.image_url = dados.get("imagem_url")
    jogo.genres = ", ".join([g["name"] for g in dados.get("genres", [])])
    jogo.platforms = ", ".join([p["name"] for p in dados.get("platforms", [])])
    jogo.game_modes = ", ".join([m["name"] for m in dados.get("game_modes", [])])

    # Desenvolvedora / publicadora
    companies = dados.get("involved_companies", [])
    devs = []
    for c in companies:
        if c.get("developer"):
            devs.append(c["company"]["name"])
    jogo.developers = ", ".join(devs)

    # Data
    if dados.get("first_release_date"):
        jogo.release_date = datetime.utcfromtimestamp(
            dados["first_release_date"]
        )
    #jogo.updated_at = datetime.utcnow()

    db.session.add(jogo)
    db.session.commit()

    return jogo
