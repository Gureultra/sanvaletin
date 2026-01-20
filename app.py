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
# Limpieza de la clave privada para evitar errores de formato (vía Secrets)
if "connections" in st.secrets and "gsheets" in st.secrets.connections:
    if "private_key" in st.secrets.connections.gsheets:
        st.secrets.connections.gsheets["private_key"] = st.secrets.connections.gsheets["private_key"].replace("\\n", "\n")

conn = st.connection("gsheets", type=GSheetsConnection)

# 4. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Nombre / Nickname:").strip().upper()
st.caption("⚠️ **Pon siempre el mismo nombre para sumar los puntos.**")

uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad y actualizando ranking...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer zonas del archivo (prioridad usuario)
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            
            # Backup zonas estándar (FC Max 190)
            if len(z_limits) < 4:
                z_limits = [114, 133, 152, 171, 220]

            hr_data = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_data:
                # Definición de multiplicadores
                config_zonas = [
                    {"nombre": "Z1", "lim": z_limits[0], "mult": 1.0},
                    {"nombre": "Z2", "lim": z_limits[1], "mult": 1.5},
                    {"nombre": "Z3", "lim": z_limits[2], "mult": 3.0},
                    {"nombre": "Z4", "lim": z_limits[3], "mult": 5.0},
                    {"nombre": "Z5", "lim": 999, "mult": 10.0}
                ]

                # Cálculo de tiempo y puntos por zona
                stats_zonas = []
                puntos_totales_actividad = 0
                
                for z in config_zonas:
                    # Contamos segundos en el rango de la zona
                    if z["nombre"] == "Z1":
                        segundos = sum(1 for hr in hr_data if hr <= z["lim"])
                    elif z["nombre"] == "Z5":
                        segundos = sum(1 for hr in hr_data if hr > z_limits[3])
                    else:
                        # Para Z2, Z3, Z4 buscamos el rango entre el límite anterior y el actual
                        idx = config_zonas.index(z)
                        segundos = sum(1 for hr in hr_data if z_limits[idx-1] < hr <= z["lim"])
                    
                    minutos = segundos / 60
                    pts = minutos * z["mult"]
                    puntos_totales_actividad += pts
                    
                    if segundos > 0:
                        stats_zonas.append({
                            "Zona": z["nombre"],
                            "Tiempo": f"{int(minutos)} min {int(segundos % 60)} seg",
                            "Puntos": round(pts, 2)
                        })

                # --- RESULTADO DE LA SUBIDA ---
                st.success(f"✅ ¡Actividad registrada para {nombre_usuario}!")
                st.write(f"**Total de la actividad:** {round(puntos_totales_actividad, 2)} puntos.")
                st.table(pd.DataFrame(stats_zonas))

                # --- ACTUALIZAR BASE DE DATOS ---
                df_ranking = conn.read(ttl=0)
                if df_ranking.empty or 'Ciclista' not in df_ranking.columns:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])

                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_totales_actividad
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_totales_actividad}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                conn.update(data=df_ranking)
            else:
                st.error("No se detectaron datos de pulsaciones.")
    except Exception as e:
        st.error(f"Error al procesar: {e}")

# 5. RANKING GLOBAL
st.divider()
st.subheader("📊 Ranking Mensual Acumulado")
try:
    ranking = conn.read(ttl=0).sort_values(by='Puntos Totales', ascending=False)
    st.dataframe(ranking, use_container_width=True, hide_index=True)
except:
    st.info("Aún no hay datos registrados.")
