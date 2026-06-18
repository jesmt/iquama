import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import google.generativeai as genai
import PyPDF2
import pandas as pd
import zipfile
import tempfile
import os

# Configuração da IA com Fallback de Segurança
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    model = genai.GenerativeModel('gemini-pro')

st.title("Consultor de Zoneamento")

# Coordenadas padrão da Matriz de Aracati
lat = st.number_input("Latitude", format="%.6f", value=-4.5606)
lon = st.number_input("Longitude", format="%.6f", value=-37.7712)

if st.button("Gerar Parecer"):
    try:
        # 1. Descompacta o KMZ para um KML temporário direto no servidor
        with zipfile.ZipFile("zoneamento_67.kmz", "r") as z:
            # Encontra o arquivo KML oculto dentro do pacote KMZ
            kml_interno = [f for f in z.namelist() if f.endswith('.kml')][0]
            
            # Cria um arquivo temporário físico no disco do Streamlit
            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_file:
                tmp_file.write(z.read(kml_interno))
                tmp_path = tmp_file.name

        # 2. Carrega o arquivo temporário usando o Geopandas padrão (que funciona perfeitamente)
        gdf = gpd.read_file(tmp_path)
        gdf = gdf.to_crs(epsg=4326)
        
        # Deleta o arquivo temporário imediatamente para não ocupar espaço no servidor
        os.unlink(tmp_path)
        
        # Cria o ponto geográfico (Longitude, Latitude)
        ponto = Point(lon, lat)
        
        # Filtra a zona correspondente
        resultado = gdf[gdf.geometry.contains(ponto)]
        
        if not resultado.empty:
            nome_da_zona = resultado.iloc[0].get('zona', resultado.iloc[0].get('Name', 'Zona Indefinida'))
            st.success(f"Imóvel localizado na: **{nome_da_zona}**")
            
            # 3. Leitura da lei em PDF
            with open("lei_67_OCR.pdf", "rb") as f:
                leitor = PyPDF2.PdfReader(f)
                texto_lei = "\n".join([p.extract_text() for p in leitor.pages if p.extract_text()])
            
            if len(texto_lei) < 100:
                st.warning("Atenção: O PDF parece estar vazio ou sem camadas de texto legíveis.")
            
            # 4. Geração do parecer pela IA
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
            
    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
        st.write("Dica: Certifique-se de que o arquivo 'zoneamento_67.kmz' original da prefeitura está na raiz do seu repositório.")
