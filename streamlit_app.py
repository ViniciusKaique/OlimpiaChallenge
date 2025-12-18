import streamlit as st
import yfinance as yf
import pandas as pd
from duckduckgo_search import DDGS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==============================================================================
# ⚙️ 1. CONFIGURAÇÃO E LISTA IBOV (HARDCODED PARA PERFORMANCE)
# ==============================================================================
st.set_page_config(page_title="IBOV AI Master", page_icon="🐂", layout="wide")

# Lista das principais ações do IBOVESPA para monitoramento rápido
# (Adicionei as mais líquidas para não deixar o app pesado demais, mas cobre 90% do volume)
IBOV_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", "ABEV3.SA",
    "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", "B3SA3.SA", "EQTL3.SA",
    "RADL3.SA", "PRIO3.SA", "RAIL3.SA", "GGBR4.SA", "JBSS3.SA", "VIVT3.SA", "CSAN3.SA",
    "ELET3.SA", "SBSP3.SA", "TIMS3.SA", "LREN3.SA", "MGLU3.SA", "ASAI3.SA", "HYPE3.SA",
    "CMIG4.SA", "TRPL4.SA", "CPLE6.SA", "CCRO3.SA", "GOLL4.SA", "AZUL4.SA", "EMBR3.SA"
]

# ==============================================================================
# 🚀 2. MOTOR DE DADOS OTIMIZADO (ETL)
# ==============================================================================

@st.cache_data(ttl=600)  # Cache de 10 minutos para não travar o app
def get_ibov_ranking():
    """
    Baixa dados de TODOS os tickers de uma vez só (Batch Download).
    É muito mais rápido do que um loop for.
    """
    try:
        # Baixa apenas os últimos 2 dias para calcular a variação
        df = yf.download(IBOV_TICKERS, period="2d", progress=False)['Close']
        
        # Se baixou com sucesso, pega o último preço e o penúltimo
        if len(df) >= 2:
            current_prices = df.iloc[-1]
            prev_prices = df.iloc[-2]
            
            # Calcula Variação %
            changes = ((current_prices - prev_prices) / prev_prices) * 100
            
            # Cria um DataFrame limpo
            ranking = pd.DataFrame({
                'Ticker': changes.index.str.replace('.SA', ''),
                'Price': current_prices.values,
                'Change': changes.values
            })
            
            # Remove dados vazios (caso alguma ação não tenha negociado)
            ranking = ranking.dropna()
            
            # Separa Top 5
            top_high = ranking.sort_values(by='Change', ascending=False).head(5)
            top_low = ranking.sort_values(by='Change', ascending=True).head(5)
            
            return top_high, top_low
    except Exception as e:
        st.error(f"Erro ao atualizar mercado: {e}")
        return pd.DataFrame(), pd.DataFrame()

def get_company_logo(ticker):
    """Tenta pegar o logo via Yahoo Finance. Retorna None se falhar."""
    try:
        t = yf.Ticker(ticker + ".SA" if not ticker.endswith(".SA") else ticker)
        return t.info.get('logo_url', None)
    except:
        return None

def get_web_search(query):
    """Busca notícias com links para o relatório (Requisito PDF)."""
    text = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, region='br-pt', safesearch='off', max_results=4))
            for r in results:
                text += f"TITULO: {r['title']} | LINK: {r['url']} | FONTE: {r['source']}\n"
    except Exception as e:
        text = f"Erro na busca: {e}"
    return text

# ==============================================================================
# 🧠 3. INTELIGÊNCIA (GEMINI)
# ==============================================================================

