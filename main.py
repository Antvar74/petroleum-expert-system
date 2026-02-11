"""
Petroleum Expert System - Main Application (Interactive Mode)
Multi-Agent System for Oilfield Operations Analysis - No API Required
Version 2.0 - Includes RCA Analysis and Custom Case Creation
"""

import os
import sys
from datetime import datetime
from orchestrator import StuckPipeCoordinator
from models import OperationalProblem
from utils.interactive_helper import (
    print_header, print_separator, clear_screen,
    print_success, print_error, print_warning
)


def print_banner():
    """Print application banner"""
    clear_screen()
    print("\n" + "="*80)
    print(" " * 15 + "PETROLEUM EXPERT SYSTEM")
    print(" " * 10 + "Sistema Multi-Agente para Análisis de Operaciones")
    print(" " * 15 + "Modo Interactivo (Sin API)")
    print("="*80 + "\n")


def print_instructions():
    """Print usage instructions"""
    print_header("CÓMO FUNCIONA ESTE SISTEMA", "📖")
    print("""
Este sistema NO hace llamadas automáticas a la API de Claude.
En su lugar, funciona de manera INTERACTIVA:

1. El sistema genera una consulta pre-formateada para cada especialista
2. TÚ copias esa consulta y la pegas en Claude (Code, chat, o app)
3. Claude te responde con su análisis experto
4. TÚ copias la respuesta de Claude y la pegas aquí
5. El sistema procesa la respuesta y continúa con el siguiente especialista
6. Al final, genera un reporte integrado con todos los análisis

VENTAJAS:
✓ Usa tu suscripción actual de Claude (Pro, Team, etc.)
✓ Sin costos adicionales de API
✓ Mantienes control total del proceso
✓ Puedes revisar cada análisis antes de continuar

Los 5 especialistas son:
  1. 👷 Drilling Engineer / Company Man
  2. 🧪 Mud Engineer / Fluids Specialist
  3. 🪨 Geologist / Petrophysicist
  4. 🎯 Well Engineer / Trajectory Specialist
  5. 💧 Hydrologist / Pore Pressure Specialist
""")
    print_separator()


def example_differential_sticking():
    """Example: Differential Sticking Case"""
    return OperationalProblem(
        well_name="WELL-A-001",
        depth_md=12450.0,
        depth_tvd=11800.0,
        description="""
Durante operación de perforación a 12,450 ft MD en la formación Naricual (arenisca permeable),
se observó incremento progresivo de torque de 15 klb-ft a 28 klb-ft en últimas 2 horas.

Al intentar sacar tubería (POOH), se detectó overpull de 85,000 lbs (string weight = 180,000 lbs).
La tubería quedó atrapada sin posibilidad de rotación ni movimiento axial.

No hubo pérdidas de circulación. Bombas operando normalmente. Sin incremento de presión en standpipe.
Última conexión realizada hace 45 minutos sin problemas.

Lodo base agua, densidad 10.2 ppg, sin cambios recientes en propiedades.
""",
        operation="drilling",
        formation="Naricual (Sandstone)",
        mud_weight=10.2,
        inclination=45.0,
        azimuth=85.0,
        torque=28.0,
        overpull=85000,
        string_weight=180000,
        additional_data={
            "mud_properties": {
                "type": "WBM",
                "density_ppg": 10.2,
                "funnel_viscosity": 48,
                "pv": 18,
                "yp": 12,
                "api_filtrate": 8.5,
                "cake_thickness_32nds": 4
            },
            "formation_data": {
                "lithology": "Sandstone - permeable",
                "porosity_est": 0.22,
                "permeability_md": 150,
                "exposure_time_hrs": 6.5
            },
            "pressure_data": {
                "pore_pressure_ppg": 9.1,
                "estimated_frac_gradient": 13.5
            }
        }
    )


