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
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3, div {
        color: #FFFFFF !important;
    }
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; font-weight: bold; }
    
    /* Inputs */
    input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: 2px solid #FF4B4B !important;
    }
    
    /* Botón Guardar */
    div[data-testid="stButton"] button {
        background-color: #FFFFFF !important;
        border: 2px solid #FF0000 !important;
        color: #FF0000 !important;
        font-size: 20px !important;
        font-weight: bold !important;
        width: 100%;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #FF0000 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stButton"] button p { color: #FF0000 !important; }
    div[data-testid="stButton"] button:hover p { color: #FFFFFF !important; }

    /* Caja de subida */
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
    
    /* Avisos y Métricas */
    .instruction-box {
        background-color: #2D2D2D; border: 2px solid #FF4B4B;
        border-radius: 10px; padding: 20px; margin-bottom: 25px;
    }
    div[data-testid="stMetricValue"] { color: #FF4B4B !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Error de conexión con Google Sheets.")

# 4. CABECERA
col_h1, col_h2, col_h3 = st.columns([1, 1, 1])
with col_h2:
    st.image("https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png", use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. INSTRUCCIONES
st.markdown("""
    <div class="instruction-box">
        <h4>📋 INSTRUCCIONES</h4>
        <ol>
            <li><b>Sube tu Archivo FIT:</b> La app detectará si usas Pulso o Potencia.</li>
            <li><b>Configura tus Zonas:</b> Introduce tu FC Máxima o FTP según corresponda.</li>
            <li><b>Nombre Único:</b> Usa siempre el mismo nombre para el ranking.</li>
            <li>❤️ <b>14 de Febrero:</b> ¡Puntos DOBLES en San Valentín!</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

# 6. SUBIDA Y LÓGICA INTELIGENTE
st.divider()
st.subheader("📤 Sube tu actividad (.FIT)")
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file:
    try:
        with st.spinner('Analizando tipo de datos (Pulso vs Potencia)...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # 1. Extracción de datos
            records = []
            has_hr = False
            has_power = False
            
            for m in fitfile.get_messages('record'):
                ts = m.get_value('timestamp')
                hr = m.get_value('heart_rate')
                pwr = m.get_value('power')
                
                if ts:
                    # Guardamos el dato disponible
                    records.append({'t': ts, 'hr': hr, 'pwr': pwr})
                    if hr: has_hr = True
                    if pwr: has_power = True
            
            if len(records) > 1:
                # 2. Validación de Fecha
                fecha_act = records[0]['t'].date()
                if not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
                    st.error(f"❌ Fecha {fecha_act} fuera de rango. Solo se admite FEBRERO 2026.")
                    st.stop()

                # 3. SELECCIÓN DE MODO
                mode = "NONE"
                if has_hr:
                    mode = "HR"
                elif has_power:
                    mode = "POWER"
                
                # 4. CONFIGURACIÓN DINÁMICA DE ZONAS
                st.markdown("### ⚙️ Configuración de Zonas")
                
                secs_zones = [0.0] * 7
                points_map = [1.0, 1.5, 3.0, 5.0, 10.0, 10.0, 10.0]
                
                if mode == "HR":
                    st.success("✅ Se han detectado datos de **FRECUENCIA CARDÍACA**.")
                    val_ref = st.number_input("Introduce tu FC MÁXIMA de la temporada:", 100, 250, 190)
                    
                    # Límites FC (7 Zonas)
                    l1, l2 = int(val_ref*0.60), int(val_ref*0.70)
                    l3, l4 = int(val_ref*0.80), int(val_ref*0.88)
                    l5, l6 = int(val_ref*0.93), int(val_ref*0.97)
                    limits = [l1, l2, l3, l4, l5, l6]
                    
                    st.info(f"Zonas FC: Z1<{l1} | Z2:{l1}-{l2} | Z3:{l2}-{l3} | Z4:{l3}-{l4} | Z5+ >{l4}")

                elif mode == "POWER":
                    st.warning("⚠️ No hay pulso, pero sí **POTENCIA**. Usaremos Vatios.")
                    val_ref = st.number_input("Introduce tu FTP (Umbral de Potencia):", 100, 500, 250)
                    
                    # Límites Potencia (Coggan 7 Zonas)
                    # Z1 <55%, Z2 56-75%, Z3 76-90%, Z4 91-105%, Z5 106-120%, Z6 121-150%, Z7 >150%
                    l1, l2 = int(val_ref*0.55), int(val_ref*0.75)
                    l3, l4 = int(val_ref*0.90), int(val_ref*1.05)
                    l5, l6 = int(val_ref*1.20), int(val_ref*1.50)
                    limits = [l1, l2, l3, l4, l5, l6]
                    
                    st.info(f"Zonas Vatios: Z1<{l1} | Z2:{l1}-{l2} | Z3:{l2}-{l3} | Z4:{l3}-{l4} | Z5+ >{l4}")
                
                else:
                    st.error("❌ El archivo no tiene ni Pulso ni Potencia. No se puede puntuar.")
                    st.stop()

                # 5. CÁLCULO DE PUNTOS
                for i in range(len(records)-1):
                    delta = (records[i+1]['t'] - records[i]['t']).total_seconds()
                    if delta > 15: delta = 1 
                    
                    # Obtener valor según modo
                    val = records[i]['hr'] if mode == "HR" else records[i]['pwr']
                    
                    if val:
                        if val <= limits[0]: secs_zones[0] += delta
                        elif val <= limits[1]: secs_zones[1] += delta
                        elif val <= limits[2]: secs_zones[2] += delta
                        elif val <= limits[3]: secs_zones[3] += delta
                        elif val <= limits[4]: secs_zones[4] += delta
                        elif val <= limits[5]: secs_zones[5] += delta
                        else: secs_zones[6] += delta

                # Bonus
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
                            "Tiempo": f"{int(s//60)}m {int(s%60)}s",
                            "Puntos": round(p, 2)
                        })

                # 6. RESULTADOS
                st.markdown("### 📊 Resultados")
                c1, c2 = st.columns(2)
                c1.metric("PUNTOS TOTALES", f"{round(total_pts, 2)}")
                if es_sv: c2.warning("❤️ ¡BONUS SAN VALENTÍN (x2)!")
                else: c2.metric("FECHA", str(fecha_act))
                
                st.table(pd.DataFrame(resumen))

                # 7. GUARDAR
                st.markdown("### 💾 Guardar Puntos")
                nombre_usuario = st.text_input("Tu Nombre (siempre el mismo):", placeholder="Ej: JUAN PEREZ").strip().upper()
                
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
                        st.success(f"✅ ¡Guardado! {nombre_usuario}: +{round(total_pts, 2)} pts")
                        if es_sv: st.balloons()
                    else:
                        st.error("❌ Escribe tu nombre para guardar.")

            else:
                st.error("Archivo vacío o ilegible.")
    except Exception as e:
        st.error(f"Error procesando: {e}")

# 8. RANKING
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
        text = bars.mark_text(align='left', dx=5, color='white', fontWeight='bold').encode(text='Puntos Totales:Q')
        st.altair_chart((bars + text).properties(height=alt.Step(50), background='transparent').configure_view(strokeOpacity
