import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import base64

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Ranking Corazón de Hierro", layout="centered")

# Función para mostrar el logo SVG que proporcionaste
def render_svg(svg_code):
    b64 = base64.b64encode(svg_code.encode('utf-8')).decode("utf-8")
    html = f'<img src="data:image/svg+xml;base64,{b64}" width="250"/>'
    st.write(html, unsafe_allow_html=True)

# Logo SVG (Gure Ultra)
logo_svg = """<?xml version="1.0" encoding="UTF-8" standalone="no"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg width="100%" height="100%" viewBox="0 0 11407 5054" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xml:space="preserve" xmlns:serif="http://www.serif.com/" style="fill-rule:evenodd;clip-rule:evenodd;stroke-linejoin:round;stroke-miterlimit:2;"><path d="M2689.94,5042.64c-872.084,0 -1744.2,-0.515 -2616.28,1.175c-54.222,0.115 -73.221,-8.855 -72.374,-67.631c3.793,-261.7 3.385,-523.486 0.145,-785.215c-0.612,-52.328 15.876,-61.556 64.729,-61.527c1752.81,1.175 3505.61,1.175 5258.42,0.057c47.919,-0.029 65.312,7.881 64.67,60.353c-3.152,263.82 -2.801,527.727 -0.058,791.547c0.525,49.95 -12.724,62.474 -63.59,62.388c-878.534,-1.605 -1757.1,-1.147 -2635.66,-1.147" style="fill:#df1919;fill-rule:nonzero;"/><path d="M5396.05,1442.58c0.087,-44.483 -14.974,-51.475 -54.65,-51.417c-926.547,1.078 -1853.06,1.399 -2779.58,-0.291c-51.824,-0.087 -58.32,17.887 -58,62.603c1.894,263.958 2.972,527.944 -0.757,791.844c-0.845,61.321 13.167,78.159 76.586,77.809c511.631,-2.884 1023.26,-0.874 1534.89,-2.738c50.018,-0.175 65.894,11.594 63.593,62.982c-4.399,98.521 -5.797,197.655 0.262,296.002c3.904,63.622 -16.313,76.848 -77.576,76.673c-859.865,-2.098 -1719.73,-1.369 -2579.62,-1.631c-36.472,-0 -73.148,-1.137 -109.417,-4.982c-120.166,-12.672 -187.197,-83.927 -187.401,-203.132c-0.757,-450.805 0.583,-929.255 -0.874,-1381.31c0.204,-119.234 64.73,-190.314 184.925,-202.986c36.239,-3.816 72.916,-4.953 109.417,-4.953c751.322,-0.233 3820.45,-1.252 3820.45,-1.252c0,-0 46.981,13.301 46.981,-51.328c0,-71.071 -13.474,-139.314 -31.04,-208.18c-39.24,-174.088 -106.75,-252.269 -191.376,-349.829c-212.978,-245.489 -500.066,-339.99 -811.391,-342.03c-1092.01,-7.078 -2184.08,-3.845 -3276.09,-2.621c-157.454,0.174 -310.713,29.917 -459.253,85.529c-280.271,104.989 -464.846,297.458 -553.9,583.439c-43.202,138.723 -61.117,280.388 -61.467,424.383c-1.165,489.288 -0.786,1007.74 -0.087,1496.99c0.145,94.385 6.729,188.712 25.169,281.465c66.74,335.97 242.634,583.178 570.884,713.219c156.842,62.137 318.258,89.2 484.277,89.666c696.497,1.806 1393,0.757 2089.49,0.757l0,1.282c720.152,0 1440.31,-0.146 2160.46,0.408c38.89,0.029 65.72,3.321 65.545,-53.893c-2.272,-727.493 -1.952,-1454.99 -0.437,-2182.48" style="fill:#df1919;fill-rule:nonzero;"/><path d="M8722.75,5048.21c-520.254,-0 -1040.51,0.786 -1560.73,-0.437c-179.069,-0.408 -354.41,-22.868 -524.827,-84.976c-369.355,-134.615 -550.929,-410.633 -606.861,-784.969c-13.022,-87.277 -14.682,-175.282 -14.711,-263.287c-0.088,-815.499 0.553,-1631 -1.253,-2446.5c-0.146,-55.116 11.099,-72.653 69.915,-72.158c363.266,2.943 726.59,2.389 1089.91,0.292c50.63,-0.292 64.613,13.05 64.526,64.35c-1.719,794.058 -1.37,1588.09 -1.107,2382.14c0.058,219.678 63.36,281.524 284.349,281.495c797.554,-0.146 1595.14,-0.204 2392.69,0.029c47.571,0.029 94.647,-0.962 139.655,-18.382c81.363,-31.462 132.256,-85.733 133.1,-177.555c0.321,-30.034 2.244,-60.039 2.273,-90.073c0.204,-789.747 0.874,-1579.49 -0.903,-2369.24c-0.146,-55.378 11.623,-73.352 70.148,-72.915c363.295,2.68 726.619,1.573 1089.91,0.757c38.482,-0.087 58.671,17.248 58.525,69.801c-2.68,866.973 2.475,1717.22 -0.846,2584.22c-0.844,219.387 -62.806,424.879 -191.566,603.832c-157.163,218.338 -386.455,319.569 -643.013,367.868c-109.97,20.683 -221.572,26.16 -333.61,25.985c-505.164,-0.67 -1010.39,-0.291 -1515.58,-0.291" style="fill:#df1919;fill-rule:nonzero;"/><path d="M8703.1,960.715c-873.122,-0 -1746.24,-0.583 -2619.34,1.223c-60.962,0.146 -78.93,-14.566 -77.946,-78.538c4.166,-268.094 3.124,-536.305 0.665,-804.457c-0.521,-55.524 13.975,-72.683 71.668,-72.624c1744.13,1.573 3488.2,1.252 5232.31,1.165c88.738,-0 88.564,-0.204 88.536,85.5c-0.058,259.646 -0,519.263 -0,778.88c-0,88.967 -0.029,89.025 -89.347,89.054l-2606.55,0l-0,-0.203Z" style="fill:#df1919;fill-rule:nonzero;"/></svg>"""

