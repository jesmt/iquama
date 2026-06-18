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
            kml_interno = [f for f in z.namelist() if f.endswith('.kml')][0]
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_file:
                tmp_file.write(z.read(kml_interno))
                tmp_path = tmp_file.name

        # 2. Descobre TODAS as camadas (pastas de zonas) dentro do arquivo
        layer_names = []
        try:
            import pyogrio
            info = pyogrio.list_layers(tmp_path)
            layer_names = info[:, 0].tolist() if not isinstance(info, tuple) else list(info[0])
        except Exception:
            try:
                import fiona
                layer_names = fiona.listlayers(tmp_path)
            except Exception:
                pass

        # 3. Varre camada por camada e unifica tudo em um grande mapa
        gdfs = []
        if layer_names:
            for layer in layer_names:
                try:
                    sub_gdf = gpd.read_file(tmp_path, layer=layer)
                    
                    # Garante que cada polígono saiba a qual zona pertence (usa o nome da pasta se necessário)
                    if 'zona' not in sub_gdf.columns:
                        if 'Name' in sub_gdf.columns:
                            sub_gdf['zona'] = sub_gdf['Name'].apply(lambda x: x if pd.notna(x) and str(x).strip() != "" else layer)
                        else:
                            sub_gdf['zona'] = layer
                    gdfs.append(sub_gdf)
                except Exception:
                    continue
            
            if gdfs:
                gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)
            else:
                gdf = gpd.read_file(tmp_path)
        else:
            gdf = gpd.read_file(tmp_path)
        
        # Converte o mapa unificado para coordenadas geográficas globais
        gdf = gdf.to_crs(epsg=4326)
        
        # Remove o arquivo temporário com segurança
        os.unlink(tmp_path)
        
        # Cria o ponto geográfico para teste (Longitude, Latitude)
        ponto = Point(lon, lat)
        
        # Filtra a zona que contém a coordenada informada
        resultado = gdf[gdf.geometry.contains(ponto)]
        
        if not resultado.empty:
            nome_da_zona = resultado.iloc[0].get('zona', resultado.iloc[0].get('Name', 'Zona Indefinida'))
            st.success(f"Imóvel localizado na: **{nome_da_zona}**")
            
            # 4. Leitura do arquivo de texto da Lei de Zoneamento
            with open("lei_67_OCR.pdf", "rb") as f:
                leitor = PyPDF2.PdfReader(f)
                texto_lei = "\n".join([p.extract_text() for p in leitor.pages if p.extract_text()])
            
            if len(texto_lei) < 100:
                st.warning("Atenção: O PDF parece não conter camadas de texto reconhecíveis.")
            
            # 5. Geração do parecer analítico com a IA
            prompt = f"Você é um engenheiro/técnico de urbanismo. O imóvel avaliado está localizado na {nome_da_zona}. Baseado estritamente no texto da lei fornecido a seguir, gere um parecer técnico detalhado contendo os índices urbanísticos permitidos (recuos, taxa de ocupação, gabarito, etc.):\n\n{texto_lei[:15000]}"
            
            with st.spinner("Analisando parâmetros urbanísticos com a IA..."):
                parecer = model.generate_content(prompt)
                st.markdown(parecer.text)
                
        else:
            st.error("Coordenada fora da área mapeada.")
            st.write("---")
            st.write("DEBUG - Informações do mapa unificado:")
            st.write(f"Total de polígonos combinados de todas as zonas: {len(gdf)}")
            st.write("Zonas/Camadas lidas com sucesso:", layer_names)
            
    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
