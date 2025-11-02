"""
🔍 OPTIMIZADOR DE PARÁMETROS ILP - VERSIÓN MEJORADA
Encuentra los mejores parámetros usando análisis inteligente + pruebas rápidas
"""

import pandas as pd
import sys
from itertools import product
from typing import Dict, List, Tuple, Optional
import time

sys.path.insert(0, '/mnt/user-data/uploads')
from optimizador_ilp_v2 import optimizar_ilp


def sugerir_parametros_iniciales(df_desarrollos: pd.DataFrame, 
                                 df_pedidos: pd.DataFrame) -> Dict:
    """
    Sugiere parámetros óptimos usando análisis inteligente.
    
    ESTRATEGIA:
    1. Analiza los datos (anchos, kg, distribución)
    2. Calcula parámetros conservadores (objetivo: 4 bobinas)
    3. Prioriza: minimizar bobinas > reducir desperdicio > cumplimiento exacto
    """
    
    # ============================================
    # ANÁLISIS DE DATOS
    # ============================================
    anchos_desarrollos = df_desarrollos['ANCHO'].tolist()
    anchos_pedidos = df_pedidos['ANCHO'].tolist()
    
    ancho_min_desarrollo = min(anchos_desarrollos)
    ancho_max_desarrollo = max(anchos_desarrollos)
    ancho_min_pedido = min(anchos_pedidos)
    ancho_max_pedido = max(anchos_pedidos)
    
    kg_total_pedidos = df_pedidos['KG'].sum()
    kg_total_desarrollos = df_desarrollos['KG'].sum()
    ratio_demanda = kg_total_pedidos / kg_total_desarrollos
    
    num_pedidos = len(df_pedidos)
    num_desarrollos = len(df_desarrollos)
    
    # Calcular diversidad de anchos
    anchos_unicos = len(set(anchos_pedidos))
    
    # ============================================
    # LÓGICA DE SUGERENCIA INTELIGENTE
    # ============================================
    
    # 1. DESPERDICIO MÍNIMO
    # Basado en el ancho más pequeño - necesitamos margen de seguridad
    if ancho_min_pedido < 150:
        desperdicio_min = 5
    elif ancho_min_pedido < 200:
        desperdicio_min = 8
    else:
        desperdicio_min = 10
    
    # 2. DESPERDICIO MÁXIMO
    # CLAVE: Ser conservador para forzar buenas combinaciones
    # Referencia humana: máx 34.4mm
    # Fórmula: 3% del ancho mayor (no 5%)
    desperdicio_max_calculado = int(ancho_max_desarrollo * 0.03)
    
    # Ajustar según diversidad de anchos
    if anchos_unicos >= 5:
        # Muchos anchos diferentes = necesita más flexibilidad
        desperdicio_max = max(40, min(desperdicio_max_calculado, 50))
    elif anchos_unicos >= 3:
        # Anchos moderados
        desperdicio_max = max(35, min(desperdicio_max_calculado, 42))
    else:
        # Pocos anchos = puede ser más estricto
        desperdicio_max = max(30, min(desperdicio_max_calculado, 38))
    
    # 3. MARGEN EXCESO
    # CLAVE: Ser estricto (humano: 8.3% máx)
    # Ajustar según ratio de demanda
    if ratio_demanda > 0.95:
        # Material muy justo = necesita flexibilidad
        margen_exceso = 25
    elif ratio_demanda > 0.85:
        # Material ajustado
        margen_exceso = 20
    else:
        # Material suficiente = ser estricto
        margen_exceso = 15
    
    # 4. COBERTURA MÍNIMA
    # CLAVE: Alta para forzar buen cumplimiento
    # Pero no tan alta que fuerce 5 bobinas
    if ratio_demanda > 0.95:
        cobertura = 87  # Más flexible si material escaso
    elif ratio_demanda > 0.85:
        cobertura = 90  # Balance
    else:
        cobertura = 92  # Estricto si hay material
    
    # 5. PENALIZACIÓN DESPERDICIO
    # CLAVE: Moderada-alta para reducir desperdicio
    # Pero no tan alta que fuerce soluciones con más bobinas
    if num_pedidos <= 5:
        penalizacion = 0.02  # Casos pequeños: poco impacto
    elif num_pedidos <= 10:
        penalizacion = 0.03  # Balance
    else:
        penalizacion = 0.04  # Muchos pedidos: penalizar más
    
    # 6. ML MÍNIMO RESTO
    # Conservador
    ml_resto = 600
    
    # 7. RELAJACIÓN ML
    # Moderada
    relajacion_ml = 40
    
    # ============================================
    # CONSTRUIR JUSTIFICACIÓN
    # ============================================
    justificacion = {
        'desperdicio_min': f"Desperdicio mínimo {desperdicio_min}mm para margen de seguridad (ancho mín: {ancho_min_pedido:.0f}mm)",
        'desperdicio_max': f"Desperdicio máximo {desperdicio_max}mm (3% de {ancho_max_desarrollo:.0f}mm, {anchos_unicos} anchos diferentes)",
        'margen_exceso': f"Exceso máx {margen_exceso}% (ratio demanda: {ratio_demanda:.1%})",
        'cobertura': f"Cobertura {cobertura}% para balance entre cumplimiento y eficiencia",
        'penalizacion': f"Penalización {penalizacion} para reducir desperdicio sin forzar más bobinas",
        'ml_resto': f"ML resto {ml_resto}ml para uso eficiente de material",
        'relajacion': f"Relajación ML {relajacion_ml}% para flexibilidad moderada"
    }
    
    return {
        'desperdicio_bordes_minimo': desperdicio_min,
        'desperdicio_bordes_maximo': desperdicio_max,
        'margen_exceso': margen_exceso,
        'ml_minimo_resto': ml_resto,
        'margen_cobertura_pct': cobertura,
        'relajacion_ml_pct': relajacion_ml,
        'factor_penalizacion': penalizacion,
        'kg_max_bobina': 7500,
        'kg_min_bobina': 200,
        'max_cortes_por_pedido': 15,
        'justificacion': justificacion
    }


