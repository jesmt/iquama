import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import google.generativeai as genai
import PyPDF2
import pandas as pd

# Configuração da IA com Fallback de Segurança (Evita o erro 404 Not Found)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    # Se o flash falhar ou não for encontrado na sua região, ele tenta o pro automaticamente
    model = genai.GenerativeModel('gemini-pro')

st.title("Consultor de Zoneamento")

# Coordenadas padrão ajustadas para a Matriz de Aracati (Centro)
lat = st.number_input("Latitude", format="%.6f", value=-4.5606)
lon = st.number_input("Longitude", format="%.6f", value=-37.7712)

if st.button("Gerar Parecer"):
    try:
        # 1. Carrega o KMZ completo usando o driver KML (Lê todas as pastas internas de uma vez)
        gdf = gpd.read_file("zoneamento_67.kmz", driver='KML')
        gdf = gdf.to_crs(epsg=4326)
        
        # Cria o ponto geográfico (Longitude, Latitude)
        ponto = Point(lon, lat)
        
        # Filtra a zona que contém geometricamente o ponto inserido
        resultado = gdf[gdf.geometry.contains(ponto)]
        
        if not resultado.empty:
            # Identifica de forma robusta o nome da zona usando a coluna 'zona' ou 'Name'
            nome_da_zona = resultado.iloc[0].get('zona', resultado.iloc[0].get('Name', 'Zona Indefinida'))
            st.success(f"Imóvel localizado na: **{nome_da_zona}**")
            
            # 2. Leitura da lei em PDF
            with open("lei_67_OCR.pdf", "rb") as f:
                leitor = PyPDF2.PdfReader(f)
                texto_lei = "\n".join([p.extract_text() for p in leitor.pages if p.extract_text()])
            
            if len(texto_lei) < 100:
                st.warning("Atenção: O PDF parece estar vazio ou sem camadas de texto legíveis.")
            
            # 3. Geração do parecer pela IA
            prompt = f"Você é um técnico de urbanismo. O imóvel está na zona {nome_da_zona}. Baseado no texto da lei fornecido, gere um parecer técnico detalhado sobre os índices permitidos para construção:\n\n{texto_lei[:15000]}"
            
            with st.spinner("Gerando parecer técnico com a IA..."):
                parecer = model.generate_content(prompt)
                st.markdown(parecer.text)
                
        else:
            st.error("Coordenada fora da área mapeada.")
            st.write("---")
            st.write("DEBUG - Informações do mapa lido:")
            st.write(f"Total de polígonos/camadas carregados com sucesso: {len(gdf)}")
            if len(gdf) > 0:
                st.write("Colunas capturadas do arquivo da prefeitura:", gdf.columns.tolist())
            st.write("Dica: Verifique se os números de Latitude e Longitude não foram digitados nos campos invertidos.")
            
    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
        st.write("Dica: Certifique-se de que os arquivos 'zoneamento_67.kmz' e 'lei_67_OCR.pdf' estão na raiz do repositório.")
