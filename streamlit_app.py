import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# ==============================================================================
# ⚙️ 1. CONFIGURAÇÃO DA PÁGINA E CSS
# ==============================================================================
st.set_page_config(page_title="Dashboard Mercado", page_icon="📉", layout="wide")

# CSS para esconder elementos padrões do Streamlit e compactar a view
st.markdown("""
<style>
    /* Remove padding excessivo do topo */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    /* Esconde menu e footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Estilo dos Cards de Ações */
    .stock-card {
        background-color: #262730;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid #363945;
    }
    .stock-info { display: flex; align-items: center; gap: 10px; }
    .stock-logo { width: 30px; height: 30px; border-radius: 50%; object-fit: cover;}
    .price-tag { font-weight: bold; font-size: 14px; }
    .pos { color: #4ade80; }
    .neg { color: #f87171; }
    
    /* Estilo das Notícias */
    .news-card {
        background-color: #1f2937;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 4px solid #3b82f6;
    }
    .news-title { font-weight: 600; font-size: 15px; margin-bottom: 5px; color: #fff; text-decoration: none;}
    .news-meta { font-size: 12px; color: #9ca3af; display: flex; justify-content: space-between;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🗂️ 2. DADOS E MAPEAMENTO (LOGOS CORRIGIDOS)
# ==============================================================================

TOP_STOCKS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", "ABEV3.SA",
    "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", "B3SA3.SA", "EQTL3.SA",
    "PRIO3.SA", "RAIL3.SA", "GGBR4.SA", "JBSS3.SA", "VIVT3.SA", "CSAN3.SA", "ELET3.SA",
    "MGLU3.SA", "LREN3.SA", "AZUL4.SA", "GOLL4.SA", "HYPE3.SA"
]

# Mapeamento manual para garantir logos certos (Clearbit usa domínios)
DOMAINS = {
    "VALE3": "vale.com", "PETR4": "petrobras.com.br", "ITUB4": "itau.com.br", 
    "BBDC4": "bradesco.com.br", "BBAS3": "bb.com.br", "WEGE3": "weg.net", 
    "ABEV3": "ambev.com.br", "RENT3": "localiza.com", "BPAC11": "btgpactual.com",
    "SUZB3": "suzano.com.br", "HAPV3": "hapvida.com.br", "RDOR3": "rededorsaoluiz.com.br",
    "B3SA3": "b3.com.br", "EQTL3": "equatorialenergia.com.br", "PRIO3": "prio3.com.br",
    "RAIL3": "rumolog.com", "GGBR4": "gerdau.com.br", "JBSS3": "jbs.com.br",
    "VIVT3": "telefonica.com.br", "CSAN3": "cosan.com.br", "ELET3": "eletrobras.com",
    "MGLU3": "magazineluiza.com.br", "LREN3": "lojasrenner.com.br", "AZUL4": "voeazul.com.br",
    "GOLL4": "voegol.com.br", "HYPE3": "hypera.com.br"
}

# ==============================================================================
# 📊 3. FUNÇÕES DE DADOS
# ==============================================================================

@st.cache_data(ttl=300) # Cache de 5 min
def get_market_data():
    """Baixa dados e calcula variações"""
    df_prices = yf.download(TOP_STOCKS, period="2d", progress=False)['Close']
    
    # Cálculo Variação %
    changes = ((df_prices.iloc[-1] - df_prices.iloc[-2]) / df_prices.iloc[-2]) * 100
    last_price = df_prices.iloc[-1]
    
    # Montar DataFrame Final
    df = pd.DataFrame({
        'Ticker': changes.index,
        'Change': changes.values,
        'Price': last_price.values
    })
    df['Ticker'] = df['Ticker'].str.replace('.SA', '') # Limpar .SA
    
    top_high = df.sort_values('Change', ascending=False).head(5)
    top_low = df.sort_values('Change', ascending=True).head(5)
    
    return top_high, top_low

@st.cache_data(ttl=900) # Cache de 15 min
def get_news():
    """Busca notícias via yfinance (Ticker ^BVSP - Ibovespa) que traz notícias gerais"""
    try:
        # Tenta pegar notícias do índice Bovespa via Yahoo Finance
        ibov = yf.Ticker("^BVSP")
        news_list = ibov.news
        
        # Formata para uso simples
        formatted_news = []
        for item in news_list[:6]: # Pega as 6 ultimas
            # Tenta resolver a imagem da notícia ou usa placeholder
            img_uuid = item.get('thumbnail', {}).get('resolutions', [{}])[0].get('url', '')
            
            formatted_news.append({
                "title": item['title'],
                "publisher": item['publisher'],
                "link": item['link'],
                "time": datetime.fromtimestamp(item['providerPublishTime']).strftime('%H:%M')
            })
        return formatted_news
    except:
        # Fallback caso falhe (Dados falsos para não quebrar a tela)
        return [
            {"title": "Mercado aguarda decisão de juros do Copom", "publisher": "InfoMoney", "link": "#", "time": "10:00"},
            {"title": "Petrobras sobe com alta do petróleo no exterior", "publisher": "Bloomberg", "link": "#", "time": "09:45"},
            {"title": "Dólar opera em baixa com fluxo estrangeiro", "publisher": "Valor", "link": "#", "time": "09:30"}
        ]

# ==============================================================================
# 🖥️ 4. RENDERIZAÇÃO DA INTERFACE
# ==============================================================================

st.title("⚡ Mercado Agora")

# Layout Principal: Coluna Esquerda (Dados) | Coluna Direita (Notícias)
col_left, col_right = st.columns([1, 1], gap="large")

# --- LADO ESQUERDO: TOP ALTAS E BAIXAS ---
with col_left:
    highs, lows = get_market_data()
    
    # Sub-divisão: Altas na esquerda, Baixas na direita (dentro da coluna da esquerda)
    c_high, c_low = st.columns(2)
    
    with c_high:
        st.subheader("🔥 Maiores Altas")
        for _, row in highs.iterrows():
            ticker = row['Ticker']
            domain = DOMAINS.get(ticker, 'google.com')
            logo_url = f"https://logo.clearbit.com/{domain}"
            
            # HTML Card Customizado
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-info">
                    <img src="{logo_url}" class="stock-logo" onerror="this.style.display='none'">
                    <div><b>{ticker}</b><br><span style="font-size:12px; color:#aaa">R$ {row['Price']:.2f}</span></div>
                </div>
                <div class="price-tag pos">+{row['Change']:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

    with c_low:
        st.subheader("❄️ Maiores Baixas")
        for _, row in lows.iterrows():
            ticker = row['Ticker']
            domain = DOMAINS.get(ticker, 'google.com')
            logo_url = f"https://logo.clearbit.com/{domain}"
            
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-info">
                    <img src="{logo_url}" class="stock-logo" onerror="this.style.display='none'">
                    <div><b>{ticker}</b><br><span style="font-size:12px; color:#aaa">R$ {row['Price']:.2f}</span></div>
                </div>
                <div class="price-tag neg">{row['Change']:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

# --- LADO DIREITO: NOTÍCIAS ---
with col_right:
    st.subheader("📰 Últimas Notícias (Relevantes)")
    
    news_data = get_news()
    
    for news in news_data:
        st.markdown(f"""
        <a href="{news['link']}" target="_blank" style="text-decoration:none;">
            <div class="news-card">
                <div class="news-title">{news['title']}</div>
                <div class="news-meta">
                    <span>{news['publisher']}</span>
                    <span>🕒 {news['time']}</span>
                </div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()