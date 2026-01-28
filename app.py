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
    st.info("❤️ **BONUS SAN VALENTÍN**: Las actividades del 14 de febrero valen el DOBLE.")

# 3. CONEXIÓN A GOOGLE SHEETS
try:
    # Extraemos secretos a un diccionario local
    conf_dict = st.secrets["connections"]["gsheets"].to_dict()
    
    # Limpiamos la clave privada para que Google la acepte correctamente
    if "private_key" in conf_dict:
        conf_dict["private_key"] = conf_dict["private_key"].replace("\\n", "\n")
    
    # Conexión limpia (sin pasar 'type' explícitamente para evitar duplicados)
    conn = st.connection("gsheets", **conf_dict)
except Exception as e:
    st.error(f"Error de configuración en Secrets: {e}")
    st.stop()

# 4. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()
st.caption("⚠️ **Pon siempre el mismo nombre para sumar los puntos correctamente.**")

uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Detectar fecha de la actividad (Bonus x2)
            fecha_act = None
            for record in fitfile.get_messages('session'):
                fecha_act = record.get_value('start_time')
                if fecha_act: break
            
            es_san_valentin = (fecha_act and fecha_act.month == 2 and fecha_act.day == 14)

            # Extraer zonas de frecuencia cardíaca (o estándar)
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            if len(z_limits) < 4: z_limits = [114, 133, 152, 171, 220]

            # Procesar datos de pulso
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                mult_zonas = [1.0, 1.5, 3.0, 5.0, 10.0]
                stats_zonas = []
                puntos_actividad = 0
                bonus = 2.0 if es_san_valentin else 1.0

                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    pts = mins * mult_zonas[i] * bonus
                    puntos_actividad += pts
                    if segs > 0:
                        stats_zonas.append({
                            "Zona": f"Z{i+1}", 
                            "Tiempo": f"{int(mins)}m {int(segs%60)}s", 
                            "Puntos": round(pts, 2)
                        })

                # --- RESULTADOS INDIVIDUALES ---
                if es_san_valentin:
                    st.balloons()
                    st.subheader("❤️ ¡PUNTOS DOBLES! Actividad de San Valentín")
                
                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_actividad, 2)} puntos!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Desglose:**")
                    st.table(pd.DataFrame(stats_zonas))
                with col2:
                    st.write("**Esfuerzo (BPM):**")
                    st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))

                # --- ACTUALIZAR GOOGLE SHEETS ---
                df_ranking = conn.read(ttl=0)
                if df_ranking is None or df_ranking.empty:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df_ranking['Puntos Totales'] = pd.to_numeric(df_ranking['Puntos Totales'], errors='coerce').fillna(0)

                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_actividad
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_actividad}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                conn.update(data=df_ranking)
            else:
                st.error("No se encontraron datos de pulso en el archivo.")
    except Exception as e:
        st.error(f"Error al procesar: {e}")

# 5. RANKING GLOBAL
st.divider()
st.subheader("📊 Ranking Mensual Acumulado")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales'], errors='coerce')
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False)
        st.dataframe(ranking, use_container_width=True, hide_index=True)
    else:
        st.info("El ranking está vacío actualmente.")
except:
    st.info("Conectando con la base de datos...")

# 6. RESET (Solo para el administrador)
if st.sidebar.button("🗑️ Reiniciar Ranking"):
    reset_df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
    conn.update(data=reset_df)
    st.sidebar.success("Ranking reseteado.")
    st.rerun()
