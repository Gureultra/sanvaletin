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

# 2. DISEÑO CSS CORREGIDO (Legibilidad garantizada)
st.markdown("""
    <style>
    /* Fondo oscuro global */
    .stApp { background-color: #1A1A1A !important; }
    
    /* Forzar color blanco en textos generales */
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3, div {
        color: #FFFFFF !important;
    }
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; font-weight: bold; }
    
    /* Inputs: Fondo blanco y texto negro para ver lo que escribes */
    input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: 2px solid #FF4B4B !important;
    }
    
    /* BOTÓN DE GUARDAR (Blanco con letras rojas) */
    div[data-testid="stButton"] button {
        background-color: #FFFFFF !important;
        border: 2px solid #FF0000 !important;
        color: #FF0000 !important;
        font-size: 20px !important;
        font-weight: bold !important;
        width: 100%;
        transition: 0.3s;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #FF0000 !important;
        color: #FFFFFF !important;
        border-color: #FFFFFF !important;
    }
    /* Asegurar que el texto dentro del botón sea rojo */
    div[data-testid="stButton"] button p {
        color: #FF0000 !important;
    }
    div[data-testid="stButton"] button:hover p {
        color: #FFFFFF !important;
    }

    /* Caja de subida de archivos */
    [data-testid="stFileUploader"] {
        background-color: #262730 !important;
        border: 2px dashed #FF4B4B !important;
        border-radius: 15px;
        padding: 15px;
    }
    [data-testid="stFileUploader"] section div span { font-size: 0 !important; }
    [data-testid="stFileUploader"] section div span::before {
        content: "Arrastra aquí tu archivo .FIT";
        color: #FF4B4B !important; font-size: 16px !important; font-weight: bold;
    }
    
    /* Avisos */
    .warning-box {
        background-color: #332200 !important; border-left: 5px solid #FFA500 !important;
        padding: 15px; border-radius: 8px; margin-bottom: 20px;
    }
    
    /* Métricas grandes en rojo */
    div[data-testid="stMetricValue"] { color: #FF4B4B !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Error de conexión con Google Sheets.")

# 4. CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"
col_h1, col_h2, col_h3 = st.columns([1, 1, 1])
with col_h2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. CONFIGURACIÓN DE FC MÁXIMA
st.markdown("### ⚙️ 1. Tu Frecuencia Cardíaca")
col_cfg1, col_cfg2 = st.columns([1, 2])

with col_cfg1:
    max_hr = st.number_input("Introduce tu FC Máxima de la temporada:", min_value=100, max_value=250, value=190, step=1)

# Cálculo de las 7 zonas
lim_z1 = int(max_hr * 0.60)
lim_z2 = int(max_hr * 0.70)
lim_z3 = int(max_hr * 0.80)
lim_z4 = int(max_hr * 0.88)
lim_z5 = int(max_hr * 0.93)
lim_z6 = int(max_hr * 0.97)

with col_cfg2:
    st.info(f"""
    **Tus Zonas Calculadas:**
    Z1 (<{lim_z1}) | Z2 ({lim_z1}-{lim_z2}) | Z3 ({lim_z2}-{lim_z3}) | Z4 ({lim_z3}-{lim_z4})
    **Zonas de Máxima Puntuación (10 pts):** Z5, Z6 y Z7 (> {lim_z4} ppm)
    """)

# 6. SUBIDA Y CÁLCULO
st.divider()
st.subheader("📤 2. Sube tu actividad (.FIT)")
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file:
    try:
        with st.spinner('Analizando datos segundo a segundo...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            records = []
            for m in fitfile.get_messages('record'):
                ts = m.get_value('timestamp')
                hr = m.get_value('heart_rate')
                if ts and hr:
                    records.append({'t': ts, 'hr': hr})
            
            if len(records) > 1:
                # Validar fecha
                fecha_act = records[0]['t'].date()
                if not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
                    st.error(f"❌ Fecha {fecha_act} incorrecta. El reto es del 1 de febrero al 1 de marzo de 2026.")
                    st.stop()

                # Motor de Puntos
                secs_zones = [0.0] * 7
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

                # Bonus San Valentín
                es_sv = (fecha_act.month == 2 and fecha_act.day == 14)
                bonus = 2.0 if es_sv else 1.0
                
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
                            "Rango PPM": f"{['<'+str(lim_z1), f'{lim_z1}-{lim_z2}', f'{lim_z2}-{lim_z3}', f'{lim_z3}-{lim_z4}', f'{lim_z4}-{lim_z5}', f'{lim_z5}-{lim_z6}', '>'+str(lim_z6)][z]}",
                            "Tiempo": f"{int(s//60)}m {int(s%60)}s",
                            "Puntos": round(p, 2)
                        })

                # MOSTRAR RESULTADOS
                st.markdown("### 📊 3. Resultados de hoy")
                c1, c2 = st.columns(2)
                c1.metric("PUNTOS A SUMAR", f"{round(total_pts, 2)}")
                if es_sv: c2.warning("❤️ ¡BONUS SAN VALENTÍN (x2)!")
                else: c2.metric("FECHA", str(fecha_act))
                
                st.table(pd.DataFrame(resumen))

                # GUARDAR
                st.markdown("### 💾 4. Guardar en la Clasificación")
                st.info("⚠️ Recuerda usar SIEMPRE el MISMO NOMBRE para acumular tus puntos.")
                
                nombre_usuario = st.text_input("Escribe tu NOMBRE:", placeholder="Ej: JUAN PEREZ").strip().upper()
                
                if st.button("GUARDAR PUNTOS AHORA"):
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
                        st.success(f"✅ ¡Puntos guardados para {nombre_usuario}!")
                        if es_sv: st.balloons()
                    else:
                        st.error("❌ Por favor, escribe tu NOMBRE antes de guardar.")

            else:
                st.error("El archivo no tiene datos de pulso válidos.")
    except Exception as e:
        st.error(f"Error procesando archivo: {e}")

# 7. CLASIFICACIÓN Y GRÁFICA
st.divider()
st.subheader("🏆 Clasificación General")
try:
    data = conn.read(ttl=0)
    if data is not None and not data.empty:
        data['Puntos Totales'] = pd.to_numeric(data['Puntos Totales']).round(2)
        ranking = data.sort_values('Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1
        
        st.dataframe(ranking, use_container_width=True)

        st.markdown("### 📈 Gráfica de Líderes")
        
        # Gráfica Altair con Textos BLANCOS forzados
        bars = alt.Chart(ranking).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Puntos Totales:Q', title='Puntos Totales', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', title='Ciclista', axis=alt.Axis(labelColor='white', titleColor='white'))
        )
        
        text = bars.mark_text(
            align='left',
            dx=5,
            color='white',  # Color del texto de los puntos
            fontWeight='bold'
        ).encode(
            text='Puntos Totales:Q'
        )
        
        chart = (bars + text).properties(
            height=alt.Step(50),
            background='transparent' # Fondo transparente para que se vea el gris de la app
        ).configure_view(
            strokeOpacity=0
        ).configure_axis(
            domainColor='white',
            tickColor='white'
        )
        
        st.altair_chart(chart, use_container_width=True)
except:
    st.info("Cargando ranking...")