class OptimizadorParametros:
    """
    Busca los mejores parámetros del ILP para un conjunto de datos específico
    """
    
    def __init__(self, df_desarrollos: pd.DataFrame, df_pedidos: pd.DataFrame):
        self.df_desarrollos = df_desarrollos
        self.df_pedidos = df_pedidos
        self.resultados = []
        
    def analizar_datos(self) -> Dict:
        """
        Analiza los datos de entrada para sugerir rangos de parámetros
        """
        # Analizar anchos
        anchos_desarrollos = self.df_desarrollos['ANCHO'].tolist()
        anchos_pedidos = self.df_pedidos['ANCHO'].tolist()
        
        ancho_min_desarrollo = min(anchos_desarrollos)
        ancho_max_desarrollo = max(anchos_desarrollos)
        ancho_min_pedido = min(anchos_pedidos)
        ancho_max_pedido = max(anchos_pedidos)
        
        # Calcular desperdicio típico
        desperdicio_teorico_min = ancho_min_pedido * 0.05  # 5% del ancho más pequeño
        desperdicio_teorico_max = ancho_max_desarrollo * 0.05  # 5% del ancho mayor
        
        # Analizar kg
        kg_total_pedidos = self.df_pedidos['KG'].sum()
        kg_total_desarrollos = self.df_desarrollos['KG'].sum()
        kg_promedio_pedido = self.df_pedidos['KG'].mean()
        
        # Sugerencias basadas en datos
        analisis = {
            'ancho_min_desarrollo': ancho_min_desarrollo,
            'ancho_max_desarrollo': ancho_max_desarrollo,
            'ancho_min_pedido': ancho_min_pedido,
            'ancho_max_pedido': ancho_max_pedido,
            'desperdicio_sugerido_min': max(5, int(desperdicio_teorico_min)),
            'desperdicio_sugerido_max': min(100, int(desperdicio_teorico_max)),
            'kg_total_pedidos': kg_total_pedidos,
            'kg_total_desarrollos': kg_total_desarrollos,
            'kg_promedio_pedido': kg_promedio_pedido,
            'num_pedidos': len(self.df_pedidos),
            'num_desarrollos': len(self.df_desarrollos),
            'ratio_demanda': kg_total_pedidos / kg_total_desarrollos if kg_total_desarrollos > 0 else 0
        }
        
        return analisis
    
    def buscar_parametros_optimos(self, 
                                   modo: str = 'rapido',
                                   callback=None) -> Dict:
        """
        Busca los mejores parámetros
        
        Modos:
        - 'rapido': Pocas combinaciones (~16 pruebas)
        - 'completo': Más combinaciones (~192 pruebas)
        """
        analisis = self.analizar_datos()
        
        print("="*80)
        print("🔍 OPTIMIZADOR DE PARÁMETROS ILP")
        print("="*80)
        print()
        print("📊 Análisis de datos:")
        print(f"   - Desarrollos: {analisis['num_desarrollos']}")
        print(f"   - Pedidos: {analisis['num_pedidos']}")
        print(f"   - Kg solicitados: {analisis['kg_total_pedidos']:.0f}kg")
        print(f"   - Kg disponibles: {analisis['kg_total_desarrollos']:.0f}kg")
        print(f"   - Ratio demanda: {analisis['ratio_demanda']:.1%}")
        print()
        
        # Definir rangos de búsqueda según modo
        if modo == 'rapido':
            rangos = {
                'desperdicio_min': [5, 10],
                'desperdicio_max': [35, 42, 50],
                'margen_exceso': [1.15, 1.20, 1.30],  # 15%, 20%, 30%
                'ml_minimo_resto': [600],
                'margen_cobertura': [0.90, 0.92],  # 90%, 92%
                'relajacion_ml_pct': [40],
                'factor_penalizacion': [0.02, 0.03],
            }
            total_combinaciones = 2 * 3 * 3 * 1 * 2 * 1 * 2  # 72
            
        else:  # completo
            rangos = {
                'desperdicio_min': [5, 8, 10],
                'desperdicio_max': [32, 38, 42, 50],
                'margen_exceso': [1.10, 1.15, 1.20, 1.30],  # 10%, 15%, 20%, 30%
                'ml_minimo_resto': [600],
                'margen_cobertura': [0.87, 0.90, 0.92, 0.95],  # 87%, 90%, 92%, 95%
                'relajacion_ml_pct': [30, 40, 50],
                'factor_penalizacion': [0.01, 0.02, 0.03, 0.05],
            }
            total_combinaciones = 3 * 4 * 4 * 1 * 4 * 3 * 4  # 2304
        
        print(f"🔧 Modo: {modo.upper()}")
        print(f"📝 Combinaciones a probar: {total_combinaciones}")
        print()
        print("⏳ Iniciando búsqueda...")
        print()
        
        # Parámetros fijos (no varían en la búsqueda)
        parametros_fijos = {
            'kg_max_bobina': 7500,
            'kg_min_bobina': 200,
            'max_cortes_por_pedido': 15,
            'tiempo_max_segundos': 60,  # Reducido para búsqueda rápida
            'debug': False
        }
        
        # Generar todas las combinaciones
        combinaciones = list(product(
            rangos['desperdicio_min'],
            rangos['desperdicio_max'],
            rangos['margen_exceso'],
            rangos['ml_minimo_resto'],
            rangos['margen_cobertura'],
            rangos['relajacion_ml_pct'],
            rangos['factor_penalizacion']
        ))
        
        mejor_resultado = None
        mejor_puntuacion = float('inf')
        
        for idx, (desp_min, desp_max, margen, ml_resto, cobertura, relajacion_ml, penalizacion) in enumerate(combinaciones, 1):
            # Validar que min < max
            if desp_min >= desp_max:
                continue
            
            if callback:
                callback(idx / len(combinaciones), f"Probando {idx}/{len(combinaciones)}")
            
            try:
                # Ejecutar ILP con estos parámetros
                inicio = time.time()
                
                soluciones = optimizar_ilp(
                    self.df_desarrollos,
                    self.df_pedidos,
                    desperdicio_bordes_minimo=desp_min,
                    desperdicio_bordes_maximo=desp_max,
                    margen_exceso=margen,
                    ml_minimo_resto=ml_resto,
                    margen_cobertura=cobertura,
                    margen_tolerancia_ml_pct=relajacion_ml,
                    factor_penalizacion_desperdicio=penalizacion,
                    **parametros_fijos
                )
                
                tiempo_ejecucion = time.time() - inicio
                
                if soluciones and len(soluciones) > 0:
                    solucion = soluciones[0]
                    df_resultado = solucion['dataframe']
                    
                    num_bobinas = len(df_resultado['BOBINA'].unique())
                    desperdicio_total = df_resultado.groupby('BOBINA')['DESPERDICIO'].first().sum()
                    
                    # Verificar cobertura
                    kg_asignados_por_pedido = df_resultado.groupby('PEDIDO')['KG_ASIGNADOS'].sum()
                    kg_solicitados = self.df_pedidos.set_index('PEDIDO')['KG']
                    
                    cobertura_min = 100
                    for pedido_id in self.df_pedidos['PEDIDO']:
                        kg_asignado = kg_asignados_por_pedido.get(pedido_id, 0)
                        kg_solicitado = kg_solicitados.get(pedido_id, 0)
                        cobertura_pct = (kg_asignado / kg_solicitado * 100) if kg_solicitado > 0 else 0
                        cobertura_min = min(cobertura_min, cobertura_pct)
                    
                    # Puntuación (menor es mejor)
                    # Prioridad 1: Minimizar bobinas (peso 10000)
                    # Prioridad 2: Minimizar desperdicio (peso 1)
                    puntuacion = num_bobinas * 10000 + desperdicio_total
                    
                    resultado = {
                        'desperdicio_min': desp_min,
                        'desperdicio_max': desp_max,
                        'margen_exceso_pct': int((margen - 1) * 100),
                        'ml_minimo_resto': ml_resto,
                        'margen_cobertura_pct': int(cobertura * 100),
                        'relajacion_ml_pct': int(relajacion_ml),
                        'factor_penalizacion': penalizacion,
                        'num_bobinas': num_bobinas,
                        'desperdicio_total': desperdicio_total,
                        'cobertura_min': cobertura_min,
                        'puntuacion': puntuacion,
                        'tiempo': tiempo_ejecucion,
                        'valido': cobertura_min >= 85  # Mínimo 85% de cobertura
                    }
                    
                    self.resultados.append(resultado)
                    
                    # Actualizar mejor resultado (solo si cumple cobertura)
                    if resultado['valido'] and puntuacion < mejor_puntuacion:
                        mejor_puntuacion = puntuacion
                        mejor_resultado = resultado
                        
                        print(f"✨ Nuevo mejor: {num_bobinas} bobinas, {desperdicio_total:.1f}mm desperdicio")
                        print(f"   Parámetros: desp={desp_min}-{desp_max}mm, exceso={int((margen-1)*100)}%, penalización={penalizacion}")
                        print()
                
            except Exception as e:
                # Ignorar errores y continuar
                pass
        
        if callback:
            callback(1.0, "Búsqueda completada")
        
        return self._formatear_resultados(mejor_resultado)
    
    def _formatear_resultados(self, mejor: Dict) -> Dict:
        """Formatea los resultados para mostrar al usuario"""
        
        print()
        print("="*80)
        print("✅ BÚSQUEDA COMPLETADA")
        print("="*80)
        print()
        
        if mejor is None:
            print("❌ No se encontró ninguna configuración válida")
            return None
        
        print("🏆 MEJORES PARÁMETROS ENCONTRADOS:")
        print()
        print(f"   Desperdicio bordes: {mejor['desperdicio_min']}-{mejor['desperdicio_max']}mm")
        print(f"   Margen exceso pedidos: {mejor['margen_exceso_pct']}%")
        print(f"   ML mínimo resto: {mejor['ml_minimo_resto']}ml")
        print(f"   Cobertura: {mejor['margen_cobertura_pct']}%")
        print(f"   Penalización: {mejor['factor_penalizacion']}")
        print()
        print(f"📊 RESULTADO:")
        print(f"   ✅ Bobinas: {mejor['num_bobinas']}")
        print(f"   ✅ Desperdicio total: {mejor['desperdicio_total']:.1f}mm")
        print(f"   ✅ Cobertura mínima: {mejor['cobertura_min']:.1f}%")
        print(f"   ⏱️  Tiempo: {mejor['tiempo']:.2f}s")
        print()
        
        # Top 5 alternativas
        print("="*80)
        print("📋 TOP 5 CONFIGURACIONES:")
        print("="*80)
        print()
        
        # Ordenar por puntuación
        top5 = sorted([r for r in self.resultados if r['valido']], 
                     key=lambda x: x['puntuacion'])[:5]
        
        for idx, resultado in enumerate(top5, 1):
            print(f"{idx}. {resultado['num_bobinas']} bobinas, {resultado['desperdicio_total']:.1f}mm")
            print(f"   desp={resultado['desperdicio_min']}-{resultado['desperdicio_max']}mm, "
                  f"exceso={resultado['margen_exceso_pct']}%, penalización={resultado['factor_penalizacion']}")
            print()
        
        return {
            'mejor': mejor,
            'top5': top5,
            'todos': self.resultados
        }