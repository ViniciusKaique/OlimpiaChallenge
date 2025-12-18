import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Invest Pro", page_icon="📈", layout="wide")

# ==============================================================================
# 2. CSS CUSTOMIZADO (VISUAL)
# ==============================================================================
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
    /* Cards de Ações */
    .stock-card {
        background-color: #262730;
        border: 1px solid #3f3f46;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .logo-img {
        width: 28px; height: 28px; border-radius: 50%; 
        background-color: #fff; padding: 2px; margin-right: 10px;
    }
    .txt-green { color: #4ade80; font-weight: bold; }
    .txt-red { color: #f87171; font-weight: bold; }
    
    /* Notícias */
    .news-card {
        background-color: #1f2937;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
        border-left: 3px solid #3b82f6;
        transition: background 0.2s;
    }
    .news-card:hover { background-color: #374151; }
    .news-title { font-size: 0.85rem; color: #e5e7eb; font-weight: 500; text-decoration: none; }
    .news-time { font-size: 0.7rem; color: #9ca3af; margin-top: 4px; display: block; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. GERENCIAMENTO DE ESTADO (LOGIN)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'usuario_atual' not in st.session_state:
    st.session_state['usuario_atual'] = ""

def check_login():
    """Valida o login e SALVA o usuário numa variável persistente"""
    user = st.session_state.get("username_input", "")
    password = st.session_state.get("password_input", "")
    
    if user == "admin" and password == "1234":
        st.session_state['logged_in'] = True
        st.session_state['usuario_atual'] = user # Salva aqui para usar depois
    else:
        st.error("Usuário ou senha incorretos")

def logout():
    st.session_state['logged_in'] = False
    st.session_state['usuario_atual'] = ""
    st.rerun()

# ==============================================================================
# 4. TELA DE LOGIN
# ==============================================================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=80)
        st.title("Acesso Restrito")
        st.text_input("Usuário", key="username_input")
        st.text_input("Senha", type="password", key="password_input")
        st.button("Entrar", on_click=check_login, use_container_width=True)
        st.info("Use: admin / 1234")
    st.stop() # Para o código aqui se não estiver logado

# ==============================================================================
# 5. LÓGICA DE DADOS (COM CORREÇÕES)
# ==============================================================================

# Lista de ativos
MONITORED_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", 
    "ABEV3.SA", "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", 
    "B3SA3.SA", "EQTL3.SA", "PRIO3.SA", "LREN3.SA", "MGLU3.SA", "HYPE3.SA"
]

@st.cache_data(ttl=600)
def get_dashboard_data():
    try:
        df = yf.download(MONITORED_TICKERS, period="2d", progress=False)['Close']
        if df.empty: return pd.DataFrame(), pd.DataFrame()
        
        changes = ((df.iloc[-1] - df.iloc[-2]) / df.iloc[-2]) * 100
        prices = df.iloc[-1]
        
        data = pd.DataFrame({'Change': changes, 'Price': prices})
        data.index = data.index.str.replace('.SA', '')
        
        return data.sort_values('Change', ascending=False).head(5), \
               data.sort_values('Change', ascending=True).head(5)
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=3600)
def get_logo(ticker):
    """Busca logo via Google Favicons"""
    try:
        # Mapeamento rápido manual para evitar chamadas lentas
        manual_map = {
            "VALE3": "vale.com", "PETR4": "petrobras.com.br", "ITUB4": "itau.com.br",
            "BBDC4": "bradesco.com.br", "BBAS3": "bb.com.br", "WEGE3": "weg.net",
            "MGLU3": "magazineluiza.com.br", "LREN3": "lojasrenner.com.br", "HAPV3": "hapvida.com.br"
        }
        
        domain = manual_map.get(ticker)
        if not domain:
            # Fallback lento: busca no Yahoo
            t = yf.Ticker(f"{ticker}.SA")
            url = t.info.get('website', '')
            if url: domain = url.split('//')[-1].split('/')[0].replace('www.', '')
            else: return "https://via.placeholder.com/32"
            
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    except:
        return "https://via.placeholder.com/32"

@st.cache_data(ttl=900)
def get_market_news():
    """Sistema robusto de busca de notícias (Índice -> Petrobras -> Mock)"""
    news_items = []
    
    # 1. Tenta Ibovespa
    try:
        news = yf.Ticker("^BVSP").news
        if news: news_items = news
    except: pass
    
    # 2. Se vazio, tenta Petrobras (sempre tem notícia)
    if not news_items:
        try:
            news = yf.Ticker("PETR4.SA").news
            if news: news_items = news
        except: pass
        
    # Formata o resultado se encontrou algo
    final_news = []
    if news_items:
        for n in news_items[:5]:
            # Proteção contra campos faltando
            if 'title' in n and 'link' in n:
                final_news.append({
                    "title": n['title'],
                    "link": n['link'],
                    "pub": n.get('publisher', 'Yahoo Finance'),
                    "time": datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%H:%M')
                })
    
    # 3. Fallback final (Mock) para garantir que não fique em branco
    if not final_news:
        final_news = [
            {"title": "Ibovespa fecha em leve alta com cenário externo", "link": "#", "pub": "InfoMoney", "time": "10:30"},
            {"title": "Dólar opera instável à espera de dados dos EUA", "link": "#", "pub": "Investing.com", "time": "09:45"},
            {"title": "Petrobras anuncia novos planos de investimento", "link": "#", "pub": "Reuters", "time": "08:15"},
            {"title": "Banco Central reforça compromisso com meta de inflação", "link": "#", "pub": "Valor", "time": "08:00"}
        ]
        
    return final_news

def resolve_ticker(user_input):
    """Converte nomes comuns em Tickers"""
    mapa = {
        "ITAU": "ITUB4.SA", "ITAÚ": "ITUB4.SA", "ITUB": "ITUB4.SA",
        "VALE": "VALE3.SA",
        "PETROBRAS": "PETR4.SA", "PETRO": "PETR4.SA",
        "BRADESCO": "BBDC4.SA",
        "AMBEV": "ABEV3.SA",
        "WEG": "WEGE3.SA",
        "MAGALU": "MGLU3.SA", "MAGAZINE": "MGLU3.SA",
        "NUBANK": "ROXO34.SA"
    }
    clean_input = user_input.upper().strip()
    
    # Se já estiver no mapa, retorna o ticker correto
    if clean_input in mapa:
        return mapa[clean_input]
    
    # Se o usuário digitou só o código (ex: WEGE3), adiciona .SA
    if not clean_input.endswith(".SA") and len(clean_input) <= 6:
        return f"{clean_input}.SA"
        
    return clean_input

def run_langchain_analysis(ticker_query):
    """Executa a análise via Gemini 1.5 Flash"""
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            return "⚠️ Erro: GOOGLE_API_KEY não encontrada no secrets.toml"
            
        # ATUALIZAÇÃO DO MODELO: gemini-1.5-flash é o padrão atual
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
        
        template = """Você é um analista financeiro sênior. 
        Analise a ação {ticker} listando 3 pontos positivos (Bullish) ou negativos (Bearish) baseados em análise fundamentalista geral.
        Seja direto e use bullet points. Responda em Português."""
        
        chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
        return chain.invoke({"ticker": ticker_query})
    except Exception as e:
        return f"Erro na IA: {str(e)}"

# ==============================================================================
# 6. LAYOUT DO DASHBOARD
# ==============================================================================

# BARRA LATERAL
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=50)
    st.write(f"Olá, **{st.session_state['usuario_atual']}**")
    st.caption("🟢 Sistema Online")
    st.divider()
    st.button("🔒 Sair", on_click=logout, type="primary")

st.title("📊 Mercado Agora")

# Colunas Principais
col_dados, col_noticias = st.columns([2, 1], gap="large")

with col_dados:
    highs, lows = get_dashboard_data()
    
    if not highs.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🚀 Maiores Altas")
            for ticker, row in highs.iterrows():
                logo = get_logo(ticker)
                st.markdown(f"""
                <div class="stock-card">
                    <div style="display:flex; align-items:center">
                        <img src="{logo}" class="logo-img">
                        <div><b>{ticker}</b><br><span style="font-size:12px; color:#aaa">R$ {row['Price']:.2f}</span></div>
                    </div>
                    <div class="txt-green">+{row['Change']:.2f}%</div>
                </div>""", unsafe_allow_html=True)
                
        with c2:
            st.markdown("#### 🔻 Maiores Baixas")
            for ticker, row in lows.iterrows():
                logo = get_logo(ticker)
                st.markdown(f"""
                <div class="stock-card">
                    <div style="display:flex; align-items:center">
                        <img src="{logo}" class="logo-img">
                        <div><b>{ticker}</b><br><span style="font-size:12px; color:#aaa">R$ {row['Price']:.2f}</span></div>
                    </div>
                    <div class="txt-red">{row['Change']:.2f}%</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.warning("Carregando dados do mercado...")

# Coluna de Notícias
with col_noticias:
    st.markdown("#### 📰 Manchetes")
    news_list = get_market_news()
    for n in news_list:
        st.markdown(f"""
        <a href="{n['link']}" target="_blank" style="text-decoration:none;">
            <div class="news-card">
                <div class="news-title">{n['title']}</div>
                <span class="news-time">{n['pub']} • {n['time']}</span>
            </div>
        </a>""", unsafe_allow_html=True)

st.divider()

# Langchain e Gráficos
st.subheader("🤖 Analista & Gráficos")
ticker_input = st.text_input("Pesquisar Ativo (ex: Itau, Vale, PETR4):", placeholder="Digite o nome ou código...")

if ticker_input:
    # Usa a função inteligente para corrigir o nome
    full_ticker = resolve_ticker(ticker_input)
    clean_ticker = full_ticker.replace(".SA", "")
    
    cgraf, cia = st.columns([2, 1])
    
    with cgraf:
        st.markdown(f"**Histórico: {clean_ticker}**")
        try:
            stock_obj = yf.Ticker(full_ticker)
            hist = stock_obj.history(period="1y")
            
            if not hist.empty:
                tab1, tab2, tab3 = st.tabs(["1 Mês", "6 Meses", "1 Ano"])
                with tab1: st.line_chart(hist["Close"].tail(22), color="#3b82f6")
                with tab2: st.line_chart(hist["Close"].tail(126), color="#3b82f6")
                with tab3: st.line_chart(hist["Close"], color="#3b82f6")
            else:
                st.warning(f"Dados não encontrados para {full_ticker}. Tente usar o código oficial (ex: ITUB4).")
        except:
            st.error("Erro ao carregar gráfico.")

    with cia:
        st.markdown("**🧠 Opinião da IA**")
        with st.spinner(f"Analisando {clean_ticker}..."):
            analise = run_langchain_analysis(clean_ticker)
            st.info(analise)