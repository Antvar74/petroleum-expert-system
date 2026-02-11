"""
Interactive Helper Utilities
Funciones para mejorar la experiencia interactiva del sistema
"""

import os
import sys
import subprocess
from typing import Optional


# Colores ANSI para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str, emoji: str = ""):
    """Imprime un encabezado destacado"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{emoji} {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * (len(text) + 3)}{Colors.ENDC}\n")


def print_separator(char: str = "-", length: int = 80):
    """Imprime un separador"""
    print(f"{Colors.OKCYAN}{char * length}{Colors.ENDC}")


def print_query_box(title: str, content: str):
    """Imprime una caja destacada con la consulta"""
    width = 80
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'┌' + '─' * (width-2) + '┐'}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}│ {title.center(width-4)} │{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{'├' + '─' * (width-2) + '┤'}{Colors.ENDC}")
    
    for line in content.split('\n'):
        if len(line) > width - 4:
            words = line.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= width - 4:
                    current_line += word + " "
                else:
                    print(f"{Colors.OKBLUE}│{Colors.ENDC} {current_line.ljust(width-4)} {Colors.OKBLUE}│{Colors.ENDC}")
                    current_line = word + " "
            if current_line:
                print(f"{Colors.OKBLUE}│{Colors.ENDC} {current_line.ljust(width-4)} {Colors.OKBLUE}│{Colors.ENDC}")
        else:
            print(f"{Colors.OKBLUE}│{Colors.ENDC} {line.ljust(width-4)} {Colors.OKBLUE}│{Colors.ENDC}")
    
    print(f"{Colors.BOLD}{Colors.OKBLUE}{'└' + '─' * (width-2) + '┘'}{Colors.ENDC}\n")


def get_multiline_input(prompt: str = "Pega la respuesta de Claude (termina con una línea vacía):") -> str:
    """Captura entrada multilínea del usuario"""
    print(f"\n{Colors.OKCYAN}{prompt}{Colors.ENDC}")
    print(f"{Colors.WARNING}(Presiona Enter dos veces para terminar){Colors.ENDC}\n")
    
    lines = []
    empty_line_count = 0
    
    while True:
        try:
            line = input()
            if line == "":
                empty_line_count += 1
                if empty_line_count >= 2:
                    break
            else:
                empty_line_count = 0
                lines.append(line)
        except EOFError:
            break
    
    return "\n".join(lines)


def confirm_action(prompt: str = "¿Continuar?") -> bool:
    """Solicita confirmación del usuario"""
    response = input(f"\n{Colors.WARNING}{prompt} (s/n): {Colors.ENDC}").strip().lower()
    return response in ['s', 'si', 'sí', 'y', 'yes']


def show_progress(current: int, total: int, prefix: str = "Progreso"):
    """Muestra una barra de progreso"""
    bar_length = 40
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    percentage = int(100 * current / total)
    
    print(f"\r{Colors.OKCYAN}{prefix}: [{bar}] {percentage}% ({current}/{total}){Colors.ENDC}", end='')
    if current == total:
        print()


def format_agent_name(agent_id: str) -> str:
    """Formatea el nombre del agente con emoji"""
    emojis = {
        "drilling_engineer": "👷",
        "mud_engineer": "🧪",
        "geologist": "🪨",
        "well_engineer": "🎯",
        "hydrologist": "💧"
    }
    
    names = {
        "drilling_engineer": "Drilling Engineer / Company Man",
        "mud_engineer": "Mud Engineer / Fluids Specialist",
        "geologist": "Geologist / Petrophysicist",
        "well_engineer": "Well Engineer / Trajectory Specialist",
        "hydrologist": "Hydrologist / Pore Pressure Specialist"
    }
    
    emoji = emojis.get(agent_id, "🔧")
    name = names.get(agent_id, agent_id.replace('_', ' ').title())
    
    return f"{emoji} {name}"


def save_to_clipboard(text: str) -> bool:
    """Intenta copiar texto al portapapeles (macOS)"""
    try:
        process = subprocess.Popen(
            ['pbcopy'],
            stdin=subprocess.PIPE,
            close_fds=True
        )
        process.communicate(text.encode('utf-8'))
        return True
    except Exception:
        return False


def clear_screen():
    """Limpia la pantalla de la terminal"""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_success(message: str):
    """Imprime mensaje de éxito"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Imprime mensaje de error"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Imprime mensaje de advertencia"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")
