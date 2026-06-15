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
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
else:
    st.error("Por favor, configure a chave GROQ_API_KEY nos Secrets do Streamlit.")
    st.stop()

# 3. Mapear o PDF por páginas separadas (Para não estourar o limite de contexto)
@st.cache_data
def carregar_paginas_pdf():
    caminho_pdf = "LeisIQUAMA.pdf" 
    if os.path.exists(caminho_pdf):
        with st.spinner("Carregando e indexando a base jurídica..."):
            reader = pypdf.PdfReader(caminho_pdf)
            paginas_mapeadas = []
            for i, pagina in enumerate(reader.pages):
                texto = pagina.extract_text()
                if texto:
                    # Limpa e guarda o texto associado ao número da página
                    texto_limpo = " ".join(texto.split())
                    paginas_mapeadas.append({"numero": i + 1, "texto": texto_limpo})
            return paginas_mapeadas
    else:
        st.error("Arquivo LeisIQUAMA.pdf não encontrado no servidor do GitHub.")
        st.stop()

base_paginas = carregar_paginas_pdf()

# 4. Função de Busca Inteligente (Pega apenas o que interessa para a pergunta)
def buscar_trechos_relevantes(pergunta, paginas, max_paginas=4):
    # Divide a pergunta em palavras-chave importantes (ignora conectivos curtos)
    palavras_chave = [p.lower() for p in pergunta.split() if len(p) > 3]
    
    if not palavras_chave:
        return "Nenhum contexto específico selecionado."
    
    paginas_pontuadas = []
    for p in paginas:
        score = 0
        texto_pag_lower = p["texto"].lower()
        for palavra in palavras_chave:
            if palavra in texto_pag_lower:
                score += 1 # Ganha pontos se a palavra da pergunta estiver na página
        
        if score > 0:
            paginas_pontuadas.append((score, p))
            
    # Ordena as páginas que têm mais a ver com a pergunta
    paginas_pontuadas.sort(key=lambda x: x[0], reverse=True)
    
    # Junta o texto das melhores páginas encontradas
    trechos_selecionados = []
    for score, p in paginas_pontuadas[:max_paginas]:
        trechos_selecionados.append(f"[Página {p['numero']}]\n{p['texto']}")
        
    return "\n\n---\n\n".join(trechos_selecionados)

# Instruções de comportamento para o Bot
PROMPT_SISTEMA = """
Você é um assistente virtual oficial para ajudar os cidadãos a tirarem dúvidas sobre as Leis de Controle Urbanístico e Ambiental (IQUAMA) de Aracati.
Regras Cruciais:
1. Seja extremamente preciso. Se a resposta estiver em uma tabela ou anexo, cite detalhadamente (Ex: "O valor é de 300 UFIRM, conforme o Item 10 do Anexo III da Lei Complementar nº 017/2019").
2. Sempre cite a Página, Artigo, Item ou Anexo de onde retirou a informação para dar segurança jurídica ao cidadão.
3. Você deve se basear apenas nos fragmentos de lei fornecidos no contexto.
4. Se a informação NÃO estiver explícita nos fragmentos fornecidos, diga textualmente: "Desculpe, não encontrei essa informação específica nos trechos da legislação consultados. Recomendo consultar diretamente o órgão do IQUAMA." Não invente dados ou valores.
"""

# 5. Inicializar o histórico da conversa na tela
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensagens anteriores na tela
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Onde o cidadão digita a pergunta
if prompt := st.chat_input("Ex: Qual o valor da consulta prévia?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Busca dinamicamente apenas as páginas do PDF que importam para aquela pergunta
            contexto_filtrado = buscar_trechos_relevantes(prompt, base_paginas)
            
            # Monta a mensagem final super leve
            contexto_mensagem = f"TRECHOS EXTRAÍDOS DA LEI:\n{contexto_filtrado}\n\nPERGUNTA DO CIDADÃO: {prompt}"
            
            # Chamada ultra rápida usando o modelo estável da Groq
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": contexto_mensagem}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
            )
            
            texto_resposta = chat_completion.choices[0].message.content
            message_placeholder.markdown(texto_resposta)
            st.session_state.messages.append({"role": "assistant", "content": texto_resposta})
            
        except Exception as e:
            st.error(f"Erro ao processar a resposta da IA: {e}")
