#!/usr/bin/env python3
"""
missing_functions.py

Überprüfe, welche Python-Funktionen aus <stagingdatei> nicht in <originaldatei> enthalten sind,
und schreibe sie in <diffdatei>.
"""

import argparse
import ast
from pathlib import Path
import sys

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fallback: probiere ohne Angabe (system default)
        return path.read_text()

def top_level_function_nodes(tree: ast.AST):
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node

def function_names_in_file(path: Path) -> set[str]:
    code = read_text(path)
    tree = ast.parse(code, filename=str(path))
    return {n.name for n in top_level_function_nodes(tree)}

def extract_function_blocks(path: Path, names: set[str]) -> list[str]:
    """
    Schneidet die Original-Textblöcke (inkl. Dekoratoren) der gewählten Funktionen aus.
    """
    code = read_text(path)
    lines = code.splitlines()
    tree = ast.parse(code, filename=str(path))

    blocks: list[str] = []
    for node in top_level_function_nodes(tree):
        if node.name in names:
            # lineno zeigt bei dekorierten Funktionen auf die erste Dekorator-Zeile
            start = (node.lineno - 1)
            end = node.end_lineno  # exklusiv
            snippet = "\n".join(lines[start:end])
            blocks.append(snippet)
    return blocks

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="missing_functions",
        description="Überprüfe, welche Python-Funktionen aus <stagingdatei> nicht in <originaldatei> enthalten sind, und schreibe sie in <diffdatei>."
    )
    parser.add_argument("originaldatei", type=Path, help="Pfad zur bestehenden Zieldatei (z. B. funcs.py)")
    parser.add_argument("stagingdatei", type=Path, help="Pfad zur Stage-Datei (z. B. stage/funcs.py)")
    parser.add_argument("diffdatei", type=Path, help="Pfad zur Ausgabedatei mit fehlenden Funktionen")

    args = parser.parse_args(argv)

    if not args.originaldatei.exists():
        print(f"Fehler: Originaldatei nicht gefunden: {args.originaldatei}", file=sys.stderr)
        return 2
    if not args.stagingdatei.exists():
        print(f"Fehler: Stagingdatei nicht gefunden: {args.stagingdatei}", file=sys.stderr)
        return 2

    try:
        original_funcs = function_names_in_file(args.originaldatei)
        staging_funcs = function_names_in_file(args.stagingdatei)
    except SyntaxError as e:
        print(f"SyntaxError beim Parsen: {e}", file=sys.stderr)
        return 2

    missing = [name for name in staging_funcs if name not in original_funcs]
    missing_set = set(missing)

    header_lines = [
        "# --- missing_functions Output ---",
        f"# Quelle (Original): {args.originaldatei}",
        f"# Quelle (Stage)   : {args.stagingdatei}",
        f"# Enthalten: {len(missing)} fehlende Funktion(en): {', '.join(missing) if missing else '-'}",
        ""
    ]

    if missing:
        blocks = extract_function_blocks(args.stagingdatei, missing_set)
        content = "\n\n".join(header_lines + blocks) + "\n"
        args.diffdatei.write_text(content, encoding="utf-8")
        print(f"{len(missing)} fehlende Funktion(en) gefunden und nach '{args.diffdatei}' geschrieben.")
        return 0
    else:
        # Schreibe nur Header als Hinweis, damit der Nutzer trotzdem Feedback in der Datei sieht.
        args.diffdatei.write_text("\n".join(header_lines) + "# (Keine fehlenden Funktionen)\n", encoding="utf-8")
        print("Keine fehlenden Funktionen gefunden. Hinweis in diff-Datei geschrieben.")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
