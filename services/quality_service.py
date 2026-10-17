"""Diagnóstico de calidad. Solo analiza: nunca modifica el DataFrame recibido."""

import pandas as pd

from services.texto import mascara_inconsistente

COLUMNAS_TEXTO = ("ciudad", "metodo_pago", "canal_venta")


def perfilar_dataset(df: pd.DataFrame) -> dict:
    """Resumen general de estructura, faltantes, duplicados y estadísticas."""
    faltantes = df.isna().sum()
    return {
        "filas": len(df),
        "columnas": df.shape[1],
        "nombres_columnas": list(df.columns),
        "tipos": df.dtypes.astype(str).to_dict(),
        "faltantes_por_columna": faltantes.to_dict(),
        "total_faltantes": int(faltantes.sum()),
        "filas_duplicadas": int(df.duplicated().sum()),
        "estadisticas": df.describe(include="number"),
    }


def _numerica(df: pd.DataFrame, columna: str) -> pd.Series:
    """Serie numérica; lo que no se pueda convertir queda como NaN (no cuenta como inválido)."""
    return pd.to_numeric(df[columna], errors="coerce")


def _fuera_de_rango(df, columna, minimo=None, maximo=None, minimo_estricto=False):
    serie = _numerica(df, columna)
    invalido = pd.Series(False, index=df.index)
    if minimo is not None:
        invalido |= (serie <= minimo) if minimo_estricto else (serie < minimo)
    if maximo is not None:
        invalido |= serie > maximo
    return df[invalido]


def _texto_inconsistente(df: pd.DataFrame) -> pd.DataFrame:
    mascara = pd.Series(False, index=df.index)
    for columna in COLUMNAS_TEXTO:
        if columna in df.columns:
            mascara |= mascara_inconsistente(df[columna])
    return df[mascara]


def detectar_problemas(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Devuelve un DataFrame con los registros involucrados por cada tipo de problema.

    No corrige ni elimina nada. Los problemas sin casos se devuelven vacíos
    para que la interfaz pueda mostrar que la regla se evaluó y pasó.
    """
    faltantes = df[df.isna().any(axis=1)]
    return {
        "Valores faltantes": faltantes,
        "Filas completamente duplicadas": df[df.duplicated(keep=False)],
        "id_venta duplicados": df[df.duplicated(subset="id_venta", keep=False)],
        "Texto inconsistente (ciudad, metodo_pago, canal_venta)": _texto_inconsistente(df),
        "cantidad <= 0": _fuera_de_rango(df, "cantidad", 0, minimo_estricto=True),
        "precio_unitario_cop <= 0": _fuera_de_rango(df, "precio_unitario_cop", 0, minimo_estricto=True),
        "costo_unitario_cop <= 0": _fuera_de_rango(df, "costo_unitario_cop", 0, minimo_estricto=True),
        "descuento_pct fuera de 0 a 100": _fuera_de_rango(df, "descuento_pct", 0, 100),
        "calificacion_servicio fuera de 1 a 5": _fuera_de_rango(df, "calificacion_servicio", 1, 5),
        "dias_entrega < 0": _fuera_de_rango(df, "dias_entrega", 0),
    }


def resumir_problemas(df: pd.DataFrame, problemas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tabla Problema / Casos / Registros involucrados.

    En los duplicados, «casos» son las copias sobrantes (se conserva la primera),
    mientras que «registros involucrados» incluye también la copia original.
    """
    sobrantes = {
        "Filas completamente duplicadas": int(df.duplicated().sum()),
        "id_venta duplicados": int(df.duplicated(subset="id_venta").sum()),
    }
    filas = [
        {
            "Problema": nombre,
            "Casos": sobrantes.get(nombre, len(registros)),
            "Registros involucrados": len(registros),
        }
        for nombre, registros in problemas.items()
    ]
    return pd.DataFrame(filas)


def detectar_outliers(df: pd.DataFrame, columna: str = "total_venta_cop") -> pd.DataFrame:
    """Valores atípicos por rango intercuartílico. Son para revisar, no errores."""
    serie = _numerica(df, columna)
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    return df[(serie < q1 - 1.5 * iqr) | (serie > q3 + 1.5 * iqr)]


REGLAS_DE_NEGOCIO = (
    "id_venta duplicados",
    "cantidad <= 0",
    "precio_unitario_cop <= 0",
    "costo_unitario_cop <= 0",
    "descuento_pct fuera de 0 a 100",
    "calificacion_servicio fuera de 1 a 5",
    "dias_entrega < 0",
)


def validar_dataset(df: pd.DataFrame) -> dict:
    """Pendientes tras una limpieza: faltantes, duplicados y filas que rompen reglas."""
    problemas = detectar_problemas(df)
    filas_en_regla = set()
    for nombre in REGLAS_DE_NEGOCIO:
        filas_en_regla |= set(problemas[nombre].index)
    return {
        "faltantes": int(df.isna().sum().sum()),
        "duplicados": int(df.duplicated().sum()),
        "reglas_invalidas": len(filas_en_regla),
        "texto_inconsistente": len(problemas["Texto inconsistente (ciudad, metodo_pago, canal_venta)"]),
    }
