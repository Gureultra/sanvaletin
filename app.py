import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import altair as alt

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Gure Ultra | Ranking Corazón de Hierro",
    page_icon="🔥",
    layout="wide"
)

# 2. DISEÑO CSS "BLACK & RED"
st.markdown("""
    <style>
    .stApp { background-color: #1A1A1A !important; }
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3 {
        color: #FFFFFF !important;
    }
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; font-weight: bold; }
    
    /* Input numérico y de texto */
    input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold;
    }
    
    /* Caja de subida */
    [data-testid="stFileUploader"] {
        background-color: #262730 !important;
        border: 2px dashed #FF0000 !important;
        border-radius: 15px;
        padding: 15px;
    }
    [data-testid="stFileUploader"] section div span { font-size: 0 !important; }
    [data-testid="stFileUploader"] section div span::before {
        content: "Arrastra tu archivo .FIT aquí";
        color: #FF0000 !important; font-size: 16px !important; font-weight: bold;
    }
    
    .warning-box {
        background-color: #332200 !important; border-left: 5px solid #FFA500 !important;
        padding: 15px; border-radius: 8px; margin-bottom: 20px;
    }
    
    /* Métrica personalizada */
    div[data-testid="stMetricValue"] {
        color: #FF4B4B !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Error de conexión con la base de datos.")

# 4. CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"
col_h1, col_h2, col_h3 = st.columns([1, 1, 1])
with col_h2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. CONFIGURACIÓN DE ZONAS AUTOMÁTICA
st.markdown("### ⚙️ Configuración Personal")
col_input, col_info = st.columns([1, 2])

with col_input:
    max_hr = st.number_input("Introduce tu FC Máxima de la temporada:", min_value=100, max_value=250, value=190, step=1)

# Cálculo automático de zonas (Modelo de 7 Zonas basado en % FC Máx)
# Z1: <60%, Z2: 60-70%, Z3: 70-80%, Z4: 80-88%, Z5: 88-93%, Z6: 93-97%, Z7: >97%
lim_z1 = int(max_hr * 0.60)
lim_z2 = int(max_hr * 0.70)
lim_z3 = int(max_hr * 0.80)
lim_z4 = int(max_hr * 0.88)
lim_z5 = int(max_hr * 0.93)
lim_z6 = int(max_hr * 0.97)

with col_info:
    st.info(f"""
    **Tus Zonas Calculadas:**
    - **Z1:** < {lim_z1} ppm | **Z2:** {lim_z1}-{lim_z2} ppm | **Z3:** {lim_z2}-{lim_z3} ppm
    - **Z4:** {lim_z3}-{lim_z4} ppm | **Z5:** {lim_z4}-{lim_z5} ppm
    - **Z6:** {lim_z5}-{lim_z6} ppm | **Z7:** > {lim_z6} ppm
    """)

# 6. SUBIDA DE ARCHIVO
st.divider()
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file:
    try:
        with st.spinner('Procesando datos...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer registros
            records = []
            for m in fitfile.get_messages('record'):
                ts = m.get_value('timestamp')
                hr = m.get_value('heart_rate')
                if ts and hr:
                    records.append({'t': ts, 'hr': hr})
            
            if len(records) > 1:
                # Fecha
                fecha_act = records[0]['t'].date()
                if not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
                    st.error(f"❌ Fecha {fecha_act} fuera de rango (Feb 2026).")
                    st.stop()

                # CÁLCULO DE SEGUNDOS REALES CON ZONAS DINÁMICAS
                secs_zones = [0.0] * 7
                # Puntuación: Z1=1, Z2=1.5, Z3=3, Z4=5, Z5/6/7=10
                points_map = [1.0, 1.5, 3.0, 5.0, 10.0, 10.0, 10.0]
                
                for i in range(len(records)-1):
                    delta = (records[i+1]['t'] - records[i]['t']).total_seconds()
                    if delta > 15: delta = 1 
                    
                    hr = records[i]['hr']
                    
                    if hr <= lim_z1: secs_zones[0] += delta
                    elif hr <= lim_z2: secs_zones[1] += delta
                    elif hr <= lim_z3: secs_zones[2] += delta
                    elif hr <= lim_z4: secs_zones[3] += delta
                    elif hr <= lim_z5: secs_zones[4] += delta
                    elif hr <= lim_z6: secs_zones[5] += delta
                    else: secs_zones[6] += delta

                # Resultados
                bonus = 2.0 if (fecha_act.month == 2 and fecha_act.day == 14) else 1.0
                total_pts = 0
                resumen = []

                for z in range(7):
                    s = secs_zones[z]
                    if s > 0:
                        m = s / 60
                        p = m * points_map[z] * bonus
                        total_pts += p
                        resumen.append({
                            "Zona": f"Zona {z+1}",
                            "Rango": f"{['<'+str(lim_z1), f'{lim_z1}-{lim_z2}', f'{lim_z2}-{lim_z3}', f'{lim_z3}-{lim_z4}', f'{lim_z4}-{lim_z5}', f'{lim_z5}-{lim_z6}', '>'+str(lim_z6)][z]}",
                            "Tiempo": f"{int(s//60)}m {int(s%60)}s",
                            "Puntos": round(p, 2)
                        })

                # VISUALIZACIÓN
                st.markdown("### 📊 Resultado de la Actividad")
                c_res1, c_res2 = st.columns(2)
                c_res1.metric("PUNTOS TOTALES", f"{round(total_pts, 2)}")
                if bonus > 1: c_res2.warning("❤️ BONUS SAN VALENTÍN x2")
                else: c_res2.metric("FECHA", str(fecha_act))
                
                st.table(pd.DataFrame(resumen))

                # GUARDAR
                st.markdown("### 💾 Guardar en Ranking")
                nombre_usuario = st.text_input("Tu Nickname:", placeholder="Ej: JUAN_GARCIA").strip().upper()
                
                if st.button("CONFIRMAR Y GUARDAR"):
                    if nombre_usuario:
                        df = conn.read(ttl=0)
                        if df is None or df.empty: df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                        df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)
                        
                        if nombre_usuario in df['Ciclista'].values:
                            df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += total_pts
                        else:
                            new_row = pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [total_pts]})
                            df = pd.concat([df, new_row], ignore_index=True)
                        
                        conn.update(data=df)
                        st.success("✅ ¡Guardado con éxito!")
                        st.balloons()
                    else:
                        st.warning("⚠️ Escribe un nombre para guardar.")

            else:
                st.error("Archivo sin datos de pulso válidos.")
    except Exception as e:
        st.error(f"Error: {e}")

# 7. RANKING
st.divider()
st.subheader("🏆 Clasificación General")
try:
    data = conn.read(ttl=0)
    if data is not None and not data.empty:
        data['Puntos Totales'] = pd.to_numeric(data['Puntos Totales']).round(2)
        ranking = data.sort_values('Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1
        
        st.dataframe(ranking, use_container_width=True)

        bars = alt.Chart(ranking).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Puntos Totales:Q', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', axis=alt.Axis(labelColor='white', titleColor='white'))
        )
        text = bars.mark_text(align='left', dx=5, color='white').encode(text='Puntos Totales:Q')
        st.altair_chart((bars + text).properties(height=alt.Step(40)).configure_view(strokeOpacity=0), use_container_width=True)
except:
    st.info("Cargando ranking...")