def run_analysis(company, ticker):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=st.secrets["GOOGLE_API_KEY"],
        temperature=0.1
    )
    
    # Busca focada
    web_data = get_web_search(f"{company} {ticker} notícias mercado financeiro status invest")

    prompt = PromptTemplate.from_template(
        """
        Você é um analista sênior.
        EMPRESA: {company} ({ticker})
        DADOS DA WEB: {web_data}
        
        Gere um relatório técnico em Markdown.
        
        ### 🏢 1. Perfil e Setor
        * **Setor:** [Identifique o setor]
        * **Histórico/Produtos:** [Resumo curto baseada nos dados]

        ### 📰 2. Destaques (Com Links)
        (Liste 3 notícias. OBRIGATÓRIO: Use o formato de link Markdown).
        
        * 🔗 **[TITULO_DA_NOTICIA](LINK_DA_NOTICIA)**
          *Fonte:* [Nome da Fonte]

        ### 💡 3. Veredito
        [Conclusão de 1 linha]
        """
    )
    
    return (prompt | llm | StrOutputParser()).invoke({
        "company": company, "ticker": ticker, "web_data": web_data
    })

# ==============================================================================
# 🖥️ 4. INTERFACE
# ==============================================================================

def main():
    st.title("📊 IBOVESPA AI Tracker")
    
    # --- BLOCO 1: DASHBOARD DE MERCADO (CACHEADO) ---
    st.markdown("### 🔥 Termômetro do Mercado (Top 5)")
    
    with st.spinner("Atualizando cotações do IBOVESPA..."):
        highs, lows = get_ibov_ranking()

    if not highs.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🚀 Maiores Altas")
            # Usando st.dataframe ou metricas para ficar bonito
            for _, row in highs.iterrows():
                st.markdown(f"**{row['Ticker']}**: :green[R$ {row['Price']:.2f} (+{row['Change']:.2f}%)]")
                
        with col2:
            st.markdown("#### 🔻 Maiores Baixas")
            for _, row in lows.iterrows():
                st.markdown(f"**{row['Ticker']}**: :red[R$ {row['Price']:.2f} ({row['Change']:.2f}%)]")
    
    st.markdown("---")

    # --- BLOCO 2: PESQUISA DETALHADA ---
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_input = st.text_input("Pesquisar Ação (Nome ou Ticker):", placeholder="Ex: Petrobras, WEGE3...")
    with col_btn:
        st.write("") # Espaçamento
        st.write("")
        btn_go = st.button("Analisar 🔎", use_container_width=True)

    if btn_go and search_input:
        # 1. Identificar Ticker (Rápido)
        llm_quick = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=st.secrets["GOOGLE_API_KEY"])
        ticker = (PromptTemplate.from_template("Responda APENAS o ticker da ação {q} na B3 (ex: VALE3). Sem .SA") 
                  | llm_quick | StrOutputParser()).invoke({"q": search_input}).strip()
        
        # 2. Pegar Logo e Preço Específico
        logo_url = get_company_logo(ticker)
        
        # Busca cotação específica atualizada
        try:
            stock = yf.Ticker(f"{ticker}.SA")
            price = stock.fast_info.last_price
            change = ((price - stock.fast_info.previous_close) / stock.fast_info.previous_close) * 100
            color = "green" if change >= 0 else "red"
        except:
            price = 0.0
            change = 0.0
            color = "gray"

        # --- EXIBIÇÃO DO CABEÇALHO DA AÇÃO ---
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 2])
            
            with c1:
                if logo_url:
                    st.image(logo_url, width=100)
                else:
                    st.header("🏢") # Placeholder se não tiver logo
            
            with c2:
                st.subheader(f"{search_input.upper()}")
                st.caption(f"Ticker: {ticker}")
                
            with c3:
                st.metric(label="Cotação Atual", value=f"R$ {price:.2f}", delta=f"{change:.2f}%")

        # --- RELATÓRIO GEMINI (NO EXPANDER) ---
        with st.expander("📋 Ver Análise Fundamentalista e Notícias (Gemini AI)", expanded=True):
            with st.spinner("Lendo notícias e gerando insights..."):
                report = run_analysis(search_input, ticker)
                st.markdown(report)

if __name__ == "__main__":
    main()