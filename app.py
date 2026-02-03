import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import altair as alt

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Gure Ultra | Ranking Corazón de Hierro", page_icon="🔥")

# 2. DISEÑO CSS (Fondo oscuro, texto blanco, input legible)
st.markdown("""
    <style>
    .stApp { background-color: #1A1A1A !important; }
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3 {
        color: #FFFFFF !important;
    }
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; }
    input { background-color: #FFFFFF !important; color: #000000 !important; font-weight: bold; }
    [data-testid="stFileUploader"] { border: 2px dashed #FF0000 !important; background-color: #262730 !important; }
    [data-testid="stFileUploader"] section div span { font-size: 0 !important; }
    [data-testid="stFileUploader"] section div span::before { content: "Arrastra tu archivo .FIT aquí"; color: #FF0000 !important; font-size: 16px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN
conn = st.connection("gsheets", type=GSheetsConnection)

# 4. CABECERA
st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. INPUTS
nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()

# DEFINICIÓN DE ZONAS (Ajusta estos valores a tus zonas reales si es necesario)
# Estos límites marcan donde TERMINA cada zona.
with st.expander("📊 Configurar Umbrales de tus 7 Zonas"):
    z1 = st.number_input("Fin Zona 1 (Recuperación)", value=114)
    z2 = st.number_input("Fin Zona 2 (Resistencia)", value=133)
    z3 = st.number_input("Fin Zona 3 (Tempo)", value=152)
    z4 = st.number_input("Fin Zona 4 (Umbral)", value=171)
    z5 = st.number_input("Fin Zona 5 (VO2 Máx)", value=185)
    z6 = st.number_input("Fin Zona 6 (Cap. Anaeróbica)", value=195)
    st.caption("Zona 7 es cualquier valor por encima de la Zona 6.")

uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file and nombre_usuario:
    try:
        fitfile = fitparse.FitFile(uploaded_file)
        records = list(fitfile.get_messages('record'))
        
        # Obtener fecha de la actividad
        fecha_act = None
        for msg in fitfile.get_messages('session'):
            fecha_act = msg.get_value('start_time').date()
            break
        
        if not fecha_act or not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
            st.error("Fecha fuera de rango (Solo Febrero 2026).")
            st.stop()

        # MOTOR DE CÁLCULO POR SEGUNDOS REALES
        # Usamos un diccionario para acumular segundos en cada zona
        segundos_zonas = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0}
        puntos_por_minuto = {1:1, 2:1.5, 3:3, 4:5, 5:10, 6:10, 7:10}
        
        last_time = None
        hr_lista = []

        for record in records:
            timestamp = record.get_value('timestamp')
            hr = record.get_value('heart_rate')
            
            if timestamp and hr:
                hr_lista.append(hr)
                if last_time:
                    # Diferencia de tiempo entre registros (normalmente 1 seg)
                    delta = (timestamp - last_time).total_seconds()
                    if delta > 10: delta = 1 # Evitar saltos por pausa
                    
                    # Clasificar en las 7 zonas
                    if hr <= z1: segundos_zonas[1] += delta
                    elif hr <= z2: segundos_zonas[2] += delta
                    elif hr <= z3: segundos_zonas[3] += delta
                    elif hr <= z4: segundos_zonas[4] += delta
                    elif hr <= z5: segundos_zonas[5] += delta
                    elif hr <= z6: segundos_zonas[6] += delta
                    else: segundos_zonas[7] += delta
                
                last_time = timestamp

        # Calcular puntos con Bonus San Valentín
        bonus = 2.0 if (fecha_act.month == 2 and fecha_act.day == 14) else 1.0
        total_puntos = 0
        tabla_datos = []

        for zona, segs in segundos_zonas.items():
            if segs > 0:
                mins = segs / 60
                pts = mins * puntos_por_minuto[zona] * bonus
                total_puntos += pts
                tabla_datos.append({
                    "Zona": f"Zona {zona}",
                    "Tiempo": f"{int(segs//60)}m {int(segs%60)}s",
                    "Puntos": round(pts, 2)
                })

        # Mostrar resultados
        st.success(f"Actividad procesada: {fecha_act}")
        if bonus > 1: st.markdown("### ❤️ BONUS DOBLE SAN VALENTÍN APLICADO")
        
        st.metric("PUNTOS TOTALES DE ESTA RUTA", round(total_puntos, 2))
        st.table(pd.DataFrame(tabla_datos))

        # ACTUALIZAR GOOGLE SHEETS
        df = conn.read(ttl=0)
        if df is None or df.empty:
            df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
        
        df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)
        
        if nombre_usuario in df['Ciclista'].values:
            df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += total_puntos
        else:
            df = pd.concat([df, pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [total_puntos]})], ignore_index=True)
        
        conn.update(data=df)
        st.toast("Clasificación actualizada")

    except Exception as e:
        st.error(f"Error: {e}")

# 7. RANKING Y GRÁFICA
st.divider()
st.subheader("🏆 Clasificación General (Empieza en 1)")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales']).round(2)
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        ranking_display = ranking.copy()
        ranking_display.index += 1
        st.dataframe(ranking_display, use_container_width=True)

        # Gráfica horizontal
        chart = alt.Chart(ranking).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Puntos Totales:Q', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', axis=alt.Axis(labelColor='white', titleColor='white')),
            text='Puntos Totales:Q'
        )
        st.altair_chart(chart.properties(height=alt.Step(40)), use_container_width=True)
except:
    pass
