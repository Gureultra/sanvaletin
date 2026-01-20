import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Ranking Corazón de Hierro", layout="centered")

# Logotipo
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)
st.title("🏆 Ranking: Corazón de Hierro")

# 2. CUADRO INFORMATIVO DE PUNTOS
with st.expander("ℹ️ Ver baremo de puntos por zona"):
    st.write("""
    - **Z1**: 1 min = 1.0 punto
    - **Z2**: 1 min = 1.5 puntos
    - **Z3**: 1 min = 3.0 puntos
    - **Z4**: 1 min = 5.0 puntos
    - **Z5**: 1 min = 10.0 puntos
    """)

# 3. CONEXIÓN A GOOGLE SHEETS
# Usamos una forma de conexión que no depende de pasar el diccionario por parámetros
# Streamlit leerá directamente de st.secrets["connections"]["gsheets"]
# El truco para la private_key es que en tus SECRETS de la web debes ponerla bien formateada.
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error al conectar con la base de datos. Verifica los Secrets en Streamlit Cloud.")

# 4. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Nombre / Nickname:").strip().upper()
st.caption("⚠️ **Pon siempre el mismo nombre para sumar los puntos.**")

uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Límites de zonas (extracción o estándar)
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            
            if len(z_limits) < 4:
                z_limits = [114, 133, 152, 171, 220]

            hr_data = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_data:
                config_zonas = [
                    {"nombre": "Z1", "lim": z_limits[0], "mult": 1.0},
                    {"nombre": "Z2", "lim": z_limits[1], "mult": 1.5},
                    {"nombre": "Z3", "lim": z_limits[2], "mult": 3.0},
                    {"nombre": "Z4", "lim": z_limits[3], "mult": 5.0},
                    {"nombre": "Z5", "lim": 999, "mult": 10.0}
                ]

                stats_zonas = []
                puntos_totales_actividad = 0
                
                # Cálculo de tiempo por zona
                for i, z in enumerate(config_zonas):
                    if i == 0: segundos = sum(1 for hr in hr_data if hr <= z["lim"])
                    elif i == 4: segundos = sum(1 for hr in hr_data if hr > z_limits[3])
                    else: segundos = sum(1 for hr in hr_data if z_limits[i-1] < hr <= z["lim"])
                    
                    minutos = segundos / 60
                    pts = minutos * z["mult"]
                    puntos_totales_actividad += pts
                    if segundos > 0:
                        stats_zonas.append({"Zona": z["nombre"], "Tiempo": f"{int(minutos)} min {int(segundos % 60)} seg", "Puntos": round(pts, 2)})

                # RESULTADOS INDIVIDUALES
                st.success(f"✅ ¡Actividad registrada para {nombre_usuario}!")
                st.write(f"**Total acumulado hoy:** {round(puntos_totales_actividad, 2)} puntos.")
                st.table(pd.DataFrame(stats_zonas))

                # ACTUALIZACIÓN DEL RANKING EN LA HOJA
                df_ranking = conn.read(ttl=0)
                if df_ranking is None or df_ranking.empty:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                # Asegurar que la columna de puntos sea numérica
                df_ranking['Puntos Totales'] = pd.to_numeric(df_ranking['Puntos Totales'], errors='coerce').fillna(0)

                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_totales_actividad
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_totales_actividad}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                conn.update(data=df_ranking)
            else:
                st.error("No se encontraron datos de pulsaciones.")
    except Exception as e:
        st.error(f"Error técnico: {e}")

# 5. RANKING GLOBAL
st.divider()
st.subheader("📊 Ranking Mensual Acumulado")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        # Forzar orden numérico para el ranking
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales'], errors='coerce')
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False)
        st.dataframe(ranking, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay datos registrados.")
except:
    st.info("Conectando con la base de datos...")
