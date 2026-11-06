"""Esquemas de entrada y validación de la API.

Los límites superiores evitan que una petición mal formada dispare
integraciones numéricas inviables (por ejemplo caudales de 10^9 m3/d).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InfluenteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caudal_m3_d: float = Field(9000.0, gt=0.0, le=2.0e6, description="Caudal medio")
    dbo5_mg_l: float = Field(240.0, ge=0.0, le=20000.0, description="DBO5")
    dqo_mg_l: float = Field(455.0, gt=0.0, le=60000.0, description="DQO total")
    sst_mg_l: float = Field(230.0, ge=0.0, le=30000.0, description="SST")
    ssv_mg_l: float | None = Field(None, ge=0.0, description="SSV (por defecto 0,82·SST)")
    ntk_mg_l: float | None = Field(42.0, ge=0.0, le=5000.0)
    nh4_mg_l: float | None = Field(None, ge=0.0, le=5000.0)
    no3_mg_l: float = Field(0.0, ge=0.0, le=5000.0)
    pt_mg_l: float | None = Field(7.0, ge=0.0, le=1000.0)
    po4_mg_l: float | None = Field(None, ge=0.0, le=1000.0)
    alcalinidad_mg_l: float = Field(250.0, ge=5.0, le=5000.0)
    ph: float = Field(7.2, ge=4.0, le=10.0)
    temperatura_c: float = Field(22.0, ge=-5.0, le=45.0)
    coliformes_ufc_100ml: float = Field(2.5e7, ge=0.0)
    turbiedad_ntu: float = Field(180.0, ge=0.0)

    @model_validator(mode="after")
    def validar_coherencia(self) -> "InfluenteIn":
        if self.dbo5_mg_l >= self.dqo_mg_l:
            raise ValueError(
                "La DBO5 debe ser menor que la DQO. Revise la caracterización."
            )
        if self.ssv_mg_l is not None and self.ssv_mg_l > self.sst_mg_l:
            raise ValueError("Los SSV no pueden superar a los SST.")
        if self.nh4_mg_l is not None and self.ntk_mg_l is not None:
            if self.nh4_mg_l > self.ntk_mg_l:
                raise ValueError("El N-NH4 no puede superar al NTK.")
        return self


class PretratamientoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    abertura_rejillas_mm: float = Field(20.0, ge=3.0, le=100.0)
    velocidad_rejillas_m_s: float = Field(0.75, ge=0.2, le=1.5)
    angulo_rejillas_grados: float = Field(60.0, ge=30.0, le=90.0)
    trh_desarenador_s: float = Field(60.0, ge=10.0, le=600.0)
    velocidad_desarenador_m_s: float = Field(0.30, ge=0.05, le=0.8)


class PrimarioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n_unidades: int = Field(2, ge=1, le=8)
    diametro_m: float = Field(14.0, ge=2.0, le=60.0)
    profundidad_m: float = Field(3.5, ge=1.0, le=8.0)
    v50_m_d: float = Field(45.0, ge=5.0, le=200.0)


class BiologicoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    volumen_anaerobio_m3: float = Field(900.0, ge=10.0, le=100000.0)
    volumen_anoxico_m3: float = Field(1800.0, ge=10.0, le=100000.0)
    volumen_aerobio_m3: float = Field(5400.0, ge=10.0, le=500000.0)
    ras: float = Field(0.8, ge=0.1, le=3.0, description="Relación de recirculación de lodos")
    recirculacion_interna: float = Field(3.0, ge=0.0, le=6.0)
    purga_m3_d: float = Field(180.0, ge=0.1, le=50000.0)
    od_aerobio_mg_l: float = Field(2.0, ge=0.2, le=8.0)
    od_anoxico_mg_l: float = Field(0.15, ge=0.0, le=1.0)
    svi_ml_g: float = Field(140.0, ge=40.0, le=400.0)
    area_secundario_m2: float = Field(905.0, ge=10.0, le=50000.0)
    dias_simulacion: float = Field(180.0, ge=30.0, le=365.0)

    @model_validator(mode="after")
    def validar_purga(self) -> "BiologicoIn":
        if self.purga_m3_d <= 0:
            raise ValueError("La purga debe ser mayor que cero para controlar la SRT.")
        return self


class DesinfeccionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metodo: str = Field("cloro", pattern="^(cloro|uv|ozono|ninguno)$")
    dosis_cloro_mg_l: float = Field(4.0, ge=0.0, le=50.0)
    tiempo_contacto_min: float = Field(30.0, ge=0.0, le=240.0)
    dosis_uv_mj_cm2: float = Field(30.0, ge=0.0, le=500.0)
    dosis_ozono_mg_l: float = Field(0.0, ge=0.0, le=50.0)


class DisenoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pretratamiento: PretratamientoIn = PretratamientoIn()
    primario: PrimarioIn = PrimarioIn()
    biologico: BiologicoIn = BiologicoIn()
    desinfeccion: DesinfeccionIn = DesinfeccionIn()


class LimitesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dbo5_mg_l: float = Field(50.0, gt=0.0)
    dqo_mg_l: float = Field(150.0, gt=0.0)
    sst_mg_l: float = Field(50.0, gt=0.0)
    nt_mg_l: float = Field(15.0, gt=0.0)
    pt_mg_l: float = Field(2.0, gt=0.0)
    ph_min: float = Field(6.0, ge=0.0, le=14.0)
    ph_max: float = Field(9.0, ge=0.0, le=14.0)
    coliformes_ufc_100ml: float = Field(1000.0, gt=0.0)


class SimulacionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    influente: InfluenteIn = InfluenteIn()
    diseno: DisenoIn = DisenoIn()
    limites: LimitesIn = LimitesIn()


class PresetOut(BaseModel):
    id: str
    nombre: str
    descripcion: str
    influente: dict
    diseno: dict
