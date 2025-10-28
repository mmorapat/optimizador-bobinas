"""
📊 VISUALIZADOR DE BOBINAS - VERSIÓN SIMPLE
Solo cambio: rectángulo más alto y textos debajo
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
from typing import List, Dict
import numpy as np


def visualizar_bobinas_detallado(df_solucion: pd.DataFrame):
    """
    Visualización detallada (una bobina por fila)
    CAMBIO SIMPLE: Rectángulo de altura 100 y textos debajo
    """
    bobinas = df_solucion['BOBINA'].unique()
    
    if len(bobinas) == 0:
        return None
    
    fig, axes = plt.subplots(len(bobinas), 1, figsize=(14, 3*len(bobinas)))
    
    if len(bobinas) == 1:
        axes = [axes]
    
    # Colores para los pedidos
    pedidos_unicos = df_solucion['PEDIDO'].unique()
    colores = plt.cm.Set3(np.linspace(0, 1, len(pedidos_unicos)))
    color_map = {pedido: colores[i] for i, pedido in enumerate(pedidos_unicos)}
    
    for idx, bobina_nombre in enumerate(bobinas):
        ax = axes[idx]
        bobina_data = df_solucion[df_solucion['BOBINA'] == bobina_nombre]
        
        # Obtener datos
        desarrollo = bobina_data.iloc[0]['DESARROLLO']
        ancho_desarrollo = bobina_data.iloc[0]['ANCHO_DESARROLLO']
        ml = bobina_data.iloc[0]['METROS_LINEALES']
        desperdicio = bobina_data.iloc[0]['DESPERDICIO']
        
        # CALCULAR KG BRUTOS
        espesor = float(desarrollo.split('×')[1])
        kg_brutos = ml * 2.73 * espesor * (ancho_desarrollo / 1000)
        
        # TÍTULO
        ax.set_title(
            f"{bobina_nombre} - ANCHO: {ancho_desarrollo:.1f}×{espesor:.2f}, {kg_brutos:.0f}KG {ml:.0f}ML, DESP: {desperdicio:.0f}mm",
            fontsize=11, fontweight='bold', pad=10
        )
        
        # SIMPLE: Rectángulo de altura 100
        altura_rect = 100
        y_rect = 50  # Base del rectángulo
        
        # Dibujar rectángulo de la bobina
        ax.add_patch(patches.Rectangle((0, y_rect), ancho_desarrollo, altura_rect, 
                                      fill=False, edgecolor='black', linewidth=3))
        
        # Dibujar cortes
        posicion_x = 0
        for _, corte in bobina_data.iterrows():
            ancho_corte = corte['ANCHO_CORTE']
            num_cortes = corte['NUM_CORTES']
            pedido = corte['PEDIDO']
            kg_corte = corte['KG_ASIGNADOS']
            kg_por_rodillo = kg_corte / num_cortes
            
            # Dibujar cada corte individual
            for i in range(int(num_cortes)):
                ax.add_patch(patches.Rectangle(
                    (posicion_x, y_rect), ancho_corte, altura_rect,
                    facecolor=color_map[pedido], 
                    edgecolor='black', 
                    linewidth=1.5,
                    alpha=0.7
                ))
                
                # NÚMERO DENTRO DEL RECTÁNGULO
                centro_x_rect = posicion_x + ancho_corte/2
                centro_y_rect = y_rect + altura_rect/2
                ax.text(centro_x_rect, centro_y_rect, f"{i+1}", 
                       ha='center', va='center', fontsize=12, fontweight='bold', color='white',
                       bbox=dict(boxstyle='circle,pad=0.3', facecolor='black', alpha=0.7))
                
                # TEXTOS DEBAJO CON SEPARACIÓN MUY GRANDE
                centro_x = posicion_x + ancho_corte/2
                ax.text(centro_x, 40, f"{pedido}", 
                       ha='center', va='top', fontsize=9, fontweight='bold')
                ax.text(centro_x, 25, f"{ancho_corte:.1f}mm", 
                       ha='center', va='top', fontsize=8, fontweight='bold', color='black')
                ax.text(centro_x, 5, f"{kg_corte:.0f}kg", 
                       ha='center', va='top', fontsize=8, color='red', fontweight='bold')
                ax.text(centro_x, -15, f"{kg_por_rodillo:.0f}kg/rodillo", 
                       ha='center', va='top', fontsize=7, color='maroon', fontweight='bold')
                ax.text(centro_x, -30, f"{ml}ml", 
                       ha='center', va='top', fontsize=7, color='dimgray', fontweight='bold')
                
                posicion_x += ancho_corte
        
        # Dibujar desperdicio
        if desperdicio > 0:
            ax.add_patch(patches.Rectangle(
                (posicion_x, y_rect), desperdicio, altura_rect,
                facecolor='lightgray', 
                edgecolor='red', 
                linewidth=2,
                alpha=0.5,
                hatch='//'
            ))
            # Texto ARRIBA del rectángulo
            ax.text(posicion_x + desperdicio/2, y_rect + altura_rect + 5, 
                   f"DESPERDICIO: {desperdicio:.0f}mm", 
                   ha='center', va='bottom', fontsize=9, color='red', fontweight='bold')
        
        # Configuración de ejes
        ax.set_xlim(0, ancho_desarrollo * 1.02)
        ax.set_ylim(-35, y_rect + altura_rect + 20)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Agregar escala
        ax.text(0, -38, '0mm', ha='center', va='top', fontsize=8)
        ax.text(ancho_desarrollo, -38, f'{ancho_desarrollo:.1f}mm', 
               ha='center', va='top', fontsize=8)
    
    plt.tight_layout()
    return fig


def visualizar_bobinas(df_solucion: pd.DataFrame, max_bobinas: int = 10):
    """
    Visualización compacta (varias por fila)
    """
    bobinas = df_solucion['BOBINA'].unique()[:max_bobinas]
    
    if len(bobinas) == 0:
        return None
    
    # Calcular dimensiones
    bobinas_por_fila = min(3, len(bobinas))
    num_filas = (len(bobinas) + bobinas_por_fila - 1) // bobinas_por_fila
    
    fig, axes = plt.subplots(num_filas, bobinas_por_fila, 
                            figsize=(6*bobinas_por_fila, 4*num_filas))
    
    if len(bobinas) == 1:
        axes = np.array([axes])
    axes = axes.flatten() if isinstance(axes, np.ndarray) else [axes]
    
    # Colores para los pedidos
    pedidos_unicos = df_solucion['PEDIDO'].unique()
    colores = plt.cm.Set3(np.linspace(0, 1, len(pedidos_unicos)))
    color_map = {pedido: colores[i] for i, pedido in enumerate(pedidos_unicos)}
    
    for idx, bobina_nombre in enumerate(bobinas):
        ax = axes[idx]
        bobina_data = df_solucion[df_solucion['BOBINA'] == bobina_nombre]
        
        # Obtener datos
        desarrollo = bobina_data.iloc[0]['DESARROLLO']
        ancho_desarrollo = bobina_data.iloc[0]['ANCHO_DESARROLLO']
        ml = bobina_data.iloc[0]['METROS_LINEALES']
        desperdicio = bobina_data.iloc[0]['DESPERDICIO']
        
        # CALCULAR KG BRUTOS
        espesor = float(desarrollo.split('×')[1])
        kg_brutos = ml * 2.73 * espesor * (ancho_desarrollo / 1000)
        
        # TÍTULO
        ax.set_title(
            f"{bobina_nombre}\n{desarrollo}, {kg_brutos:.0f}kg, {ml:.0f}ml",
            fontsize=10, fontweight='bold'
        )
        
        # Rectángulo de altura 100
        altura_rect = 100
        y_rect = 40
        
        # Dibujar rectángulo de la bobina
        ax.add_patch(patches.Rectangle((0, y_rect), ancho_desarrollo, altura_rect, 
                                      fill=False, edgecolor='black', linewidth=2))
        
        # Dibujar cortes
        posicion_x = 0
        for _, corte in bobina_data.iterrows():
            ancho_corte = corte['ANCHO_CORTE']
            num_cortes = corte['NUM_CORTES']
            pedido = corte['PEDIDO']
            kg_corte = corte['KG_ASIGNADOS']
            
            # Dibujar cada corte individual
            for i in range(int(num_cortes)):
                ax.add_patch(patches.Rectangle(
                    (posicion_x, y_rect), ancho_corte, altura_rect,
                    facecolor=color_map[pedido], 
                    edgecolor='black', 
                    linewidth=1,
                    alpha=0.7
                ))
                
                # NÚMERO DENTRO DEL RECTÁNGULO
                centro_x_rect = posicion_x + ancho_corte/2
                centro_y_rect = y_rect + altura_rect/2
                ax.text(centro_x_rect, centro_y_rect, f"{i+1}", 
                       ha='center', va='center', fontsize=10, fontweight='bold', color='white',
                       bbox=dict(boxstyle='circle,pad=0.3', facecolor='black', alpha=0.7))
                
                posicion_x += ancho_corte
            
            # TEXTOS DEBAJO con SEPARACIÓN EXAGERADA
            centro_x = posicion_x - (num_cortes * ancho_corte / 2)
            kg_por_rodillo = kg_corte / num_cortes
            
            ax.text(centro_x, 38, f"{pedido}", 
                   ha='center', va='top', fontsize=9, fontweight='bold')
            ax.text(centro_x, 10, f"{int(num_cortes)}×{ancho_corte:.1f}mm", 
                   ha='center', va='top', fontsize=8, fontweight='bold', color='black')
            ax.text(centro_x, -20, f"{kg_corte:.0f}kg", 
                   ha='center', va='top', fontsize=8, color='red', fontweight='bold')
            ax.text(centro_x, -50, f"{kg_por_rodillo:.0f}kg/rodillo", 
                   ha='center', va='top', fontsize=7, color='maroon', fontweight='bold')
        
        # Dibujar desperdicio
        if desperdicio > 0:
            ax.add_patch(patches.Rectangle(
                (posicion_x, y_rect), desperdicio, altura_rect,
                facecolor='lightgray', 
                edgecolor='red', 
                linewidth=2,
                alpha=0.5,
                hatch='//'
            ))
            # Texto ARRIBA del rectángulo
            ax.text(posicion_x + desperdicio/2, y_rect + altura_rect + 5, 
                   f"Desp: {desperdicio:.0f}mm", 
                   ha='center', va='bottom', fontsize=8, color='red', fontweight='bold')
        
        # Configuración de ejes (ajustado para textos MUY separados)
        ax.set_xlim(0, ancho_desarrollo)
        ax.set_ylim(-60, y_rect + altura_rect + 20)
        ax.set_aspect('equal')
        ax.axis('off')
    
    # Ocultar axes sobrantes
    for idx in range(len(bobinas), len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    return fig


def mostrar_estadisticas_visuales(df_solucion: pd.DataFrame, df_pedidos: pd.DataFrame):
    """
    Gráficos de cumplimiento y distribución
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Gráfico 1: Cumplimiento de pedidos
    pedidos_asignados = df_solucion.groupby('PEDIDO')['KG_ASIGNADOS'].sum()
    pedidos_solicitados = df_pedidos.set_index('PEDIDO')['KG']
    
    cumplimiento_data = []
    for pedido_id in df_pedidos['PEDIDO']:
        kg_asignado = pedidos_asignados.get(pedido_id, 0)
        kg_solicitado = pedidos_solicitados.get(pedido_id, 0)
        porcentaje = (kg_asignado / kg_solicitado * 100) if kg_solicitado > 0 else 0
        cumplimiento_data.append({
            'PEDIDO': pedido_id,
            'PORCENTAJE': porcentaje
        })
    
    df_cumplimiento = pd.DataFrame(cumplimiento_data)
    
    colores = ['green' if x >= 95 else 'orange' if x >= 80 else 'red' 
               for x in df_cumplimiento['PORCENTAJE']]
    
    ax1.barh(df_cumplimiento['PEDIDO'], df_cumplimiento['PORCENTAJE'], color=colores)
    ax1.axvline(x=95, color='red', linestyle='--', linewidth=2, label='Mínimo 95%')
    ax1.axvline(x=100, color='green', linestyle='--', linewidth=2, label='Objetivo 100%')
    ax1.set_xlabel('Porcentaje de Cumplimiento (%)', fontsize=10)
    ax1.set_ylabel('Pedido', fontsize=10)
    ax1.set_title('Cumplimiento de Pedidos', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(axis='x', alpha=0.3)
    
    # Gráfico 2: Distribución de peso por bobina
    bobinas_kg = []
    bobinas_nombres = []
    
    for bobina in df_solucion['BOBINA'].unique():
        bobina_data = df_solucion[df_solucion['BOBINA'] == bobina]
        desarrollo = bobina_data.iloc[0]['DESARROLLO']
        ancho_desarrollo = bobina_data.iloc[0]['ANCHO_DESARROLLO']
        ml = bobina_data.iloc[0]['METROS_LINEALES']
        
        # CALCULAR KG BRUTOS
        espesor = float(desarrollo.split('×')[1])
        kg_brutos = ml * 2.73 * espesor * (ancho_desarrollo / 1000)
        
        bobinas_kg.append(kg_brutos)
        bobinas_nombres.append(bobina)
    
    ax2.bar(bobinas_nombres, bobinas_kg, color='steelblue', alpha=0.7)
    ax2.set_xlabel('Bobina', fontsize=10)
    ax2.set_ylabel('KG Brutos (con desperdicio)', fontsize=10)
    ax2.set_title('Distribución de Peso por Bobina', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    # Agregar valores sobre las barras
    for i, (nombre, kg) in enumerate(zip(bobinas_nombres, bobinas_kg)):
        ax2.text(i, kg + 50, f'{kg:.0f}kg', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    return fig