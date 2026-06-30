#!/usr/bin/env python3
"""
apply_editor_stubs.py

Bindeglied zwischen dem Terrain-Editor und dem Adventure.

Der Editor exportiert über "Export Runtime" ein python_stubs.zip mit je einer
Stub-Datei pro Callback-Modul (game_apply_functions.py, way_prompts.py, ...).
Dieses Skript vergleicht jede Stub-Datei mit dem echten Modul im Adventure und
schreibt pro Modul nur die Funktionen heraus, die hier noch NICHT existieren -
zum Einfuegen ins echte Modul.

Es nutzt dafuer die Logik aus missing_functions.py.

Beispiel:
    unzip python_stubs.zip -d stage_editor
    python3 apply_editor_stubs.py stage_editor
    # -> stage_editor/missing_<modul>.py mit den fehlenden Funktionen
"""
import argparse
import sys
from pathlib import Path

# missing_functions.py liegt im selben Verzeichnis wie dieses Skript.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import missing_functions as mf  # noqa: E402

# Reihenfolge = die vom Editor/Spiel verwendeten snake_case Modulnamen
# (vgl. module_map in game_state.py).
MODULES = [
    "game_apply_functions",
    "game_take_functions",
    "game_reveal_functions",
    "game_obstruction_check_functions",
    "place_prompts",
    "object_prompts",
    "way_prompts",
]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="apply_editor_stubs",
        description="Vergleicht die Editor-Stub-Module mit den echten Adventure-Modulen "
                    "und schreibt pro Modul die fehlenden Funktionen heraus.",
    )
    parser.add_argument("stubdir", type=Path,
                        help="Ordner mit den entpackten Editor-Stub-Dateien (z. B. game_apply_functions.py ...)")
    parser.add_argument("--game-dir", type=Path, default=Path(__file__).resolve().parent,
                        help="Ordner mit den echten Adventure-Modulen (Default: dieses Skript-Verzeichnis)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Ausgabeordner fuer die missing_<modul>.py Dateien (Default: <stubdir>)")
    args = parser.parse_args(argv)

    if not args.stubdir.is_dir():
        print(f"Fehler: Stub-Ordner nicht gefunden: {args.stubdir}", file=sys.stderr)
        return 2

    out_dir = args.out_dir or args.stubdir
    out_dir.mkdir(parents=True, exist_ok=True)

    total_missing = 0
    seen_any = False
    for mod in MODULES:
        stub = args.stubdir / f"{mod}.py"
        original = args.game_dir / f"{mod}.py"
        if not stub.exists():
            continue  # Editor hat fuer dieses Modul nichts referenziert
        seen_any = True
        try:
            staging_funcs = mf.function_names_in_file(stub)
            original_funcs = mf.function_names_in_file(original) if original.exists() else set()
        except SyntaxError as e:
            print(f"[{mod}] SyntaxError beim Parsen: {e}", file=sys.stderr)
            continue

        missing = sorted(n for n in staging_funcs if n not in original_funcs)
        if not missing:
            print(f"[{mod}] OK - keine fehlenden Funktionen ({len(staging_funcs)} referenziert).")
            continue

        blocks = mf.extract_function_blocks(stub, set(missing))
        header = [
            "# --- apply_editor_stubs Output ---",
            f"# Modul    : {mod}",
            f"# Original : {original}",
            f"# Stub     : {stub}",
            f"# Fehlend  : {len(missing)}: {', '.join(missing)}",
            "",
        ]
        out_file = out_dir / f"missing_{mod}.py"
        out_file.write_text("\n\n".join(header + blocks) + "\n", encoding="utf-8")
        total_missing += len(missing)
        print(f"[{mod}] {len(missing)} fehlende Funktion(en) -> {out_file}")

    if not seen_any:
        print("Keine Editor-Stub-Module im angegebenen Ordner gefunden "
              "(erwartet z. B. game_apply_functions.py).", file=sys.stderr)
        return 1

    print(f"\nFertig. Insgesamt {total_missing} fehlende Funktion(en).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
