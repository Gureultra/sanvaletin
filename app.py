import streamlit as st
import fitparse
import pandas as pd

st.set_page_config(page_title="Calculadora Reto Ciclista", layout="centered")

st.title("🚴‍♂️ Calculador de Puntos: Reto FC")
st.write("Sube tu archivo .fit y calcularemos tus puntos automáticamente.")

# 1. Configuración automática de zonas
fc_max = st.number_input("Introduce tu FC Máxima (o usa 220 - edad):", value=190)

zonas = {
    "Z1": (0, fc_max * 0.60, 1.0),
    "Z2": (fc_max * 0.60, fc_max * 0.70, 1.5),
    "Z3": (fc_max * 0.70, fc_max * 0.80, 3.0),
    "Z4": (fc_max * 0.80, fc_max * 0.90, 5.0),
    "Z5": (fc_max * 0.90, fc_max * 1.10, 10.0), # 1.10 para cubrir picos por encima de la máxima teórica
}

uploaded_file = st.file_uploader("Elige tu archivo .fit", type=["fit"])

if uploaded_file is not None:
    fitfile = fitparse.FitFile(uploaded_file)
    hr_data = []

    for record in fitfile.get_messages('record'):
        for data in record:
            if data.name == 'heart_rate':
                hr_data.append(data.value)

    if hr_data:
        df = pd.DataFrame(hr_data, columns=['hr'])
        
        # Clasificación por zonas
        def calcular_puntos(hr):
            for zona, (min_hr, max_hr, mult) in zonas.items():
                if min_hr <= hr < max_hr:
                    return zona, mult
            return None, 0

        df['zona'], df['multiplicador'] = zip(*df['hr'].apply(calcular_puntos))
        
        # Cálculo de tiempo (cada registro suele ser 1 segundo)
        segundos_por_zona = df['zona'].value_counts()
        total_puntos = 0
        resumen = []

        for zona in ["Z1", "Z2", "Z3", "Z4", "Z5"]:
            segundos = segundos_por_zona.get(zona, 0)
            minutos = segundos / 60
            puntos = minutos * zonas[zona][2]
            total_puntos += puntos
            resumen.append({
                "Zona": zona,
                "Tiempo (min)": round(minutos, 2),
                "Puntos": round(puntos, 2)
            })

        # Mostrar Resultados
        st.metric("Puntos Totales Conseguidos", f"{round(total_puntos, 2)} pts")
        st.table(pd.DataFrame(resumen))
        
    else:
        st.error("No se encontraron datos de Frecuencia Cardíaca en este archivo.")