def example_packoff():
    """Example: Pack-off Case"""
    return OperationalProblem(
        well_name="WELL-B-002",
        depth_md=8920.0,
        depth_tvd=8650.0,
        description="""
Durante slide drilling en sección de 8-1/2" a 8,920 ft MD, se observó incremento súbito
de presión en standpipe de 2,800 psi a 3,450 psi.

Imposible rotar la sarta. Al intentar reciprocar, movimiento libre solo 15 ft.
Circulación posible pero con presión elevada. Retornos con alta concentración de recortes.

Sección altamente inclinada (65°) con múltiples cambios de ángulo (DLS hasta 6.5°/100ft).
ROP promedio últimas 3 horas: 85 ft/hr (alto para la formación).

Lodo base aceite, densidad 12.8 ppg. Viscosidad Marsh 62 seg (incrementó de 55 seg).
""",
        operation="drilling",
        formation="Gobernador Shale",
        mud_weight=12.8,
        inclination=65.0,
        torque=35.0,
        string_weight=210000,
        additional_data={
            "mud_properties": {
                "type": "OBM",
                "density_ppg": 12.8,
                "funnel_viscosity": 62,
                "pv": 35,
                "yp": 28,
                "oil_water_ratio": "75/25"
            },
            "drilling_parameters": {
                "rop_ft_hr": 85,
                "wob_klbs": 35,
                "rpm": 0,
                "flow_rate_gpm": 420,
                "pump_pressure_psi": 3450,
                "normal_pressure_psi": 2800
            },
            "trajectory": {
                "inclination_deg": 65,
                "dls_100ft": 6.5,
                "build_section": True
            }
        }
    )


def select_agents():
    """Let user select which agents to consult"""
    print_header("SELECCIÓN DE ESPECIALISTAS", "🎯")
    
    agents = {
        "1": ("drilling_engineer", "Drilling Engineer / Company Man"),
        "2": ("mud_engineer", "Mud Engineer / Fluids Specialist"),
        "3": ("geologist", "Geologist / Petrophysicist"),
        "4": ("well_engineer", "Well Engineer / Trajectory Specialist"),
        "5": ("hydrologist", "Hydrologist / Pore Pressure Specialist")
    }
    
    print("Especialistas disponibles:")
    for key, (agent_id, name) in agents.items():
        print(f"  {key}. {name}")
    
    print("\nIngresa los números separados por comas (ej: 1,2,5)")
    print("O presiona Enter para consultar TODOS los especialistas")
    
    selection = input("\n➤ Tu selección: ").strip()
    
    if not selection:
        return [agent_id for agent_id, _ in agents.values()]
    
    selected = []
    for num in selection.split(','):
        num = num.strip()
        if num in agents:
            selected.append(agents[num][0])
    
    return selected if selected else [agent_id for agent_id, _ in agents.values()]


def create_custom_case():
    """Create a custom case through interactive interview"""
    try:
        from data_capture.interactive_interview import InteractiveInterview
        
        print_header("CREAR CASO PERSONALIZADO", "📝")
        print("A continuación te haré una serie de preguntas para crear tu caso personalizado.\n")
        
        interview = InteractiveInterview()
        problem = interview.conduct_interview()
        
        if problem:
            print_success("\n✓ Caso personalizado creado exitosamente")
            return problem
        else:
            print_warning("Creación de caso cancelada")
            return None
            
    except ImportError as e:
        print_error(f"Error: Módulo de captura de datos no encontrado: {e}")
        return None


