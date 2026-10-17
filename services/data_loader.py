"""Carga de archivos CSV. No limpia ni valida: solo lee."""

import pandas as pd

CODIFICACIONES = ("utf-8-sig", "utf-8", "latin-1")


class ErrorDeCarga(Exception):
    """Error de lectura con un mensaje pensado para mostrarse al usuario."""


def cargar_csv(origen) -> pd.DataFrame:
    """Lee un CSV desde una ruta o desde un archivo cargado en Streamlit.

    Devuelve un DataFrame. Si no se puede leer, lanza ErrorDeCarga.
    """
    ultimo_error = None
    for codificacion in CODIFICACIONES:
        try:
            if hasattr(origen, "seek"):
                origen.seek(0)
            df = pd.read_csv(origen, encoding=codificacion)
        except UnicodeDecodeError as error:
            ultimo_error = error
            continue
        except pd.errors.EmptyDataError:
            raise ErrorDeCarga("El archivo está vacío.")
        except pd.errors.ParserError as error:
            raise ErrorDeCarga(f"El archivo no tiene formato CSV válido: {error}")
        except FileNotFoundError:
            raise ErrorDeCarga(f"No se encontró el archivo: {origen}")

        if df.empty:
            raise ErrorDeCarga("El archivo no contiene filas de datos.")
        return df

    raise ErrorDeCarga(
        f"No se pudo decodificar el archivo con {', '.join(CODIFICACIONES)}: {ultimo_error}"
    )


def exportar_csv(df: pd.DataFrame) -> bytes:
    """Serializa el estado actual a CSV sin índice, con BOM para que Excel lea las tildes."""
    return df.to_csv(index=False).encode("utf-8-sig")
