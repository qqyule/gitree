"""
Print a directory tree using box-drawing characters, respecting .gitignore
rules found at the provided root.

Example format:

SketchLogic
├─ assets/
│  └─ logo.jpg
├─ backend/
│  └─ app.py
├─ skelo_ai/
│  ├─ __init__.py
│  ├─ boolean.py
│  ├─ draw.py
│  ├─ inference.py
│  ├─ label.py
│  ├─ wires.py
│  └─ circuit_parser.py
├─ CODE_OF_CONDUCT.md
├─ CONTRIBUTING.md
├─ SECURITY.md
├─ README.md
└─ LICENSE

Usage:
  python tree.py [PATH] [--max-depth N] [--all] [--ignore PATTERN ...] [--no-gitignore]

Notes:
- Fully faithful .gitignore support uses the 'pathspec' library.
  Install with: pip install pathspec
- If 'pathspec' isn't available, the script falls back to a basic parser
  that handles comments, blank lines, and simple globs, but not all edge cases
  (e.g., anchored patterns, '**', or complex negations).
"""
from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path
from typing import Iterable, List, Optional

# ----- Drawing chars -----
BRANCH = "├─ "
LAST   = "└─ "
VERT   = "│  "
SPACE  = "   "

# ----- Optional pathspec support -----
try:
    import pathspec  # type: ignore
except Exception:  # pragma: no cover
    pathspec = None  # handled gracefully below


class GitIgnoreMatcher:
    """
    Wraps .gitignore matching. Uses pathspec if available for full fidelity.
    Falls back to a simple fnmatch-based matcher otherwise.
    """
    def __init__(self, root: Path, enabled: bool = True):
        self.root = root
        self.enabled = enabled
        self._using_pathspec = False
        self._spec = None
        self._fallback_excludes: List[str] = []
        self._fallback_includes: List[str] = []

        if not enabled:
            return

        gi_path = root / ".gitignore"
        if not gi_path.is_file():
            return

        lines = gi_path.read_text(encoding="utf-8", errors="ignore").splitlines()

        if pathspec is not None:
            # Full-fidelity git wildmatch
            self._spec = pathspec.PathSpec.from_lines("gitwildmatch", lines)
            self._using_pathspec = True
        else:
            # Minimal fallback: strip comments/empties, split into exclude/include
            for raw in lines:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("\\#"):  # escaped '#'
                    line = line[1:]
                if line.startswith("!"):
                    self._fallback_includes.append(line[1:].strip())
                else:
                    self._fallback_excludes.append(line)

            # Warn once about reduced fidelity
            print(
                "[tree] 'pathspec' not installed: using basic .gitignore fallback. "
                "Run 'pip install pathspec' for full support.",
                file=sys.stderr,
            )

    def is_ignored(self, path: Path) -> bool:
        if not self.enabled:
            return False

        rel = path.relative_to(self.root)
        rel_posix = rel.as_posix()

        if self._using_pathspec and self._spec is not None:
            # pathspec handles directories and files; try both path and path with trailing slash
            if self._spec.match_file(rel_posix):
                return True
            # If it's a directory, patterns ending with '/' will match only with slash; pathspec covers this,
            # but adding an extra check is harmless.
            if path.is_dir() and self._spec.match_file(rel_posix + "/"):
                return True
            return False

        # --- Fallback behavior (approximate) ---
        # If any exclude matches -> ignored, unless an include explicitly matches.
        def _any_match(patterns: List[str]) -> bool:
            # Support a very rough interpretation of directory patterns ending with '/'
            if path.is_dir():
                # Try matching the directory itself and its path with trailing slash
                targets = [rel_posix, rel_posix + "/"]
            else:
                targets = [rel_posix]
            # Also try basename matches for common 'node_modules/'-style patterns
            targets.append(path.name)
            return any(
                fnmatch.fnmatchcase(t, pat) or (pat.endswith("/") and fnmatch.fnmatchcase(t + "/", pat))
                for t in targets for pat in patterns
            )

        if _any_match(self._fallback_excludes):
            # Check for negation (include) override
            if _any_match(self._fallback_includes):
                return False
            return True
        return False


def list_entries(
    directory: Path,
    show_all: bool,
    extra_ignores: List[str],
    gi: GitIgnoreMatcher,
) -> List[Path]:
    try:
        items = list(directory.iterdir())
    except PermissionError:
        return []

    def _hidden(p: Path) -> bool:
        return p.name.startswith(".")

    def _matches_extra(p: Path) -> bool:
        # extra ignore patterns are applied to relative posix path from the git root if possible,
        # otherwise from the provided directory.
        try:
            rel = p.relative_to(gi.root).as_posix()
        except Exception:
            rel = p.name
        return any(fnmatch.fnmatchcase(rel, pat) or fnmatch.fnmatchcase(p.name, pat) for pat in extra_ignores)

    filtered: List[Path] = []
    for e in items:
        if not show_all and _hidden(e):
            continue
        if gi.is_ignored(e):
            continue
        if _matches_extra(e):
            continue
        filtered.append(e)

    # Directories first, then files; case-insensitive alphabetical
    filtered.sort(key=lambda x: (x.is_file(), x.name.lower()))
    return filtered


def draw_tree(
    root: Path,
    max_depth: Optional[int],
    show_all: bool,
    extra_ignores: List[str],
    respect_gitignore: bool,
) -> None:
    gi = GitIgnoreMatcher(root, enabled=respect_gitignore)

    print(root.name)

    def _recurse(dirpath: Path, prefix: str, depth: int) -> None:
        if max_depth is not None and depth >= max_depth:
            return
        entries = list_entries(dirpath, show_all, extra_ignores, gi)
        for idx, entry in enumerate(entries):
            is_last = idx == len(entries) - 1
            connector = LAST if is_last else BRANCH
            suffix = "/" if entry.is_dir() else ""
            print(prefix + connector + entry.name + suffix)
            if entry.is_dir():
                _recurse(entry, prefix + (SPACE if is_last else VERT), depth + 1)

    if root.is_dir():
        _recurse(root, "", 0)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Print a directory tree (respects .gitignore).")
    ap.add_argument("path", nargs="?", default=".", help="Root path (default: .)")
    ap.add_argument("--max-depth", type=int, default=None, help="Limit recursion depth")
    ap.add_argument("--all", "-a", action="store_true", help="Include hidden files/dirs (still respects .gitignore)")
    ap.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        help="Additional glob patterns to ignore (e.g., --ignore __pycache__ *.pyc build/)",
    )
    ap.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Do not read or apply .gitignore",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.path).resolve()

    if not root.exists():
        print(f"Error: path not found: {root}", file=sys.stderr)
        sys.exit(1)

    draw_tree(
        root=root,
        max_depth=args.max_depth,
        show_all=args.all,
        extra_ignores=args.ignore,
        respect_gitignore=not args.no_gitignore,
    )


if __name__ == "__main__":
    main()
