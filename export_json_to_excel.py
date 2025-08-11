
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Union

import pandas as pd

# -------- Helpers --------

def is_json_lines(path: Path) -> bool:
    """Quick heuristic: try reading the first non-empty line as JSON object."""
    try:
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # If it's valid JSON and it's a dict or list, assume JSON Lines
                try:
                    parsed = json.loads(line)
                    return True if isinstance(parsed, (dict, list)) else False
                except json.JSONDecodeError:
                    return False
        return False
    except Exception:
        return False

def load_json_to_df(path: Path) -> pd.DataFrame:
    """Load a JSON file into a DataFrame, handling JSON Lines and nested structures."""
    # 1) Try JSON Lines via pandas
    try:
        return pd.read_json(path, lines=True)
    except ValueError:
        pass  # not JSONL or incompatible

    # 2) Try standard JSON via json.load
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    # Normalize to tabular
    if isinstance(data, list):
        # list of dicts or scalars
        if len(data) == 0:
            return pd.DataFrame()
        if isinstance(data[0], dict):
            return pd.json_normalize(data, sep='.')  # flatten nested dicts
        else:
            return pd.DataFrame({'value': data})
    elif isinstance(data, dict):
        # single dict -> one-row table
        return pd.json_normalize(data, sep='.')
    else:
        # scalar
        return pd.DataFrame({'value': [data]})

def sanitize_sheet_name(name: str) -> str:
    """Excel sheet name rules: max 31 chars, cannot contain : \ / ? * [ ]"""
    name = re.sub(r'[:\\/\?\*\[\]]', '_', name)
    if len(name) > 31:
        name = name[:31]
    # Sheet name cannot be empty or only quotes
    return name or 'Sheet'

def uniquify(name: str, taken: set) -> str:
    base = name
    i = 1
    while name in taken:
        suffix = f"_{i}"
        trunc = 31 - len(suffix)
        name = (base[:trunc] if len(base) > trunc else base) + suffix
        i += 1
    taken.add(name)
    return name

def auto_column_widths(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame):
    """Best-effort column width adjustment using openpyxl engine."""
    try:
        ws = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns, 1):
            # Determine max length in this column
            try:
                series = df[col].astype(str)
            except Exception:
                series = df[col].map(str)
            max_len = max([len(str(col))] + [len(s) for s in series.tolist()]) if len(df) else len(str(col))
            ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = min(max_len + 2, 60)
    except Exception:
        # Ignore if engine not openpyxl or something else goes wrong
        pass

# -------- Main --------

def find_json_files(root: Path, patterns: List[str], exclude: List[str]) -> List[Path]:
    files = []
    for pat in patterns:
        files.extend(root.rglob(pat))
    # Exclude by substring match
    if exclude:
        files = [p for p in files if not any(ex in str(p) for ex in exclude)]
    # Keep unique & sorted
    files = sorted(set(files))
    return files

def main():
    parser = argparse.ArgumentParser(description="Export JSON/JSONL files to a single Excel workbook.")
    parser.add_argument("--root", type=str, default=".", help="Project root to scan (default: current folder)")
    parser.add_argument("--out", type=str, default="json_export.xlsx", help="Output Excel filename")
    parser.add_argument("--patterns", nargs="*", default=["*.json"], help="Glob patterns to include (default: *.json)")
    parser.add_argument("--exclude", nargs="*", default=[], help="Path substrings to exclude (e.g., --exclude venv .git)")
    parser.add_argument("--sheet-from", choices=["stem", "parent", "relative"], default="stem",
                        help="How to build sheet names: stem (file name), parent (parent folder), relative (relative path)" )
    parser.add_argument("--relative-to", type=str, default=None, help="Base for --sheet-from=relative (default: --root)" )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    rel_base = Path(args.relative_to).resolve() if args.relative_to else root

    files = find_json_files(root, args.patterns, args.exclude)
    if not files:
        print("No JSON files found.")
        return

    print(f"Found {len(files)} JSON files. Exporting to {args.out} ...")
    taken_names = set()
    with pd.ExcelWriter(args.out, engine="openpyxl") as writer:
        for path in files:
            try:
                df = load_json_to_df(path)
            except Exception as e:
                print(f"[SKIP] {path}: {e}")
                continue

            if args.sheet_from == "stem":
                base = path.stem
            elif args.sheet_from == "parent":
                base = path.parent.name
            else:  # relative
                try:
                    base = str(path.relative_to(rel_base))
                except ValueError:
                    base = str(path)

            name = sanitize_sheet_name(base)
            name = uniquify(name, taken_names)

            # Ensure something to write
            if df is None or df.empty:
                df = pd.DataFrame({"info": ["(empty or non-tabular JSON)"]})

            df.to_excel(writer, sheet_name=name, index=False)
            auto_column_widths(writer, name, df)
            print(f" - {name} <= {path}")

    print("Done.")

if __name__ == "__main__":
    main()
