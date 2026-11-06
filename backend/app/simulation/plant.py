"""Orquestación del tren de tratamiento completo de una PTAR.

Flujo de procesos
-----------------
    afluente → rejillas → desarenador → sedimentador primario
             → reactor A2O (anaerobio → anóxico → aerobio)
             → sedimentador secundario → desinfección → efluente
    lodo primario + purga → espesador → digestor anaerobio → deshidratación

Cada etapa devuelve la corriente de salida, sus indicadores de diseño y la
remoción másica de DBO5, DQO y SST. El resultado está pensado para ser
consumido directamente por la API y por la visualización 3D.
"""

from __future__ import annotations

from dataclasses import asdict
from time import perf_counter

import numpy as np

from . import constants as K
from .biological import BioConfig, simular_biologico
from .quality import (
    comprobar_limites,
    eficiencia,
    fraccionar_influente,
    indice_calidad_agua,
    resumen_calidad,
)
from .sludge import tren_lodos
from .streams import Stream
from .units import desarenador, desinfeccion, rejillas, sedimentador_primario

VERSION_MODELO = "1.0.0"


# ---------------------------------------------------------------------------
# Catálogo de unidades (geometría para el gemelo digital 3D)
# ---------------------------------------------------------------------------
CATALOGO = [
    {
        "id": "afluente",
        "nombre": "Afluente",
        "tipo": "entrada",
        "descripcion": "Llegada del agua residual cruda y punto de muestreo.",
        "forma": "canal",
        "posicion": [-42.0, 0.0, 0.0],
        "dimensiones": [4.0, 0.8, 2.2],
        "color": "#38bdf8",
    },
    {
        "id": "rejillas",
        "nombre": "Rejillas de desbaste",
        "tipo": "pretratamiento",
        "descripcion": "Retención de sólidos gruesos y protección de equipos.",
        "forma": "canal",
        "posicion": [-35.0, 0.0, 0.0],
        "dimensiones": [5.0, 1.2, 2.6],
        "color": "#64748b",
        "parametros_clave": ["abertura_mm", "velocidad_m_s", "perdida_carga_m"],
    },
    {
        "id": "desarenador",
        "nombre": "Desarenador",
        "tipo": "pretratamiento",
        "descripcion": "Separación de arenas y material inorgánico denso.",
        "forma": "canal",
        "posicion": [-27.5, 0.0, 0.0],
        "dimensiones": [7.0, 1.4, 2.6],
        "color": "#94a3b8",
        "parametros_clave": ["trh_s", "volumen_m3"],
    },
    {
        "id": "primario",
        "nombre": "Sedimentador primario",
        "tipo": "primario",
        "descripcion": "Remoción de sólidos suspendidos sedimentables.",
        "forma": "cilindro",
        "posicion": [-16.0, 0.0, 0.0],
        "dimensiones": [14.0, 3.5, 14.0],
        "color": "#7dd3fc",
        "parametros_clave": ["sor_m3_m2_d", "trh_h", "remocion_sst_pct"],
    },
    {
        "id": "anaerobio",
        "nombre": "Zona anaerobia",
        "tipo": "biologico",
        "descripcion": "Liberación de polifosfato y selección biológica.",
        "forma": "tanque",
        "posicion": [-4.0, 0.0, 0.0],
        "dimensiones": [7.0, 3.0, 8.0],
        "color": "#a78bfa",
        "parametros_clave": ["trh_h", "sst", "spo4"],
    },
    {
        "id": "anoxico",
        "nombre": "Zona anóxica",
        "tipo": "biologico",
        "descripcion": "Desnitrificación con recirculación interna.",
        "forma": "tanque",
        "posicion": [4.5, 0.0, 0.0],
        "dimensiones": [8.0, 3.0, 8.0],
        "color": "#818cf8",
        "parametros_clave": ["trh_h", "sst", "sno"],
    },
    {
        "id": "aerobio",
        "nombre": "Zona aerobia",
        "tipo": "biologico",
        "descripcion": "Nitrificación y oxidación de materia orgánica.",
        "forma": "tanque",
        "posicion": [17.0, 0.0, 0.0],
        "dimensiones": [17.0, 3.2, 8.0],
        "color": "#22d3ee",
        "parametros_clave": ["trh_h", "sst", "od", "our_kg_d"],
    },
    {
        "id": "secundario",
        "nombre": "Sedimentador secundario",
        "tipo": "secundario",
        "descripcion": "Separación de lodos activados y clarificación final.",
        "forma": "cilindro",
        "posicion": [31.0, 0.0, 0.0],
        "dimensiones": [24.0, 4.0, 24.0],
        "color": "#38bdf8",
        "parametros_clave": ["sor_m3_m2_d", "punto_estado", "sst_rebose"],
    },
    {
        "id": "desinfeccion",
        "nombre": "Desinfección",
        "tipo": "desinfeccion",
        "descripcion": "Inactivación de microorganismos patógenos.",
        "forma": "canal",
        "posicion": [43.0, 0.0, 0.0],
        "dimensiones": [10.0, 1.2, 3.0],
        "color": "#34d399",
        "parametros_clave": ["metodo", "inactivacion_log", "ct"],
    },
    {
        "id": "efluente",
        "nombre": "Efluente",
        "tipo": "salida",
        "descripcion": "Punto de descarga o reúso del agua tratada.",
        "forma": "canal",
        "posicion": [51.0, 0.0, 0.0],
        "dimensiones": [4.0, 0.8, 2.2],
        "color": "#4ade80",
    },
    {
        "id": "espesador",
        "nombre": "Espesador de lodos",
        "tipo": "lodos",
        "descripcion": "Concentración de lodos primarios y purga biológica.",
        "forma": "cilindro",
        "posicion": [6.0, 0.0, 18.0],
        "dimensiones": [8.0, 3.0, 8.0],
        "color": "#a16207",
    },
    {
        "id": "digestor",
        "nombre": "Digestor anaerobio",
        "tipo": "lodos",
        "descripcion": "Estabilización de lodos y producción de biogás.",
        "forma": "digestor",
        "posicion": [-8.0, 0.0, 18.0],
        "dimensiones": [12.0, 9.0, 12.0],
        "color": "#65a30d",
    },
    {
        "id": "deshidratacion",
        "nombre": "Deshidratación",
        "tipo": "lodos",
        "descripcion": "Deshidratación mecánica y disposición de torta.",
        "forma": "edificio",
        "posicion": [-23.0, 0.0, 18.0],
        "dimensiones": [12.0, 5.0, 9.0],
        "color": "#78716c",
    },
]


