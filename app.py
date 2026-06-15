import streamlit as st
from groq import Groq
import os
import pypdf

# 1. Configuração da página do Chatbot
st.set_page_config(page_title="Assistente IQUAMA", page_icon="🤖")
st.title("🤖 Assistente Virtual - Leis do IQUAMA")
st.caption("Tire suas dúvidas sobre o Controle Urbanístico e Ambiental de Aracati.")

# 2. Configurar a chave da API da Groq
if "GROQ_API_KEY" in st.secrets:
    # Inicializa o cliente oficial da Groq
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
else:
    st.error("Por favor, configure a chave GROQ_API_KEY nos Secrets do Streamlit.")
    st.stop()

# 3. Extrair e otimizar o texto do PDF localmente
@st.cache_data
def extrair_texto_pdf():
    caminho_pdf = "LeisIQUAMA.pdf" 
    if os.path.exists(caminho_pdf):
        with st.spinner("Carregando e processando a base jurídica..."):
            reader = pypdf.PdfReader(caminho_pdf)
            texto_completo = ""
            for pagina in reader.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_completo += texto + "\n"
            
            # Otimização para economizar tamanho de texto (Tokens)
            linhas_limpas = [linha.strip() for linha in texto_completo.split("\n") if linha.strip()]
            return "\n".join(linhas_limpas)
    else:
        st.error("Arquivo LeisIQUAMA.pdf não encontrado no servidor do GitHub.")
        st.stop()

texto_leis = extrair_texto_pdf()

# Instruções de comportamento para o Bot (Prompt de Sistema)
PROMPT_SISTEMA = """
Você é um assistente virtual oficial para ajudar os cidadãos a tirarem dúvidas sobre as Leis de Controle Urbanístico e Ambiental (IQUAMA) de Aracati.
Regras Cruciais:
1. Seja extremamente preciso. Se a resposta estiver em uma tabela ou anexo, cite detalhadamente (Ex: "O valor é de 300 UFIRM, conforme o Item 10 do Anexo III da Lei Complementar nº 017/2019").
2. Sempre cite o Artigo, Parágrafo, Item ou Anexo de onde retirou a informação.
3. Se a informação NÃO estiver no texto fornecido pelo usuário, diga textualmente: "Desculpe, não encontrei essa informação específica na legislação disponível. Recomendo consultar diretamente o órgão do IQUAMA." Não invente dados.
"""

# 4. Inicializar o histórico da conversa na tela
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensagens anteriores na tela
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Onde o cidadão digita a pergunta
if prompt := st.chat_input("Ex: Qual o valor da consulta prévia?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Construímos o contexto juntando as leis com a pergunta atual
            contexto_mensagem = f"BASE DE LEIS DISPONÍVEL:\n{texto_leis}\n\nPERGUNTA DO CIDADÃO: {prompt}"
            
            # Chamada usando o modelo Llama 3 da Meta via Groq (Super Rápido e Gratuito)
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": contexto_mensagem}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.2, # Baixa temperatura para o bot ser ultra focado e não inventar nada
            )
            
            texto_resposta = chat_completion.choices[0].message.content
            message_placeholder.markdown(texto_resposta)
            st.session_state.messages.append({"role": "assistant", "content": texto_resposta})
            
        except Exception as e:
            st.error(f"Erro ao processar a resposta da IA: {e}")
