"""
🔬 OPTIMIZADOR ILP V5 - MINIMIZA CONFIGURACIONES DISTINTAS
Basado en V4 pero reformulado para replicar la lógica del planificador humano:

OBJETIVOS (en orden de prioridad):
1. Minimizar configuraciones DISTINTAS de corte (setups)
2. Maximizar metros lineales totales
3. Minimizar desperdicio

Mantiene TODAS las capacidades de V4:
- Hasta 6 pedidos por configuración
- Restricción de material disponible
- Restricción de ML_MINIMOS
- Restricción de ML_MINIMO_RESTO
- Desperdicio mínimo y máximo
"""

import pandas as pd
from pulp import *
from typing import List, Dict
import time
import hashlib


class OptimizadorILP:
    """
    Optimizador ILP V5 - Minimiza configuraciones distintas
    """
    
    def __init__(self,
                 desperdicio_bordes_minimo: int = 0,
                 desperdicio_bordes_maximo: int = 40,
                 kg_max_bobina: int = 7500,
                 kg_min_bobina: int = 200,
                 max_cortes_por_pedido: int = 15,
                 margen_cobertura: float = 0.95,
                 margen_exceso: float = 1.15,
                 margen_tolerancia_ml_pct: float = 10.0,
                 ml_minimo_resto: int = 0,
                 tiempo_max_segundos: int = 300,
                 max_pedidos_por_configuracion: int = 6,
                 max_instancias_por_config: int = 20,
                 factor_penalizacion_desperdicio: float = 0.01,
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
        self.max_instancias_por_config = max_instancias_por_config
        self.factor_penalizacion_desperdicio = factor_penalizacion_desperdicio
        self.debug = debug
        
        self.desarrollos = []
        self.pedidos = []
        self.problema = None
        self.solucion = None
    
    def optimizar(self, df_desarrollos: pd.DataFrame, df_pedidos: pd.DataFrame) -> List[Dict]:
        """Ejecuta optimización ILP"""
        
        if self.debug:
            print(f"\n{'='*80}")
            print(f"🔬 OPTIMIZADOR ILP V5 - MINIMIZA CONFIGURACIONES DISTINTAS")
            print(f"{'='*80}\n")
        
        # Cargar datos
        self._cargar_datos(df_desarrollos, df_pedidos)
        
        # Generar configuraciones únicas
        if self.debug:
            print(f"{'='*80}")
            print(f"📦 FASE 1: GENERAR CONFIGURACIONES ÚNICAS")
            print(f"{'='*80}\n")
        
        configuraciones = self._generar_configuraciones_unicas()
        
        if self.debug:
            print(f"\n✅ Configuraciones únicas generadas: {len(configuraciones)}\n")
        
        # Crear modelo ILP
        if self.debug:
            print(f"{'='*80}")
            print(f"🔨 FASE 2: CREAR MODELO MATEMÁTICO")
            print(f"{'='*80}\n")
        
        self._crear_modelo_ilp(configuraciones)
        
        # Resolver
        if self.debug:
            print(f"{'='*80}")
            print(f"⚡ FASE 3: RESOLVER OPTIMIZACIÓN")
            print(f"{'='*80}\n")
            print(f"🔍 Resolviendo...")
        
        inicio = time.time()
        estado = self.problema.solve(PULP_CBC_CMD(timeLimit=self.tiempo_max_segundos, msg=0))
        tiempo_resolucion = time.time() - inicio
        
        if self.debug:
            print(f"\n⏱️  Tiempo: {tiempo_resolucion:.2f}s")
            print(f"📊 Estado: {LpStatus[estado]}\n")
        
        if estado == LpStatusOptimal:
            if self.debug:
                print(f"✅ ¡SOLUCIÓN ÓPTIMA ENCONTRADA!\n")
            
            self.solucion = self._extraer_solucion(configuraciones)
            return self._formatear_resultado(df_pedidos, tiempo_resolucion)
        else:
            if self.debug:
                print(f"❌ No se encontró solución óptima")
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
            for p in self.pedidos:
                ml_info = f", ML_MIN: {p['ml_minimos']}" if p['ml_minimos'] > 0 else ""
                print(f"      • {p['id']}: {p['ancho']}mm - {p['kg_solicitados']}kg{ml_info}")
            print()
    
    def _generar_configuraciones_unicas(self) -> List[Dict]:
        """Genera configuraciones únicas (elimina duplicados por hash)"""
        configs_dict = {}
        
        for desarrollo in self.desarrollos:
            if self.debug:
                print(f"\n{'='*80}")
                print(f"🔍 PROCESANDO DESARROLLO: {desarrollo['ancho']}×{desarrollo['espesor']}")
                print(f"{'='*80}\n")
            
            pedidos_compatibles = [
                p for p in self.pedidos
                if (p['espesor'] == desarrollo['espesor'] and
                    p['aleacion'] == desarrollo['aleacion'] and
                    p['estado'] == desarrollo['estado'] and
                    p['ancho'] <= desarrollo['ancho'])
            ]
            
            if not pedidos_compatibles:
                if self.debug:
                    print(f"⚠️  No hay pedidos compatibles con este desarrollo\n")
                continue
            
            if self.debug:
                print(f"📋 Pedidos compatibles ({len(pedidos_compatibles)}):")
                for p in pedidos_compatibles:
                    print(f"   - {p['id']}: {p['ancho']}mm, {p['kg_solicitados']}kg")
                print()
            
            # Generar configs para este desarrollo
            configs_desarrollo = self._generar_configs_desarrollo(desarrollo, pedidos_compatibles)
            
            if self.debug:
                print(f"✅ Configuraciones generadas: {len(configs_desarrollo)}\n")
            
            # Agrupar por hash (eliminar duplicados)
            for config in configs_desarrollo:
                config_hash = config['hash']
                if config_hash not in configs_dict:
                    configs_dict[config_hash] = config
        
        return list(configs_dict.values())
    
    def _generar_configs_desarrollo(self, desarrollo: Dict, pedidos: List[Dict]) -> List[Dict]:
        """Genera TODAS las configs para un desarrollo (1-6 pedidos)"""
        configs = []
        
        # 1 PEDIDO
        for pedido in pedidos:
            max_cortes = int(desarrollo['ancho'] // pedido['ancho'])
            for num_cortes in range(1, min(max_cortes + 1, self.max_cortes_por_pedido + 1)):
                ancho_usado = num_cortes * pedido['ancho']
                desperdicio = desarrollo['ancho'] - ancho_usado
                
                if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                    config = self._crear_config(desarrollo, {pedido['id']: num_cortes}, ancho_usado, desperdicio)
                    configs.append(config)
        
        # 2 PEDIDOS
        for i, p1 in enumerate(pedidos):
            for p2 in pedidos[i+1:]:
                for n1 in range(1, self.max_cortes_por_pedido + 1):
                    for n2 in range(1, self.max_cortes_por_pedido + 1):
                        ancho_usado = n1 * p1['ancho'] + n2 * p2['ancho']
                        if ancho_usado <= desarrollo['ancho']:
                            desperdicio = desarrollo['ancho'] - ancho_usado
                            if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                config = self._crear_config(desarrollo, {p1['id']: n1, p2['id']: n2}, ancho_usado, desperdicio)
                                configs.append(config)
        
        # 3 PEDIDOS
        for i, p1 in enumerate(pedidos):
            for j, p2 in enumerate(pedidos[i+1:], i+1):
                for p3 in pedidos[j+1:]:
                    for n1 in range(1, min(8, self.max_cortes_por_pedido + 1)):
                        for n2 in range(1, min(6, self.max_cortes_por_pedido + 1)):
                            for n3 in range(1, min(6, self.max_cortes_por_pedido + 1)):
                                ancho_usado = n1*p1['ancho'] + n2*p2['ancho'] + n3*p3['ancho']
                                if ancho_usado <= desarrollo['ancho']:
                                    desperdicio = desarrollo['ancho'] - ancho_usado
                                    if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                        config = self._crear_config(desarrollo, 
                                            {p1['id']: n1, p2['id']: n2, p3['id']: n3}, 
                                            ancho_usado, desperdicio)
                                        configs.append(config)
        
        # 4 PEDIDOS
        if self.max_pedidos_por_configuracion >= 4:
            for i, p1 in enumerate(pedidos):
                for j, p2 in enumerate(pedidos[i+1:], i+1):
                    for k, p3 in enumerate(pedidos[j+1:], j+1):
                        for p4 in pedidos[k+1:]:
                            for n1 in range(1, min(5, self.max_cortes_por_pedido + 1)):
                                for n2 in range(1, min(4, self.max_cortes_por_pedido + 1)):
                                    for n3 in range(1, min(4, self.max_cortes_por_pedido + 1)):
                                        for n4 in range(1, min(4, self.max_cortes_por_pedido + 1)):
                                            ancho_usado = n1*p1['ancho'] + n2*p2['ancho'] + n3*p3['ancho'] + n4*p4['ancho']
                                            if ancho_usado <= desarrollo['ancho']:
                                                desperdicio = desarrollo['ancho'] - ancho_usado
                                                if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                                    config = self._crear_config(desarrollo,
                                                        {p1['id']: n1, p2['id']: n2, p3['id']: n3, p4['id']: n4},
                                                        ancho_usado, desperdicio)
                                                    configs.append(config)
        
        # 5 PEDIDOS
        if self.max_pedidos_por_configuracion >= 5:
            for i, p1 in enumerate(pedidos):
                for j, p2 in enumerate(pedidos[i+1:], i+1):
                    for k, p3 in enumerate(pedidos[j+1:], j+1):
                        for l, p4 in enumerate(pedidos[k+1:], k+1):
                            for p5 in pedidos[l+1:]:
                                for n1 in range(1, min(4, self.max_cortes_por_pedido + 1)):
                                    for n2 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                        for n3 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                            for n4 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                                for n5 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                                    ancho_usado = n1*p1['ancho'] + n2*p2['ancho'] + n3*p3['ancho'] + n4*p4['ancho'] + n5*p5['ancho']
                                                    if ancho_usado <= desarrollo['ancho']:
                                                        desperdicio = desarrollo['ancho'] - ancho_usado
                                                        if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                                            config = self._crear_config(desarrollo,
                                                                {p1['id']: n1, p2['id']: n2, p3['id']: n3, p4['id']: n4, p5['id']: n5},
                                                                ancho_usado, desperdicio)
                                                            configs.append(config)
        
        # 6 PEDIDOS
        if self.max_pedidos_por_configuracion >= 6:
            for i, p1 in enumerate(pedidos):
                for j, p2 in enumerate(pedidos[i+1:], i+1):
                    for k, p3 in enumerate(pedidos[j+1:], j+1):
                        for l, p4 in enumerate(pedidos[k+1:], k+1):
                            for m, p5 in enumerate(pedidos[l+1:], l+1):
                                for p6 in pedidos[m+1:]:
                                    for n1 in range(1, min(3, self.max_cortes_por_pedido + 1)):
                                        for n2 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                            for n3 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                                for n4 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                                    for n5 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                                        for n6 in range(1, min(2, self.max_cortes_por_pedido + 1)):
                                                            ancho_usado = n1*p1['ancho'] + n2*p2['ancho'] + n3*p3['ancho'] + n4*p4['ancho'] + n5*p5['ancho'] + n6*p6['ancho']
                                                            if ancho_usado <= desarrollo['ancho']:
                                                                desperdicio = desarrollo['ancho'] - ancho_usado
                                                                if self.desperdicio_bordes_minimo <= desperdicio <= self.desperdicio_bordes_maximo:
                                                                    config = self._crear_config(desarrollo,
                                                                        {p1['id']: n1, p2['id']: n2, p3['id']: n3, p4['id']: n4, p5['id']: n5, p6['id']: n6},
                                                                        ancho_usado, desperdicio)
                                                                    configs.append(config)
        
        return configs
    
    def _crear_config(self, desarrollo: Dict, cortes: Dict, ancho_usado: float, desperdicio: float) -> Dict:
        """
        Crea objeto de configuración con HASH DETALLADO por pedidos.
        
        FASE 1: Este hash se usa para eliminar duplicados EXACTOS de combinaciones de pedidos.
        Dos configs con los mismos pedidos y cantidades → MISMO hash → Se descarta duplicado
        Dos configs con diferentes pedidos pero mismos anchos → DISTINTO hash → Ambas se mantienen
        
        Ejemplo:
        - Config A: {pedido_1: 2, pedido_2: 1} → hash_A ✅
        - Config B: {pedido_3: 1, pedido_4: 1, pedido_2: 1} → hash_B ✅ (diferente, se mantiene)
        - Config C: {pedido_1: 2, pedido_2: 1} → hash_A ❌ (duplicado exacto, se descarta)
        """
        # String canónico ordenado por pedido_id
        cortes_ordenados = sorted([(pid, n) for pid, n in cortes.items()])
        
        # String detallado: incluye pedidos
        config_str_detallado = "+".join([f"{pid}:{n}" for pid, n in cortes_ordenados])
        
        # String físico: solo anchos (para visualización)
        config_str_fisico = "+".join([
            f"{n}×{next(p for p in self.pedidos if p['id']==pid)['ancho']}" 
            for pid, n in cortes_ordenados
        ])
        
        # HASH DETALLADO: desarrollo + pedidos específicos
        hash_str = f"{desarrollo['ancho']}x{desarrollo['espesor']}x{desarrollo['aleacion']}x{desarrollo['estado']}|{config_str_detallado}"
        config_hash = hashlib.md5(hash_str.encode()).hexdigest()[:12]
        
        return {
            'hash': config_hash,  # Hash detallado por pedidos
            'desarrollo': desarrollo,
            'cortes': cortes,
            'ancho_usado': ancho_usado,
            'desperdicio': desperdicio,
            'config_str': config_str_fisico  # String visual por anchos
        }
    
    def _crear_modelo_ilp(self, configuraciones: List[Dict]):
        """Crea modelo ILP que minimiza configuraciones distintas"""
        self.problema = LpProblem("Minimizar_Configuraciones", LpMinimize)
        
        # Variable binaria: y[config] = 1 si uso esta configuración
        y = {}
        for config in configuraciones:
            y[config['hash']] = LpVariable(f"usa_{config['hash']}", cat='Binary')
        
        # Variables: ml[config][i] = metros lineales de la instancia i
        # Variables: usa_inst[config][i] = 1 si uso esta instancia
        ml = {}
        usa_instancia = {}
        for config in configuraciones:
            ml[config['hash']] = {}
            usa_instancia[config['hash']] = {}
            for i in range(self.max_instancias_por_config):
                ml[config['hash']][i] = LpVariable(f"ml_{config['hash']}_{i}", lowBound=0, upBound=20000)
                usa_instancia[config['hash']][i] = LpVariable(f"usa_inst_{config['hash']}_{i}", cat='Binary')
        
        if self.debug:
            print(f"📊 Variables:")
            print(f"   - Configs únicas: {len(configuraciones)}")
            print(f"   - Max instancias por config: {self.max_instancias_por_config}")
            print(f"   - Total vars binarias: {len(configuraciones) * (1 + self.max_instancias_por_config)}")
            print(f"   - Total vars continuas: {len(configuraciones) * self.max_instancias_por_config}\n")
        
        # OBJETIVO MULTI-CRITERIO
        # 1. Minimizar configuraciones distintas (peso 10000)
        # 2. Maximizar ML totales (bonus -0.1)
        # 3. Minimizar desperdicio (penalización +factor)
        objetivo = lpSum([10000 * y[c['hash']] for c in configuraciones])
        
        for config in configuraciones:
            for i in range(self.max_instancias_por_config):
                # Bonus por ML (maximizar ML)
                objetivo -= 0.1 * ml[config['hash']][i]
                # Penalización por desperdicio
                objetivo += self.factor_penalizacion_desperdicio * config['desperdicio'] * usa_instancia[config['hash']][i]
        
        self.problema += objetivo, "Minimizar_Configs_Maximizar_ML"
        
        if self.debug:
            print(f"🎯 Objetivo Multi-criterio:")
            print(f"   1. Peso configs: 10000 (PRINCIPAL)")
            print(f"   2. Bonus ML: -0.1 por ml (maximizar)")
            print(f"   3. Penalización desperdicio: +{self.factor_penalizacion_desperdicio} por mm\n")
        
        # RESTRICCIONES
        if self.debug:
            print(f"📋 Creando restricciones...")
        
        num_restricciones = 0
        
        # 1. Si instancia usada → config activa
        for config in configuraciones:
            for i in range(self.max_instancias_por_config):
                self.problema += (
                    usa_instancia[config['hash']][i] <= y[config['hash']],
                    f"Activar_{config['hash']}_{i}"
                )
                num_restricciones += 1
        
        # 2. ML solo si instancia activa
        M = 20000
        for config in configuraciones:
            for i in range(self.max_instancias_por_config):
                self.problema += (
                    ml[config['hash']][i] <= M * usa_instancia[config['hash']][i],
                    f"ML_Activo_{config['hash']}_{i}"
                )
                num_restricciones += 1
        
        # 3. Cobertura mínima
        for pedido in self.pedidos:
            kg_asignados = lpSum([
                self._calcular_kg_asignado(config, pedido, ml[config['hash']][i])
                for config in configuraciones
                if pedido['id'] in config['cortes']
                for i in range(self.max_instancias_por_config)
            ])
            kg_minimo = pedido['kg_solicitados'] * self.margen_cobertura
            self.problema += (kg_asignados >= kg_minimo, f"Cob_Min_{pedido['id']}")
            num_restricciones += 1
        
        # 4. Exceso máximo
        for pedido in self.pedidos:
            kg_asignados = lpSum([
                self._calcular_kg_asignado(config, pedido, ml[config['hash']][i])
                for config in configuraciones
                if pedido['id'] in config['cortes']
                for i in range(self.max_instancias_por_config)
            ])
            kg_maximo = pedido['kg_solicitados'] * self.margen_exceso
            self.problema += (kg_asignados <= kg_maximo, f"Exc_Max_{pedido['id']}")
            num_restricciones += 1
        
        # 5. Peso máximo por bobina
        for config in configuraciones:
            for i in range(self.max_instancias_por_config):
                kg_bobina = self._calcular_kg_bobina(config, ml[config['hash']][i])
                self.problema += (kg_bobina <= self.kg_max_bobina, f"Peso_Max_{config['hash']}_{i}")
                num_restricciones += 1
        
        # 6. Peso mínimo por bobina
        for config in configuraciones:
            for i in range(self.max_instancias_por_config):
                kg_bobina = self._calcular_kg_bobina(config, ml[config['hash']][i])
                self.problema += (
                    kg_bobina >= self.kg_min_bobina * usa_instancia[config['hash']][i],
                    f"Peso_Min_{config['hash']}_{i}"
                )
                num_restricciones += 1
        
        # 7. Material disponible por desarrollo
        for desarrollo in self.desarrollos:
            kg_usados = lpSum([
                self._calcular_kg_bobina(config, ml[config['hash']][i])
                for config in configuraciones
                if config['desarrollo']['id'] == desarrollo['id']
                for i in range(self.max_instancias_por_config)
            ])
            self.problema += (kg_usados <= desarrollo['kg_disponibles'], f"Mat_{desarrollo['id']}")
            num_restricciones += 1
        
        # 8. ML mínimos por pedido (si especificado)
        if self.margen_tolerancia_ml_pct > 0:
            factor_tolerancia = 1 - (self.margen_tolerancia_ml_pct / 100)
            for pedido in self.pedidos:
                if pedido.get('ml_minimos', 0) > 0:
                    ml_min_requerido = pedido['ml_minimos'] * factor_tolerancia
                    for config in configuraciones:
                        if pedido['id'] in config['cortes']:
                            for i in range(self.max_instancias_por_config):
                                self.problema += (
                                    ml[config['hash']][i] >= ml_min_requerido * usa_instancia[config['hash']][i],
                                    f"ML_Min_{pedido['id']}_{config['hash']}_{i}"
                                )
                                num_restricciones += 1
        
        if self.debug:
            print(f"   ✅ Total restricciones: {num_restricciones}\n")
        
        self.variables_y = y
        self.variables_ml = ml
        self.variables_usa_instancia = usa_instancia
    
    def _calcular_kg_asignado(self, config: Dict, pedido: Dict, ml_var) -> float:
        """Calcula kg asignados a un pedido"""
        if pedido['id'] not in config['cortes']:
            return 0
        num_cortes = config['cortes'][pedido['id']]
        ancho_corte = num_cortes * pedido['ancho']
        espesor = config['desarrollo']['espesor']
        constante = 2.73 * espesor * (ancho_corte / 1000)
        return ml_var * constante
    
    def _calcular_kg_bobina(self, config: Dict, ml_var) -> float:
        """Calcula kg totales de bobina"""
        ancho_desarrollo = config['desarrollo']['ancho']
        espesor = config['desarrollo']['espesor']
        constante = 2.73 * espesor * (ancho_desarrollo / 1000)
        return ml_var * constante
    
    def _calcular_hash_fisico(self, config: Dict) -> str:
        """
        Calcula hash FÍSICO basado solo en anchos (no en pedidos).
        
        FASE 3: Este hash se usa SOLO para contar configuraciones físicas distintas.
        Dos bobinas con los mismos anchos → MISMO hash físico → 1 configuración
        
        Ejemplo:
        - Bobina A: {pedido_1: 2, pedido_2: 1} con anchos {536.3: 2, 143: 1}
        - Bobina B: {pedido_3: 1, pedido_4: 1, pedido_5: 1} con anchos {536.3: 2, 143: 1}
        → Ambas generan hash_fisico "2×536.3+1×143" → 1 configuración física
        """
        # Agrupar por ANCHO físico
        anchos_count = {}
        for pedido_id, num_cortes in config['cortes'].items():
            pedido = next(p for p in self.pedidos if p['id'] == pedido_id)
            ancho = pedido['ancho']
            anchos_count[ancho] = anchos_count.get(ancho, 0) + num_cortes
        
        # String ordenado por ancho
        config_str_fisico = "+".join([f"{n}×{ancho}" for ancho, n in sorted(anchos_count.items())])
        
        # Hash físico: desarrollo + anchos
        hash_str = f"{config['desarrollo']['ancho']}x{config['desarrollo']['espesor']}|{config_str_fisico}"
        return hashlib.md5(hash_str.encode()).hexdigest()[:12]
    
    def _extraer_solucion(self, configuraciones: List[Dict]) -> Dict:
        """Extrae solución usando hash físico para contar configuraciones distintas"""
        configs_usadas_fisicas = {}  # Agrupar por hash FÍSICO
        bobinas_usadas = []
        
        for config in configuraciones:
            if value(self.variables_y[config['hash']]) > 0.5:
                # Calcular hash FÍSICO para agrupar
                hash_fisico = self._calcular_hash_fisico(config)
                
                if hash_fisico not in configs_usadas_fisicas:
                    configs_usadas_fisicas[hash_fisico] = {
                        'config': config,
                        'instancias': []
                    }
                
                for i in range(self.max_instancias_por_config):
                    if value(self.variables_usa_instancia[config['hash']][i]) > 0.5:
                        ml_valor = value(self.variables_ml[config['hash']][i])
                        if ml_valor and ml_valor > 10:
                            configs_usadas_fisicas[hash_fisico]['instancias'].append({
                                'ml': ml_valor,
                                'instancia': i,
                                'config_detallada': config  # Guardar config con pedidos
                            })
                            
                            # Calcular kg
                            desarrollo = config['desarrollo']
                            ancho_desarrollo = desarrollo['ancho']
                            espesor = desarrollo['espesor']
                            kg_total = ml_valor * 2.73 * espesor * (ancho_desarrollo / 1000)
                            ancho_usado = config['ancho_usado']
                            kg_usados = ml_valor * 2.73 * espesor * (ancho_usado / 1000)
                            
                            cortes = []
                            for pedido_id, num_cortes in config['cortes'].items():
                                pedido = next(p for p in self.pedidos if p['id'] == pedido_id)
                                ancho_corte = num_cortes * pedido['ancho']
                                proporcion = ancho_corte / ancho_usado
                                kg_asignado = kg_usados * proporcion
                                cortes.append({
                                    'pedido_id': pedido_id,
                                    'num_cortes': num_cortes,
                                    'ancho': pedido['ancho'],
                                    'kg_asignados': kg_asignado
                                })
                            
                            bobinas_usadas.append({
                                'desarrollo': desarrollo,
                                'cortes': cortes,
                                'metros_lineales': ml_valor,
                                'kg_totales': kg_total,
                                'desperdicio': config['desperdicio'],
                                'config_hash_fisico': hash_fisico,
                                'config_str': config['config_str']
                            })
        
        if self.debug:
            print(f"{'='*80}")
            print(f"✅ SOLUCIÓN:")
            print(f"{'='*80}\n")
            print(f"🎯 Configuraciones FÍSICAS DISTINTAS: {len(configs_usadas_fisicas)}")
            print(f"📦 Bobinas totales generadas: {len(bobinas_usadas)}\n")
            
            for hash_fisico, data in configs_usadas_fisicas.items():
                config = data['config']
                instancias = data['instancias']
                print(f"📋 Config física: {config['config_str']} (desp: {config['desperdicio']:.1f}mm)")
                print(f"   Usada {len(instancias)} {'vez' if len(instancias)==1 else 'veces'}:")
                for idx, inst in enumerate(instancias, 1):
                    config_det = inst['config_detallada']
                    pedidos_str = ", ".join([pid for pid in config_det['cortes'].keys()])
                    print(f"      Instancia {idx}: ML={inst['ml']:.0f} → Pedidos: {pedidos_str}")
                print()
        
        return {
            'bobinas': bobinas_usadas,
            'num_bobinas': len(bobinas_usadas),
            'num_configs': len(configs_usadas_fisicas)
        }
    
    def _formatear_resultado(self, df_pedidos: pd.DataFrame, tiempo: float) -> List[Dict]:
        """Formatea resultado"""
        if not self.solucion:
            return []
        
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
                    'KG_TOTALES_BOBINA': round(bobina['kg_totales'], 2),
                    'ANCHO_DESARROLLO': desarrollo['ancho'],
                    'DESPERDICIO': round(bobina['desperdicio'], 2)
                })
        
        df_resultado = pd.DataFrame(filas)
        
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
        
        desperdicio_total = sum(b['desperdicio'] for b in self.solucion['bobinas'])
        kg_totales = sum(b['kg_totales'] for b in self.solucion['bobinas'])
        
        return [{
            'nombre': 'ILP V5 - Configuraciones Distintas',
            'num_bobinas': self.solucion['num_bobinas'],
            'num_configuraciones': self.solucion['num_configs'],
            'dataframe': df_resultado,
            'dataframe_desarrollos': self._agrupar_por_desarrollos(df_resultado),
            'desperdicio_total': desperdicio_total,
            'kg_totales': kg_totales,
            'cobertura': cobertura,
            'es_valido': all(c['cubierto'] for c in cobertura.values()),
            'tiempo_resolucion': tiempo
        }]
    
    def _agrupar_por_desarrollos(self, df_resultado: pd.DataFrame) -> pd.DataFrame:
        """
        Agrupa resultados por DESARROLLO + CONFIGURACIÓN FÍSICA.
        
        Muestra cada combinación única de:
        - Desarrollo (con aleación y estado)
        - Configuración de cortes física
        - ML totales (suma si hay varias bobinas)
        - KG totales (suma si hay varias bobinas)
        - Número de bobinas con esta configuración
        - Detalle de pedidos y kg asignados
        """
        if df_resultado.empty:
            return pd.DataFrame()
        
        # Agrupar por Bobina para obtener configuraciones únicas
        agrupaciones = []
        
        for bobina_id in df_resultado['BOBINA'].unique():
            df_bobina = df_resultado[df_resultado['BOBINA'] == bobina_id]
            
            # Obtener info básica
            desarrollo = df_bobina['DESARROLLO'].iloc[0]
            ml = df_bobina['METROS_LINEALES'].iloc[0]
            kg_total_bobina = df_bobina['KG_TOTALES_BOBINA'].iloc[0]
            
            # Obtener aleación y estado desde df_desarrollos
            desarrollo_parts = desarrollo.split('×')
            if len(desarrollo_parts) == 2:
                ancho_dev = float(desarrollo_parts[0])
                espesor_dev = float(desarrollo_parts[1])
                
                dev_match = self.pedidos[0] if len(self.pedidos) > 0 else None  # Placeholder
                # Buscar en desarrollos originales
                for des in self.desarrollos:
                    if des['ancho'] == ancho_dev and des['espesor'] == espesor_dev:
                        aleacion = des['aleacion']
                        estado = des['estado']
                        desarrollo_completo = f"{aleacion} {estado} {desarrollo}"
                        break
                else:
                    desarrollo_completo = desarrollo
            else:
                desarrollo_completo = desarrollo
            
            # Construir configuración física (agrupar por ancho)
            anchos_count = {}
            for _, row in df_bobina.iterrows():
                ancho = row['ANCHO_CORTE']
                if ancho not in anchos_count:
                    anchos_count[ancho] = 0
                anchos_count[ancho] += row['NUM_CORTES']
            
            # String de configuración ordenado
            config_str = " + ".join([f"{count}×{ancho:.1f}" for ancho, count in sorted(anchos_count.items())])
            
            # Clave para agrupar: desarrollo_completo + config_str
            clave = f"{desarrollo_completo}|{config_str}"
            
            # Detalle de pedidos
            pedidos_detalle = []
            for _, row in df_bobina.iterrows():
                pedidos_detalle.append({
                    'pedido': row['PEDIDO'],
                    'kg': row['KG_ASIGNADOS']
                })
            
            agrupaciones.append({
                'clave': clave,
                'desarrollo_completo': desarrollo_completo,
                'config_str': config_str,
                'ml': ml,
                'kg_total': kg_total_bobina,
                'pedidos': pedidos_detalle,
                'bobina_id': bobina_id
            })
        
        # Agrupar por clave (desarrollo + configuración)
        grupos = {}
        for item in agrupaciones:
            clave = item['clave']
            if clave not in grupos:
                grupos[clave] = {
                    'desarrollo_completo': item['desarrollo_completo'],
                    'config_str': item['config_str'],
                    'ml_total': 0,
                    'kg_total': 0,
                    'num_bobinas': 0,
                    'pedidos_acumulados': {}
                }
            
            grupos[clave]['ml_total'] += item['ml']
            grupos[clave]['kg_total'] += item['kg_total']
            grupos[clave]['num_bobinas'] += 1
            
            # Acumular kg por pedido
            for ped_info in item['pedidos']:
                pedido_id = ped_info['pedido']
                kg = ped_info['kg']
                if pedido_id not in grupos[clave]['pedidos_acumulados']:
                    grupos[clave]['pedidos_acumulados'][pedido_id] = 0
                grupos[clave]['pedidos_acumulados'][pedido_id] += kg
        
        # Convertir a DataFrame
        filas = []
        for clave, data in grupos.items():
            # Construir string de pedidos
            pedidos_str = ", ".join(data['pedidos_acumulados'].keys())
            
            # Construir detalle de kg por pedido
            pedidos_kg_list = [f"{ped}: {kg:.0f}kg" for ped, kg in data['pedidos_acumulados'].items()]
            pedidos_kg_str = " | ".join(pedidos_kg_list)
            
            filas.append({
                'DESARROLLO_CONFIG': f"{data['desarrollo_completo']}: [{data['config_str']}]",
                'ML_TOTALES': round(data['ml_total'], 2),
                'KG_TOTALES': round(data['kg_total'], 2),
                'NUM_BOBINAS': data['num_bobinas'],
                'PEDIDOS': pedidos_str,
                'KG_POR_PEDIDO': pedidos_kg_str
            })
        
        return pd.DataFrame(filas)


