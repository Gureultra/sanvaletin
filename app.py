import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Ranking Corazón de Hierro", layout="centered")
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)

# Conexión oficial usando los Secrets de Service Account
conn = st.connection("gsheets", type=GSheetsConnection)

nombre_usuario = st.text_input("Tu Nombre:").strip().upper()
uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Guardando en Google Sheets...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer zonas del archivo (prioridad usuario)
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            
            if len(z_limits) < 4:
                z_limits = [114, 133, 152, 171, 220]

            hr_data = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_data:
                def calc_pts(hr):
                    if hr <= z_limits[0]: return 1.0 / 60
                    if hr <= z_limits[1]: return 1.5 / 60
                    if hr <= z_limits[2]: return 3.0 / 60
                    if hr <= z_limits[3]: return 5.0 / 60
                    return 10.0 / 60

                puntos_nuevos = sum(calc_pts(hr) for hr in hr_data)

                # Leer ranking actual
                df_ranking = conn.read(ttl=0)
                
                if df_ranking.empty:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])

                # Actualizar o añadir
                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_nuevos
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_nuevos}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                # ACTUALIZAR HOJA (Ahora con permisos de Service Account)
                conn.update(data=df_ranking)
                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_nuevos, 2)} puntos!")
            else:
                st.error("Archivo sin datos de pulso.")
    except Exception as e:
        st.error(f"Error: {e}")

st.divider()
st.subheader("📊 Clasificación General")
try:
    ranking = conn.read(ttl=0).sort_values(by='Puntos Totales', ascending=False)
    st.dataframe(ranking, use_container_width=True, hide_index=True)
except:
    st.info("Sube la primera actividad para empezar.")
