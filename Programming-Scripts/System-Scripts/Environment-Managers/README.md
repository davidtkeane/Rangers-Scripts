# Python Environment Managers

Two powerful CLI tools for managing Python virtual environments and Conda environments.

## Scripts

| Script | Version | Description |
|--------|---------|-------------|
| `venv_setup.py` | v2.3 | Python Virtual Environment Manager |
| `conda_setup.py` | v5.6 | Conda Environment Manager |

## Features

### venv_setup.py - Virtual Environment Manager

- Create, activate, delete virtual environments
- Auto-detect venv in current directory
- Show venv info (size, packages, Python version)
- Install from requirements.txt / pyproject.toml
- Auto-offer to install dependencies when activating
- Search installed packages
- Update all packages
- Cross-platform (macOS, Linux, Windows)

### conda_setup.py - Conda Environment Manager

- Create, clone, delete conda environments
- Auto-detect conda environment
- Export/import environment.yml
- Install/uninstall packages
- Search packages in conda-forge
- Show environment info and stats
- Auto-offer to install dependencies when switching environments

## Quick Start

### Installation

```bash
# Make executable
chmod +x venv_setup.py conda_setup.py

# Optional: Add to PATH or create alias
alias venv_setup='python3 /path/to/venv_setup.py'
alias conda_setup='python3 /path/to/conda_setup.py'
```

### Usage

```bash
# Interactive menu
python3 venv_setup.py
python3 conda_setup.py

# CLI commands
python3 venv_setup.py --list          # List all venvs
python3 venv_setup.py --detect        # Auto-detect venv
python3 venv_setup.py --info myenv    # Show venv info
python3 venv_setup.py --help          # Full help

python3 conda_setup.py --list         # List all envs
python3 conda_setup.py --detect       # Auto-detect env
python3 conda_setup.py --info myenv   # Show env info
python3 conda_setup.py --search numpy # Search packages
python3 conda_setup.py --help         # Full help
```

## Requirements

- Python 3.6+
- colorama
- tqdm
- For conda_setup: Anaconda/Miniconda installed

## Easter Eggs

Both scripts have hidden features! Try `--bunny` for a surprise.

---

Created by David (IrishRanger) and Ranger (AIRanger)

Rangers lead the way!
