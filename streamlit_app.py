import streamlit as st
import yfinance as yf
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
import time

# Imports atualizados do LangChain Core
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ==============================================================================
# BLOCO 1: CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Investment Banking AI", page_icon="📈", layout="wide")

# ==============================================================================
# BLOCO 2: FERRAMENTAS (TOOLS) COM CACHE
# ==============================================================================

# O @st.cache_data impede que o Yahoo bloqueie suas requisições se rodar muitas vezes
@st.cache_data(ttl=600) # Cache válido por 10 minutos
def get_stock_price(ticker_symbol):
    """
    Busca o preço atual. Usa Cache para evitar erro 'Too Many Requests'.
    """
    if not ticker_symbol or ticker_symbol == "DESCONHECIDO":
        return "Ticker não identificado."
    
    # Tratamento para ações brasileiras (B3)
    clean_ticker = ticker_symbol.upper().strip()
    if not clean_ticker.endswith(".SA") and len(clean_ticker) <= 6:
        clean_ticker += ".SA"
        
    try:
        stock = yf.Ticker(clean_ticker)
        # Tenta pegar o preço instantâneo primeiro (mais leve)
        price = stock.fast_info.last_price
        
        # Se falhar, tenta o histórico do dia
        if not price:
            history = stock.history(period="1d")
            if history.empty: return f"Sem dados recentes para {clean_ticker}"
            price = history['Close'].iloc[-1]
            
        return f"R$ {price:.2f}"
    except Exception as e:
        return f"Indisponível no momento (Erro API)"

def get_web_search(query):
    """Busca notícias e informações no DuckDuckGo."""
    try:
        search = DuckDuckGoSearchRun()
        # Adiciona 'brasil' para focar em resultados locais
        return search.run(f"{query}")
    except Exception as e:
        return f"Erro na busca: {str(e)}"

# ==============================================================================
# BLOCO 3: SEGURANÇA (LOGIN)
# ==============================================================================

def check_password():
    """Sistema simples de autenticação via secrets.toml"""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        return True

    st.sidebar.title("🔐 Acesso Restrito")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type="password")

    if st.sidebar.button("Entrar"):
        try:
            if (username == st.secrets["auth"]["username"] and 
                password == st.secrets["auth"]["password"]):
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.sidebar.error("Credenciais inválidas.")
        except Exception:
            st.error("Erro: Configure o arquivo .streamlit/secrets.toml")
            
    return False

# ==============================================================================
# BLOCO 4: LÓGICA DE INTELIGÊNCIA (LANGCHAIN)
# ==============================================================================

def run_analysis(company_name):
    # 1. Configura o Modelo
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=st.secrets["GOOGLE_API_KEY"],
        temperature=0.1
    )

    # 2. Descobrir o Ticker (Rápido)
    ticker_prompt = PromptTemplate.from_template(
        "Identifique o código da ação (Ticker) da empresa {company} na B3. Retorne APENAS o código (Ex: VALE3). Se não achar, retorne DESCONHECIDO."
    )
    ticker_chain = ticker_prompt | llm | StrOutputParser()
    
    with st.status("⚡ Processando em alta velocidade...", expanded=True) as status:
        st.write("🔍 Identificando empresa...")
        ticker = ticker_chain.invoke({"company": company_name}).strip()
        
        # Paralelismo simulado: Já buscamos o preço
        st.write(f"💵 Buscando cotação para {ticker}...")
        stock_price = get_stock_price(ticker)
        
        st.write("🌐 Acessando fontes de notícias (Busca Única)...")
        # OTIMIZAÇÃO: Uma única busca robusta em vez de duas separadas
        # Isso reduz o tempo de espera pela metade
        search_query = f"{company_name} BVMF:{ticker} investor relations notícias financeiras recentes e perfil da empresa"
        web_data = get_web_search(search_query)
        
        status.update(label="Análise Pronta!", state="complete", expanded=False)

    # 3. Geração do Relatório (Prompt Único)
    final_prompt = PromptTemplate.from_template(
        """
        Você é um Analista de Investment Banking Sênior. Gere um relatório Markdown.
        
        EMPRESA: {company} ({ticker})
        PREÇO: {stock_price}
        
        DADOS DA WEB (Notícias + Info):
        {web_data}
        
        ---
        Gere o relatório EXATAMENTE neste formato:
        
        ## 🏢 Relatório: {company}
        **Ticker:** `{ticker}` | **Cotação:** {stock_price}
        
        ### 📊 1. Resumo Corporativo
        (Crie um resumo denso sobre o que a empresa faz baseado nos DADOS DA WEB)
        
        ### 📰 2. Destaques e Notícias
        (Identifique 3 fatos ou notícias recentes nos DADOS DA WEB. Se houver links, inclua-os.)
        * **[Título]**: Resumo do fato.
        * **[Título]**: Resumo do fato.
        
        ### 💡 3. Conclusão
        (Veredito curto sobre o momento da empresa)
        
        Data: 17/12/2025
        """
    )

    full_chain = final_prompt | llm | StrOutputParser()
    
    return full_chain.invoke({
        "company": company_name,
        "ticker": ticker,
        "stock_price": stock_price,
        "web_data": web_data
    })

# ==============================================================================
# BLOCO 5: INTERFACE PRINCIPAL
# ==============================================================================

def main():
    if not check_password():
        st.stop()

    st.title("🏦 IB AI Analyst Agent")
    st.markdown("**Ferramenta de Automação para Análise Preliminar de Empresas (B3)**")
    
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            company = st.text_input("Digite o nome da empresa (ex: Vale, Itaú, Weg):", placeholder="Ex: Petrobras")
        with col2:
            st.write("")
            st.write("")
            btn_gerar = st.button("🚀 Gerar Relatório", use_container_width=True)

    if btn_gerar and company:
        try:
            result = run_analysis(company)
            st.markdown(result)
            
            # Botão de Download (Requisito de documentação/saída)
            st.download_button(
                label="📥 Baixar Relatório Completo (.md)",
                data=result,
                file_name=f"Relatorio_{company.upper()}.md",
                mime="text/markdown"
            )
        except Exception as e:
            st.error(f"Erro Crítico: {e}")

if __name__ == "__main__":
    main()