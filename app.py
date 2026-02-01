import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Gure Ultra | Ranking Corazón de Hierro",
    page_icon="🔥",
    layout="centered"
)

# 2. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Error de conexión con la base de datos.")

# 3. DISEÑO CSS PROFESIONAL (Fondo 70% negro y legibilidad)
st.markdown("""
    <style>
    .stApp { background-color: #1A1A1A; }
    
    /* Textos generales en blanco */
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label {
        color: #FFFFFF !important;
    }
    
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; }

    /* Inputs de texto: fondo oscuro con borde rojo y letra blanca */
    input {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
        border: 1px solid #FF4B4B !important;
        border-radius: 5px !important;
    }

    /* Caja de subida de archivos */
    section[data-testid="stFileUploader"] {
        background-color: #262730;
        border: 2px dashed #FF4B4B;
        border-radius: 15px;
        padding: 20px;
    }

    /* Caja de aviso */
    .warning-box {
        background-color: #332200;
        border-left: 5px solid #FFA500;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. INSTRUCCIONES
st.markdown("""
    <div class="warning-box">
        <b>📋 RECORDATORIO DE DINÁMICA:</b><br>
        • Usa siempre el <b>MISMO NOMBRE</b> para que tus puntos se acumulen.<br>
        • Rango del reto: <b>1 de febrero al 1 de marzo de 2026</b>.<br>
        • ❤️ <b>BONUS SAN VALENTÍN:</b> ¡Las rutas del 14 de febrero puntúan <b>DOBLE</b>!
    </div>
    """, unsafe_allow_html=True)

# 6. PANEL DE SUBIDA
st.divider()
nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()

st.markdown("### 📁 Sube tu archivo .FIT")
uploaded_file = st.file_uploader("", type=["fit"], label_visibility="collapsed")

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Validar Fecha y Bonus
            fecha_act = None
            for record in fitfile.get_messages('session'):
                if record.get_value('start_time'):
                    fecha_act = record.get_value('start_time').date()
                    break
            
            # Control de fechas del reto
            inicio_reto = date(2026, 2, 1)
            fin_reto = date(2026, 3, 1)

            if not fecha_act or not (inicio_reto <= fecha_act <= fin_reto):
                st.error(f"❌ Actividad del {fecha_act} fuera de rango. Solo febrero de 2026.")
                st.stop()

            # Lógica de Puntos y Zonas
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]
            
            if hr_records:
                z_limits = [114, 133, 152, 171, 220]
                mults = [1.0, 1.5, 3.0, 5.0, 10.0]
                
                # --- CÁLCULO DE MULTIPLICADOR SAN VALENTÍN ---
                es_san_valentin = (fecha_act.month == 2 and fecha_act.day == 14)
                factor_puntos = 2.0 if es_san_valentin else 1.0
                
                desglose_data = []
                total_puntos_actividad = 0

                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    pts_zona = mins * mults[i] * factor_puntos
                    total_puntos_actividad += pts_zona
                    
                    if segs > 0:
                        desglose_data.append({
                            "Zona": f"Zona {i+1}",
                            "Tiempo": f"{int(mins)}m {int(segs%60)}s",
                            "Puntos": round(pts_zona, 2)
                        })

                # --- MOSTRAR RESULTADOS ---
                st.success(f"✅ Actividad del día {fecha_act} procesada con éxito.")
                
                if es_san_valentin:
                    st.balloons()
                    st.markdown("### ❤️ ¡BONUS SAN VALENTÍN APLICADO! (Puntos x2)")

                c_m1, c_m2 = st.columns(2)
                c_m1.metric("PUNTOS GENERADOS", f"+{round(total_puntos_actividad, 2)}")
                c_m2.metric("MODO", "DOBLE ❤️" if es_san_valentin else "Estándar")

                st.markdown("#### 📊 Detalle por Zonas")
                st.table(pd.DataFrame(desglose_data))

                # --- SINCRONIZACIÓN GOOGLE SHEETS ---
                df = conn.read(ttl=0)
                if df is None or df.empty:
                    df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)

                if nombre_usuario in df['Ciclista'].values:
                    idx = df[df['Ciclista'] == nombre_usuario].index
                    df.loc[idx, 'Puntos Totales'] += total_puntos_actividad
                else:
                    nueva_fila = pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [total_puntos_actividad]})
                    df = pd.concat([df, nueva_fila], ignore_index=True)

                conn.update(data=df)
                st.toast(f"¡Hecho! Puntos añadidos a {nombre_usuario}")
                
                st.markdown("#### 📈 Gráfica de Intensidad")
                st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))
            else:
                st.error("No se detectaron pulsaciones en el archivo.")
    except Exception as e:
        st.error(f"Error técnico: {e}")

# 7. CLASIFICACIÓN GLOBAL
st.divider()
st.subheader("🏆 Ranking General")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales']).round(2)
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1
        st.dataframe(ranking, use_container_width=True)
except:
    st.info("Sincronizando clasificación...")
