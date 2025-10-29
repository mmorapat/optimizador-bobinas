"""
🔍 OPTIMIZADOR DE PARÁMETROS ILP
Encuentra la mejor configuración de parámetros para minimizar bobinas y desperdicio
"""

import pandas as pd
import sys
from itertools import product
from typing import Dict, List, Tuple
import time

sys.path.insert(0, '/mnt/user-data/uploads')
from optimizador_ilp_v2 import optimizar_ilp


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
        - 'rapido': Pocas combinaciones (~10-20 pruebas)
        - 'completo': Más combinaciones (~50-100 pruebas)
        - 'exhaustivo': Todas las combinaciones (~200+ pruebas)
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
                'desperdicio_min': [0, 8],
                'desperdicio_max': [40, 70],
                'margen_exceso': [1.30, 1.50, 2.00],  # 30%, 50%, 100%
                'ml_minimo_resto': [0, 600],
                'margen_cobertura': [0.90, 0.95],  # 90%, 95%
                'relajacion_ml_pct': [30, 50, 80],  # 30%, 50%, 80%
                'factor_penalizacion': [0.01, 0.05],
            }
            total_combinaciones = 2 * 2 * 3 * 2 * 2 * 3 * 2  # 288
            
        elif modo == 'completo':
            rangos = {
                'desperdicio_min': [0, 5, 8],
                'desperdicio_max': [30, 50, 70, 100],
                'margen_exceso': [1.20, 1.30, 1.50, 2.00],  # 20%, 30%, 50%, 100%
                'ml_minimo_resto': [0, 300, 600],
                'margen_cobertura': [0.85, 0.90, 0.95],  # 85%, 90%, 95%
                'relajacion_ml_pct': [30, 50, 70, 90],  # 30%, 50%, 70%, 90%
                'factor_penalizacion': [0.01, 0.03, 0.05],
            }
            total_combinaciones = 3 * 4 * 4 * 3 * 3 * 4 * 3  # 5184
            
        else:  # exhaustivo
            rangos = {
                'desperdicio_min': [0, 5, 8, 10],
                'desperdicio_max': [30, 40, 50, 70, 100],
                'margen_exceso': [1.10, 1.20, 1.30, 1.50, 2.00],
                'ml_minimo_resto': [0, 300, 600, 900],
                'margen_cobertura': [0.80, 0.85, 0.90, 0.95],
                'relajacion_ml_pct': [20, 30, 50, 70, 90],
                'factor_penalizacion': [0.001, 0.01, 0.03, 0.05],
            }
            total_combinaciones = 4 * 5 * 5 * 4 * 4 * 5 * 4  # 64000
        
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
                        cobertura = (kg_asignado / kg_solicitado * 100) if kg_solicitado > 0 else 0
                        cobertura_min = min(cobertura_min, cobertura)
                    
                    # Puntuación (menor es mejor)
                    # Prioridad 1: Minimizar bobinas
                    # Prioridad 2: Minimizar desperdicio
                    puntuacion = num_bobinas * 1000 + desperdicio_total
                    
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
                        'valido': cobertura_min >= 90
                    }
                    
                    self.resultados.append(resultado)
                    
                    # Actualizar mejor resultado (solo si cumple cobertura)
                    if resultado['valido'] and puntuacion < mejor_puntuacion:
                        mejor_puntuacion = puntuacion
                        mejor_resultado = resultado
                        
                        print(f"✨ Nuevo mejor: {num_bobinas} bobinas, {desperdicio_total:.1f}mm desperdicio")
                        print(f"   Parámetros: desp={desp_min}-{desp_max}mm, exceso={int((margen-1)*100)}%, ml_resto={ml_resto}ml")
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
                  f"exceso={resultado['margen_exceso_pct']}%, ml_resto={resultado['ml_minimo_resto']}ml")
            print()
        
        return {
            'mejor': mejor,
            'top5': top5,
            'todos': self.resultados
        }


