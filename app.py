import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Ranking Corazón de Hierro", layout="centered")
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)
st.title("🏆 Ranking: Corazón de Hierro")

# URL de tu hoja (asegúrate de que sea pública como 'Editor')
URL_HOJA = "https://docs.google.com/spreadsheets/d/1kf6MwoAzD1vXmX_BfxRb0TVAZFf1-zZSzzuhe_HjstY/edit?usp=sharing"

# Intentar conexión
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error de conexión inicial. Revisa los Secrets.")

# 2. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()
uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer zonas
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            
            if len(z_limits) < 4:
                z_limits = [114, 133, 152, 171, 220]

            # Procesar datos de pulso
            hr_data = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_data:
                def calc_pts(hr):
                    if hr <= z_limits[0]: return 1.0 / 60
                    if hr <= z_limits[1]: return 1.5 / 60
                    if hr <= z_limits[2]: return 3.0 / 60
                    if hr <= z_limits[3]: return 5.0 / 60
                    return 10.0 / 60

                puntos_nuevos = sum(calc_pts(hr) for hr in hr_data)

                # LEER Y ACTUALIZAR
                # Usamos ttl=0 para que no use datos viejos de caché
                df_ranking = conn.read(spreadsheet=URL_HOJA, ttl=0)
                
                if df_ranking is None or df_ranking.empty:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])

                # Asegurar nombres de columnas correctos
                if 'Ciclista' not in df_ranking.columns:
                    df_ranking.columns = ['Ciclista', 'Puntos Totales']

                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_nuevos
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_nuevos}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                # GUARDAR
                conn.update(spreadsheet=URL_HOJA, data=df_ranking)
                st.success(f"✅ ¡Hecho! Has sumado {round(puntos_nuevos, 2)} pts.")
            else:
                st.error("El archivo no tiene datos de pulso.")
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# 3. MOSTRAR RANKING
st.divider()
st.subheader("📊 Clasificación General")
try:
    # Leemos la hoja pública directamente
    df_ver = conn.read(spreadsheet=URL_HOJA, ttl=0)
    if not df_ver.empty:
        df_ver = df_ver.sort_values(by=df_ver.columns[1], ascending=False)
        st.dataframe(df_ver, use_container_width=True, hide_index=True)
except:
    st.info("Sube una actividad para empezar.")
