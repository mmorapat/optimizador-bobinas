"""
🔬 OPTIMIZADOR ILP V3 - MEJORADO
Genera MÁS configuraciones y usa objetivo correcto
"""

import pandas as pd
from pulp import *
from typing import List, Dict
import time
import hashlib


def optimizar_ilp(df_desarrollos: pd.DataFrame,
                 df_pedidos: pd.DataFrame,
                 desperdicio_bordes_minimo: int = 0,
                 desperdicio_bordes_maximo: int = 60,
                 kg_max_bobina: int = 7500,
                 kg_min_bobina: int = 200,
                 max_cortes_por_pedido: int = 15,
                 margen_cobertura: float = 0.95,
                 margen_exceso: float = 1.15,
                 margen_tolerancia_ml_pct: float = 10.0,
                 ml_minimo_resto: int = 300,
                 tiempo_max_segundos: int = 300,
                 factor_penalizacion_desperdicio: float = 0.01,
                 debug: bool = True) -> List[Dict]:
    """
    Optimizador ILP mejorado - genera MÁS configuraciones
    """
    
    if debug:
        print(f"\n{'='*80}")
        print(f"🔬 OPTIMIZADOR ILP V3 - MEJORADO")
        print(f"{'='*80}\n")
    
    # Cargar datos
    desarrollos = []
    for idx, row in df_desarrollos.iterrows():
        desarrollos.append({
            'id': f"des_{idx}",
            'ancho': float(row['ANCHO']),
            'espesor': float(row['ESPESOR']),
            'aleacion': str(row['ALEACION']),
            'estado': str(row['ESTADO']),
            'kg_disponibles': float(row['KG'])
        })
    
    pedidos = []
    for _, row in df_pedidos.iterrows():
        pedidos.append({
            'id': str(row['PEDIDO']),
            'ancho': float(row['ANCHO']),
            'kg_solicitados': float(row['KG']),
            'aleacion': str(row['ALEACION']),
            'estado': str(row['ESTADO']),
            'espesor': float(row['ESPESOR']),
            'ml_minimos': float(row['ML']) if 'ML' in row and pd.notna(row['ML']) else 0
        })
    
    if debug:
        print(f"📊 Desarrollos: {len(desarrollos)}")
        print(f"📊 Pedidos: {len(pedidos)}")
        print(f"📊 Desperdicio máx: {desperdicio_bordes_maximo}mm")
        print(f"📊 KG máx bobina: {kg_max_bobina}kg")
        print()
    
    # ============================================
    # GENERAR MUCHAS MÁS CONFIGURACIONES
    # ============================================
    
    if debug:
        print(f"🎲 Generando configuraciones (VERSIÓN AMPLIADA)...")
    
    bobinas_candidatas = []
    id_bobina = 0
    
    for desarrollo in desarrollos:
        pedidos_compatibles = [
            p for p in pedidos
            if (p['espesor'] == desarrollo['espesor'] and
                p['aleacion'] == desarrollo['aleacion'] and
                p['estado'] == desarrollo['estado'] and
                p['ancho'] <= desarrollo['ancho'])
        ]
        
        if not pedidos_compatibles:
            continue
        
        # ML máximo para este desarrollo
        constante_kg_des = 2.73 * desarrollo['espesor'] * (desarrollo['ancho'] / 1000)
        ml_max = kg_max_bobina / constante_kg_des
        
        # ===== 1 PEDIDO =====
        for pedido in pedidos_compatibles:
            max_cortes = int(desarrollo['ancho'] // pedido['ancho'])
            
            for num_cortes in range(1, min(max_cortes + 1, max_cortes_por_pedido + 1)):
                ancho_usado = num_cortes * pedido['ancho']
                desperdicio = desarrollo['ancho'] - ancho_usado
                
                if desperdicio_bordes_minimo <= desperdicio <= desperdicio_bordes_maximo:
                    id_bobina += 1
                    ancho_corte = num_cortes * pedido['ancho']
                    constante_pedido = 2.73 * desarrollo['espesor'] * (ancho_corte / 1000)
                    kg_asignado = ml_max * constante_pedido
                    kg_total_bobina = ml_max * constante_kg_des
                    
                    config_str = f"{desarrollo['ancho']}x{desarrollo['espesor']}|{num_cortes}x{pedido['ancho']}"
                    config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]
                    
                    bobinas_candidatas.append({
                        'id': f"bob_{id_bobina}",
                        'desarrollo_id': desarrollo['id'],
                        'desarrollo': desarrollo,
                        'cortes': {pedido['id']: num_cortes},
                        'ancho_usado': ancho_usado,
                        'desperdicio': desperdicio,
                        'metros_lineales': ml_max,
                        'kg_totales': kg_total_bobina,
                        'kg_por_pedido': {pedido['id']: kg_asignado},
                        'config_hash': config_hash
                    })
        
        # ===== 2 PEDIDOS (MÁS ITERACIONES) =====
        for i, pedido1 in enumerate(pedidos_compatibles):
            for pedido2 in pedidos_compatibles[i+1:]:
                # AUMENTADO: hasta 10 cortes por pedido
                for n1 in range(1, min(11, max_cortes_por_pedido + 1)):
                    for n2 in range(1, min(11, max_cortes_por_pedido + 1)):
                        ancho_usado = n1 * pedido1['ancho'] + n2 * pedido2['ancho']
                        
                        if ancho_usado <= desarrollo['ancho']:
                            desperdicio = desarrollo['ancho'] - ancho_usado
                            
                            if desperdicio_bordes_minimo <= desperdicio <= desperdicio_bordes_maximo:
                                id_bobina += 1
                                kg_total_bobina = ml_max * constante_kg_des
                                ancho1 = n1 * pedido1['ancho']
                                ancho2 = n2 * pedido2['ancho']
                                const1 = 2.73 * desarrollo['espesor'] * (ancho1 / 1000)
                                const2 = 2.73 * desarrollo['espesor'] * (ancho2 / 1000)
                                
                                config_str = f"{desarrollo['ancho']}x{desarrollo['espesor']}|{n1}x{pedido1['ancho']}+{n2}x{pedido2['ancho']}"
                                config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]
                                
                                bobinas_candidatas.append({
                                    'id': f"bob_{id_bobina}",
                                    'desarrollo_id': desarrollo['id'],
                                    'desarrollo': desarrollo,
                                    'cortes': {pedido1['id']: n1, pedido2['id']: n2},
                                    'ancho_usado': ancho_usado,
                                    'desperdicio': desperdicio,
                                    'metros_lineales': ml_max,
                                    'kg_totales': kg_total_bobina,
                                    'kg_por_pedido': {
                                        pedido1['id']: ml_max * const1,
                                        pedido2['id']: ml_max * const2
                                    },
                                    'config_hash': config_hash
                                })
        
        # ===== 3 PEDIDOS (MUCHAS MÁS ITERACIONES) =====
        for i, pedido1 in enumerate(pedidos_compatibles):
            for j, pedido2 in enumerate(pedidos_compatibles[i+1:], i+1):
                for pedido3 in pedidos_compatibles[j+1:]:
                    # AUMENTADO: más iteraciones para generar configs como el humano
                    for n1 in range(1, min(11, max_cortes_por_pedido + 1)):
                        for n2 in range(1, min(9, max_cortes_por_pedido + 1)):
                            for n3 in range(1, min(9, max_cortes_por_pedido + 1)):
                                ancho_usado = (n1 * pedido1['ancho'] + 
                                             n2 * pedido2['ancho'] + 
                                             n3 * pedido3['ancho'])
                                
                                if ancho_usado <= desarrollo['ancho']:
                                    desperdicio = desarrollo['ancho'] - ancho_usado
                                    
                                    if desperdicio_bordes_minimo <= desperdicio <= desperdicio_bordes_maximo:
                                        id_bobina += 1
                                        kg_total_bobina = ml_max * constante_kg_des
                                        ancho1 = n1 * pedido1['ancho']
                                        ancho2 = n2 * pedido2['ancho']
                                        ancho3 = n3 * pedido3['ancho']
                                        const1 = 2.73 * desarrollo['espesor'] * (ancho1 / 1000)
                                        const2 = 2.73 * desarrollo['espesor'] * (ancho2 / 1000)
                                        const3 = 2.73 * desarrollo['espesor'] * (ancho3 / 1000)
                                        
                                        config_str = f"{desarrollo['ancho']}x{desarrollo['espesor']}|{n1}x{pedido1['ancho']}+{n2}x{pedido2['ancho']}+{n3}x{pedido3['ancho']}"
                                        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]
                                        
                                        bobinas_candidatas.append({
                                            'id': f"bob_{id_bobina}",
                                            'desarrollo_id': desarrollo['id'],
                                            'desarrollo': desarrollo,
                                            'cortes': {pedido1['id']: n1, pedido2['id']: n2, pedido3['id']: n3},
                                            'ancho_usado': ancho_usado,
                                            'desperdicio': desperdicio,
                                            'metros_lineales': ml_max,
                                            'kg_totales': kg_total_bobina,
                                            'kg_por_pedido': {
                                                pedido1['id']: ml_max * const1,
                                                pedido2['id']: ml_max * const2,
                                                pedido3['id']: ml_max * const3
                                            },
                                            'config_hash': config_hash
                                        })
    
    if debug:
        print(f"✅ Configuraciones generadas: {len(bobinas_candidatas)}")
        configs_unicas = len(set(b['config_hash'] for b in bobinas_candidatas))
        print(f"🎯 Patrones únicos: {configs_unicas}")
        print()
    
    # ============================================
    # CREAR MODELO ILP CON OBJETIVO CORRECTO
    # ============================================
    
    if debug:
        print(f"🔨 Creando modelo ILP...")
    
    problema = LpProblem("Minimizar_Bobinas", LpMinimize)
    
    y = {}
    ml = {}
    for bobina in bobinas_candidatas:
        y[bobina['id']] = LpVariable(f"y_{bobina['id']}", cat='Binary')
        ml[bobina['id']] = LpVariable(f"ml_{bobina['id']}", lowBound=0, upBound=bobina['metros_lineales'])
    
    # ===== OBJETIVO CORRECTO =====
    objetivo = 0
    
    # PRIORIDAD 1: Minimizar bobinas (peso: 1000)
    objetivo += 1000 * lpSum([y[b['id']] for b in bobinas_candidatas])
    
    # PRIORIDAD 2: Maximizar ML total (peso: -1)
    ml_total = lpSum([ml[b['id']] for b in bobinas_candidatas])
    objetivo += -1.0 * ml_total
    
    # PRIORIDAD 3: Minimizar desperdicio (peso configurable)
    if factor_penalizacion_desperdicio > 0:
        for b in bobinas_candidatas:
            objetivo += factor_penalizacion_desperdicio * b['desperdicio'] * y[b['id']]
    
    if debug:
        print(f"   🎯 OBJETIVO:")
        print(f"      1. Minimizar bobinas (peso: 1000)")
        print(f"      2. Maximizar ML total (peso: -1)")
        print(f"      3. Minimizar desperdicio (peso: {factor_penalizacion_desperdicio})")
    
    problema += objetivo, "Minimizar_Bobinas_Maximizar_ML"
    
    # ===== RESTRICCIONES =====
    
    # 1. Vincular ML con y
    for bobina in bobinas_candidatas:
        problema += (ml[bobina['id']] <= bobina['metros_lineales'] * y[bobina['id']], f"ML_Max_{bobina['id']}")
    
    # 2. Cobertura mínima
    for pedido in pedidos:
        kg_asignados = lpSum([
            (ml[b['id']] / b['metros_lineales']) * b['kg_por_pedido'].get(pedido['id'], 0)
            for b in bobinas_candidatas
            if pedido['id'] in b['kg_por_pedido']
        ])
        kg_minimo = pedido['kg_solicitados'] * margen_cobertura
        problema += (kg_asignados >= kg_minimo, f"Cob_Min_{pedido['id']}")
    
    # 3. Exceso máximo
    for pedido in pedidos:
        kg_asignados = lpSum([
            (ml[b['id']] / b['metros_lineales']) * b['kg_por_pedido'].get(pedido['id'], 0)
            for b in bobinas_candidatas
            if pedido['id'] in b['kg_por_pedido']
        ])
        kg_maximo = pedido['kg_solicitados'] * margen_exceso
        problema += (kg_asignados <= kg_maximo, f"Exc_Max_{pedido['id']}")
    
    # 4. Material disponible
    for desarrollo in desarrollos:
        kg_usados = lpSum([
            (ml[b['id']] / b['metros_lineales']) * b['kg_totales']
            for b in bobinas_candidatas
            if b['desarrollo_id'] == desarrollo['id']
        ])
        problema += (kg_usados <= desarrollo['kg_disponibles'], f"Mat_{desarrollo['id']}")
    
    if debug:
        print(f"✅ Modelo creado")
        print()
    
    # ============================================
    # RESOLVER
    # ============================================
    
    if debug:
        print(f"⚡ Resolviendo...")
    
    inicio = time.time()
    estado = problema.solve(PULP_CBC_CMD(timeLimit=tiempo_max_segundos, msg=0))
    tiempo_resolucion = time.time() - inicio
    
    if debug:
        print(f"⏱️  Tiempo: {tiempo_resolucion:.2f}s")
        print(f"📊 Estado: {LpStatus[estado]}")
        print()
    
    if estado != LpStatusOptimal:
        if debug:
            print(f"❌ No se encontró solución óptima")
        return []
    
    # ============================================
    # EXTRAER SOLUCIÓN
    # ============================================
    
    bobinas_usadas = []
    configs_usadas = set()
    
    for bobina in bobinas_candidatas:
        if value(y[bobina['id']]) and value(y[bobina['id']]) > 0.5:
            ml_valor = value(ml[bobina['id']])
            
            if ml_valor and ml_valor > 10:
                factor = ml_valor / bobina['metros_lineales']
                
                bobina_usada = {
                    'desarrollo': bobina['desarrollo'],
                    'cortes': bobina['cortes'],
                    'metros_lineales': ml_valor,
                    'kg_totales': bobina['kg_totales'] * factor,
                    'kg_por_pedido': {pid: kg * factor for pid, kg in bobina['kg_por_pedido'].items()},
                    'desperdicio': bobina['desperdicio'],
                    'config_hash': bobina['config_hash']
                }
                
                bobinas_usadas.append(bobina_usada)
                configs_usadas.add(bobina['config_hash'])
    
    if debug:
        print(f"✅ SOLUCIÓN ENCONTRADA")
        print(f"🏆 Configuraciones distintas: {len(configs_usadas)}")
        print(f"📦 Bobinas totales: {len(bobinas_usadas)}")
        print()
    
    # Formatear resultado
    filas = []
    for i, bobina in enumerate(bobinas_usadas, 1):
        desarrollo = bobina['desarrollo']
        desarrollo_str = f"{desarrollo['ancho']}×{desarrollo['espesor']}"
        
        for pedido_id, num_cortes in bobina['cortes'].items():
            pedido = next(p for p in pedidos if p['id'] == pedido_id)
            
            filas.append({
                'BOBINA': f"Bobina_{i}",
                'DESARROLLO': desarrollo_str,
                'PEDIDO': pedido_id,
                'NUM_CORTES': num_cortes,
                'ANCHO_CORTE': pedido['ancho'],
                'METROS_LINEALES': round(bobina['metros_lineales'], 2),
                'KG_ASIGNADOS': round(bobina['kg_por_pedido'][pedido_id], 2),
                'KG_TOTALES_BOBINA': round(bobina['kg_totales'], 2),
                'ANCHO_DESARROLLO': desarrollo['ancho'],
                'DESPERDICIO': round(bobina['desperdicio'], 2)
            })
    
    df_resultado = pd.DataFrame(filas)
    desperdicio_total = sum(b['desperdicio'] for b in bobinas_usadas)
    kg_totales = sum(b['kg_totales'] for b in bobinas_usadas)
    
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
    
    return [{
        'nombre': 'Solución ILP V3 Mejorado',
        'num_bobinas': len(bobinas_usadas),
        'num_configuraciones': len(configs_usadas),
        'dataframe': df_resultado,
        'desperdicio_total': desperdicio_total,
        'kg_totales': kg_totales,
        'cobertura': cobertura,
        'es_valido': all(c['cubierto'] for c in cobertura.values()),
        'tiempo_resolucion': tiempo_resolucion
    }]