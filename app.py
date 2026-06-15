import streamlit as st
import google.generativeai as genai
import os
import pypdf

# 1. Configuração da página do Chatbot
st.set_page_config(page_title="Assistente IQUAMA", page_icon="🤖")
st.title("🤖 Assistente Virtual - Leis do IQUAMA")
st.caption("Tire suas dúvidas sobre o Controle Urbanístico e Ambiental de Aracati.")

# 2. Configurar a chave da API do Gemini
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Por favor, configure a chave GEMINI_API_KEY nos Secrets do Streamlit.")
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
            
            # Otimização crucial: Remove espaços múltiplos e quebras de linha repetidas
            # Isso reduz o tamanho do texto enviado pela metade sem perder nenhuma palavra da lei!
            linhas_limpas = [linha.strip() for linha in texto_completo.split("\n") if linha.strip()]
            return "\n".join(linhas_limpas)
    else:
        st.error("Arquivo LeisIQUAMA.pdf não encontrado no servidor do GitHub.")
        st.stop()

texto_leis = extrair_texto_pdf()

# Instruções de comportamento para o Bot
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
            # Voltamos para o 1.5-flash que aceita chaves gratuitas na hora
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=PROMPT_SISTEMA
            )
            
            # Construímos o contexto compactado
            contexto_mensagem = f"BASE DE LEIS DISPONÍVEL:\n{texto_leis}\n\nPERGUNTA DO CIDADÃO: {prompt}"
            
            response = model.generate_content(contexto_mensagem)
            
            texto_resposta = response.text
            message_placeholder.markdown(texto_resposta)
            st.session_state.messages.append({"role": "assistant", "content": texto_resposta})
            
        except Exception as e:
            st.error(f"Erro ao processar a resposta da IA: {e}")
