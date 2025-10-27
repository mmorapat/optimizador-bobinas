import pandas as pd
import numpy as np
import random
import copy
from itertools import combinations

class OptimizadorBobinas:
    def __init__(self, desperdicio_max=40, margen_exceso_pedidos=10, kg_max_bobina=4000, 
                 kg_min_bobina=200, max_intentos=200, margen_exceso_bobina=15, 
                 max_cortes_por_pedido=15, max_pedidos_por_bobina=6, debug=False):
        self.desperdicio_max = desperdicio_max
        self.margen_exceso_pedidos_pct = margen_exceso_pedidos / 100
        self.kg_max_bobina = kg_max_bobina
        self.kg_min_bobina = kg_min_bobina
        self.max_intentos = max_intentos
        self.margen_exceso_bobina_pct = margen_exceso_bobina / 100
        self.max_cortes_por_pedido = max_cortes_por_pedido
        self.max_pedidos_por_bobina = max_pedidos_por_bobina
        self.debug = debug
        self.desarrollos = []
        self.pedidos = []
        self.combinaciones_por_desarrollo = {}
    
    def calcular_kg_de_ml(self, ancho, espesor, ml):
        """Calcula kg a partir de metros lineales"""
        return ml * 2.73 * espesor * (ancho / 1000)
    
    def calcular_ml_de_kg(self, ancho, espesor, kg):
        """Calcula metros lineales necesarios para obtener X kg"""
        if ancho == 0 or espesor == 0:
            return 0
        return (kg * 1000) / (2.73 * espesor * ancho)
    
    def cargar_desarrollos(self, df_desarrollos):
        """Carga los desarrollos disponibles"""
        self.desarrollos = []
        for _, row in df_desarrollos.iterrows():
            desarrollo = {
                'ancho': float(row['ANCHO']),
                'espesor': float(row['ESPESOR']),
                'aleacion': str(row['ALEACION']),
                'estado': str(row['ESTADO']),
                'kg_disponibles': float(row['KG']),
                'nombre': f"{row['ANCHO']}Ã—{row['ESPESOR']} ({row['ALEACION']}-{row['ESTADO']})"
            }
            self.desarrollos.append(desarrollo)
    
    def cargar_pedidos(self, df_pedidos):
        """Carga los pedidos a satisfacer"""
        self.pedidos = []
        for _, row in df_pedidos.iterrows():
            pedido = {
                'id': str(row['PEDIDO']),
                'ancho': float(row['ANCHO']),
                'kg_solicitados': float(row['KG']),
                'ml_minimos': float(row['ML_MINIMOS']) if 'ML_MINIMOS' in row and pd.notna(row['ML_MINIMOS']) else 0,
                'aleacion': str(row['ALEACION']),
                'estado': str(row['ESTADO']),
                'espesor': float(row['ESPESOR'])
            }
            self.pedidos.append(pedido)
    
    def _generar_combinaciones_corte(self, desarrollo, pedidos_compatibles):
        """Genera todas las combinaciones posibles de corte para un desarrollo"""
        ancho_desarrollo = desarrollo['ancho']
        combinaciones = []
        
        if pedidos_compatibles:
            ancho_minimo = min(p['ancho'] for p in pedidos_compatibles)
            max_pedidos_teorico = min(
                int(ancho_desarrollo // ancho_minimo),
                self.max_pedidos_por_bobina,
                len(pedidos_compatibles)
            )
        else:
            max_pedidos_teorico = 1
        
        if self.debug:
            print(f"   Generando combinaciones para hasta {max_pedidos_teorico} pedidos...")
        
        # Combinaciones de 1 pedido
        for pedido in pedidos_compatibles:
            max_cortes_posibles = min(int(ancho_desarrollo // pedido['ancho']), self.max_cortes_por_pedido)
            for num_cortes in range(1, max_cortes_posibles + 1):
                ancho_usado = pedido['ancho'] * num_cortes
                desperdicio = ancho_desarrollo - ancho_usado
                
                if 0 <= desperdicio <= self.desperdicio_max:
                    combinaciones.append({
                        'pedidos': [{'pedido': pedido, 'num_cortes': num_cortes}],
                        'ancho_usado': ancho_usado,
                        'desperdicio': desperdicio
                    })
        
        # Combinaciones de 2 hasta max_pedidos_teorico pedidos
        for num_pedidos in range(2, max_pedidos_teorico + 1):
            max_cortes_por_pedido_ajustado = max(1, self.max_cortes_por_pedido // num_pedidos)
            
            for combo_pedidos in combinations(pedidos_compatibles, num_pedidos):
                self._generar_combinaciones_recursivas(
                    combo_pedidos, 
                    ancho_desarrollo, 
                    max_cortes_por_pedido_ajustado,
                    combinaciones
                )
        
        if self.debug:
            print(f"   Total: {len(combinaciones)} combinaciones")
            
            # ðŸ”¥ MOSTRAR TODAS LAS COMBINACIONES DE 3 PEDIDOS (sin lÃ­mite)
            combis_3_pedidos = [c for c in combinaciones if len(c['pedidos']) == 3]
            if combis_3_pedidos:
                print(f"   ðŸ“‹ Combinaciones de 3 pedidos ({len(combis_3_pedidos)}):")
                # Mostrar TODAS las combinaciones de 3 pedidos (sin lÃ­mite)
                for i, comb in enumerate(combis_3_pedidos):
                    detalles = []
                    pedidos_ids = []
                    for p in comb['pedidos']:
                        ancho = p['pedido']['ancho']
                        num = p['num_cortes']
                        pedido_id = p['pedido']['id']
                        detalles.append(f"{num}Ã—{ancho:.1f}")
                        pedidos_ids.append(pedido_id)
                    print(f"      {i+1}. {' + '.join(detalles)} (desp:{comb['desperdicio']}mm) [{', '.join(pedidos_ids)}]")
            
            encontradas = []
            for comb in combinaciones:
                if len(comb['pedidos']) == 1:
                    p = comb['pedidos'][0]
                    if (p['num_cortes'] == 10 and int(p['pedido']['ancho']) == 120):
                        encontradas.append(f"10Ã—120 (desp:{comb['desperdicio']}mm)")
                elif len(comb['pedidos']) == 3:
                    anchos_cortes = {}
                    for p in comb['pedidos']:
                        ancho = int(p['pedido']['ancho'])
                        num = p['num_cortes']
                        anchos_cortes[ancho] = anchos_cortes.get(ancho, 0) + num
                    
                    # ðŸ”¥ BUSCAR LA COMBINACIÃ“N DEL PLANIFICADOR: 4Ã—132.5 + 2Ã—153 + 3Ã—120
                    if (anchos_cortes.get(132, 0) + anchos_cortes.get(133, 0) == 4 and
                        anchos_cortes.get(153, 0) == 2 and
                        anchos_cortes.get(120, 0) == 3):
                        encontradas.append(f"â­ 4Ã—132.5+2Ã—153+3Ã—120 (desp:{comb['desperdicio']}mm)")
            
            if encontradas:
                print(f"   ðŸŽ¯ PLANIFICADOR: {', '.join(encontradas)}")
        
        return combinaciones
    
    def _generar_combinaciones_recursivas(self, pedidos, ancho_desarrollo, max_cortes, combinaciones, 
                                         asignacion_actual=None, idx=0, ancho_usado=0):
        """Genera combinaciones de mÃºltiples pedidos de forma recursiva"""
        if asignacion_actual is None:
            asignacion_actual = []
        
        if idx == len(pedidos):
            desperdicio = ancho_desarrollo - ancho_usado
            if 0 <= desperdicio <= self.desperdicio_max and ancho_usado > 0:
                combinaciones.append({
                    'pedidos': asignacion_actual.copy(),
                    'ancho_usado': ancho_usado,
                    'desperdicio': desperdicio
                })
            return
        
        pedido_actual = pedidos[idx]
        espacio_restante = ancho_desarrollo - ancho_usado
        max_cortes_posibles = min(
            int(espacio_restante // pedido_actual['ancho']),
            max_cortes
        )
        
        for num_cortes in range(1, max_cortes_posibles + 1):
            nuevo_ancho = ancho_usado + (pedido_actual['ancho'] * num_cortes)
            
            if nuevo_ancho <= ancho_desarrollo:
                nueva_asignacion = asignacion_actual + [{
                    'pedido': pedido_actual,
                    'num_cortes': num_cortes
                }]
                
                self._generar_combinaciones_recursivas(
                    pedidos, ancho_desarrollo, max_cortes, combinaciones,
                    nueva_asignacion, idx + 1, nuevo_ancho
                )
    
    def _validar_integridad_bobina(self, bobina):
        """Valida que los kg calculados sean consistentes"""
        ml = bobina['metros_lineales']
        espesor = bobina['desarrollo']['espesor']
        kg_totales_declarado = bobina['kg_totales']
        ancho_desarrollo = bobina['desarrollo']['ancho']
        
        # ðŸ”¥ CALCULAR PESO REAL BASADO EN ANCHO TOTAL USADO
        ancho_total_usado = sum(c['ancho_usado'] for c in bobina['cortes'])
        kg_real_total = self.calcular_kg_de_ml(ancho_total_usado, espesor, ml)
        
        if ancho_total_usado > ancho_desarrollo:
            if self.debug:
                print(f"      âŒ ERROR: Ancho usado ({ancho_total_usado}mm) > Desarrollo ({ancho_desarrollo}mm)")
            return False
        
        # Validar que el total declarado coincida con el calculado
        if abs(kg_totales_declarado - kg_real_total) > kg_real_total * 0.02:  # 2% tolerancia
            if self.debug:
                print(f"      âŒ ERROR: KG declarado ({kg_totales_declarado:.2f}) != KG real ({kg_real_total:.2f})")
            return False
        
        # ðŸ”¥ VALIDACIÃ“N CRÃTICA: Verificar coherencia de kg_generado
        suma_kg_generados = 0
        for corte in bobina['cortes']:
            # Calcular kg_generado para este corte
            ancho_total_corte = corte['num_cortes'] * corte['ancho_corte']
            kg_gen = ml * 2.73 * espesor * (ancho_total_corte / 1000)
            suma_kg_generados += kg_gen
            
            # Validar que kg_asignado <= kg_generado
            if corte['kg_asignados'] > kg_gen * 1.01:  # 1% tolerancia
                if self.debug:
                    print(f"      âŒ ERROR: {corte['pedido_id']}: kg_asignado ({corte['kg_asignados']:.2f}) > kg_generado ({kg_gen:.2f})")
                return False
        
        # âœ… VALIDAR QUE LA SUMA DE KG_GENERADOS = KG_REAL_TOTAL
        if abs(suma_kg_generados - kg_real_total) > 1.0:
            if self.debug:
                print(f"      âŒ ERROR: Suma kg_generados ({suma_kg_generados:.2f}) != kg_real_total ({kg_real_total:.2f})")
            return False
        
        # ðŸ”¥ VALIDAR QUE CADA CORTE TENGA KG_ASIGNADOS CORRECTOS
        for corte in bobina['cortes']:
            # CÃ¡lculo usando la fÃ³rmula: KG = ML Ã— 2.73 Ã— espesor Ã— (num_cortes Ã— ancho_corte) / 1000
            ancho_total_corte = corte['num_cortes'] * corte['ancho_corte']
            kg_calculado_formula = ml * 2.73 * espesor * (ancho_total_corte / 1000)
            kg_asignado = corte['kg_asignados']
            
            # Validar que la diferencia sea menor a 1kg o 1%
            diferencia_absoluta = abs(kg_asignado - kg_calculado_formula)
            diferencia_porcentual = (diferencia_absoluta / kg_calculado_formula) * 100 if kg_calculado_formula > 0 else 0
            
            if diferencia_absoluta > 1 and diferencia_porcentual > 1:
                if self.debug:
                    print(f"      âŒ ERROR: Corte {corte['pedido_id']}: KG_asignado ({kg_asignado:.2f}) != KG_formula ({kg_calculado_formula:.2f}), diff={diferencia_absoluta:.2f}kg ({diferencia_porcentual:.1f}%)")
                return False
        
        # ðŸ”¥ VALIDAR QUE LA SUMA DE KG ASIGNADOS NO EXCEDA EL PESO REAL
        suma_kg_asignados = sum(c['kg_asignados'] for c in bobina['cortes'])
        if suma_kg_asignados > kg_real_total * 1.01:  # 1% tolerancia
            if self.debug:
                print(f"      âŒ ERROR: Suma KG asignados ({suma_kg_asignados:.2f}) > KG real ({kg_real_total:.2f})")
            return False
        
        if kg_real_total > self.kg_max_bobina * 1.01:
            if self.debug:
                print(f"      âŒ ERROR: KG real ({kg_real_total:.2f}) > KG mÃ¡x ({self.kg_max_bobina})")
            return False
        
        return True
    
    def _crear_bobina_desde_combinacion(self, combinacion, desarrollo, pedidos_estado):
        """Crea una bobina validando todas las restricciones"""
        espesor = desarrollo['espesor']
        ancho_total_usado = combinacion['ancho_usado']
        
        if self.debug:
            cortes_info = [f"{asig['num_cortes']}Ã—{int(asig['pedido']['ancho'])}" for asig in combinacion['pedidos']]
            cortes_str = ", ".join(cortes_info)
            print(f"\n   ðŸ”§ Intentando crear bobina: {cortes_str}")
        
        pedidos_ids = [asig['pedido']['id'] for asig in combinacion['pedidos']]
        if len(pedidos_ids) != len(set(pedidos_ids)):
            if self.debug:
                print(f"      âŒ RECHAZADA: Pedidos duplicados")
            return None
        
        for asig in combinacion['pedidos']:
            if asig['num_cortes'] <= 0:
                if self.debug:
                    print(f"      âŒ RECHAZADA: num_cortes invÃ¡lido")
                return None
        
        # ðŸ”¥ CALCULAR ML MAX BASADO EN ANCHO TOTAL USADO
        ml_max_por_kg = self.calcular_ml_de_kg(ancho_total_usado, espesor, self.kg_max_bobina)
        
        # ðŸ”¥ CALCULAR ML MIN: MÃ¡ximo entre ML_MINIMOS de todos los pedidos
        ml_min_global = max((asig['pedido']['ml_minimos'] for asig in combinacion['pedidos']), default=0)
        
        # ðŸ”¥ CALCULAR ML NECESARIO PARA CUBRIR KG PENDIENTES
        ml_necesario_max = 0
        for asig in combinacion['pedidos']:
            pedido = asig['pedido']
            kg_pendiente = pedidos_estado[pedido['id']]['kg_pendientes']
            ancho_corte_total = pedido['ancho'] * asig['num_cortes']
            ml_para_pedido = self.calcular_ml_de_kg(ancho_corte_total, espesor, kg_pendiente * (1 + self.margen_exceso_pedidos_pct))
            ml_necesario_max = max(ml_necesario_max, ml_para_pedido)
        
        ml_min = max(ml_min_global, 100)
        ml_max = min(ml_max_por_kg, ml_necesario_max * 1.5) if ml_necesario_max > 0 else ml_max_por_kg
        
        if ml_min > ml_max:
            if self.debug:
                print(f"      âŒ RECHAZADA: ml_min ({ml_min:.0f}) > ml_max ({ml_max:.0f})")
            return None
        
        if self.debug:
            print(f"      ML rango: {ml_min:.0f}ml - {ml_max:.0f}ml")
        
        num_candidatos = min(max(int((ml_max - ml_min) / 200), 10), 30)
        candidatos_ml = np.linspace(ml_min, ml_max, num_candidatos)
        
        if self.debug:
            print(f"      Evaluando {len(candidatos_ml)} candidatos de ML...")
        
        ml_mejor = None
        kg_total_mejor = 0
        kg_real_mejor = 0
        cortes_mejor = []
        
        for ml_prueba in candidatos_ml:
            kg_real_total_bobina = self.calcular_kg_de_ml(ancho_total_usado, espesor, ml_prueba)
            
            if kg_real_total_bobina > self.kg_max_bobina:
                continue
            
            if kg_real_total_bobina < self.kg_min_bobina:
                continue
            
            cortes_prueba = []
            kg_total_asignado = 0
            valido = True
            
            for asig in combinacion['pedidos']:
                pedido = asig['pedido']
                kg_pendiente = pedidos_estado[pedido['id']]['kg_pendientes']
                
                if kg_pendiente <= 0:
                    valido = False
                    break
                
                ancho_corte_total = pedido['ancho'] * asig['num_cortes']
                kg_generado = ml_prueba * 2.73 * espesor * (ancho_corte_total / 1000)
                
                kg_asignar = min(kg_generado, kg_pendiente * (1 + self.margen_exceso_bobina_pct))
                
                if kg_asignar < 1:
                    valido = False
                    break
                
                kg_total_asignado += kg_asignar
                
                cortes_prueba.append({
                    'pedido_id': pedido['id'],
                    'num_cortes': asig['num_cortes'],
                    'ancho_corte': pedido['ancho'],
                    'ancho_usado': pedido['ancho'] * asig['num_cortes'],
                    'kg_asignados': kg_asignar,
                    'kg_generado': kg_generado
                })
            
            if not valido:
                continue
            
            if ml_prueba < ml_min_global:
                continue
            
            if kg_total_asignado < self.kg_min_bobina:
                continue
            
            if ml_mejor is None or kg_total_asignado > kg_total_mejor:
                ml_mejor = ml_prueba
                kg_total_mejor = kg_total_asignado
                kg_real_mejor = kg_real_total_bobina
                cortes_mejor = cortes_prueba
        
        if ml_mejor is None:
            if self.debug:
                print(f"      âŒ RECHAZADA: No se encontrÃ³ ML vÃ¡lido")
            return None
        
        # âœ… Limpiar campos de debug antes de crear la bobina final
        for corte in cortes_mejor:
            if 'kg_generado' in corte:
                del corte['kg_generado']
        
        bobina = {
            'desarrollo': desarrollo,
            'metros_lineales': ml_mejor,
            'kg_totales': kg_real_mejor,
            'desperdicio': combinacion['desperdicio'],
            'cortes': cortes_mejor
        }
        
        if not self._validar_integridad_bobina(bobina):
            if self.debug:
                print(f"      âŒ RECHAZADA: FallÃ³ validaciÃ³n de integridad")
            return None
        
        if self.debug:
            print(f"      âœ… ACEPTADA: ML={ml_mejor:.0f}ml, KG_real={kg_real_mejor:.0f}kg, KG_asignados={kg_total_mejor:.0f}kg")
        
        return bobina
    
    def _generar_solucion_inicial(self, seed=None, estrategia='balanceada'):
        """Genera soluciÃ³n inicial con diferentes estrategias"""
        if seed is not None:
            random.seed(seed)
        
        bobinas = []
        pedidos_estado = {p['id']: {'kg_pendientes': p['kg_solicitados']} for p in self.pedidos}
        desarrollos_disponibles = copy.deepcopy(self.desarrollos)
        
        if estrategia == 'priorizar_pequeÃ±os':
            desarrollos_disponibles.sort(key=lambda d: d['kg_disponibles'])
        elif estrategia == 'priorizar_grandes':
            desarrollos_disponibles.sort(key=lambda d: d['kg_disponibles'], reverse=True)
        elif estrategia == 'diversa':
            random.shuffle(desarrollos_disponibles)
        
        intento = 0
        indice_desarrollo = 0
        
        umbral_kg_pendiente = self.kg_min_bobina / 2
        
        while any(pedidos_estado[p['id']]['kg_pendientes'] > umbral_kg_pendiente for p in self.pedidos) and intento < self.max_intentos:
            intento += 1
            
            desarrollos_validos = [d for d in desarrollos_disponibles if d['kg_disponibles'] > umbral_kg_pendiente]
            if not desarrollos_validos:
                break
            
            if estrategia == 'balanceada':
                if intento % 3 == 0:
                    desarrollos_validos.sort(key=lambda d: d['ancho'], reverse=True)
                elif intento % 3 == 1:
                    desarrollos_validos.sort(key=lambda d: d['kg_disponibles'], reverse=True)
                else:
                    random.shuffle(desarrollos_validos)
                desarrollo_actual = desarrollos_validos[0]
            else:
                desarrollo_actual = desarrollos_validos[indice_desarrollo % len(desarrollos_validos)]
                indice_desarrollo += 1
            
            pedidos_compatibles = [
                p for p in self.pedidos
                if (p['aleacion'] == desarrollo_actual['aleacion'] and
                    p['estado'] == desarrollo_actual['estado'] and
                    abs(p['espesor'] - desarrollo_actual['espesor']) < 0.01 and
                    pedidos_estado[p['id']]['kg_pendientes'] > umbral_kg_pendiente)
            ]
            
            if not pedidos_compatibles:
                continue
            
            if self.debug:
                print(f"\nðŸ“ Ancho {desarrollo_actual['ancho']}mm - Pedidos: {len(pedidos_compatibles)}")
            
            clave_desarrollo = (desarrollo_actual['aleacion'], desarrollo_actual['estado'], 
                              desarrollo_actual['espesor'], desarrollo_actual['ancho'])
            
            if clave_desarrollo not in self.combinaciones_por_desarrollo:
                self.combinaciones_por_desarrollo[clave_desarrollo] = self._generar_combinaciones_corte(
                    desarrollo_actual, pedidos_compatibles
                )
            
            combinaciones = self.combinaciones_por_desarrollo[clave_desarrollo]
            combinaciones_validas = [
                c for c in combinaciones 
                if all(pedidos_estado[asig['pedido']['id']]['kg_pendientes'] > umbral_kg_pendiente 
                      for asig in c['pedidos'])
            ]
            
            if not combinaciones_validas:
                continue
            
            combinaciones_validas.sort(key=lambda c: (-len(c['pedidos']), c['desperdicio']))
            
            for combinacion in combinaciones_validas[:5]:
                bobina = self._crear_bobina_desde_combinacion(combinacion, desarrollo_actual, pedidos_estado)
                
                if bobina:
                    bobinas.append(bobina)
                    
                    for corte in bobina['cortes']:
                        pedidos_estado[corte['pedido_id']]['kg_pendientes'] -= corte['kg_asignados']
                    
                    desarrollo_actual['kg_disponibles'] -= bobina['kg_totales']
                    break
        
        return bobinas
    
    def _evaluar_solucion(self, bobinas):
        """EvalÃºa la calidad de una soluciÃ³n"""
        if not bobinas:
            return float('inf')
        
        num_bobinas = len(bobinas)
        desperdicio_total = sum(b['desperdicio'] for b in bobinas)
        kg_totales = sum(b['kg_totales'] for b in bobinas)
        
        penalizacion = num_bobinas * 1000 + desperdicio_total * 10
        
        kg_asignados_por_pedido = {}
        for bobina in bobinas:
            for corte in bobina['cortes']:
                pedido_id = corte['pedido_id']
                kg_asignados_por_pedido[pedido_id] = kg_asignados_por_pedido.get(pedido_id, 0) + corte['kg_asignados']
        
        for pedido in self.pedidos:
            kg_asignado = kg_asignados_por_pedido.get(pedido['id'], 0)
            kg_faltante = max(0, pedido['kg_solicitados'] - kg_asignado)
            if kg_faltante > 0:
                penalizacion += kg_faltante * 5
        
        return penalizacion
    
    def optimizar_con_progreso(self, num_intentos_por_estrategia=10, callback=None):
        """Optimiza con mÃºltiples estrategias y callback de progreso"""
        estrategias = ['balanceada', 'priorizar_grandes', 'priorizar_pequeÃ±os', 'diversa']
        mejor_solucion = None
        mejor_puntuacion = float('inf')
        
        total_intentos = len(estrategias) * num_intentos_por_estrategia
        intento_actual = 0
        
        for estrategia in estrategias:
            for i in range(num_intentos_por_estrategia):
                intento_actual += 1
                
                if callback:
                    progreso = intento_actual / total_intentos
                    callback(progreso, f"Estrategia: {estrategia} ({i+1}/{num_intentos_por_estrategia})")
                
                seed = random.randint(0, 100000)
                solucion = self._generar_solucion_inicial(seed=seed, estrategia=estrategia)
                
                if solucion:
                    puntuacion = self._evaluar_solucion(solucion)
                    if puntuacion < mejor_puntuacion:
                        mejor_puntuacion = puntuacion
                        mejor_solucion = solucion
        
        if callback:
            callback(1.0, "OptimizaciÃ³n completada")
        
        return mejor_solucion
    
    def formatear_resultados(self, bobinas):
        """Formatea los resultados para visualizaciÃ³n"""
        bobinas_formateadas = []
        
        for i, bobina in enumerate(bobinas, 1):
            desarrollo = bobina['desarrollo']
            bobina_formateada = {
                'bobina_num': i,
                'desarrollo': f"{desarrollo['ancho']}Ã—{desarrollo['espesor']}",
                'aleacion': desarrollo['aleacion'],
                'estado': desarrollo['estado'],
                'ancho_desarrollo': desarrollo['ancho'],
                'espesor': desarrollo['espesor'],
                'metros_lineales': bobina['metros_lineales'],
                'kg_totales': bobina['kg_totales'],
                'desperdicio': bobina['desperdicio'],
                'cortes': [
                    {
                        'pedido_id': c['pedido_id'],
                        'num_cortes': c['num_cortes'],
                        'ancho_corte': c['ancho_corte'],
                        'ancho_usado': c['ancho_usado'],
                        'kg_asignados': round(c['kg_asignados'], 2)
                    }
                    for c in bobina['cortes']
                ]
            }
            bobinas_formateadas.append(bobina_formateada)
        
        return bobinas_formateadas


def optimizar_por_desarrollo(df_desarrollos, df_pedidos, desperdicio_max=40, margen_exceso_pedidos=10, 
                            kg_max_bobina=4000, kg_min_bobina=200, max_intentos=200, 
                            margen_exceso_bobina=15, max_cortes_por_pedido=15, 
                            max_pedidos_por_bobina=6, intensidad_busqueda=50, callback_progreso=None):
    """FunciÃ³n principal de optimizaciÃ³n"""
    opt = OptimizadorBobinas(
        desperdicio_max=desperdicio_max,
        margen_exceso_pedidos=margen_exceso_pedidos,
        kg_max_bobina=kg_max_bobina,
        kg_min_bobina=kg_min_bobina,
        max_intentos=max_intentos,
        margen_exceso_bobina=margen_exceso_bobina,
        max_cortes_por_pedido=max_cortes_por_pedido,
        max_pedidos_por_bobina=max_pedidos_por_bobina,
        debug=True
    )
    opt.cargar_desarrollos(df_desarrollos)
    opt.cargar_pedidos(df_pedidos)
    
    num_intentos_por_estrategia = int(intensidad_busqueda * 3)
    
    bobinas = opt.optimizar_con_progreso(
        num_intentos_por_estrategia=num_intentos_por_estrategia,
        callback=callback_progreso
    )
    
    if not bobinas:
        return pd.DataFrame()
    
    filas = []
    bobinas_formateadas = opt.formatear_resultados(bobinas)
    
    for bobina in bobinas_formateadas:
        ancho_usado_total = sum(c['ancho_usado'] for c in bobina['cortes'])
        
        if ancho_usado_total > bobina['ancho_desarrollo']:
            print(f"âš ï¸ ERROR DETECTADO en Bobina_{bobina['bobina_num']}:")
            print(f"   Desarrollo: {bobina['ancho_desarrollo']}mm")
            print(f"   Ancho usado: {ancho_usado_total}mm")
            for c in bobina['cortes']:
                print(f"   - {c['num_cortes']}Ã—{c['ancho_corte']}mm = {c['ancho_usado']}mm (Pedido: {c['pedido_id']})")
        
        for i, corte in enumerate(bobina['cortes']):
            ml_bobina = bobina['metros_lineales']
            espesor_bobina = bobina['espesor']
            num_cortes = corte['num_cortes']
            ancho_corte = corte['ancho_corte']
            
            kg_calculado = ml_bobina * 2.73 * espesor_bobina * ((num_cortes * ancho_corte) / 1000)
            kg_asignado = corte['kg_asignados']
            diferencia = kg_asignado - kg_calculado
            
            filas.append({
                'BOBINA': f"Bobina_{bobina['bobina_num']}",
                'DESARROLLO': bobina['desarrollo'],
                'PEDIDO': corte['pedido_id'],
                'NUM_CORTES': corte['num_cortes'],
                'ANCHO_CORTE': corte['ancho_corte'],
                'METROS_LINEALES': bobina['metros_lineales'],
                'KG_ASIGNADOS': corte['kg_asignados'],
                'ANCHO_USADO': ancho_usado_total if i == 0 else '',
                'ANCHO_DESARROLLO': bobina['ancho_desarrollo'],
                'DESPERDICIO': bobina['desperdicio'],
                'KG_CALCULADO_FORMULA': round(kg_calculado, 2),
                'DIFERENCIA': round(diferencia, 2)
            })
    
    return pd.DataFrame(filas)