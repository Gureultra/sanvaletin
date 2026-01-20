import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Ranking Corazón de Hierro", layout="centered")
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)
st.title("🏆 Ranking Mensual")

# Conexión a la hoja de Google
conn = st.connection("gsheets", type=GSheetsConnection)
url_hoja = "https://docs.google.com/spreadsheets/d/1kf6MwoAzD1vXmX_BfxRb0TVAZFf1-zZSzzuhe_HjstY/edit?usp=sharing"

# 2. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()
uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Procesando actividad y guardando en la nube...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer zonas del archivo
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            
            if len(z_limits) < 4:
                z_limits = [114, 133, 152, 171, 220] # Estándar backup

            # Procesar pulso
            hr_data = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_data:
                def calc_pts(hr):
                    if hr <= z_limits[0]: return 1.0 / 60
                    if hr <= z_limits[1]: return 1.5 / 60
                    if hr <= z_limits[2]: return 3.0 / 60
                    if hr <= z_limits[3]: return 5.0 / 60
                    return 10.0 / 60

                puntos_nuevos = sum(calc_pts(hr) for hr in hr_data)

                # LEER Y ACTUALIZAR GOOGLE SHEETS
                df_ranking = conn.read(spreadsheet=url_hoja, ttl=0)
                
                # Limpiar datos vacíos si los hay
                if df_ranking.empty:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])

                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_nuevos
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_nuevos}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                # Guardar permanentemente
                conn.update(spreadsheet=url_hoja, data=df_ranking)
                st.success(f"✅ ¡Puntos guardados! Has sumado {round(puntos_nuevos, 2)} pts.")
            else:
                st.error("No hay datos de pulso.")
    except Exception as e:
        st.error(f"Error de conexión: Asegúrate de que la hoja de Google sea Pública y Editor. Detalle: {e}")

# 3. MOSTRAR RANKING DESDE LA HOJA
st.divider()
st.subheader("📊 Clasificación General (Datos en tiempo real)")

try:
    # Leemos siempre de la hoja para que el ranking sea el oficial
    ranking_final = conn.read(spreadsheet=url_hoja, ttl=0).sort_values(by='Puntos Totales', ascending=False)
    st.dataframe(ranking_final, use_container_width=True, hide_index=True)
except:
    st.info("Sube la primera actividad para empezar el ranking.")

# 4. BOTÓN PARA REINICIAR EL MES (Solo visible en barra lateral)
if st.sidebar.button("🗑️ Poner Ranking a 0 (Nuevo Mes)"):
    reset_df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
    conn.update(spreadsheet=url_hoja, data=reset_df)
    st.sidebar.success("Ranking reseteado en Google Sheets.")
    st.rerun()
