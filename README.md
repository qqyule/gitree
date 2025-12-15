# PrintStruct

A Python CLI script for printing the structure of your project in a visually easy-to-read format. Respects `.gitignore` files when present so ignored files and folders are omitted from the output.

**Features**

- Print a tree view of a project directory (default: current directory).
- Respects `.gitignore` to filter ignored files.
- Minimal, dependency-free Python script.

**Requirements**

- Python 3.8 or newer.

**Quick start**

1. Clone or copy this repository.
2. Run the script from your project root:

```bash
python structure.py
```

To print a different directory:

```bash
python structure.py path/to/project
```

If the directory contains a `.gitignore` file, ignored paths will be omitted from the printed structure.

**Usage**

- `python structure.py [PATH]` — prints the structure for `PATH` (defaults to `.`).
- `-h` / `--help` — shows help if the script provides an argument parser.

**Notes**

- This README assumes `structure.py` is a CLI-style script. If the script exposes additional flags (depth, show-hidden, output format), refer to its `--help` output for exact usage.

**Contributing**

- Feel free to open issues or submit pull requests to improve formatting, add features (e.g. colorized output), or add tests.

**License**

- MIT