def _etapa(
    id_: str,
    nombre: str,
    tipo: str,
    descripcion: str,
    entrada: Stream,
    salida: Stream,
    info: dict,
    parametros: dict | None = None,
) -> dict:
    return {
        "id": id_,
        "nombre": nombre,
        "tipo": tipo,
        "descripcion": descripcion,
        "parametros": parametros or {},
        "info": info,
        "entrada": resumen_calidad(entrada),
        "salida": resumen_calidad(salida),
        "remocion": {
            "dbo5_pct": round(eficiencia(entrada, salida, "dbo5"), 1),
            "dqo_pct": round(eficiencia(entrada, salida, "dqo"), 1),
            "sst_pct": round(eficiencia(entrada, salida, "sst"), 1),
            "nt_pct": round(eficiencia(entrada, salida, "nt"), 1),
            "tp_pct": round(eficiencia(entrada, salida, "tp"), 1),
        },
    }


def _balance_masa(
    afluente: Stream,
    efluente: Stream,
    lodos: dict,
    vs_destruido_kg_d: float,
    residuos_pretratamiento_sst_kg_d: float = 0.0,
    residuos_pretratamiento_dqo_kg_d: float = 0.0,
    dqo_oxidada_kg_d: float = 0.0,
) -> dict:
    """Verificación de cierre de balance para DQO y SST.

    La salida de DQO incluye materia orgánica oxidada en el reactor (calculada
    a partir del oxígeno consumido, descontando la nitrificación) y la DQO
    destruida en el digestor (equivalente en metano). La salida de SST incluye
    los residuos de pretratamiento y los sólidos volatilizados.
    """
    dqo_in = afluente.cod * afluente.q / 1000.0
    dqo_out = efluente.cod * efluente.q / 1000.0
    dqo_lodo = lodos["resumen"]["torta_kg_sst_d"] * 1.42
    dqo_biogas = lodos["resumen"]["cod_destruido_kg_d"]
    dqo_total_out = (
        dqo_out + dqo_lodo + dqo_biogas
        + dqo_oxidada_kg_d + residuos_pretratamiento_dqo_kg_d
    )
    cierre_dqo = 100.0 * dqo_total_out / max(dqo_in, 1e-9)

    sst_in = afluente.tss * afluente.q / 1000.0
    sst_out = efluente.tss * efluente.q / 1000.0
    sst_lodo = lodos["resumen"]["torta_kg_sst_d"]
    sst_total_out = (
        sst_out + sst_lodo + vs_destruido_kg_d
        + residuos_pretratamiento_sst_kg_d
    )
    cierre_sst = 100.0 * sst_total_out / max(sst_in, 1e-9)

    def estado(cierre: float) -> str:
        return "cerrado" if 85.0 <= cierre <= 115.0 else "revisar"

    return {
        "dqo": {
            "entrada_kg_d": round(dqo_in, 1),
            "efluente_kg_d": round(dqo_out, 1),
            "lodo_kg_d": round(dqo_lodo, 1),
            "biogas_kg_d": round(dqo_biogas, 1),
            "oxidada_kg_d": round(dqo_oxidada_kg_d, 1),
            "residuos_pretratamiento_kg_d": round(residuos_pretratamiento_dqo_kg_d, 1),
            "salida_total_kg_d": round(dqo_total_out, 1),
            "cierre_pct": round(cierre_dqo, 1),
            "estado": estado(cierre_dqo),
        },
        "sst": {
            "entrada_kg_d": round(sst_in, 1),
            "efluente_kg_d": round(sst_out, 1),
            "torta_kg_d": round(sst_lodo, 1),
            "destruido_kg_d": round(vs_destruido_kg_d, 1),
            "residuos_pretratamiento_kg_d": round(residuos_pretratamiento_sst_kg_d, 1),
            "salida_total_kg_d": round(sst_total_out, 1),
            "cierre_pct": round(cierre_sst, 1),
            "estado": estado(cierre_sst),
        },
    }


