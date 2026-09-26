import os
import argparse
from pathlib import Path

def generate_tree(dir_path: Path, prefix: str = "", exclude_dirs: set = None) -> list:
    """Genera recursivamente las líneas de la estructura de árbol para un directorio."""
    if exclude_dirs is None:
        exclude_dirs = {".git", ".dart_tool", "build", "__pycache__", "node_modules", ".DS_Store"}

    try:
        entries = sorted(list(dir_path.iterdir()), key=lambda x: (x.is_file(), x.name.lower()))
    except PermissionError:
        return []

    entries = [e for e in entries if e.name not in exclude_dirs]
    lines = []
    
    for i, entry in enumerate(entries):
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        
        if entry.is_dir():
            next_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(generate_tree(entry, next_prefix, exclude_dirs))
            
    return lines

def main():
    """Punto de entrada para analizar argumentos y mostrar la estructura del proyecto."""
    parser = argparse.ArgumentParser(
        description="Muestra la estructura de carpetas de la aplicación de Flutter."
    )
    parser.add_argument(
        "--path",
        type=str,
        default="/Users/anthonyrubio/Downloads/03.Learning/PG/ponteglam_mobile/lib",
        help="Ruta de la carpeta a escanear (por defecto: lib de ponteglam_mobile)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Incluye todas las carpetas del proyecto, no solo 'lib'",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Ruta del archivo donde se guardará la salida (opcional)",
    )
    args = parser.parse_args()

    target_path = Path(args.path)
    if args.all:
        target_path = Path("/Users/anthonyrubio/Downloads/03.Learning/PG/ponteglam_mobile")

    if not target_path.exists():
        print(f"Error: La ruta '{target_path}' no existe.")
        return

    header = f"📁 Estructura de: {target_path.resolve()}\n"
    tree_lines = generate_tree(target_path)
    content = header + "\n".join(tree_lines) + f"\n\nTotal de elementos mostrados: {len(tree_lines)}\n"

    if args.output:
        output_path = Path(args.output)
        try:
            output_path.write_text(content, encoding="utf-8")
            print(f"✅ Estructura guardada con éxito en: {output_path.resolve()}")
        except Exception as e:
            print(f"❌ Error al escribir en el archivo: {e}")
    else:
        print(content)

if __name__ == "__main__":
    main()