def sugerir_parametros_iniciales(df_desarrollos: pd.DataFrame, 
                                 df_pedidos: pd.DataFrame) -> Dict:
    """
    Sugiere parámetros iniciales SIN ejecutar búsqueda completa.
    Usa heurísticas rápidas basadas en los datos.
    """
    # Análisis rápido
    anchos_desarrollos = df_desarrollos['ANCHO'].tolist()
    anchos_pedidos = df_pedidos['ANCHO'].tolist()
    
    ancho_min_desarrollo = min(anchos_desarrollos)
    ancho_max_desarrollo = max(anchos_desarrollos)
    ancho_min_pedido = min(anchos_pedidos)
    
    kg_total_pedidos = df_pedidos['KG'].sum()
    kg_total_desarrollos = df_desarrollos['KG'].sum()
    
    # Heurísticas
    desperdicio_min_sugerido = 5 if ancho_min_pedido < 200 else 8
    desperdicio_max_sugerido = int(ancho_max_desarrollo * 0.05)  # 5% del ancho mayor
    desperdicio_max_sugerido = max(40, min(80, desperdicio_max_sugerido))
    
    # Si hay mucha demanda vs material, ser más flexible
    ratio_demanda = kg_total_pedidos / kg_total_desarrollos
    if ratio_demanda > 0.9:
        margen_exceso_sugerido = 50  # Ser más flexible
        ml_resto_sugerido = 300  # Permitir restos más pequeños
    else:
        margen_exceso_sugerido = 30
        ml_resto_sugerido = 600
    
    return {
        'desperdicio_bordes_minimo': desperdicio_min_sugerido,
        'desperdicio_bordes_maximo': desperdicio_max_sugerido,
        'margen_exceso': margen_exceso_sugerido,
        'ml_minimo_resto': ml_resto_sugerido,
        'margen_cobertura_pct': 90,  # 90% por defecto
        'relajacion_ml_pct': 50,  # 50% por defecto
        'factor_penalizacion': 0.01,  # Balance por defecto
        'kg_max_bobina': 7500,
        'kg_min_bobina': 200,
        'max_cortes_por_pedido': 15,
        'justificacion': {
            'desperdicio': f"Basado en anchos de {ancho_min_pedido:.0f}-{ancho_max_desarrollo:.0f}mm",
            'margen_exceso': f"Ratio demanda/material: {ratio_demanda:.1%}",
            'ml_resto': "Balance entre flexibilidad y eficiencia",
            'cobertura': "90% permite flexibilidad en cumplimiento",
            'relajacion_ml': "50% equilibra requisitos ML con eficiencia"
        }
    }


# ============================================
# EJEMPLO DE USO
# ============================================

if __name__ == "__main__":
    # Datos de prueba
    datos_desarrollos = {
        'ANCHO': [1250.0, 1150.0],
        'ESPESOR': [0.77, 0.77],
        'KG': [15000, 2200],
        'ALEACION': ['3105', '3105'],
        'ESTADO': ['H18', 'H18']
    }

    datos_pedidos = {
        'PEDIDO': ['451602/1', '451603/1', '451603/2', '451388/1', '451388/3', '451390/1', '451631/1'],
        'ANCHO': [178.0, 436.8, 563.3, 436.8, 536.3, 143.0, 536.3],
        'KG': [1500, 3000, 1800, 1500, 2700, 1750, 2000],
        'ALEACION': ['3105', '3105', '3105', '3105', '3105', '3105', '3105'],
        'ESTADO': ['H18', 'H18', 'H18', 'H18', 'H18', 'H18', 'H18'],
        'ESPESOR': [0.77, 0.77, 0.77, 0.77, 0.77, 0.77, 0.77],
        'ML_MINIMOS': [0, 0, 0, 0, 0, 0, 0]
    }

    df_desarrollos = pd.DataFrame(datos_desarrollos)
    df_pedidos = pd.DataFrame(datos_pedidos)
    
    print("="*80)
    print("OPCIÓN 1: SUGERENCIA RÁPIDA (sin búsqueda)")
    print("="*80)
    print()
    
    sugerencia = sugerir_parametros_iniciales(df_desarrollos, df_pedidos)
    
    print("💡 PARÁMETROS SUGERIDOS:")
    print()
    print(f"   Desperdicio bordes: {sugerencia['desperdicio_bordes_minimo']}-{sugerencia['desperdicio_bordes_maximo']}mm")
    print(f"   Margen exceso: {sugerencia['margen_exceso']}%")
    print(f"   ML mínimo resto: {sugerencia['ml_minimo_resto']}ml")
    print()
    print("📝 Justificación:")
    for key, valor in sugerencia['justificacion'].items():
        print(f"   - {key}: {valor}")
    print()
    print()
    
    # Búsqueda completa (opcional)
    respuesta = input("¿Ejecutar búsqueda completa de parámetros óptimos? (s/n): ")
    
    if respuesta.lower() == 's':
        print()
        print("="*80)
        print("OPCIÓN 2: BÚSQUEDA COMPLETA")
        print("="*80)
        print()
        
        optimizador = OptimizadorParametros(df_desarrollos, df_pedidos)
        resultado = optimizador.buscar_parametros_optimos(modo='rapido')