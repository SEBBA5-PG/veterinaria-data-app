"""Correcciones. Cada función recibe un DataFrame y devuelve una copia modificada.

Nada se ejecuta solo: la interfaz pide confirmación antes de llamar a estas funciones.
"""

import pandas as pd

from services.texto import normalizar_serie

COLUMNAS_TEXTO = ("ciudad", "metodo_pago", "canal_venta")
COLUMNAS_NUMERICAS = (
    "cantidad",
    "precio_unitario_cop",
    "costo_unitario_cop",
    "descuento_pct",
    "total_venta_cop",
    "dias_entrega",
    "calificacion_servicio",
)
ESTRATEGIAS = {
    "moda": "Moda de la columna",
    "moda_relacionada": "Moda según una columna relacionada",
    "texto_fijo": "Texto fijo",
}


def eliminar_duplicados_completos(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina las filas idénticas en todas las columnas y conserva la primera."""
    return df.drop_duplicates(keep="first").copy()


def normalizar_columnas_texto(df: pd.DataFrame, columnas=COLUMNAS_TEXTO) -> pd.DataFrame:
    """Unifica mayúsculas, tildes y espacios en las columnas indicadas."""
    resultado = df.copy()
    for columna in columnas:
        if columna in resultado.columns:
            resultado[columna] = normalizar_serie(resultado[columna])
    return resultado


def completar_faltantes(
    df: pd.DataFrame,
    columna: str,
    estrategia: str,
    columna_relacionada: str | None = None,
    valor: str | None = None,
) -> pd.DataFrame:
    """Rellena los nulos de una columna según la estrategia elegida por el usuario."""
    if estrategia not in ESTRATEGIAS:
        raise ValueError(f"Estrategia desconocida: {estrategia}")

    resultado = df.copy()
    nulos = resultado[columna].isna()
    moda_global = resultado[columna].mode(dropna=True)

    if estrategia == "texto_fijo":
        if not valor:
            raise ValueError("Indica el texto con el que completar.")
        resultado.loc[nulos, columna] = valor
    elif estrategia == "moda":
        if moda_global.empty:
            raise ValueError("La columna no tiene valores para calcular la moda.")
        resultado.loc[nulos, columna] = moda_global.iloc[0]
    else:
        if not columna_relacionada:
            raise ValueError("Elige la columna relacionada.")
        por_grupo = resultado.groupby(columna_relacionada)[columna].agg(
            lambda s: s.mode(dropna=True).iloc[0] if not s.mode(dropna=True).empty else None
        )
        relleno = resultado.loc[nulos, columna_relacionada].map(por_grupo)
        if not moda_global.empty:
            relleno = relleno.fillna(moda_global.iloc[0])
        resultado.loc[nulos, columna] = relleno
    return resultado


def eliminar_registros(df: pd.DataFrame, indices) -> pd.DataFrame:
    """Elimina las filas con los índices dados."""
    return df.drop(index=list(indices)).copy()


def actualizar_registros(df: pd.DataFrame, editado: pd.DataFrame) -> pd.DataFrame:
    """Aplica los valores corregidos por el usuario a las filas (mismo índice) y columnas editadas."""
    resultado = df.copy()
    for columna in editado.columns:
        resultado.loc[editado.index, columna] = editado[columna]
    return resultado


def celdas_editadas(original: pd.DataFrame, editado: pd.DataFrame) -> int:
    """Cuenta las celdas cuyo valor cambió entre dos DataFrames con la misma forma."""
    distinto = original.ne(editado) & ~(original.isna() & editado.isna())
    return int(distinto.to_numpy().sum())


def convertir_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """fecha → datetime y columnas numéricas → número; lo no convertible queda como nulo."""
    resultado = df.copy()
    if "fecha" in resultado.columns:
        resultado["fecha"] = pd.to_datetime(resultado["fecha"], errors="coerce")
    for columna in COLUMNAS_NUMERICAS:
        if columna in resultado.columns:
            resultado[columna] = pd.to_numeric(resultado[columna], errors="coerce")
    return resultado
