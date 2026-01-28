import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Ranking Corazón de Hierro", layout="centered")
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)
st.title("🏆 Ranking: Corazón de Hierro")

# 2. INFORMACIÓN DEL RETO
with st.expander("ℹ️ Baremo de puntos y Bonus"):
    st.write("- **Z1**: 1.0 | **Z2**: 1.5 | **Z3**: 3.0 | **Z4**: 5.0 | **Z5**: 10.0")
    st.info("❤️ **BONUS SAN VALENTÍN**: Las actividades del 14 de febrero valen el DOBLE.")

# Limpieza de clave para conexión segura
try:
    secrets_dict = st.secrets["connections"]["gsheets"].to_dict()
    if "private_key" in secrets_dict:
        secrets_dict["private_key"] = secrets_dict["private_key"].replace("\\n", "\n")
    conn = st.connection("gsheets", type=GSheetsConnection, **secrets_dict)
except Exception as e:
    st.error("Error de configuración en los Secrets de Streamlit.")

# 3. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Nombre / Nickname:").strip().upper()
st.caption("⚠️ **Pon siempre el mismo nombre para sumar los puntos.**")

uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer fecha de la actividad para el Bonus
            fecha_actividad = None
            for record in fitfile.get_messages('session'):
                fecha_actividad = record.get_value('start_time')
                if fecha_actividad: break
            
            es_san_valentin = (fecha_actividad and fecha_actividad.month == 2 and fecha_actividad.day == 14)

            # Extraer zonas
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            if len(z_limits) < 4: z_limits = [114, 133, 152, 171, 220]

            # Procesar datos de frecuencia cardíaca (HR)
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                mult_zonas = [1.0, 1.5, 3.0, 5.0, 10.0]
                stats_zonas = []
                puntos_totales = 0
                bonus_factor = 2.0 if es_san_valentin else 1.0

                # Cálculo por zonas
                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    pts = mins * mult_zonas[i] * bonus_factor
                    puntos_totales += pts
                    if segs > 0:
                        stats_zonas.append({"Zona": f"Z{i+1}", "Tiempo": f"{int(mins)}m {int(segs%60)}s", "Puntos": round(pts, 2)})

                # --- MOSTRAR RESULTADOS DE LA SUBIDA ---
                if es_san_valentin:
                    st.balloons()
                    st.subheader("❤️ ¡BONUS SAN VALENTÍN APLICADO (x2)! ❤️")
                
                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_totales, 2)} puntos!")
                
                col1, col2 = st.columns(2)
                col1.write("**Desglose de puntos:**")
                col1.table(pd.DataFrame(stats_zonas))
                
                # --- BOTÓN DE GRÁFICO DE PULSACIONES ---
                with col2:
                    st.write("**Gráfica de Esfuerzo:**")
                    df_hr = pd.DataFrame(hr_records, columns=['BPM'])
                    st.line_chart(df_hr)
                    st.caption("Evolución de tus pulsaciones durante la ruta.")

                # --- ACTUALIZAR GOOGLE SHEETS ---
                df_ranking = conn.read(ttl=0)
                if df_ranking is None or df_ranking.empty:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df_ranking['Puntos Totales'] = pd.to_numeric(df_ranking['Puntos Totales'], errors='coerce').fillna(0)

                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_totales
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_totales}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                conn.update(data=df_ranking)
            else:
                st.error("No se detectaron datos de pulsaciones en el archivo.")
    except Exception as e:
        st.error(f"Error al procesar: {e}")

# 4. RANKING GLOBAL
st.divider()
st.subheader("📊 Ranking Mensual Acumulado")
try:
    ranking = conn.read(ttl=0).sort_values(by='Puntos Totales', ascending=False)
    st.dataframe(ranking, use_container_width=True, hide_index=True)
except:
    st.info("Conectando con la base de datos...")
