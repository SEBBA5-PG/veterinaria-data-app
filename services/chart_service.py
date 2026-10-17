"""Preparación de datos y figuras Plotly. app.py solo las muestra con st.plotly_chart."""

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

TOTAL = "total_venta_cop"
ETIQUETAS = {
    "cantidad": "Cantidad comprada",
    TOTAL: "Facturación (COP)",
    "precio_unitario_cop": "Precio unitario (COP)",
    "ciudad": "Ciudad",
    "categoria_producto": "Categoría",
    "canal_venta": "Canal de venta",
    "tipo_cliente": "Tipo de cliente",
    "especie_destino": "Especie destino",
    "mes": "Mes",
}


def _ranking(df: pd.DataFrame, categoria: str, valor: str, limite: int | None = None) -> pd.DataFrame:
    """Suma `valor` por `categoria`, de mayor a menor."""
    tabla = (
        df.groupby(categoria, as_index=False)[valor]
        .sum()
        .sort_values(valor, ascending=False)
    )
    return tabla.head(limite) if limite else tabla


def _barras(df: pd.DataFrame, categoria: str, valor: str, titulo: str, limite: int | None = None) -> Figure:
    tabla = _ranking(df, categoria, valor, limite)
    fig = px.bar(
        tabla, x=valor, y=categoria, orientation="h", title=titulo, labels=ETIQUETAS
    )
    fig.update_layout(yaxis={"autorange": "reversed"})
    return fig


def top_ciudades_por_cantidad(df: pd.DataFrame) -> Figure:
    return _barras(df, "ciudad", "cantidad", "Top 10 ciudades por cantidad comprada", 10)


def top_ciudades_por_facturacion(df: pd.DataFrame) -> Figure:
    return _barras(df, "ciudad", TOTAL, "Top 10 ciudades por facturación", 10)


def ventas_por_categoria(df: pd.DataFrame) -> Figure:
    return _barras(df, "categoria_producto", TOTAL, "Ventas por categoría de producto")


def ventas_por_canal(df: pd.DataFrame) -> Figure:
    return _barras(df, "canal_venta", TOTAL, "Ventas por canal")


def ventas_por_tipo_cliente(df: pd.DataFrame) -> Figure:
    return _barras(df, "tipo_cliente", TOTAL, "Ventas por tipo de cliente")


def ventas_por_especie(df: pd.DataFrame) -> Figure:
    return _barras(df, "especie_destino", TOTAL, "Ventas por especie destino")


def tendencia_mensual(df: pd.DataFrame) -> Figure:
    """Facturación por mes. Convierte `fecha` aquí para no depender de la limpieza."""
    fechas = pd.to_datetime(df["fecha"], errors="coerce")
    tabla = (
        df.assign(mes=fechas.dt.to_period("M").dt.to_timestamp())
        .dropna(subset=["mes"])
        .groupby("mes", as_index=False)[TOTAL]
        .sum()
        .sort_values("mes")
    )
    fig = px.line(
        tabla, x="mes", y=TOTAL, markers=True,
        title="Tendencia mensual de la facturación", labels=ETIQUETAS,
    )
    return fig


def dispersion_precio_cantidad(df: pd.DataFrame) -> Figure:
    return px.scatter(
        df, x="precio_unitario_cop", y="cantidad",
        color="categoria_producto", hover_data=["id_venta", "producto"],
        title="Precio unitario vs cantidad", labels=ETIQUETAS,
    )


def caja_total_por_categoria(df: pd.DataFrame) -> Figure:
    return px.box(
        df, x="categoria_producto", y=TOTAL, points="outliers",
        title="Distribución de la facturación por categoría", labels=ETIQUETAS,
    )


def _compacto(fig: Figure) -> Figure:
    """Títulos más pequeños y leyenda debajo, para que quepan en dos columnas."""
    fig.update_layout(
        title_font_size=14,
        margin={"t": 50, "l": 10, "r": 10, "b": 10},
        legend={"orientation": "h", "y": -0.25, "title": None},
    )
    return fig


_FIGURAS = {
    "Top 10 ciudades por cantidad": top_ciudades_por_cantidad,
    "Top 10 ciudades por facturación": top_ciudades_por_facturacion,
    "Ventas por categoría": ventas_por_categoria,
    "Ventas por canal": ventas_por_canal,
    "Ventas por tipo de cliente": ventas_por_tipo_cliente,
    "Ventas por especie destino": ventas_por_especie,
    "Tendencia mensual": tendencia_mensual,
    "Precio vs cantidad": dispersion_precio_cantidad,
    "Boxplot por categoría": caja_total_por_categoria,
}

# Cada entrada recibe un DataFrame y devuelve la figura ya ajustada.
GRAFICOS = {
    nombre: (lambda df, f=funcion: _compacto(f(df))) for nombre, funcion in _FIGURAS.items()
}
