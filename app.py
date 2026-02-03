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

# 2. DISEÑO CSS "BLACK & RED" (LEGIBILIDAD TOTAL)
st.markdown("""
    <style>
    /* Fondo oscuro global */
    .stApp { background-color: #1A1A1A !important; }
    
    /* Textos generales en blanco */
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3, div {
        color: #FFFFFF !important;
    }
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; font-weight: bold; }
    
    /* Inputs (Cajas de texto y números): Fondo blanco, letra negra */
    input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold;
        border: 2px solid #FF4B4B !important;
    }
    
    /* BOTÓN "GUARDAR" (Solución al problema de lectura) */
    div.stButton > button {
        background-color: #FFFFFF !important;
        color: #FF0000 !important;
        font-weight: bold !important;
        border: 2px solid #FF0000 !important;
        font-size: 18px !important;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #FF0000 !important;
        color: #FFFFFF !important;
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
    
    /* Avisos */
    .warning-box {
        background-color: #332200 !important; border-left: 5px solid #FFA500 !important;
        padding: 15px; border-radius: 8px; margin-bottom: 20px;
    }
    
    /* Métricas */
    div[data-testid="stMetricValue"] { color: #FF4B4B !important; }
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

# 5. CONFIGURACIÓN DE ZONAS
st.markdown("### ⚙️ Configuración Personal")
col_input, col_info = st.columns([1, 2])

with col_input:
    max_hr = st.number_input("Introduce tu FC Máxima (Temporada):", min_value=100, max_value=250, value=190, step=1)

# Cálculo automático de zonas (Modelo 7 Zonas)
lim_z1 = int(max_hr * 0.60)
lim_z2 = int(max_hr * 0.70)
lim_z3 = int(max_hr * 0.80)
lim_z4 = int(max_hr * 0.88)
lim_z5 = int(max_hr * 0.93)
lim_z6 = int(max_hr * 0.97)

with col_info:
    st.info(f"""
    **Tus Zonas Calculadas (Z5, Z6 y Z7 valen 10 pts/min):**
    - **Z1:** <{lim_z1} | **Z2:** {lim_z1}-{lim_z2} | **Z3:** {lim_z2}-{lim_z3}
    - **Z4:** {lim_z3}-{lim_z4} | **Z5:** {lim_z4}-{lim_z5}
    - **Z6:** {lim_z5}-{lim_z6} | **Z7:** >{lim_z6}
    """)

# 6. SUBIDA DE ARCHIVO
st.divider()
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file:
    try:
        with st.spinner('Procesando datos...'):
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
                    st.error(f"❌ Fecha {fecha_act} fuera de rango. Solo se admite FEBRERO 2026.")
                    st.stop()

                # Cálculo de puntos
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

                # Bonus San Valentín (14 de Febrero)
                es_san_valentin = (fecha_act.month == 2 and fecha_act.day == 14)
                bonus = 2.0 if es_san_valentin else 1.0
                
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

                # Visualización de Resultados
                st.markdown("### 📊 Resultados")
                c_res1, c_res2 = st.columns(2)
                c_res1.metric("PUNTOS TOTALES", f"{round(total_pts, 2)}")
                if es_san_valentin:
                    c_res2.warning("❤️ ¡BONUS SAN VALENTÍN (x2) APLICADO!")
                else:
                    c_res2.metric("FECHA", str(fecha_act))
                
                st.table(pd.DataFrame(resumen))

                # Guardar
                st.markdown("### 💾 Guardar Puntos")
                st.warning("⚠️ IMPORTANTE: Usa SIEMPRE el MISMO NOMBRE para sumar puntos.")
                
                nombre_usuario = st.text_input("Tu Nombre:", placeholder="Ej: JUAN GARCIA").strip().upper()
                
                if st.button("GUARDAR PUNTOS"):
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
                        st.success("✅ ¡Puntos guardados correctamente!")
                        if es_san_valentin: st.balloons()
                    else:
                        st.error("Por favor, escribe tu nombre para poder guardar.")

            else:
                st.error("No se encontraron datos de pulso en el archivo.")
    except Exception as e:
        st.error(f"Error técnico: {e}")

# 7. RANKING Y GRÁFICA
st.divider()
st.subheader("🏆 Clasificación General")
try:
    data = conn.read(ttl=0)
    if data is not None and not data.empty:
        data['Puntos Totales'] = pd.to_numeric(data['Puntos Totales']).round(2)
        ranking = data.sort_values('Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1
        
        st.dataframe(ranking, use_container_width=True)

        st.markdown("### 📈 Comparativa")
        
        # Gráfica Altair con textos BLANCOS forzados
        base = alt.Chart(ranking).encode(
            x=alt.X('Puntos Totales:Q', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', axis=alt.Axis(labelColor='white', titleColor='white'))
        )
        bars = base.mark_bar(color="#FF4B4B")
        text = base.mark_text(align='left', dx=5, color='white', fontWeight='bold').encode(text='Puntos Totales:Q')
        
        st.altair_chart((bars + text).properties(height=alt.Step(40)).configure_view(strokeOpacity=0), use_container_width=True)
except:
    st.info("Cargando clasificación...")