def _json_safe(valor):
    """Convierte escalares de NumPy a tipos nativos de Python."""
    if isinstance(valor, dict):
        return {k: _json_safe(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_json_safe(v) for v in valor]
    if isinstance(valor, np.floating):
        return float(valor)
    if isinstance(valor, np.integer):
        return int(valor)
    if isinstance(valor, np.bool_):
        return bool(valor)
    return valor


def simular_planta(
    entrada: Stream,
    meta_influente: dict | None = None,
    diseno: dict | None = None,
    limites: dict | None = None,
) -> dict:
    """Ejecuta el tren completo y devuelve un resultado serializable.

    ``diseno`` admite las claves de pretratamiento, primario, biológico y
    desinfección. Los valores ausentes se completan con los predeterminados
    de diseño de una planta municipal de 9 000 m3/d.
    """
    inicio = perf_counter()
    diseno = diseno or {}
    pre = diseno.get("pretratamiento", {})
    pri = diseno.get("primario", {})
    bio_opt = diseno.get("biologico", {})
    des = diseno.get("desinfeccion", {})

    # ------------------------------------------------------------------
    # Tren de agua
    # ------------------------------------------------------------------
    e1, i1 = rejillas(
        entrada,
        espaciamiento_mm=float(pre.get("abertura_rejillas_mm", 20.0)),
        velocidad_m_s=float(pre.get("velocidad_rejillas_m_s", 0.75)),
        angulo_grados=float(pre.get("angulo_rejillas_grados", 60.0)),
    )
    e2, i2 = desarenador(
        e1,
        t_h_s=float(pre.get("trh_desarenador_s", 60.0)),
        velocidad_m_s=float(pre.get("velocidad_desarenador_m_s", 0.30)),
    )
    e3, i3 = sedimentador_primario(
        e2,
        n_unidades=int(pri.get("n_unidades", 2)),
        diametro_m=float(pri.get("diametro_m", 14.0)),
        profundidad_m=float(pri.get("profundidad_m", 3.5)),
        v50_m_d=float(pri.get("v50_m_d", 45.0)),
    )

    cfg = BioConfig(
        q_in=e3.q,
        v_ana=float(bio_opt.get("volumen_anaerobio_m3", 900.0)),
        v_anox=float(bio_opt.get("volumen_anoxico_m3", 1800.0)),
        v_aer=float(bio_opt.get("volumen_aerobio_m3", 5400.0)),
        ras_ratio=float(bio_opt.get("ras", 0.8)),
        ir_ratio=float(bio_opt.get("recirculacion_interna", 3.0)),
        q_waste=float(bio_opt.get("purga_m3_d", 180.0)),
        do_aer=float(bio_opt.get("od_aerobio_mg_l", 2.0)),
        do_anox=float(bio_opt.get("od_anoxico_mg_l", 0.15)),
        svi=float(bio_opt.get("svi_ml_g", 140.0)),
        sec_area=float(bio_opt.get("area_secundario_m2", 905.0)),
        temp=entrada.temp,
    )
    bio = simular_biologico(e3, cfg, dias=float(bio_opt.get("dias_simulacion", 180.0)))
    efluente_bio: Stream = bio["efluente"]

    e5, i5 = desinfeccion(
        efluente_bio,
        metodo=str(des.get("metodo", "cloro")),
        dosis_mg_l=float(des.get("dosis_cloro_mg_l", 4.0)),
        tiempo_contacto_min=float(des.get("tiempo_contacto_min", 30.0)),
        dosis_uv_mj_cm2=float(des.get("dosis_uv_mj_cm2", 30.0)),
        ozono_mg_l=float(des.get("dosis_ozono_mg_l", 0.0)),
    )

    etapas = [
        _etapa(
            "rejillas", "Rejillas de desbaste", "pretratamiento",
            "Retención de sólidos gruesos mediante barras inclinadas.",
            entrada, e1, i1,
            {"abertura_mm": pre.get("abertura_rejillas_mm", 20.0),
             "velocidad_m_s": pre.get("velocidad_rejillas_m_s", 0.75)},
        ),
        _etapa(
            "desarenador", "Desarenador", "pretratamiento",
            "Sedimentación de arenas por flujo horizontal.",
            e1, e2, i2,
            {"trh_s": pre.get("trh_desarenador_s", 60.0)},
        ),
        _etapa(
            "primario", "Sedimentador primario", "primario",
            "Sedimentación primaria asistida por distribución de velocidades.",
            e2, e3, i3,
            {"n_unidades": pri.get("n_unidades", 2),
             "diametro_m": pri.get("diametro_m", 14.0),
             "profundidad_m": pri.get("profundidad_m", 3.5),
             "v50_m_d": pri.get("v50_m_d", 45.0)},
        ),
        _etapa(
            "biologico", "Reactor A2O + sedimentador secundario", "biologico",
            "Eliminación biológica de materia orgánica, nitrógeno y fósforo.",
            e3, efluente_bio,
            {
                "reactores": bio["reactores"],
                "sedimentador": bio["sedimentador"],
                "operacion": bio["operacion"],
            },
            {
                "volumen_anaerobio_m3": cfg.v_ana,
                "volumen_anoxico_m3": cfg.v_anox,
                "volumen_aerobio_m3": cfg.v_aer,
                "ras": cfg.ras_ratio,
                "recirculacion_interna": cfg.ir_ratio,
                "purga_m3_d": cfg.q_waste,
                "svi_ml_g": cfg.svi,
                "od_aerobio_mg_l": cfg.do_aer,
                "od_anoxico_mg_l": cfg.do_anox,
                "dias_simulacion": bio_opt.get("dias_simulacion", 180.0),
            },
        ),
        _etapa(
            "desinfeccion", "Desinfección", "desinfeccion",
            "Inactivación de coliformes y patógenos.",
            efluente_bio, e5, i5,
            {"metodo": des.get("metodo", "cloro"),
             "dosis_cloro_mg_l": des.get("dosis_cloro_mg_l", 4.0),
             "tiempo_contacto_min": des.get("tiempo_contacto_min", 30.0),
             "dosis_uv_mj_cm2": des.get("dosis_uv_mj_cm2", 30.0)},
        ),
    ]

    # ------------------------------------------------------------------
    # Tren de lodos
    # ------------------------------------------------------------------
    carga_in = entrada.cod * entrada.q / 1000.0
    carga_out = e5.cod * e5.q / 1000.0
    carga_removida = max(carga_in - carga_out, 0.0)

    lodos = tren_lodos(
        lodo_primario_m3_d=float(i3.get("lodo_m3_d", 0.0)),
        solidos_primario_kg_d=float(i3.get("solidos_kg_d", 0.0)),
        purga_m3_d=cfg.q_waste,
        sst_purga_mg_l=float(bio["sedimentador"]["sst_purga"]),
        caudal_planta_m3_d=entrada.q,
        carga_dqo_removida_kg_d=carga_removida,
    )
    vs_destruido = float(lodos["etapas"][1]["vs_destruido_kg_d"])

    # ------------------------------------------------------------------
    # Indicadores globales
    # ------------------------------------------------------------------
    claves = {
        "dbo5": "dbo5_mg_l",
        "dqo": "dqo_mg_l",
        "sst": "sst_mg_l",
        "nt": "nt_mg_l",
        "tp": "pt_mg_l",
    }
    calidad_in = resumen_calidad(entrada)
    calidad_out = resumen_calidad(e5)

    def kpi(param: str) -> dict:
        clave = claves[param]
        return {
            "entrada": calidad_in[clave],
            "salida": calidad_out[clave],
            "eficiencia_pct": round(eficiencia(entrada, e5, param), 1),
        }

    dqo = kpi("dqo")
    dbo5 = kpi("dbo5")
    sst = kpi("sst")
    nt = kpi("nt")
    tp = kpi("tp")

    carga_in = entrada.cod * entrada.q / 1000.0
    carga_out = e5.cod * e5.q / 1000.0
    carga_removida = max(carga_in - carga_out, 0.0)
    energia_aireacion = float(bio["operacion"]["potencia_sopladores_kw"])
    energia_biogas = float(lodos["resumen"]["energia_kwh_d"])
    produccion_lodo = float(lodos["resumen"]["torta_kg_sst_d"])

    kpis = {
        "caudal_tratado_m3_d": round(entrada.q, 1),
        "caudal_efluente_m3_d": round(e5.q, 1),
        "dbo5": dbo5,
        "dqo": dqo,
        "sst": sst,
        "nt": nt,
        "tp": tp,
        "carga_dqo_removida_kg_d": round(carga_removida, 1),
        "carga_organica_kg_d": round(entrada.bod5 * entrada.q / 1000.0, 1),
        "carga_dqo_kg_d": round(carga_in, 1),
        "produccion_lodo_kg_sst_d": round(produccion_lodo, 1),
        "energia_aireacion_kw": round(energia_aireacion, 1),
        "energia_biogas_kwh_d": round(energia_biogas, 0),
        "energia_especifica_kwh_kg_dqo": round(
            max(energia_aireacion * 24.0 - energia_biogas, 0.0) / max(carga_removida, 1e-6), 3
        ),
        "autosuficiencia_energetica_pct": round(
            100.0 * energia_biogas / max(energia_aireacion * 24.0, 1e-9), 1
        ),
        "mlss_mg_l": bio["operacion"]["mlss_mg_l"],
        "srt_d": bio["operacion"]["srt_d"],
        "fm_kg_cod_kg_ssv_d": bio["operacion"]["fm_kg_cod_kg_ssv_d"],
        "trh_h": bio["operacion"]["trh_h"],
        "our_kg_o2_d": bio["operacion"]["our_kg_o2_d"],
        "aire_m3_d": bio["operacion"]["aire_m3_d"],
        "recuperacion_agua_pct": round(100.0 * e5.q / max(entrada.q, 1e-9), 1),
        "indice_calidad": indice_calidad_agua(e5),
    }

    perfil = [
        {
            "etapa": "Afluente",
            "dbo5": round(entrada.bod5, 1),
            "dqo": round(entrada.cod, 1),
            "sst": round(entrada.tss, 1),
            "nt": round(entrada.tn, 1),
        }
    ]
    for etapa in etapas:
        perfil.append({
            "etapa": etapa["nombre"],
            "dbo5": etapa["salida"]["dbo5_mg_l"],
            "dqo": etapa["salida"]["dqo_mg_l"],
            "sst": etapa["salida"]["sst_mg_l"],
            "nt": etapa["salida"]["nt_mg_l"],
        })

    limites_eval = comprobar_limites(e5, limites)
    duracion = (perf_counter() - inicio) * 1000.0

    residuos_sst = entrada.q * (entrada.tss - e2.tss) / 1000.0
    residuos_dqo = entrada.q * (entrada.cod - e2.cod) / 1000.0
    dqo_oxidada = max(
        float(bio["operacion"]["our_kg_o2_d"])
        - K.O2_POR_NH4 * float(bio["operacion"]["nitrificacion_kg_n_d"]),
        0.0,
    )

    return _json_safe({
        "meta": {
            "version_modelo": VERSION_MODELO,
            "duracion_ms": round(duracion, 1),
            "unidades": {
                "caudal": "m3/d",
                "concentracion": "mg/L",
                "carga": "kg/d",
                "energia": "kWh/d",
            },
            "referencias": [
                "Henze et al. (1987). Activated Sludge Model No. 1.",
                "Metcalf & Eddy (2014). Wastewater Engineering, 5th ed.",
                "von Sperling (2007). Activated Sludge and Aerobic Biofilm Reactors.",
            ],
        },
        "afluente": resumen_calidad(entrada),
        "caracterizacion": meta_influente or {},
        "etapas": etapas,
        "tren_lodos": lodos,
        "efluente": resumen_calidad(e5),
        "kpis": kpis,
        "limites": limites_eval,
        "balance": _balance_masa(
            entrada, e5, lodos, vs_destruido,
            residuos_pretratamiento_sst_kg_d=residuos_sst,
            residuos_pretratamiento_dqo_kg_d=residuos_dqo,
            dqo_oxidada_kg_d=dqo_oxidada,
        ),
        "perfil": perfil,
        "reactores": bio["reactores"],
        "sedimentador_secundario": bio["sedimentador"],
        "operacion_biologica": bio["operacion"],
    })


def simular_desde_parametros(payload: dict) -> dict:
    """Punto de entrada de la API: valida, fracciona y simula."""
    inf = payload["influente"]
    entrada, meta = fraccionar_influente(
        caudal_m3_d=inf["caudal_m3_d"],
        dbo5_mg_l=inf["dbo5_mg_l"],
        dqo_mg_l=inf["dqo_mg_l"],
        sst_mg_l=inf["sst_mg_l"],
        ssv_mg_l=inf.get("ssv_mg_l"),
        ntk_mg_l=inf.get("ntk_mg_l"),
        nh4_mg_l=inf.get("nh4_mg_l"),
        no3_mg_l=inf.get("no3_mg_l", 0.0),
        pt_mg_l=inf.get("pt_mg_l"),
        po4_mg_l=inf.get("po4_mg_l"),
        alcalinidad_mg_l=inf.get("alcalinidad_mg_l", 250.0),
        ph=inf.get("ph", 7.2),
        temperatura_c=inf.get("temperatura_c", 20.0),
        coliformes_ufc_100ml=inf.get("coliformes_ufc_100ml", 1.0e7),
        turbiedad_ntu=inf.get("turbiedad_ntu", 150.0),
    )
    return simular_planta(
        entrada,
        meta_influente=meta,
        diseno=payload.get("diseno"),
        limites=payload.get("limites"),
    )


def preset(nombre: str) -> dict:
    """Configuraciones de arranque para la interfaz."""
    base_diseno = {
        "pretratamiento": {
            "abertura_rejillas_mm": 20.0,
            "velocidad_rejillas_m_s": 0.75,
            "trh_desarenador_s": 60.0,
        },
        "primario": {
            "n_unidades": 2,
            "diametro_m": 14.0,
            "profundidad_m": 3.5,
            "v50_m_d": 45.0,
        },
        "biologico": {
            "volumen_anaerobio_m3": 900.0,
            "volumen_anoxico_m3": 1800.0,
            "volumen_aerobio_m3": 5400.0,
            "ras": 0.8,
            "recirculacion_interna": 3.0,
            "purga_m3_d": 180.0,
            "od_aerobio_mg_l": 2.0,
            "od_anoxico_mg_l": 0.15,
            "svi_ml_g": 140.0,
            "area_secundario_m2": 905.0,
            "dias_simulacion": 180.0,
        },
        "desinfeccion": {
            "metodo": "cloro",
            "dosis_cloro_mg_l": 4.0,
            "tiempo_contacto_min": 30.0,
            "dosis_uv_mj_cm2": 30.0,
            "dosis_ozono_mg_l": 0.0,
        },
    }

    presets = {
        "municipal": {
            "id": "municipal",
            "nombre": "Municipal estándar · 9 000 m³/d",
            "descripcion": "Agua residual doméstica típica de una ciudad intermedia.",
            "influente": {
                "caudal_m3_d": 9000.0,
                "dbo5_mg_l": 240.0,
                "dqo_mg_l": 455.0,
                "sst_mg_l": 230.0,
                "ssv_mg_l": 185.0,
                "ntk_mg_l": 42.0,
                "nh4_mg_l": 32.0,
                "no3_mg_l": 0.0,
                "pt_mg_l": 7.0,
                "po4_mg_l": 5.0,
                "alcalinidad_mg_l": 260.0,
                "ph": 7.2,
                "temperatura_c": 22.0,
                "coliformes_ufc_100ml": 2.5e7,
                "turbiedad_ntu": 180.0,
            },
            "diseno": base_diseno,
        },
        "municipal_lluvia": {
            "id": "municipal_lluvia",
            "nombre": "Municipal · época de lluvias",
            "descripcion": "Caudal alto, concentraciones diluidas y menor tiempo de retención.",
            "influente": {
                "caudal_m3_d": 13500.0,
                "dbo5_mg_l": 160.0,
                "dqo_mg_l": 310.0,
                "sst_mg_l": 155.0,
                "ssv_mg_l": 118.0,
                "ntk_mg_l": 30.0,
                "nh4_mg_l": 22.0,
                "no3_mg_l": 0.5,
                "pt_mg_l": 5.0,
                "po4_mg_l": 3.4,
                "alcalinidad_mg_l": 180.0,
                "ph": 7.0,
                "temperatura_c": 19.0,
                "coliformes_ufc_100ml": 1.2e7,
                "turbiedad_ntu": 130.0,
            },
            "diseno": {
                **base_diseno,
                "biologico": {
                    **base_diseno["biologico"],
                    "purga_m3_d": 220.0,
                    "recirculacion_interna": 2.5,
                },
            },
        },
        "industrial": {
            "id": "industrial",
            "nombre": "Industrial láctea · 3 500 m³/d",
            "descripcion": "Alta carga orgánica biodegradable y relación DQO/DBO5 baja.",
            "influente": {
                "caudal_m3_d": 3500.0,
                "dbo5_mg_l": 950.0,
                "dqo_mg_l": 1500.0,
                "sst_mg_l": 480.0,
                "ssv_mg_l": 400.0,
                "ntk_mg_l": 65.0,
                "nh4_mg_l": 18.0,
                "no3_mg_l": 0.0,
                "pt_mg_l": 14.0,
                "po4_mg_l": 9.0,
                "alcalinidad_mg_l": 420.0,
                "ph": 6.8,
                "temperatura_c": 28.0,
                "coliformes_ufc_100ml": 5.0e5,
                "turbiedad_ntu": 420.0,
            },
            "diseno": {
                **base_diseno,
                "primario": {
                    **base_diseno["primario"],
                    "diametro_m": 10.0,
                },
                "biologico": {
                    **base_diseno["biologico"],
                    "volumen_anaerobio_m3": 500.0,
                    "volumen_anoxico_m3": 900.0,
                    "volumen_aerobio_m3": 3200.0,
                    "purga_m3_d": 110.0,
                    "ras": 1.0,
                    "od_aerobio_mg_l": 2.5,
                    "svi_ml_g": 160.0,
                    "area_secundario_m2": 420.0,
                },
            },
        },
        "pequena": {
            "id": "pequena",
            "nombre": "Pequeña comunidad · 1 200 m³/d",
            "descripcion": "Planta compacta con caudal bajo y carga moderada.",
            "influente": {
                "caudal_m3_d": 1200.0,
                "dbo5_mg_l": 260.0,
                "dqo_mg_l": 480.0,
                "sst_mg_l": 260.0,
                "ssv_mg_l": 205.0,
                "ntk_mg_l": 45.0,
                "nh4_mg_l": 34.0,
                "no3_mg_l": 0.0,
                "pt_mg_l": 8.0,
                "po4_mg_l": 5.5,
                "alcalinidad_mg_l": 280.0,
                "ph": 7.3,
                "temperatura_c": 20.0,
                "coliformes_ufc_100ml": 3.0e7,
                "turbiedad_ntu": 210.0,
            },
            "diseno": {
                **base_diseno,
                "primario": {
                    "n_unidades": 1,
                    "diametro_m": 9.0,
                    "profundidad_m": 3.0,
                    "v50_m_d": 40.0,
                },
                "biologico": {
                    "volumen_anaerobio_m3": 180.0,
                    "volumen_anoxico_m3": 320.0,
                    "volumen_aerobio_m3": 1100.0,
                    "ras": 0.9,
                    "recirculacion_interna": 2.5,
                    "purga_m3_d": 35.0,
                    "od_aerobio_mg_l": 2.2,
                    "od_anoxico_mg_l": 0.15,
                    "svi_ml_g": 150.0,
                    "area_secundario_m2": 180.0,
                    "dias_simulacion": 180.0,
                },
            },
        },
    }
    return presets[nombre]


def lista_presets() -> list[dict]:
    return [
        {
            "id": p["id"],
            "nombre": p["nombre"],
            "descripcion": p["descripcion"],
            "caudal_m3_d": p["influente"]["caudal_m3_d"],
            "carga_dbo5_kg_d": round(
                p["influente"]["dbo5_mg_l"] * p["influente"]["caudal_m3_d"] / 1000.0, 0
            ),
        }
        for p in (preset(k) for k in ("municipal", "municipal_lluvia", "industrial", "pequena"))
    ]


# Alias de compatibilidad
def simular(payload: dict) -> dict:
    return simular_desde_parametros(payload)


def corriente_a_dict(s: Stream) -> dict:
    return asdict(s)
