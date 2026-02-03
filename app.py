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
    layout="centered"
)

# 2. DISEÑO CSS "BLACK & RED"
st.markdown("""
    <style>
    .stApp { background-color: #1A1A1A !important; }
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3 {
        color: #FFFFFF !important;
    }
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; font-weight: bold; }
    
    input { background-color: #FFFFFF !important; color: #000000 !important; font-weight: bold; }

    [data-testid="stFileUploader"] {
        background-color: #262730 !important;
        border: 2px dashed #FF0000 !important;
        border-radius: 15px;
        padding: 10px;
    }
    [data-testid="stFileUploader"] section div span { font-size: 0 !important; }
    [data-testid="stFileUploader"] section div span::before {
        content: "Arrastra tu archivo .FIT aquí";
        color: #FF0000 !important; font-size: 16px !important; font-weight: bold;
    }
    [data-testid="stFileUploader"] button span::before {
        content: "Buscar archivo"; color: #FF0000 !important; font-size: 14px !important;
    }
    .warning-box {
        background-color: #332200 !important; border-left: 5px solid #FFA500 !important;
        padding: 15px; border-radius: 8px; margin-bottom: 20px;
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
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

st.markdown("""
    <div class="warning-box">
        <b>🏆 PUNTUACIÓN:</b> Z1: 1pt | Z2: 1.5pts | Z3: 3pts | Z4: 5pts | <b>Z5, Z6, Z7: 10 pts</b>.<br>
        ❤️ <b>14 FEB:</b> Puntos Dobles. Ranking empieza en 1.
    </div>
    """, unsafe_allow_html=True)

# 5. PANEL DE SUBIDA (Ahora procesa solo con el archivo)
st.divider()
st.subheader("📤 1. Sube tu actividad")
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file:
    try:
        with st.spinner('Analizando tu esfuerzo segundo a segundo...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer registros de pulso y tiempo
            records = []
            for m in fitfile.get_messages('record'):
                ts = m.get_value('timestamp')
                hr = m.get_value('heart_rate')
                if ts and hr:
                    records.append({'t': ts, 'hr': hr})
            
            if len(records) > 1:
                # Obtener la fecha del primer registro (100% fiable)
                fecha_act = records[0]['t'].date()
                
                # Validar fecha del reto (Feb 2026)
                if not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
                    st.error(f"❌ La actividad es del {fecha_act}. Solo se acepta febrero de 2026.")
                    st.stop()

                # CONFIGURACIÓN DE ZONAS EN PANTALLA
                st.markdown("### ⚙️ 2. Confirma tus Zonas")
                st.caption("Ajusta los topes de pulsaciones si no coinciden con tu perfil.")
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                lim_z1 = c1.number_input("Fin Z1", value=114)
                lim_z2 = c2.number_input("Fin Z2", value=133)
                lim_z3 = c3.number_input("Fin Z3", value=152)
                lim_z4 = c4.number_input("Fin Z4", value=171)
                lim_z5 = c5.number_input("Fin Z5", value=185)
                lim_z6 = c6.number_input("Fin Z6", value=195)
                # Z7 es todo lo que supere lim_z6

                # CÁLCULO PRECISO DE SEGUNDOS
                secs_zones = [0.0] * 7
                points_map = [1.0, 1.5, 3.0, 5.0, 10.0, 10.0, 10.0]
                
                for i in range(len(records)-1):
                    delta = (records[i+1]['t'] - records[i]['t']).total_seconds()
                    if delta > 15: delta = 1 # Filtro de pausas largas
                    
                    hr = records[i]['hr']
                    if hr <= lim_z1: secs_zones[0] += delta
                    elif hr <= lim_z2: secs_zones[1] += delta
                    elif hr <= lim_z3: secs_zones[2] += delta
                    elif hr <= lim_z4: secs_zones[3] += delta
                    elif hr <= lim_z5: secs_zones[4] += delta
                    elif hr <= lim_z6: secs_zones[5] += delta
                    else: secs_zones[6] += delta

                # RESULTADOS
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
                            "Tiempo": f"{int(s//60)}m {int(s%60)}s",
                            "Puntos": round(p, 2)
                        })

                st.markdown("### 📊 3. Tus Resultados")
                if bonus > 1: st.info("❤️ ¡BONUS SAN VALENTÍN (x2) ACTIVADO!")
                
                col_res1, col_res2 = st.columns(2)
                col_res1.metric("PUNTOS GENERADOS", f"+{round(total_pts, 2)}")
                col_res2.metric("FECHA DE ACTIVIDAD", str(fecha_act))
                
                st.table(pd.DataFrame(resumen))

                # GUARDAR EN RANKING (SOLO SI PONE NOMBRE)
                st.markdown("### 💾 4. Guardar en el Ranking")
                nombre_usuario = st.text_input("Introduce tu Nickname para sumar los puntos:").strip().upper()
                if st.button("Guardar Puntos"):
                    if nombre_usuario:
                        df = conn.read(ttl=0)
                        if df is None or df.empty:
                            df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                        
                        df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)

                        if nombre_usuario in df['Ciclista'].values:
                            df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += total_pts
                        else:
                            df = pd.concat([df, pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [total_pts]})], ignore_index=True)
                        
                        conn.update(data=df)
                        st.success(f"✅ ¡Hecho! Puntos sumados al perfil de {nombre_usuario}")
                        st.balloons()
                    else:
                        st.error("Debes introducir un nombre para guardar.")
            else:
                st.error("El archivo no tiene suficientes datos de pulso.")
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

# 6. RANKING Y GRÁFICA
st.divider()
st.subheader("🏆 Clasificación General")
try:
    data = conn.read(ttl=0)
    if data is not None and not data.empty:
        data['Puntos Totales'] = pd.to_numeric(data['Puntos Totales']).round(2)
        ranking = data.sort_values('Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1 # Ranking empieza en 1
        
        st.dataframe(ranking, use_container_width=True)

        st.write("")
        st.subheader("📈 Comparativa Visual")
        # Gráfica horizontal con puntos en las barras
        bars = alt.Chart(ranking).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Puntos Totales:Q', title='Puntos Totales', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', title='', axis=alt.Axis(labelColor='white', titleColor='white'))
        )
        labels = bars.mark_text(align='left', baseline='middle', dx=5, color='white', fontWeight='bold').encode(text='Puntos Totales:Q')
        st.altair_chart((bars + labels).properties(height=alt.Step(45)), use_container_width=True)
except:
    st.info("Esperando datos del ranking...")
