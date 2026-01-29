import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Ranking Corazón de Hierro", layout="centered")

# URL del nuevo logo (GureUltraRRSS.png) configurada para visualización directa
# Nota: Asegúrate de que el archivo en Drive tenga permisos de "Cualquier persona con el enlace puede ver"
URL_LOGO = "https://drive.google.com/thumbnail?id=15ppJHj1Dsg06HBpv4eJnCgZMfhrDmqpX&sz=w600"

# Mostrar logo centrado
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🏆 Ranking: Corazón de Hierro</h1>", unsafe_allow_html=True)

# 2. INFORMACIÓN DEL RETO
with st.expander("ℹ️ Baremo de puntos y Bonus"):
    st.write("- **Z1**: 1.0 pt/min | **Z2**: 1.5 pts/min | **Z3**: 3.0 pts/min | **Z4**: 5.0 pts/min | **Z5**: 10.0 pts/min")
    st.info("❤️ **BONUS SAN VALENTÍN**: Las actividades del 14 de febrero valen el DOBLE.")

# 3. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# 4. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()
st.caption("⚠️ **Usa siempre el mismo nombre para que tus puntos se acumulen correctamente.**")

uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Detectar fecha para Bonus
            fecha_act = None
            for record in fitfile.get_messages('session'):
                fecha_act = record.get_value('start_time')
                if fecha_act: break
            
            es_san_valentin = (fecha_act and fecha_act.month == 2 and fecha_act.day == 14)

            # Configuración de Zonas de FC
            z_limits = [114, 133, 152, 171, 220] # Valores por defecto

            # Extraer datos de pulso
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                mult_zonas = [1.0, 1.5, 3.0, 5.0, 10.0]
                stats_zonas = []
                puntos_act = 0
                bonus = 2.0 if es_san_valentin else 1.0

                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    pts = mins * mult_zonas[i] * bonus
                    puntos_act += pts
                    if segs > 0:
                        stats_zonas.append({"Zona": f"Z{i+1}", "Tiempo": f"{int(mins)}m {int(segs%60)}s", "Puntos": round(pts, 2)})

                if es_san_valentin:
                    st.balloons()
                    st.subheader("❤️ ¡PUNTOS DOBLES DE SAN VALENTÍN! ❤️")
                
                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_act, 2)} puntos!")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Desglose:**")
                    st.table(pd.DataFrame(stats_zonas))
                with c2:
                    st.write("**Gráfica de Esfuerzo:**")
                    st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))

                # ACTUALIZAR GOOGLE SHEETS
                df_ranking = conn.read(ttl=0)
                if df_ranking is None or df_ranking.empty:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df_ranking['Puntos Totales'] = pd.to_numeric(df_ranking['Puntos Totales'], errors='coerce').fillna(0)

                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_act
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_act}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                conn.update(data=df_ranking)
            else:
                st.error("No se detectaron datos de frecuencia cardíaca en el archivo.")
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

# 5. RANKING VISUAL
st.divider()
st.subheader("📊 Ranking Mensual Acumulado")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales'], errors='coerce')
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False)
        st.dataframe(ranking, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay datos en el ranking.")
except:
    st.info("Sincronizando con la base de datos...")
