import streamlit as st
import yfinance as yf
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

# ==============================================================================
# ⚙️ CONFIGURAÇÃO INICIAL
# ==============================================================================
st.set_page_config(
    page_title="Fast Finance AI", 
    page_icon="⚡", 
    layout="wide"
)

# Estilo CSS para limpar a interface e dar destaque
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔐 SIDEBAR & USUÁRIO
# ==============================================================================
with st.sidebar:
    st.header("👤 Perfil do Usuário")
    # Simulação de usuário logado
    st.markdown("""
    **Status:** 🟢 Online  
    **Usuário:** Analista Financeiro  
    **Acesso:** Premium
    """)
    st.divider()
    st.info("💡 Modo Turbo Ativado: Notícias externas desativadas para máxima velocidade.")

# ==============================================================================
# 🧠 LANGCHAIN & IA (GEMINI 1.5 FLASH)
# ==============================================================================

def get_llm():
    """Configura o modelo mais rápido disponível"""
    # Certifique-se de ter sua API KEY no arquivo .streamlit/secrets.toml ou no ambiente
    # Caso não tenha secrets, substitua st.secrets["GOOGLE_API_KEY"] pela string direta (não recomendado para produção)
    api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", # Modelo focado em velocidade
        google_api_key=api_key,
        temperature=0.0
    )

def identify_ticker(company_name):
    """
    Usa LangChain para traduzir 'Nome da Empresa' -> 'Ticker.SA'
    Ex: 'Itaú' -> 'ITUB4.SA'
    """
    llm = get_llm()
    
    template = """
    Você é um especialista em mercado financeiro brasileiro (B3).
    Sua única tarefa é retornar o código (Ticker) da ação principal da empresa solicitada, seguido de '.SA'.
    Se houver ações preferenciais (PN) e ordinárias (ON), prefira a de maior liquidez (geralmente PN final 4 ou Unit final 11).
    
    Exemplos:
    Entrada: Petrobras -> Saída: PETR4.SA
    Entrada: Vale -> Saída: VALE3.SA
    Entrada: Banco do Brasil -> Saída: BBAS3.SA
    
    Entrada: {company}
    Saída (APENAS O CÓDIGO):
    """
    
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    try:
        ticker = chain.invoke({"company": company_name}).strip()
        return ticker
    except Exception as e:
        st.error(f"Erro ao identificar ticker: {e}")
        return None

def generate_summary(company_name, ticker):
    """
    Gera um resumo rápido usando o conhecimento interno do modelo (sem busca web lenta)
    """
    llm = get_llm()
    
    template = """
    Analise a empresa {company} (Ticker: {ticker}).
    Forneça um resumo executivo em Markdown com:
    1. **Setor de Atuação**
    2. **Resumo do Negócio** (máximo 2 frases)
    3. **Principais Produtos/Serviços**
    
    Seja conciso e direto.
    """
    
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    return chain.invoke({"company": company_name, "ticker": ticker})

# ==============================================================================
# 📈 MOTOR DE DADOS (YFINANCE)
# ==============================================================================

@st.cache_data(ttl=300) # Cache de 5 minutos
def get_stock_data(ticker):
    """Busca dados de preço e histórico para o gráfico"""
    try:
        stock = yf.Ticker(ticker)
        
        # Dados instantâneos (mais rápido que baixar histórico completo)
        info = stock.fast_info
        current_price = info.last_price
        prev_close = info.previous_close
        
        delta = ((current_price - prev_close) / prev_close) * 100
        
        # Histórico para o gráfico (últimos 6 meses para ser leve)
        history = stock.history(period="6mo")
        
        return {
            "price": current_price,
            "delta": delta,
            "history": history
        }
    except Exception as e:
        return None

# ==============================================================================
# 🖥️ INTERFACE PRINCIPAL
# ==============================================================================

st.title("🚀 Fast Finance AI Check")
st.markdown("Digite o nome da empresa para uma análise instantânea.")

# Input centralizado
col1, col2 = st.columns([3, 1])
with col1:
    company_input = st.text_input("Nome da Empresa:", placeholder="Ex: Weg, Magazine Luiza, Ambev...")
with col2:
    st.write("") # Espaçamento
    st.write("") 
    analyze_btn = st.button("Analisar Agora", type="primary", use_container_width=True)

if analyze_btn and company_input:
    # 1. Identificação do Ticker (LangChain)
    with st.status("🔍 Identificando ativo...", expanded=True) as status:
        st.write("Consultando Gemini Flash para encontrar o ticker...")
        ticker = identify_ticker(company_input)
        
        if ticker:
            status.update(label=f"Ativo encontrado: {ticker}", state="running")
            
            # 2. Coleta de Dados (Yahoo Finance)
            st.write("Baixando cotações em tempo real...")
            data = get_stock_data(ticker)
            
            # 3. Geração de Resumo (LangChain)
            st.write("Gerando perfil corporativo...")
            summary = generate_summary(company_input, ticker)
            
            status.update(label="Análise Concluída!", state="complete", expanded=False)
        else:
            status.update(label="Erro ao encontrar empresa.", state="error")
            st.stop()

    if data:
        # Layout de Resultados
        st.divider()
        
        # Cabeçalho com Preço
        c_metrics, c_chart = st.columns([1, 2])
        
        with c_metrics:
            st.subheader(f"🏢 {ticker}")
            
            color_delta = "normal"
            if data['delta'] > 0: color_delta = "normal" # Streamlit trata verde como normal/positivo automático
            
            st.metric(
                label="Preço Atual",
                value=f"R$ {data['price']:.2f}",
                delta=f"{data['delta']:.2f}%"
            )
            
            st.markdown("---")
            st.markdown("### 📋 Perfil da Empresa")
            st.markdown(summary)

        with c_chart:
            st.subheader("📈 Performance (6 Meses)")
            # Gráfico de Área do Streamlit é rápido e bonito
            st.area_chart(data['history']['Close'], color="#4CAF50" if data['delta'] > 0 else "#FF5252")

else:
    # Estado Zero (Tela Inicial)
    st.info("Aguardando entrada de dados para iniciar o fluxo LangChain...")