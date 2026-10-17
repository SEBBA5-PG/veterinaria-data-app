"""Utilidades compartidas de texto: detección y normalización de variantes."""

import unicodedata

import pandas as pd


def clave_texto(valor):
    """Clave de comparación: sin tildes, en minúsculas y con espacios recortados."""
    if pd.isna(valor):
        return None
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", str(valor)) if not unicodedata.combining(c)
    )
    return " ".join(sin_tildes.lower().split())


def _recortar(valor):
    return None if pd.isna(valor) else " ".join(str(valor).split())


def mapa_canonico(serie: pd.Series) -> dict:
    """Para cada clave, la forma más frecuente de escribirla (con espacios recortados)."""
    no_nulos = serie.dropna()
    tabla = pd.DataFrame(
        {"clave": no_nulos.map(clave_texto), "valor": no_nulos.map(_recortar)}
    )
    conteo = tabla.groupby(["clave", "valor"]).size().reset_index(name="n")
    conteo["mayus"] = conteo["valor"].str.isupper()
    conteo = conteo.sort_values(
        ["clave", "n", "mayus", "valor"], ascending=[True, False, True, True]
    ).drop_duplicates("clave")
    return dict(zip(conteo["clave"], conteo["valor"]))


def normalizar_serie(serie: pd.Series) -> pd.Series:
    """Unifica las variantes de un mismo valor; los nulos se conservan."""
    canonico = mapa_canonico(serie)
    resultado = serie.map(lambda v: None if pd.isna(v) else canonico[clave_texto(v)])
    return resultado.astype(serie.dtype)


def mascara_inconsistente(serie: pd.Series) -> pd.Series:
    """True donde el valor se escribe distinto de su forma canónica."""
    normal = normalizar_serie(serie)
    return serie.notna() & (serie != normal)
