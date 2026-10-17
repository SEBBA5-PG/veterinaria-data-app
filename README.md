# Veterinaria Data Quality

App de Streamlit para analizar, detectar, corregir, visualizar y exportar un dataset de ventas veterinarias (proyecto práctico de Minería de Datos, CORHUILA).

## Ejecutar en local

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
```

En la app, sube un CSV o marca la casilla para usar el dataset de práctica incluido (`data/datos_veterinaria.csv`).

## Estructura

| Archivo | Responsabilidad |
| --- | --- |
| `app.py` | Interfaz Streamlit (pestañas: Calidad de datos, Limpieza, Gráficos, Exportar) |
| `services/data_loader.py` | Carga y exportación de CSV |
| `services/quality_service.py` | Detecta problemas, no corrige |
| `services/cleaning_service.py` | Aplica correcciones confirmadas por el usuario |
| `services/chart_service.py` | Prepara datos y figuras Plotly |
| `services/texto.py` | Normalización de texto compartida |

Ninguna corrección se aplica sin confirmación; los outliers se marcan para revisión, no se borran.
