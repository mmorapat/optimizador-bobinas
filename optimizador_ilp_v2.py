"""
🔬 OPTIMIZADOR ILP V4 - CORREGIDO
Con restricción de material disponible por desarrollo
Con restricción de ML_MINIMOS por pedido
VERSIÓN: 2025-10-26 18:00 - desperdicio_bordes_maximo actualizado
"""

import pandas as pd
from pulp import *
from typing import List, Dict, Tuple, Optional
import time


class OptimizadorILP:
    """
    Optimizador usando Integer Linear Programming.
    
    VERSIÓN CORREGIDA: Incluye restricción de kg_disponibles por desarrollo
    """
    
    def __init__(self,
                 desperdicio_bordes_minimo: int = 0,
                 desperdicio_bordes_maximo: int = 30,
                 kg_max_bobina: int = 4000,
                 kg_min_bobina: int = 200,
                 max_cortes_por_pedido: int = 15,
                 margen_cobertura: float = 0.95,
                 margen_exceso: float = 1.10,
                 margen_tolerancia_ml_pct: float = 10.0,
                 ml_minimo_resto: int = 300,
                 tiempo_max_segundos: int = 300,
                 max_pedidos_por_configuracion: int = 6,
                 factor_penalizacion_desperdicio: float = 0.0,
                 debug: bool = True):
        
        self.desperdicio_bordes_minimo = desperdicio_bordes_minimo
        self.desperdicio_bordes_maximo = desperdicio_bordes_maximo
        self.kg_max_bobina = kg_max_bobina
        self.kg_min_bobina = kg_min_bobina
        self.max_cortes_por_pedido = max_cortes_por_pedido
        self.margen_cobertura = margen_cobertura
        self.margen_exceso = margen_exceso
        self.margen_tolerancia_ml_pct = margen_tolerancia_ml_pct
        self.ml_minimo_resto = ml_minimo_resto
        self.tiempo_max_segundos = tiempo_max_segundos
        self.max_pedidos_por_configuracion = max_pedidos_por_configuracion
        self.factor_penalizacion_desperdicio = factor_penalizacion_desperdicio
        self.debug = debug
        
        self.desarrollos = []
        self.pedidos = []
        self.problema = None
        self.solucion = None
    
    def optimizar(self, df_desarrollos: pd.DataFrame, df_pedidos: pd.DataFrame) -> List[Dict]:
        """Ejecuta optimización ILP completa"""
        
        if self.debug:
            print(f"\n{'='*80}")
            print(f"🔬 OPTIMIZADOR ILP V3 - CON RESTRICCIÓN DE MATERIAL")
            print(f"{'='*80}\n")
        
        # Cargar datos
        self._cargar_datos(df_desarrollos, df_pedidos)
        
        # Generar bobinas candidatas
        if self.debug:
            print(f"{'='*80}")
            print(f"📦 FASE 1: GENERAR BOBINAS CANDIDATAS")
            print(f"{'='*80}\n")
        
        bobinas_candidatas = self._generar_bobinas_candidatas()
        
        if self.debug:
            print(f"✅ Bobinas candidatas generadas: {len(bobinas_candidatas)}")
            print()
        
        # Crear modelo ILP
        if self.debug:
            print(f"{'='*80}")
            print(f"🔨 FASE 2: CREAR MODELO MATEMÁTICO")
            print(f"{'='*80}\n")
        
        self._crear_modelo_ilp(bobinas_candidatas)
        
        # Resolver
        if self.debug:
            print(f"{'='*80}")
            print(f"⚡ FASE 3: RESOLVER OPTIMIZACIÓN")
            print(f"{'='*80}\n")
            print(f"🔍 Resolviendo... (esto puede tardar unos segundos)")
            print()
        
        inicio = time.time()
        estado = self.problema.solve(PULP_CBC_CMD(timeLimit=self.tiempo_max_segundos, msg=0))
        tiempo_resolucion = time.time() - inicio
        
        if self.debug:
            print(f"⏱️  Tiempo de resolución: {tiempo_resolucion:.2f}s")
            print(f"📊 Estado: {LpStatus[estado]}")
            print()
        
        # Extraer solución
        if estado == LpStatusOptimal:
            if self.debug:
                print(f"✅ ¡SOLUCIÓN ÓPTIMA ENCONTRADA!")
                print()
            
            self.solucion = self._extraer_solucion(bobinas_candidatas)
            return self._formatear_resultado(df_pedidos)
        
        else:
            if self.debug:
                print(f"❌ No se encontró solución óptima")
                print(f"   Estado: {LpStatus[estado]}")
            return []
    
    def _cargar_datos(self, df_desarrollos: pd.DataFrame, df_pedidos: pd.DataFrame):
        """Carga desarrollos y pedidos"""
        self.desarrollos = []
        for idx, row in df_desarrollos.iterrows():
            self.desarrollos.append({
                'id': f"des_{idx}",
                'ancho': float(row['ANCHO']),
                'espesor': float(row['ESPESOR']),
                'aleacion': str(row['ALEACION']),
                'estado': str(row['ESTADO']),
                'kg_disponibles': float(row['KG'])
            })
        
        self.pedidos = []
        for _, row in df_pedidos.iterrows():
            self.pedidos.append({
                'id': str(row['PEDIDO']),
                'ancho': float(row['ANCHO']),
                'kg_solicitados': float(row['KG']),
                'aleacion': str(row['ALEACION']),
                'estado': str(row['ESTADO']),
                'espesor': float(row['ESPESOR']),
                'ml_minimos': float(row['ML_MINIMOS']) if 'ML_MINIMOS' in row and pd.notna(row['ML_MINIMOS']) else 0
            })
        
        if self.debug:
            print(f"📋 Datos cargados:")
            print(f"   - Desarrollos:")
            for des in self.desarrollos:
                print(f"      • {des['ancho']}×{des['espesor']} ({des['aleacion']}-{des['estado']}): {des['kg_disponibles']}kg")
            print(f"   - Pedidos: {len(self.pedidos)}")
            print()
    
    def _generar_bobinas_candidatas(self) -> List[Dict]:
        """Genera todas las bobinas candidatas posibles"""
        candidatas = []
        id_bobina = 0
        
        for desarrollo in self.desarrollos:
            # Pedidos compatibles con este desarrollo
            pedidos_compatibles = [
                p for p in self.pedidos
                if (p['espesor'] == desarrollo['espesor'] and
                    p['aleacion'] == desarrollo['aleacion'] and
                    p['estado'] == desarrollo['estado'] and
                    p['ancho'] <= desarrollo['ancho'])
            ]
            
            if not pedidos_compatibles:
                continue
            
            # Generar configuraciones de corte
            configuraciones = self._generar_configuraciones_corte(
                desarrollo, pedidos_compatibles
            )
            
            for config in configuraciones:
                id_bobina += 1
                candidatas.append({
                    'id': f"bob_{id_bobina}",
                    'desarrollo': desarrollo,
                    'configuracion': config,
                    'ancho_usado': config['ancho_usado'],
                    'desperdicio': desarrollo['ancho'] - config['ancho_usado']
                })
        
        if self.debug:
            print(f"   Generando configuraciones por desarrollo:")
            desarrollos_count = {}
            for cand in candidatas:
                dev_key = f"{cand['desarrollo']['ancho']}×{cand['desarrollo']['espesor']}"
                desarrollos_count[dev_key] = desarrollos_count.get(dev_key, 0) + 1
            
            for dev_key, count in desarrollos_count.items():
                print(f"   - {dev_key}: {count} configuraciones")
        
        return candidatas
    
    def _generar_configuraciones_corte(self, desarrollo: Dict, 
                                      pedidos: List[Dict]) -> List[Dict]:
        """Genera todas las configuraciones de corte viables"""
        configuraciones = []
        
        # Configuraciones con 1 pedido
        for pedido in pedidos:
            max_cortes = int(desarrollo['ancho'] // pedido['ancho'])
            
            for num_cortes in range(1, min(max_cortes + 1, self.max_cortes_por_pedido + 1)):
                ancho_usado = num_cortes * pedido['ancho']
                desperdicio = desarrollo['ancho'] - ancho_usado
                
                if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                    configuraciones.append({
                        'cortes': {pedido['id']: num_cortes},
                        'ancho_usado': ancho_usado
                    })
        
        # Configuraciones con 2 pedidos
        for i, pedido1 in enumerate(pedidos):
            for pedido2 in pedidos[i+1:]:
                for n1 in range(1, self.max_cortes_por_pedido + 1):
                    for n2 in range(1, self.max_cortes_por_pedido + 1):
                        ancho_usado = n1 * pedido1['ancho'] + n2 * pedido2['ancho']
                        
                        if ancho_usado <= desarrollo['ancho']:
                            desperdicio = desarrollo['ancho'] - ancho_usado
                            
                            if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                configuraciones.append({
                                    'cortes': {
                                        pedido1['id']: n1,
                                        pedido2['id']: n2
                                    },
                                    'ancho_usado': ancho_usado
                                })
        
        # Configuraciones con 3 pedidos
        for i, pedido1 in enumerate(pedidos):
            for j, pedido2 in enumerate(pedidos[i+1:], i+1):
                for pedido3 in pedidos[j+1:]:
                    for n1 in range(1, min(8, self.max_cortes_por_pedido + 1)):
                        for n2 in range(1, min(6, self.max_cortes_por_pedido + 1)):
                            for n3 in range(1, min(6, self.max_cortes_por_pedido + 1)):
                                ancho_usado = (n1 * pedido1['ancho'] + 
                                             n2 * pedido2['ancho'] + 
                                             n3 * pedido3['ancho'])
                                
                                if ancho_usado <= desarrollo['ancho']:
                                    desperdicio = desarrollo['ancho'] - ancho_usado
                                    
                                    if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                        configuraciones.append({
                                            'cortes': {
                                                pedido1['id']: n1,
                                                pedido2['id']: n2,
                                                pedido3['id']: n3
                                            },
                                            'ancho_usado': ancho_usado
                                        })
        
        # Configuraciones con 4 pedidos (límite adaptativo: max 4 cortes por pedido)
        if self.max_pedidos_por_configuracion >= 4:
            for i, pedido1 in enumerate(pedidos):
                for j, pedido2 in enumerate(pedidos[i+1:], i+1):
                    for k, pedido3 in enumerate(pedidos[j+1:], j+1):
                        for pedido4 in pedidos[k+1:]:
                            for n1 in range(1, min(5, self.max_cortes_por_pedido + 1)):
                                for n2 in range(1, min(4, self.max_cortes_por_pedido + 1)):
                                    for n3 in range(1, min(4, self.max_cortes_por_pedido + 1)):
                                        for n4 in range(1, min(4, self.max_cortes_por_pedido + 1)):
                                            ancho_usado = (n1 * pedido1['ancho'] + 
                                                         n2 * pedido2['ancho'] + 
                                                         n3 * pedido3['ancho'] +
                                                         n4 * pedido4['ancho'])
                                            
                                            if ancho_usado <= desarrollo['ancho']:
                                                desperdicio = desarrollo['ancho'] - ancho_usado
                                                
                                                if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                                    configuraciones.append({
                                                        'cortes': {
                                                            pedido1['id']: n1,
                                                            pedido2['id']: n2,
                                                            pedido3['id']: n3,
                                                            pedido4['id']: n4
                                                        },
                                                        'ancho_usado': ancho_usado
                                                    })
        
        # Configuraciones con 5 pedidos (límite adaptativo: max 3 cortes por pedido)
        if self.max_pedidos_por_configuracion >= 5:
            for i, pedido1 in enumerate(pedidos):
                for j, pedido2 in enumerate(pedidos[i+1:], i+1):
                    for k, pedido3 in enumerate(pedidos[j+1:], j+1):
                        for l, pedido4 in enumerate(pedidos[k+1:], k+1):
                            for pedido5 in pedidos[l+1:]:
                                for n1 in range(1, min(4, self.max_cortes_por_pedido + 1)):
                                    for n2 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                        for n3 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                            for n4 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                                for n5 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                                    ancho_usado = (n1 * pedido1['ancho'] + 
                                                                 n2 * pedido2['ancho'] + 
                                                                 n3 * pedido3['ancho'] +
                                                                 n4 * pedido4['ancho'] +
                                                                 n5 * pedido5['ancho'])
                                                    
                                                    if ancho_usado <= desarrollo['ancho']:
                                                        desperdicio = desarrollo['ancho'] - ancho_usado
                                                        
                                                        if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                                            configuraciones.append({
                                                                'cortes': {
                                                                    pedido1['id']: n1,
                                                                    pedido2['id']: n2,
                                                                    pedido3['id']: n3,
                                                                    pedido4['id']: n4,
                                                                    pedido5['id']: n5
                                                                },
                                                                'ancho_usado': ancho_usado
                                                            })
        
        # Configuraciones con 6+ pedidos (límite adaptativo: max 2 cortes por pedido)
        for i, pedido1 in enumerate(pedidos):
            for j, pedido2 in enumerate(pedidos[i+1:], i+1):
                for k, pedido3 in enumerate(pedidos[j+1:], j+1):
                    for l, pedido4 in enumerate(pedidos[k+1:], k+1):
                        for m, pedido5 in enumerate(pedidos[l+1:], l+1):
                            for pedido6 in pedidos[m+1:]:
                                for n1 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                    for n2 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                        for n3 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                            for n4 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                                for n5 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                                    for n6 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                                        ancho_usado = (n1 * pedido1['ancho'] + 
                                                                     n2 * pedido2['ancho'] + 
                                                                     n3 * pedido3['ancho'] +
                                                                     n4 * pedido4['ancho'] +
                                                                     n5 * pedido5['ancho'] +
                                                                     n6 * pedido6['ancho'])
                                                        
                                                        if ancho_usado <= desarrollo['ancho']:
                                                            desperdicio = desarrollo['ancho'] - ancho_usado
                                                            
                                                            if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                                                configuraciones.append({
                                                                    'cortes': {
                                                                        pedido1['id']: n1,
                                                                        pedido2['id']: n2,
                                                                        pedido3['id']: n3,
                                                                        pedido4['id']: n4,
                                                                        pedido5['id']: n5,
                                                                        pedido6['id']: n6
                                                                    },
                                                                    'ancho_usado': ancho_usado
                                                                })
        
        return configuraciones
    
    def _crear_modelo_ilp(self, bobinas_candidatas: List[Dict]):
        """Crea el modelo matemático ILP"""
        # Crear problema
        self.problema = LpProblem("Optimizacion_Bobinas", LpMinimize)
        
        # Variables de decisión
        y = {}
        for cand in bobinas_candidatas:
            y[cand['id']] = LpVariable(f"usar_{cand['id']}", cat='Binary')
        
        ml = {}
        for cand in bobinas_candidatas:
            ml[cand['id']] = LpVariable(
                f"ml_{cand['id']}", 
                lowBound=0, 
                upBound=20000
            )
        
        if self.debug:
            print(f"📊 Variables creadas:")
            print(f"   - Variables binarias (y): {len(y)}")
            print(f"   - Variables continuas (ml): {len(ml)}")
            print()
        
        # FUNCIÓN OBJETIVO: Minimizar bobinas + penalizar desperdicio
        objetivo = lpSum([y[cand['id']] for cand in bobinas_candidatas])
        
        # Añadir penalización por desperdicio de bordes (si está configurado)
        if self.factor_penalizacion_desperdicio > 0:
            for cand in bobinas_candidatas:
                desperdicio = cand['desperdicio']
                objetivo += self.factor_penalizacion_desperdicio * desperdicio * y[cand['id']]
        
        self.problema += objetivo, "Minimizar_Bobinas_y_Desperdicio"
        
        if self.debug:
            print(f"🎯 Objetivo: Minimizar Σ bobinas usadas")
            print()
        
        # RESTRICCIONES
        num_restricciones = 0
        
        if self.debug:
            print(f"📋 Creando restricciones:")
        
        # 1. COBERTURA MÍNIMA DE PEDIDOS
        if self.debug:
            print(f"   1️⃣  Cobertura mínima de pedidos...")
        
        for pedido in self.pedidos:
            kg_asignados = lpSum([
                self._calcular_kg_asignado(cand, pedido, ml[cand['id']])
                for cand in bobinas_candidatas
                if pedido['id'] in cand['configuracion']['cortes']
            ])
            
            kg_minimo = pedido['kg_solicitados'] * self.margen_cobertura
            
            self.problema += (
                kg_asignados >= kg_minimo,
                f"Cobertura_Min_{pedido['id']}"
            )
            num_restricciones += 1
        
        if self.debug:
            print(f"      ✅ {len(self.pedidos)} restricciones de cobertura mínima")
        
        # 1B. EXCESO MÁXIMO DE PEDIDOS
        if self.debug:
            porcentaje_exceso = int((self.margen_exceso - 1) * 100)
            print(f"   1️⃣B Exceso máximo de pedidos (±{porcentaje_exceso}%)...")
        
        for pedido in self.pedidos:
            kg_asignados = lpSum([
                self._calcular_kg_asignado(cand, pedido, ml[cand['id']])
                for cand in bobinas_candidatas
                if pedido['id'] in cand['configuracion']['cortes']
            ])
            
            kg_maximo = pedido['kg_solicitados'] * self.margen_exceso
            
            self.problema += (
                kg_asignados <= kg_maximo,
                f"Exceso_Max_{pedido['id']}"
            )
            num_restricciones += 1
        
        if self.debug:
            print(f"      ✅ {len(self.pedidos)} restricciones de exceso máximo")
        
        # 2. PESO MÁXIMO POR BOBINA
        if self.debug:
            print(f"   2️⃣  Peso máximo por bobina...")
        
        for cand in bobinas_candidatas:
            kg_bobina = self._calcular_kg_bobina(cand, ml[cand['id']])
            
            self.problema += (
                kg_bobina <= self.kg_max_bobina,
                f"Peso_Max_{cand['id']}"
            )
            num_restricciones += 1
        
        if self.debug:
            print(f"      ✅ {len(bobinas_candidatas)} restricciones de peso")
        
        # 3. ACTIVACIÓN DE BOBINAS
        if self.debug:
            print(f"   3️⃣  Lógica de activación...")
        
        for cand in bobinas_candidatas:
            M = 20000
            
            self.problema += (
                ml[cand['id']] <= M * y[cand['id']],
                f"Activacion_{cand['id']}"
            )
            num_restricciones += 1
        
        if self.debug:
            print(f"      ✅ {len(bobinas_candidatas)} restricciones de activación")
        
        # 4. PESO MÍNIMO
        if self.debug:
            print(f"   4️⃣  Peso mínimo por bobina...")
        
        for cand in bobinas_candidatas:
            kg_bobina = self._calcular_kg_bobina(cand, ml[cand['id']])
            
            self.problema += (
                kg_bobina >= self.kg_min_bobina * y[cand['id']],
                f"Peso_Min_{cand['id']}"
            )
            num_restricciones += 1
        
        if self.debug:
            print(f"      ✅ {len(bobinas_candidatas)} restricciones de peso mínimo")
        
        # 🔥 5. NUEVA RESTRICCIÓN: MATERIAL DISPONIBLE POR DESARROLLO
        if self.debug:
            print(f"   5️⃣  🔥 MATERIAL DISPONIBLE POR DESARROLLO...")
        
        for desarrollo in self.desarrollos:
            # Bobinas candidatas que usan este desarrollo
            bobinas_de_este_desarrollo = [
                cand for cand in bobinas_candidatas
                if (cand['desarrollo']['id'] == desarrollo['id'])
            ]
            
            if bobinas_de_este_desarrollo:
                # Suma de kg usados en todas las bobinas de este desarrollo
                kg_usados_total = lpSum([
                    self._calcular_kg_bobina(cand, ml[cand['id']])
                    for cand in bobinas_de_este_desarrollo
                ])
                
                # No puede exceder kg_disponibles
                self.problema += (
                    kg_usados_total <= desarrollo['kg_disponibles'],
                    f"Material_Disp_{desarrollo['id']}"
                )
                num_restricciones += 1
        
        if self.debug:
            print(f"      ✅ {len(self.desarrollos)} restricciones de material disponible")
            print()
        
        # 🔥 6. NUEVA RESTRICCIÓN: ML_MINIMOS POR PEDIDO
        if self.debug:
            print(f"   6️⃣  🔥 ML MÍNIMOS POR PEDIDO...")
        
        # Calcular factor de tolerancia
        factor_tolerancia = 1 - (self.margen_tolerancia_ml_pct / 100)
        
        num_restricciones_ml = 0
        for pedido in self.pedidos:
            if pedido.get('ml_minimos', 0) > 0:
                ml_min_requerido = pedido['ml_minimos'] * factor_tolerancia
                
                # Para cada bobina que contiene este pedido
                for cand in bobinas_candidatas:
                    if pedido['id'] in cand['configuracion']['cortes']:
                        # Si la bobina está activa, debe tener ML >= ml_min_requerido
                        # ml[bobina] >= ml_min_requerido * y[bobina]
                        self.problema += (
                            ml[cand['id']] >= ml_min_requerido * y[cand['id']],
                            f"ML_Min_{pedido['id']}_{cand['id']}"
                        )
                        num_restricciones_ml += 1
        
        if self.debug:
            if num_restricciones_ml > 0:
                print(f"      ✅ {num_restricciones_ml} restricciones de ML mínimos (tolerancia: ±{self.margen_tolerancia_ml_pct}%)")
            else:
                print(f"      ℹ️  No hay pedidos con ML_MINIMOS especificados")
            print()
        
        # 🔥 7. NUEVA RESTRICCIÓN: ML MÍNIMO RESTO (USAR BOBINA COMPLETA O DEJAR SUFICIENTE)
        if self.debug:
            print(f"   7️⃣  🔥 ML MÍNIMO DE RESTO POR DESARROLLO...")
        
        num_restricciones_resto = 0
        
        if self.ml_minimo_resto > 0:
            # Variables binarias: z[des] = 1 si deja resto válido, 0 si usa todo
            z = {}
            for desarrollo in self.desarrollos:
                z[desarrollo['id']] = LpVariable(
                    f"deja_resto_{desarrollo['id']}", 
                    cat='Binary'
                )
            
            M = 20000  # Número grande para big-M
            
            for desarrollo in self.desarrollos:
                # Bobinas candidatas que usan este desarrollo
                bobinas_de_este_desarrollo = [
                    cand for cand in bobinas_candidatas
                    if (cand['desarrollo']['id'] == desarrollo['id'])
                ]
                
                if bobinas_de_este_desarrollo:
                    # Calcular ML disponibles del desarrollo
                    ancho = desarrollo['ancho']
                    espesor = desarrollo['espesor']
                    kg_disp = desarrollo['kg_disponibles']
                    ml_disponibles = kg_disp / (2.73 * espesor * (ancho / 1000))
                    
                    # ML usados (suma de todas las bobinas de este desarrollo)
                    ml_usados = lpSum([
                        ml[cand['id']] for cand in bobinas_de_este_desarrollo
                    ])
                    
                    # RESTRICCIÓN 1: ML usado no puede exceder disponible
                    self.problema += (
                        ml_usados <= ml_disponibles,
                        f"ML_Max_{desarrollo['id']}"
                    )
                    num_restricciones_resto += 1
                    
                    # RESTRICCIÓN 2: Si deja resto (z=1), debe ser >= ml_minimo_resto
                    # ml_disponibles - ml_usados >= ml_minimo_resto * z
                    self.problema += (
                        ml_disponibles - ml_usados >= self.ml_minimo_resto * z[desarrollo['id']],
                        f"ML_Resto_Min_{desarrollo['id']}"
                    )
                    num_restricciones_resto += 1
                    
                    # RESTRICCIÓN 3: Si no deja resto válido (z=0), debe usar TODO
                    # ml_usados >= ml_disponibles - M*z
                    # Cuando z=0: ml_usados >= ml_disponibles (fuerza usar TODO)
                    # Cuando z=1: ml_usados >= ml_disponibles - M (sin restricción)
                    self.problema += (
                        ml_usados >= ml_disponibles - M * z[desarrollo['id']],
                        f"ML_Usar_Todo_{desarrollo['id']}"
                    )
                    num_restricciones_resto += 1
        
        if self.debug:
            if self.ml_minimo_resto > 0:
                print(f"      ✅ {num_restricciones_resto} restricciones de resto mínimo por desarrollo ({self.ml_minimo_resto}ml)")
            else:
                print(f"      ℹ️  Restricción de resto mínimo desactivada (ml_minimo_resto=0)")
            print()
        
        # 8️⃣  🔥 ML MÍNIMO DE RESTO POR BOBINA INDIVIDUAL
        if self.debug:
            print(f"   8️⃣  🔥 ML MÍNIMO DE RESTO POR BOBINA INDIVIDUAL...")
        
        num_restricciones_bobina_resto = 0
        
        if self.ml_minimo_resto > 0:
            # Variables binarias: z_b[cand_id] = 1 si deja resto válido, 0 si usa todo
            z_b = {}
            for cand in bobinas_candidatas:
                z_b[cand['id']] = LpVariable(
                    f"deja_resto_bobina_{cand['id']}", 
                    cat='Binary'
                )
            
            M = 20000
            
            # Para cada bobina: si deja resto, debe ser >= ml_minimo_resto
            for cand in bobinas_candidatas:
                # Calcular ML máximos de esta bobina
                desarrollo = cand['desarrollo']
                kg_disponibles = desarrollo['kg_disponibles']
                ancho = desarrollo['ancho']
                espesor = desarrollo['espesor']
                ml_max = kg_disponibles / (2.73 * espesor * (ancho / 1000))
                
                # RESTRICCIÓN 1: Si deja resto (z_b=1), debe ser >= ml_minimo_resto
                # ml_max - ml[b] >= ml_minimo_resto * z_b
                self.problema += (
                    ml_max - ml[cand['id']] >= self.ml_minimo_resto * z_b[cand['id']],
                    f"ML_Resto_Min_Bobina_{cand['id']}"
                )
                num_restricciones += 1
                num_restricciones_bobina_resto += 1
                
                # RESTRICCIÓN 2: Si no deja resto válido (z_b=0), debe usar TODO
                # ml[b] >= ml_max - M*z_b
                # Cuando z_b=0: ml[b] >= ml_max (usar todo)
                # Cuando z_b=1: ml[b] >= ml_max - M (sin restricción)
                self.problema += (
                    ml[cand['id']] >= ml_max - M * z_b[cand['id']],
                    f"ML_Usar_Todo_Bobina_{cand['id']}"
                )
                num_restricciones += 1
                num_restricciones_bobina_resto += 1
        
        if self.debug:
            if self.ml_minimo_resto > 0:
                print(f"      ✅ {num_restricciones_bobina_resto} restricciones de resto mínimo por bobina ({self.ml_minimo_resto}ml)")
            else:
                print(f"      ℹ️  Sin restricciones a nivel de bobina")
            print()
            print(f"📊 Total de restricciones: {num_restricciones}")
            print()
        
        # Guardar variables
        self.variables_y = y
        self.variables_ml = ml
    
    def _calcular_kg_asignado(self, bobina: Dict, pedido: Dict, ml_var) -> LpAffineExpression:
        """
        Calcula kg asignados a un pedido en una bobina.
        
        Lógica:
        1. kg_total_bobina = ML × 2.73 × espesor × ancho_desarrollo
        2. kg_usados = kg_total × (ancho_usado / ancho_desarrollo)
        3. kg_asignado = kg_usados × (ancho_corte / ancho_usado)
        
        Simplificando: kg_asignado = ML × 2.73 × espesor × ancho_corte / 1000
        """
        if pedido['id'] not in bobina['configuracion']['cortes']:
            return 0
        
        num_cortes = bobina['configuracion']['cortes'][pedido['id']]
        ancho_corte = num_cortes * pedido['ancho']
        espesor = bobina['desarrollo']['espesor']
        
        # Fórmula simplificada: usa directamente el ancho del corte
        constante = 2.73 * espesor * (ancho_corte / 1000)
        
        return ml_var * constante
    
    def _calcular_kg_bobina(self, bobina: Dict, ml_var) -> LpAffineExpression:
        """
        Calcula kg TOTALES de una bobina (incluye desperdicio).
        
        Los ML se refieren al desarrollo COMPLETO, no solo al ancho usado.
        """
        ancho_desarrollo = bobina['desarrollo']['ancho']  # ← USAR DESARROLLO COMPLETO
        espesor = bobina['desarrollo']['espesor']
        
        constante = 2.73 * espesor * (ancho_desarrollo / 1000)
        
        return ml_var * constante
    
    def _extraer_solucion(self, bobinas_candidatas: List[Dict]) -> Dict:
        """Extrae la solución del modelo resuelto"""
        bobinas_usadas = []
        
        for cand in bobinas_candidatas:
            if value(self.variables_y[cand['id']]) > 0.5:
                ml_valor = value(self.variables_ml[cand['id']])
                
                if ml_valor and ml_valor > 1:
                    # KG TOTAL de la bobina = ML × constante con ANCHO_DESARROLLO
                    ancho_desarrollo = cand['desarrollo']['ancho']
                    espesor = cand['desarrollo']['espesor']
                    kg_total = ml_valor * 2.73 * espesor * (ancho_desarrollo / 1000)
                    
                    # KG USADOS (sin desperdicio) = ML × constante con ANCHO_USADO
                    ancho_usado = cand['ancho_usado']
                    kg_usados = ml_valor * 2.73 * espesor * (ancho_usado / 1000)
                    
                    cortes = []
                    for pedido_id, num_cortes in cand['configuracion']['cortes'].items():
                        pedido = next(p for p in self.pedidos if p['id'] == pedido_id)
                        ancho_usado_corte = num_cortes * pedido['ancho']
                        
                        # Los kg se distribuyen proporcionalmente según el ancho usado
                        proporcion = ancho_usado_corte / ancho_usado
                        kg_asignado = kg_usados * proporcion
                        
                        cortes.append({
                            'pedido_id': pedido_id,
                            'num_cortes': num_cortes,
                            'ancho': pedido['ancho'],
                            'kg_asignados': kg_asignado
                        })
                    
                    bobinas_usadas.append({
                        'desarrollo': cand['desarrollo'],
                        'cortes': cortes,
                        'metros_lineales': ml_valor,
                        'kg_totales': kg_total,  # KG totales (incluye desperdicio)
                        'desperdicio': cand['desperdicio']
                    })
        
        return {
            'bobinas': bobinas_usadas,
            'num_bobinas': len(bobinas_usadas),
            'objetivo': value(self.problema.objective)
        }
    
    def _formatear_resultado(self, df_pedidos: pd.DataFrame) -> List[Dict]:
        """Formatea resultado para output"""
        if not self.solucion:
            return []
        
        if self.debug:
            print(f"{'='*80}")
            print(f"✅ SOLUCIÓN ÓPTIMA")
            print(f"{'='*80}\n")
            print(f"🏆 Número óptimo de bobinas: {self.solucion['num_bobinas']}")
            print()
            
            # Verificar uso de material
            print(f"📦 Verificación de material usado:")
            kg_usado_por_desarrollo = {}
            for bobina in self.solucion['bobinas']:
                des_id = bobina['desarrollo']['id']
                if des_id not in kg_usado_por_desarrollo:
                    kg_usado_por_desarrollo[des_id] = 0
                kg_usado_por_desarrollo[des_id] += bobina['kg_totales']
            
            for desarrollo in self.desarrollos:
                kg_usado = kg_usado_por_desarrollo.get(desarrollo['id'], 0)
                kg_disp = desarrollo['kg_disponibles']
                porcentaje = (kg_usado / kg_disp * 100) if kg_disp > 0 else 0
                estado = "✅" if kg_usado <= kg_disp else "❌"
                print(f"   {estado} {desarrollo['ancho']}×{desarrollo['espesor']}: {kg_usado:.0f}kg / {kg_disp:.0f}kg ({porcentaje:.1f}%)")
            print()
        
        # Crear DataFrame
        filas = []
        for i, bobina in enumerate(self.solucion['bobinas'], 1):
            desarrollo = bobina['desarrollo']
            desarrollo_str = f"{desarrollo['ancho']}×{desarrollo['espesor']}"
            
            for corte in bobina['cortes']:
                filas.append({
                    'BOBINA': f"Bobina_{i}",
                    'DESARROLLO': desarrollo_str,
                    'PEDIDO': corte['pedido_id'],
                    'NUM_CORTES': corte['num_cortes'],
                    'ANCHO_CORTE': corte['ancho'],
                    'METROS_LINEALES': round(bobina['metros_lineales'], 2),
                    'KG_ASIGNADOS': round(corte['kg_asignados'], 2),
                    'KG_TOTALES_BOBINA': round(bobina['kg_totales'], 2),  # ← AGREGADO: kg totales con desperdicio
                    'ANCHO_DESARROLLO': desarrollo['ancho'],
                    'DESPERDICIO': round(bobina['desperdicio'], 2)
                })
        
        df_resultado = pd.DataFrame(filas)
        
        # Calcular cobertura
        cobertura = {}
        for _, pedido_row in df_pedidos.iterrows():
            pedido_id = str(pedido_row['PEDIDO'])
            kg_necesario = float(pedido_row['KG'])
            kg_asignado = df_resultado[df_resultado['PEDIDO'] == pedido_id]['KG_ASIGNADOS'].sum()
            porcentaje = (kg_asignado / kg_necesario * 100) if kg_necesario > 0 else 0
            cobertura[pedido_id] = {
                'kg_asignado': kg_asignado,
                'kg_necesario': kg_necesario,
                'porcentaje': porcentaje,
                'cubierto': kg_asignado >= kg_necesario * 0.95
            }
        
        # Métricas
        desperdicio_total = sum(b['desperdicio'] for b in self.solucion['bobinas'])
        kg_totales = sum(b['kg_totales'] for b in self.solucion['bobinas'])
        
        return [{
            'nombre': 'Solución ILP Óptima V3',
            'num_bobinas': self.solucion['num_bobinas'],
            'dataframe': df_resultado,
            'desperdicio_total': desperdicio_total,
            'kg_totales': kg_totales,
            'cobertura': cobertura,
            'es_valido': all(c['cubierto'] for c in cobertura.values()),
            'tiempo_resolucion': 0
        }]


def optimizar_ilp(df_desarrollos: pd.DataFrame,
                 df_pedidos: pd.DataFrame,
                 desperdicio_bordes_minimo: int = 0,
                 desperdicio_bordes_maximo: int = 30,
                 kg_max_bobina: int = 4000,
                 kg_min_bobina: int = 200,
                 max_cortes_por_pedido: int = 15,
                 margen_cobertura: float = 0.95,
                 margen_exceso: float = 1.10,
                 margen_tolerancia_ml_pct: float = 10.0,
                 ml_minimo_resto: int = 300,
                 tiempo_max_segundos: int = 300,
                 factor_penalizacion_desperdicio: float = 0.0,
                 debug: bool = True) -> List[Dict]:
    """
    Optimiza usando Integer Linear Programming V5.
    
    NUEVA VERSIÓN: 
    - Incluye restricción de kg_disponibles por desarrollo
    - Incluye restricción de ML_MINIMOS por pedido con tolerancia
    - Incluye restricción de ML_MINIMO_RESTO: Si sobra material, debe ser suficiente
    - Incluye restricción de desperdicio_bordes_minimo: Desperdicio mínimo de seguridad
    
    Parámetros:
    - desperdicio_bordes_minimo: Desperdicio mínimo de seguridad en mm (default 10mm)
    - desperdicio_bordes_maximo: Desperdicio máximo permitido en mm (default 30mm)
    - margen_tolerancia_ml_pct: Tolerancia % para ML_MINIMOS (default 10%)
                                Si pedido requiere 300ml, acepta 270ml-330ml con 10%
    - ml_minimo_resto: ML mínimo que puede sobrar (default 300ml)
                       Si sobraría menos, fuerza usar toda la bobina
                       0 = desactivado
    """
    optimizador = OptimizadorILP(
        desperdicio_bordes_minimo=desperdicio_bordes_minimo,
        desperdicio_bordes_maximo=desperdicio_bordes_maximo,
        kg_max_bobina=kg_max_bobina,
        kg_min_bobina=kg_min_bobina,
        max_cortes_por_pedido=max_cortes_por_pedido,
        margen_cobertura=margen_cobertura,
        margen_exceso=margen_exceso,
        margen_tolerancia_ml_pct=margen_tolerancia_ml_pct,
        ml_minimo_resto=ml_minimo_resto,
        tiempo_max_segundos=tiempo_max_segundos,
        factor_penalizacion_desperdicio=factor_penalizacion_desperdicio,
        debug=debug
    )
    
    return optimizador.optimizar(df_desarrollos, df_pedidos)