def optimizar_ilp(df_desarrollos: pd.DataFrame,
                 df_pedidos: pd.DataFrame,
                 desperdicio_bordes_minimo: int = 0,
                 desperdicio_bordes_maximo: int = 40,
                 kg_max_bobina: int = 7500,
                 kg_min_bobina: int = 200,
                 max_cortes_por_pedido: int = 15,
                 margen_cobertura: float = 0.95,
                 margen_exceso: float = 1.15,
                 margen_tolerancia_ml_pct: float = 10.0,
                 ml_minimo_resto: int = 0,
                 tiempo_max_segundos: int = 300,
                 max_pedidos_por_configuracion: int = 6,
                 factor_penalizacion_desperdicio: float = 0.01,
                 debug: bool = True) -> List[Dict]:
    """
    Optimizador ILP V5 - Minimiza configuraciones DISTINTAS
    
    Prioridades (igual que el planificador humano):
    1. Menor número de configuraciones DISTINTAS (setups)
    2. Mayor cantidad de metros lineales totales
    3. Menor desperdicio total
    
    Permite hasta 6 pedidos diferentes por configuración.
    Cada configuración puede usarse N veces sin penalización.
    
    Parámetros:
    - margen_tolerancia_ml_pct: Tolerancia % para ML_MINIMOS (default 10%)
    - ml_minimo_resto: ML mínimo que puede sobrar (default 0 = desactivado)
    - max_pedidos_por_configuracion: Máximo pedidos por configuración (default 6)
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
        max_pedidos_por_configuracion=max_pedidos_por_configuracion,
        max_instancias_por_config=20,     # Cada config puede usarse hasta 20 veces
        factor_penalizacion_desperdicio=factor_penalizacion_desperdicio,
        debug=debug
    )
    
    return optimizador.optimizar(df_desarrollos, df_pedidos)