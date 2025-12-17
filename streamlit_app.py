import streamlit as st
import yfinance as yf
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
import time

# --- CORREÇÃO: Imports atualizados para versões novas do LangChain ---
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ==============================================================================
# BLOCO 1: CONFIGURAÇÃO INICIAL
# Define o título da página e o ícone na aba do navegador.
# ==============================================================================
st.set_page_config(page_title="Investment Banking AI", page_icon="📈", layout="wide")

# ==============================================================================
# BLOCO 2: FERRAMENTAS (TOOLS)
# Funções Python que buscam dados reais para evitar "alucinação" da IA.
# ==============================================================================

def get_stock_price(ticker_symbol):
    """
    Busca o preço atual de uma ação usando Yahoo Finance.
    Adiciona .SA automaticamente se for ação brasileira.
    """
    if not ticker_symbol:
        return "Símbolo não fornecido."
    
    # Tratamento para ações brasileiras (B3)
    clean_ticker = ticker_symbol.upper().strip()
    if not clean_ticker.endswith(".SA") and len(clean_ticker) <= 6:
        clean_ticker += ".SA"
        
    try:
        stock = yf.Ticker(clean_ticker)
        history = stock.history(period="1d")
        
        if history.empty:
            return f"Não foi possível encontrar dados para {clean_ticker}."
            
        # Pega o último preço de fechamento
        price = history['Close'].iloc[-1]
        currency = stock.info.get('currency', 'BRL')
        return f"{currency} {price:.2f}"
    except Exception as e:
        return f"Erro ao buscar cotação: {str(e)}"

def get_web_search(query):
    """Realiza uma busca na web usando DuckDuckGo (Gratuito)."""
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        return f"Erro na busca: {str(e)}"

# ==============================================================================
# BLOCO 3: SEGURANÇA (LOGIN)
# Simula um login simples verificando dados no arquivo secrets.toml
# ==============================================================================

def check_password():
    """Retorna True se o usuário estiver logado, False caso contrário."""
    
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        return True

    st.sidebar.title("🔐 Login Seguro")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type="password")

    if st.sidebar.button("Entrar"):
        try:
            # Verifica contra os secrets configurados no Streamlit
            if (username == st.secrets["auth"]["username"] and 
                password == st.secrets["auth"]["password"]):
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.sidebar.error("Usuário ou senha incorretos.")
        except FileNotFoundError:
            st.error("Arquivo .streamlit/secrets.toml não encontrado!")
        except KeyError:
            st.error("Secrets mal configurados. Verifique as chaves 'auth'.")
            
    return False

# ==============================================================================
# BLOCO 4: INTELIGÊNCIA (LANGCHAIN + GEMINI)
# A lógica principal: Identifica Ticker -> Busca Dados -> Gera Relatório
# ==============================================================================

def run_analysis(company_name):
    # 1. Configurar o LLM (Gemini)
    # Certifique-se de ter GOOGLE_API_KEY no secrets.toml
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",   # Tente este primeiro
        # OU se falhar: model="gemini-1.0-pro"
        google_api_key=st.secrets["GOOGLE_API_KEY"],
        temperature=0.2
    )

    # 2. Descobrir o Ticker (Ex: "Nubank" -> "ROXO34")
    ticker_prompt = PromptTemplate.from_template(
        """
        Você é um assistente financeiro expert em B3. 
        Retorne APENAS o código de negociação (Ticker) principal da empresa: {company}.
        Regras:
        - Não use a extensão .SA
        - Retorne apenas o código (ex: PETR4, VALE3, MGLU3)
        - Se não souber, retorne "DESCONHECIDO"
        """
    )
    
    ticker_chain = ticker_prompt | llm | StrOutputParser()
    
    # Interface de Status Expansível (Loading bonito)
    with st.status("🔍 Iniciando análise de mercado...", expanded=True) as status:
        st.write("Identificando código da ação...")
        ticker = ticker_chain.invoke({"company": company_name}).strip()
        st.write(f"Ticker identificado: **{ticker}**")
        
        # 3. Executar Tools (Python puro)
        st.write("Consultando Yahoo Finance...")
        stock_price = get_stock_price(ticker)
        
        st.write("Buscando notícias recentes no DuckDuckGo...")
        search_query_news = f"{company_name} brasil notícias financeiras mercado hoje"
        search_query_info = f"{company_name} investor relations business overview"
        
        raw_news = get_web_search(search_query_news)
        raw_info = get_web_search(search_query_info)
        
        status.update(label="Dados coletados com sucesso!", state="complete", expanded=False)

    # 4. Chain Final: Geração do Relatório
    final_prompt = PromptTemplate.from_template(
        """
        Você é um analista Sênior de Investment Banking. Crie um relatório executivo.
        
        EMPRESA: {company}
        PREÇO ATUAL: {stock_price}
        
        CONTEXTO (Busca Web):
        {raw_info}
        
        NOTÍCIAS RECENTES:
        {raw_news}
        
        ---
        Gere um relatório em MARKDOWN seguindo exatamente este formato:
        
        ## 🏢 Análise: {company}
        **Ticker:** {ticker} | **Cotação:** {stock_price}
        
        ### 📊 Resumo Executivo
        [Resumo profissional sobre a empresa e sua atuação no mercado]
        
        ### 📰 Destaques Recentes
        * [Notícia 1]: [Breve análise]
        * [Notícia 2]: [Breve análise]
        
        ### 💡 Conclusão/Outlook
        [Uma frase final sobre o momento da empresa baseada nas notícias]
        """
    )

    full_chain = final_prompt | llm | StrOutputParser()
    
    return full_chain.invoke({
        "company": company_name,
        "ticker": ticker,
        "stock_price": stock_price,
        "raw_info": raw_info,
        "raw_news": raw_news
    })

# ==============================================================================
# BLOCO 5: INTERFACE (STREAMLIT MAIN)
# ==============================================================================

def main():
    # Verifica login antes de mostrar qualquer coisa
    if not check_password():
        st.stop()

    st.title("🤖 AI Investment Banking Analyst")
    st.caption("Powered by Gemini 1.5 Flash & LangChain")
    st.markdown("---")
    
    st.info("💡 Digite o nome de uma empresa brasileira para gerar um relatório automático.")

    with st.form("research_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            company = st.text_input("Nome da Empresa (ex: WEG, Itaú, Ambev):")
        with col2:
            st.write("") # Espaçamento
            st.write("") 
            submitted = st.form_submit_button("🚀 Gerar Relatório", use_container_width=True)

    if submitted and company:
        try:
            result = run_analysis(company)
            st.markdown(result)
            
            # Botão de Download
            st.download_button(
                label="📥 Baixar Relatório (MD)",
                data=result,
                file_name=f"relatorio_{company}.md",
                mime="text/markdown"
            )
        except Exception as e:
            st.error(f"Ocorreu um erro durante a análise: {e}")

if __name__ == "__main__":
    main()