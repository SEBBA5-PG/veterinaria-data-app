from pathlib import Path

import streamlit as st

from services import chart_service as graficos
from services import cleaning_service as limpieza
from services.data_loader import ErrorDeCarga, cargar_csv, exportar_csv
from services.quality_service import (
    detectar_outliers,
    detectar_problemas,
    perfilar_dataset,
    resumir_problemas,
    validar_dataset,
)

RUTA_EJEMPLO = Path(__file__).parent / "data" / "datos_veterinaria.csv"
COLUMNAS_RELACIONADAS = {"ciudad": "departamento", "categoria_producto": "producto"}
PROBLEMAS_REVISABLES = (
    "id_venta duplicados",
    "cantidad <= 0",
    "precio_unitario_cop <= 0",
    "costo_unitario_cop <= 0",
    "descuento_pct fuera de 0 a 100",
    "calificacion_servicio fuera de 1 a 5",
    "dias_entrega < 0",
)
OUTLIERS = "Posibles outliers de total_venta_cop (a revisar, no son error)"

st.set_page_config(page_title="Veterinaria Data Quality", page_icon="🩺", layout="wide")


# ---------------------------------------------------------------- estado
def iniciar_estado(df, firma):
    if st.session_state.get("firma") != firma:
        st.session_state.firma = firma
        st.session_state.df_original = df
        st.session_state.df_actual = df.copy()
        st.session_state.historial = []
        st.session_state.pila = []
        st.session_state.aviso = None


def aplicar(df_nuevo, mensaje):
    """Registra un cambio ya confirmado: guarda el estado previo, el historial y refresca."""
    st.session_state.pila.append(st.session_state.df_actual)
    st.session_state.df_actual = df_nuevo
    st.session_state.historial.append(mensaje)
    st.session_state.aviso = mensaje
    st.rerun()


def deshacer():
    st.session_state.df_actual = st.session_state.pila.pop()
    st.session_state.aviso = f"Deshecho: {st.session_state.historial.pop()}"


def restablecer():
    st.session_state.df_actual = st.session_state.df_original.copy()
    st.session_state.historial = []
    st.session_state.pila = []
    st.session_state.aviso = "Dataset restablecido al original."


def confirmar(texto, clave):
    return st.checkbox(texto, key=f"conf_{clave}_{len(st.session_state.historial)}")