def run_rca_analysis():
    """Run Root Cause Analysis using 5-Whys and/or Fishbone"""
    try:
        from rca.rca_coordinator import RCACoordinator
        
        print_header("ANÁLISIS RCA - ROOT CAUSE ANALYSIS", "🔍")
        print("""
El análisis de causa raíz te ayudará a identificar las causas fundamentales
del problema operacional y desarrollar acciones preventivas efectivas.

Métodos disponibles:
  1. 5-Whys (5 Porqués) - Análisis secuencial profundo
  2. Fishbone (Ishikawa) - Análisis por categorías
  3. Ambos métodos (Recomendado)
""")
        
        method_choice = input("➤ Selecciona método (1-3): ").strip()
        
        # Select or create case
        print("\n¿Qué caso quieres analizar?")
        print("  1. Differential Sticking (ejemplo)")
        print("  2. Pack-off (ejemplo)")
        print("  3. Crear caso personalizado")
        
        case_choice = input("➤ Selecciona caso (1-3): ").strip()
        
        if case_choice == "1":
            problem = example_differential_sticking()
        elif case_choice == "2":
            problem = example_packoff()
        elif case_choice == "3":
            problem = create_custom_case()
            if not problem:
                return
        else:
            print_error("Opción inválida")
            return
        
        # Run RCA
        coordinator = RCACoordinator()
        
        if method_choice == "1":
            result = coordinator.run_five_whys_interactive(problem)
        elif method_choice == "2":
            result = coordinator.run_fishbone_interactive(problem)
        elif method_choice == "3":
            result = coordinator.run_complete_rca_interactive(problem)
        else:
            print_error("Opción inválida")
            return
        
        # Save results
        if result:
            output_dir = "rca_results"
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"{output_dir}/RCA_{problem.well_name}_{timestamp}.md"
            
            coordinator.generate_report(result, filepath)
            print_success(f"\n✓ Reporte RCA guardado en: {filepath}")
        
    except ImportError as e:
        print_error(f"Error: Módulo RCA no encontrado: {e}")
    except Exception as e:
        print_error(f"Error durante análisis RCA: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main application"""
    print_banner()
    print_instructions()
    
    # Initialize coordinator
    print_separator()
    print("🔧 Inicializando sistema multi-agente...")
    
    try:
        coordinator = StuckPipeCoordinator()
        print_success("✅ Sistema listo. Agentes disponibles:")
        for agent_name, agent in coordinator.agents.items():
            print(f"   - {agent.role}")
    except Exception as e:
        print_error(f"Error inicializando coordinador: {e}")
        return
    
    # Main menu
    print_header("MENÚ PRINCIPAL", "📋")
    print("""
Selecciona una opción:

  1. Caso ejemplo: Differential Sticking en zona permeable
  2. Caso ejemplo: Pack-off por limpieza deficiente
  3. Análisis rápido (selecciona especialistas específicos)
  4. Crear caso personalizado (entrevista interactiva) 🆕
  5. Análisis RCA - Root Cause Analysis 🆕
  6. Salir
""")
    
    choice = input("➤ Selecciona opción (1-6): ").strip()
    
    if choice == "6":
        print_success("¡Hasta luego!")
        return
    
    # Handle RCA option
    if choice == "5":
        run_rca_analysis()
        return
    
    # Handle custom case creation
    if choice == "4":
        problem = create_custom_case()
        if not problem:
            return
        
        # Ask if user wants to analyze it now
        analyze = input("\n¿Deseas analizar este caso ahora? (s/n): ").strip().lower()
        if analyze != 's':
            # Save case for later
            output_dir = "saved_cases"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"{output_dir}/{problem.well_name}_{timestamp}.json"
            
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(problem.to_dict(), f, indent=2, ensure_ascii=False)
            
            print_success(f"✓ Caso guardado en: {filepath}")
            return
        
        analysis_type = "complete"
        agents_to_consult = None
    
    # Select problem for standard analysis
    elif choice == "1":
        problem = example_differential_sticking()
        analysis_type = "complete"
        agents_to_consult = None
    elif choice == "2":
        problem = example_packoff()
        analysis_type = "complete"
        agents_to_consult = None
    elif choice == "3":
        print("\nPrimero selecciona un caso base:")
        print("  1. Differential Sticking")
        print("  2. Pack-off")
        print("  3. Caso personalizado")
        case_choice = input("➤ Caso (1-3): ").strip()
        
        if case_choice == "1":
            problem = example_differential_sticking()
        elif case_choice == "2":
            problem = example_packoff()
        elif case_choice == "3":
            problem = create_custom_case()
            if not problem:
                return
        else:
            print_error("Opción inválida")
            return
        
        agents_to_consult = select_agents()
        analysis_type = "quick"
    else:
        print_error("Opción inválida")
        return
    
    # Confirm start
    print("\n" + "="*80)
    print(f"Análisis: {problem.well_name}")
    print(f"Profundidad: {problem.depth_md} ft MD")
    print(f"Tipo: {'Completo (5 agentes)' if analysis_type == 'complete' else f'Rápido ({len(agents_to_consult)} agentes)'}")
    print("="*80 + "\n")
    
    confirm = input("¿Iniciar análisis? (s/n): ").strip().lower()
    if confirm != 's':
        print_warning("Análisis cancelado")
        return
    
    # Run analysis
    try:
        if analysis_type == "complete":
            result = coordinator.analyze_stuck_pipe_interactive(problem)
        else:
            result = coordinator.quick_analysis_interactive(
                problem.description, 
                agents_to_consult
            )
        
        # Save results
        output_dir = "analysis_results"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = f"{output_dir}/{problem.well_name}_{timestamp}.json"
        report_file = f"{output_dir}/{problem.well_name}_{timestamp}.md"
        
        result.to_json(json_file)
        result.generate_report(report_file)
        
        print("\n" + "="*80)
        print_success("✓ ANÁLISIS COMPLETADO")
        print("="*80)
        print(f"\n📁 Resultados guardados en:")
        print(f"   • JSON: {json_file}")
        print(f"   • Reporte: {report_file}")
        
        if analysis_type == "complete":
            print(f"\n✓ Total de especialistas consultados: 5")
        else:
            print(f"\n✓ Especialistas consultados: {len(agents_to_consult)}")
        
        print("\n")
        
    except KeyboardInterrupt:
        print_warning("\n\n⚠️  Análisis interrumpido por el usuario")
        print("Los análisis parciales se guardaron en archivos temporales.")
    except Exception as e:
        print_error(f"\n❌ Error durante el análisis: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()