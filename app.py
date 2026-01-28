import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Ranking Corazón de Hierro", layout="centered")

# Logotipo
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)
st.title("🏆 Ranking: Corazón de Hierro")

# 2. INFORMACIÓN DEL RETO
with st.expander("ℹ️ Baremo de puntos y Bonus"):
    st.write("- **Z1**: 1.0 pt/min | **Z2**: 1.5 pts/min | **Z3**: 3.0 pts/min | **Z4**: 5.0 pts/min | **Z5**: 10.0 pts/min")
    st.info("❤️ **BONUS SAN VALENTÍN**: Las actividades realizadas el 14 de febrero valen el DOBLE.")

# 3. CONEXIÓN A GOOGLE SHEETS (Manejo de Secrets)
try:
    # Extraemos secretos a un diccionario para limpiar la clave privada
    conf_dict = st.secrets["connections"]["gsheets"].to_dict()
    if "private_key" in conf_dict:
        # Reemplazamos los saltos de línea literales por reales para la API de Google
        conf_dict["private_key"] = conf_dict["private_key"].replace("\\n", "\n")
    
    # Establecemos la conexión pasando las credenciales limpias
    conn = st.connection("gsheets", type=GSheetsConnection, **conf_dict)
except Exception as e:
    st.error(f"Error de configuración en Secrets: {e}")
    st.stop()

# 4. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()
st.caption("⚠️ **Usa siempre el mismo nombre para que tus puntos se sumen correctamente.**")

uploaded_file = st.file_uploader("Sube tu archivo .fit de la actividad", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Obtener fecha para el Bonus x2
            fecha_actividad = None
            for record in fitfile.get_messages('session'):
                fecha_actividad = record.get_value('start_time')
                if fecha_actividad: break
            
            es_san_valentin = (fecha_actividad and fecha_actividad.month == 2 and fecha_actividad.day == 14)

            # Extraer zonas del archivo (o usar estándar si no existen)
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            if len(z_limits) < 4: z_limits = [114, 133, 152, 171, 220]

            # Procesar datos de frecuencia cardíaca
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                mult_zonas = [1.0, 1.5, 3.0, 5.0, 10.0]
                stats_zonas = []
                puntos_totales_actividad = 0
                factor_san_valentin = 2.0 if es_san_valentin else 1.0

                # Cálculo de tiempo y puntos por zona
                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    pts_zona = mins * mult_zonas[i] * factor_san_valentin
                    puntos_totales_actividad += pts_zona
                    if segs > 0:
                        stats_zonas.append({
                            "Zona": f"Z{i+1}", 
                            "Tiempo": f"{int(mins)}m {int(segs%60)}s", 
                            "Puntos": round(pts_zona, 2)
                        })

                # --- MOSTRAR RESULTADOS INDIVIDUALES ---
                if es_san_valentin:
                    st.balloons()
                    st.subheader("❤️ ¡BONUS SAN VALENTÍN APLICADO! (Puntos x2)")
                
                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_totales_actividad, 2)} puntos!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Desglose de la sesión:**")
                    st.table(pd.DataFrame(stats_zonas))
                
                with col2:
                    st.write("**Gráfica de Pulsaciones:**")
                    st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))

                # --- ACTUALIZAR GOOGLE SHEETS ---
                df_ranking = conn.read(ttl=0)
                if df_ranking is None or df_ranking.empty:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                # Asegurar formato numérico
                df_ranking['Puntos Totales'] = pd.to_numeric(df_ranking['Puntos Totales'], errors='coerce').fillna(0)

                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_totales_actividad
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_totales_actividad}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                conn.update(data=df_ranking)
            else:
                st.error("El archivo no contiene datos de frecuencia cardíaca.")
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

# 5. MOSTRAR RANKING GLOBAL
st.divider()
st.subheader("📊 Clasificación General")
try:
    ranking_final = conn.read(ttl=0)
    if ranking_final is not None and not ranking_final.empty:
        ranking_final['Puntos Totales'] = pd.to_numeric(ranking_final['Puntos Totales'], errors='coerce')
        ranking_final = ranking_final.sort_values(by='Puntos Totales', ascending=False)
        st.dataframe(ranking_final, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay registros en el ranking.")
except:
    st.info("Conectando con la base de datos...")

# 6. REINICIO DEL RETO (Solo Admin)
if st.sidebar.button("🗑️ Reiniciar Ranking (Nuevo Mes)"):
    reset_df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
    conn.update(data=reset_df)
    st.sidebar.success("Ranking puesto a cero.")
    st.rerun()
