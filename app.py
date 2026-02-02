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

# 2. DISEÑO CSS AVANZADO (Fondo 70% negro, textos blancos, caja roja/español)
st.markdown("""
    <style>
    /* Fondo principal */
    .stApp {
        background-color: #1A1A1A !important;
    }
    
    /* Forzar visibilidad de textos en blanco puro */
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3 {
        color: #FFFFFF !important;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #FF4B4B !important;
        text-align: center;
        font-weight: bold;
    }

    /* Caja de texto del nombre */
    input {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
        border: 2px solid #FF4B4B !important;
    }

    /* --- CAJA DE SUBIDA PERSONALIZADA --- */
    [data-testid="stFileUploader"] {
        background-color: #262730 !important;
        border: 2px dashed #FF0000 !important;
        border-radius: 15px !important;
        padding: 10px !important;
    }
    
    /* Textos en ROJO y ESPAÑOL dentro del cargador */
    [data-testid="stFileUploader"] section div span {
        font-size: 0 !important;
    }
    [data-testid="stFileUploader"] section div span::before {
        content: "Arrastra tu archivo .FIT aquí";
        color: #FF0000 !important;
        font-size: 16px !important;
        font-weight: bold;
    }
    [data-testid="stFileUploader"] button span::before {
        content: "Buscar archivo";
        color: #FF0000 !important;
        font-size: 14px !important;
    }

    /* Advertencia naranja */
    .warning-box {
        background-color: #332200 !important;
        border-left: 5px solid #FFA500 !important;
        padding: 15px !important;
        border-radius: 8px !important;
        margin-bottom: 20px !important;
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Error de conexión con la base de datos.")

# 4. CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. INSTRUCCIONES
st.markdown("""
    <div class="warning-box">
        <b>📋 REGLAS DEL RETO:</b><br>
        • Usa siempre <b>EL MISMO NOMBRE</b> para acumular tus puntos.<br>
        • Periodo: <b>1 de febrero al 1 de marzo de 2026</b>.<br>
        • ❤️ <b>SAN VALENTÍN (14 Feb):</b> ¡Puntúa <b>DOBLE (x2)</b>!<br>
        • <b>Zonas:</b> Z5, Z6 y Z7 puntúan como zona de máxima intensidad (10 pts/min).
    </div>
    """, unsafe_allow_html=True)

# 6. PANEL DE ENTRADA
st.divider()
nombre_usuario = st.text_input("Introduce tu Nombre o Nickname:").strip().upper()

st.markdown("### 📤 Sube tu actividad")
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Obtener fecha
            fecha_act = None
            for record in fitfile.get_messages('session'):
                if record.get_value('start_time'):
                    fecha_act = record.get_value('start_time').date()
                    break
            
            # Validar rango de fechas (Febrero 2026)
            inicio_reto = date(2026, 2, 1)
            fin_reto = date(2026, 3, 1)

            if not fecha_act or not (inicio_reto <= fecha_act <= fin_reto):
                st.error(f"❌ Actividad del {fecha_act}. Fuera de rango.")
                st.stop()

            # Procesar datos de pulso
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]
            
            if hr_records:
                # Definición de límites (BPM)
                # Z1 (<114), Z2 (114-133), Z3 (133-152), Z4 (152-171), Z5+ (>171)
                z_limits = [114, 133, 152, 171] 
                mults = [1.0, 1.5, 3.0, 5.0, 10.0] # El último índice es para Z5, Z6 y Z7
                
                es_sv = (fecha_act.month == 2 and fecha_act.day == 14)
                factor = 2.0 if es_sv else 1.0
                
                desglose_data = []
                puntos_sesion = 0

                # Calculamos Z1 a Z4
                for i in range(4):
                    if i == 0:
                        segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    else:
                        segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    pts_zona = mins * mults[i] * factor
                    puntos_sesion += pts_zona
                    
                    if segs > 0:
                        desglose_data.append({
                            "Zona": f"Z{i+1}",
                            "Tiempo": f"{int(mins)}m {int(segs%60)}s",
                            "Puntos": round(pts_zona, 2)
                        })

                # LÓGICA ESPECIAL: Z5, Z6 y Z7 (Cualquier cosa por encima de Z4)
                segs_max = sum(1 for hr in hr_records if hr > z_limits[3])
                if segs_max > 0:
                    mins_max = segs_max / 60
                    pts_max = mins_max * mults[4] * factor
                    puntos_sesion += pts_max
                    desglose_data.append({
                        "Zona": "Z5 / Z6 / Z7",
                        "Tiempo": f"{int(mins_max)}m {int(segs_max%60)}s",
                        "Puntos": round(pts_max, 2)
                    })

                # --- MOSTRAR RESULTADOS ---
                if es_sv:
                    st.balloons()
                    st.markdown("### ❤️ ¡BONUS SAN VALENTÍN ACTIVADO! (Puntos x2)")

                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_sesion, 2)} puntos!")
                
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("PUNTOS HOY", f"+{round(puntos_sesion, 2)}")
                col_m2.metric("FECHA", str(fecha_act))

                st.markdown("#### 📊 Desglose de la sesión")
                st.table(pd.DataFrame(desglose_data))

                # --- ACTUALIZACIÓN DE DATOS EN GOOGLE SHEETS ---
                df = conn.read(ttl=0)
                if df is None or df.empty:
                    df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)

                if nombre_usuario in df['Ciclista'].values:
                    idx = df[df['Ciclista'] == nombre_usuario].index
                    df.loc[idx, 'Puntos Totales'] += puntos_sesion
                else:
                    nueva_fila = pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [puntos_sesion]})
                    df = pd.concat([df, nueva_fila], ignore_index=True)

                conn.update(data=df)
                st.toast("Clasificación actualizada correctamente.")
                
                st.markdown("#### 📈 Gráfica de Pulso")
                st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))
            else:
                st.error("No se detectó frecuencia cardíaca en el archivo.")
    except Exception as e:
        st.error(f"Error al procesar el archivo FIT.")

# 7. RANKING GLOBAL
st.divider()
st.subheader("🏆 Clasificación General")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales']).round(2)
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1
        st.dataframe(ranking, use_container_width=True)
except:
    st.info("Sincronizando clasificación...")