render_svg(logo_svg)
st.title("🏆 Ranking: Corazón de Hierro")

# 2. INFORMACIÓN DEL RETO
with st.expander("ℹ️ Ver baremo de puntos por zona"):
    st.write("""
    - **Z1**: 1 min = 1.0 punto
    - **Z2**: 1 min = 1.5 puntos
    - **Z3**: 1 min = 3.0 puntos
    - **Z4**: 1 min = 5.0 puntos
    - **Z5**: 1 min = 10.0 puntos
    """)
    st.info("❤️ **BONUS SAN VALENTÍN**: Las actividades del 14 de febrero valen el DOBLE.")

# 3. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# 4. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Nombre / Nickname:").strip().upper()
st.caption("⚠️ **Pon siempre el mismo nombre para sumar los puntos.**")

uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Detectar fecha (Bonus x2)
            fecha_act = None
            for record in fitfile.get_messages('session'):
                fecha_act = record.get_value('start_time')
                if fecha_act: break
            
            es_san_valentin = (fecha_act and fecha_act.month == 2 and fecha_act.day == 14)

            # Zonas de FC
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            if len(z_limits) < 4: z_limits = [114, 133, 152, 171, 220]

            # Datos de pulso
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
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Desglose:**")
                    st.table(pd.DataFrame(stats_zonas))
                with col2:
                    st.write("**Esfuerzo (BPM):**")
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
                st.error("No se encontraron datos de pulso.")
    except Exception as e:
        st.error(f"Error al procesar: {e}")

# 5. RANKING
st.divider()
st.subheader("📊 Ranking Mensual Acumulado")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales'], errors='coerce')
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False)
        st.dataframe(ranking, use_container_width=True, hide_index=True)
    else:
        st.info("Ranking vacío.")
except:
    st.info("Conectando con la base de datos...")