# ---------------------------------------------------------------- vistas
def vista_diagnostico(df):
    perfil = perfilar_dataset(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filas", perfil["filas"])
    col2.metric("Columnas", perfil["columnas"])
    col3.metric("Valores faltantes", perfil["total_faltantes"])
    col4.metric("Duplicados completos", perfil["filas_duplicadas"])

    with st.expander("Tipos de datos y faltantes por columna"):
        st.dataframe(
            {"tipo": perfil["tipos"], "faltantes": perfil["faltantes_por_columna"]},
            width="stretch",
        )
    with st.expander("Estadísticas descriptivas"):
        st.dataframe(perfil["estadisticas"], width="stretch")

    problemas = detectar_problemas(df)
    st.subheader("Problemas detectados")
    st.caption(
        "Diagnóstico → evidencia → decisión. En los duplicados, «Casos» cuenta las "
        "copias sobrantes y el detalle muestra todas las filas involucradas."
    )
    st.dataframe(resumir_problemas(df, problemas), hide_index=True, width="stretch")

    for nombre, registros in problemas.items():
        with st.expander(f"{nombre} — {len(registros)} registros"):
            if registros.empty:
                st.success("La regla se evaluó y no hay registros afectados.")
            else:
                st.dataframe(registros, width="stretch")

    outliers = detectar_outliers(df)
    with st.expander(f"{OUTLIERS} — {len(outliers)} registros"):
        st.caption("Atípico no significa incorrecto: pueden ser ventas válidas grandes.")
        st.dataframe(outliers, width="stretch")


def paso_texto(df):
    with st.container(border=True):
        st.subheader("1. Normalizar texto")
        afectadas = validar_dataset(df)["texto_inconsistente"]
        st.write(
            f"**{afectadas}** filas con variantes en `ciudad`, `metodo_pago` o `canal_venta` "
            "(mayúsculas, tildes o espacios). Se unifican a la forma más frecuente."
        )
        if afectadas == 0:
            st.success("Nada que normalizar.")
            return
        if confirmar("Confirmo que quiero normalizar estas columnas", "texto") and st.button(
            "Normalizar texto"
        ):
            aplicar(
                limpieza.normalizar_columnas_texto(df),
                f"Normalizado el texto de ciudad, metodo_pago y canal_venta ({afectadas} filas)",
            )


def paso_duplicados(df):
    with st.container(border=True):
        st.subheader("2. Duplicados completos")
        sobrantes = int(df.duplicated().sum())
        st.write(
            f"**{sobrantes}** filas son copia exacta de otra. Se conserva la primera. "
            "Conviene normalizar el texto antes: así se detectan también las copias que solo "
            "diferían en mayúsculas o espacios."
        )
        if sobrantes == 0:
            st.success("No hay duplicados completos.")
            return
        if confirmar("Confirmo que quiero eliminar las copias sobrantes", "dup") and st.button(
            "Eliminar duplicados"
        ):
            aplicar(
                limpieza.eliminar_duplicados_completos(df),
                f"Eliminados {sobrantes} duplicados completos",
            )


def paso_faltantes(df):
    with st.container(border=True):
        st.subheader("3. Valores faltantes")
        con_faltantes = [c for c in df.columns if df[c].isna().any()]
        if not con_faltantes:
            st.success("No hay valores faltantes.")
            return
        columna = st.selectbox(
            "Columna",
            con_faltantes,
            format_func=lambda c: f"{c} ({int(df[c].isna().sum())} faltantes)",
        )
        opciones = {**limpieza.ESTRATEGIAS, "eliminar": "Eliminar las filas con el faltante"}
        estrategia = st.selectbox("Estrategia", list(opciones), format_func=opciones.get)

        relacionada = valor = None
        if estrategia == "moda_relacionada":
            candidatas = [c for c in df.columns if c != columna]
            sugerida = COLUMNAS_RELACIONADAS.get(columna)
            relacionada = st.selectbox(
                "Columna relacionada",
                candidatas,
                index=candidatas.index(sugerida) if sugerida in candidatas else 0,
            )
        elif estrategia == "texto_fijo":
            valor = st.text_input("Texto", value="No informado")

        n = int(df[columna].isna().sum())
        if estrategia == "eliminar":
            st.warning(f"Se eliminarán {n} filas completas.")
        if confirmar(f"Confirmo aplicar esta estrategia a `{columna}`", "falt") and st.button(
            "Aplicar a faltantes"
        ):
            try:
                if estrategia == "eliminar":
                    nuevo = limpieza.eliminar_registros(df, df.index[df[columna].isna()])
                    mensaje = f"Eliminadas {n} filas con `{columna}` faltante"
                else:
                    nuevo = limpieza.completar_faltantes(df, columna, estrategia, relacionada, valor)
                    mensaje = (
                        f"Completados {n - int(nuevo[columna].isna().sum())} faltantes de "
                        f"`{columna}` ({opciones[estrategia].lower()})"
                    )
            except ValueError as error:
                st.error(str(error))
            else:
                aplicar(nuevo, mensaje)


def paso_revision(df):
    with st.container(border=True):
        st.subheader("4. Revisar registros que rompen reglas")
        problemas = detectar_problemas(df)
        opciones = {n: problemas[n] for n in PROBLEMAS_REVISABLES if not problemas[n].empty}
        outliers = detectar_outliers(df)
        if not outliers.empty:
            opciones[OUTLIERS] = outliers
        if not opciones:
            st.success("No hay registros pendientes de revisión.")
            return

        nombre = st.selectbox("Problema", list(opciones), format_func=lambda n: f"{n} ({len(opciones[n])})")
        registros = opciones[nombre]
        st.caption(
            "Corrige el valor en la tabla o marca **Eliminar**. Nada cambia hasta confirmar."
        )
        vista = registros.copy()
        vista.insert(0, "Eliminar", False)
        editado = st.data_editor(
            vista,
            key=f"editor_{nombre}_{len(st.session_state.historial)}",
            width="stretch",
            disabled=[c for c in vista.columns if c == "id_venta"],
        )
        eliminar = editado.index[editado["Eliminar"]]
        corregidos = editado.drop(columns="Eliminar").drop(index=eliminar)
        n_celdas = limpieza.celdas_editadas(registros.drop(index=eliminar), corregidos)
        st.write(f"Pendiente de aplicar: **{n_celdas}** celdas corregidas y **{len(eliminar)}** filas a eliminar.")
        if n_celdas + len(eliminar) and confirmar("Confirmo estos cambios", "rev") and st.button(
            "Aplicar cambios"
        ):
            nuevo = limpieza.actualizar_registros(df, corregidos)
            nuevo = limpieza.eliminar_registros(nuevo, eliminar)
            aplicar(
                nuevo,
                f"Revisión de «{nombre}»: {n_celdas} celdas corregidas, {len(eliminar)} filas eliminadas",
            )


def paso_tipos(df):
    with st.container(border=True):
        st.subheader("5. Tipos de datos")
        st.write(f"`fecha` es de tipo **{df['fecha'].dtype}**. Se convertirá a fecha y las columnas numéricas a número.")
        convertido = limpieza.convertir_tipos(df)
        nulos_nuevos = int(convertido.isna().sum().sum() - df.isna().sum().sum())
        if (convertido.dtypes.astype(str) == df.dtypes.astype(str)).all():
            st.success("Los tipos ya son los adecuados.")
            return
        if nulos_nuevos:
            st.warning(f"{nulos_nuevos} valores no se pueden convertir y quedarían como nulos.")
        if confirmar("Confirmo la conversión de tipos", "tipos") and st.button("Convertir tipos"):
            aplicar(convertido, "Convertidos los tipos de datos (fecha y columnas numéricas)")


def vista_validacion(df):
    st.subheader("Validación")
    pendientes = validar_dataset(df)
    c1, c2, c3 = st.columns(3)
    c1.metric("Faltantes pendientes", pendientes["faltantes"])
    c2.metric("Duplicados pendientes", pendientes["duplicados"])
    c3.metric("Reglas inválidas", pendientes["reglas_invalidas"])
    if not any([pendientes["faltantes"], pendientes["duplicados"], pendientes["reglas_invalidas"], pendientes["texto_inconsistente"]]):
        st.success(
            "Los problemas detectados están resueltos. Eso no garantiza calidad total: "
            "pueden quedar errores semánticos que el sistema no conoce."
        )


def vista_limpieza(df):
    paso_texto(df)
    paso_duplicados(df)
    paso_faltantes(df)
    paso_revision(df)
    paso_tipos(df)
    vista_validacion(df)


def vista_graficos(df):
    pendientes = validar_dataset(df)
    if any(pendientes.values()):
        st.warning(
            "El dataset aún tiene problemas pendientes: los gráficos reflejan esos errores "
            "(variantes de texto separadas, cantidades negativas, duplicados). "
            "Un gráfico puede verse perfecto y estar construido sobre datos incorrectos."
        )
    else:
        st.success("Los problemas detectados están resueltos: los gráficos usan el dataset actual.")

    nombres = list(graficos.GRAFICOS)
    for izquierda, derecha in zip(nombres[0::2], nombres[1::2] + [None]):
        columnas = st.columns(2)
        for columna, nombre in zip(columnas, (izquierda, derecha)):
            if nombre:
                columna.plotly_chart(graficos.GRAFICOS[nombre](df), width="stretch")


def vista_exportar(df):
    st.subheader("Exportar")
    pendientes = validar_dataset(df)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Filas finales", len(df))
    c2.metric("Columnas finales", df.shape[1])
    c3.metric("Faltantes pendientes", pendientes["faltantes"])
    c4.metric("Duplicados pendientes", pendientes["duplicados"])
    c5.metric("Reglas pendientes", pendientes["reglas_invalidas"])

    if any(pendientes.values()):
        st.warning(
            "Aún hay problemas detectados sin resolver. Puedes descargar el estado actual, "
            "pero el archivo los conserva."
        )
    else:
        st.success("Los problemas detectados están resueltos en este dataset.")

    st.download_button(
        "Descargar dataset limpio",
        data=exportar_csv(df),
        file_name="dataset_veterinaria_limpio.csv",
        mime="text/csv",
    )
    st.caption(
        "Se exporta el estado actual, después de las transformaciones del historial, no el archivo original."
    )


def barra_lateral():
    st.sidebar.header("Historial de transformaciones")
    st.sidebar.write(f"0. Dataset cargado ({len(st.session_state.df_original)} filas)")
    for i, paso in enumerate(st.session_state.historial, 1):
        st.sidebar.write(f"{i}. {paso}")
    izq, der = st.sidebar.columns(2)
    izq.button("Deshacer", on_click=deshacer, disabled=not st.session_state.pila)
    der.button("Restablecer", on_click=restablecer, disabled=not st.session_state.pila)


# ---------------------------------------------------------------- flujo principal
st.title("🩺 Veterinaria Data Quality")
st.caption("¿Podemos confiar en los datos antes de analizarlos?")

archivo = st.file_uploader("Carga el CSV de ventas", type=["csv"])
usar_ejemplo = st.checkbox(
    "Usar el dataset de práctica incluido (500 filas)",
    disabled=archivo is not None or not RUTA_EJEMPLO.exists(),
)
origen = archivo if archivo is not None else (RUTA_EJEMPLO if usar_ejemplo else None)

if origen is None:
    st.info("Sube un CSV o marca la casilla para usar el dataset de práctica.")
else:
    try:
        df_cargado = cargar_csv(origen)
    except ErrorDeCarga as error:
        st.error(str(error))
    else:
        firma = (archivo.name, archivo.size) if archivo is not None else "ejemplo"
        iniciar_estado(df_cargado, firma)
        df = st.session_state.df_actual

        st.success(f"Dataset actual: {len(df)} filas × {df.shape[1]} columnas")
        if st.session_state.aviso:
            st.toast(st.session_state.aviso)
            st.session_state.aviso = None
        barra_lateral()

        with st.expander("Primeras 10 filas"):
            st.dataframe(df.head(10), width="stretch")

        tab_calidad, tab_limpieza, tab_graficos, tab_exportar = st.tabs(
            ["Calidad de datos", "Limpieza", "Gráficos", "Exportar"]
        )
        with tab_calidad:
            vista_diagnostico(df)
        with tab_limpieza:
            vista_limpieza(df)
        with tab_graficos:
            vista_graficos(df)
        with tab_exportar:
            vista_exportar(df)
