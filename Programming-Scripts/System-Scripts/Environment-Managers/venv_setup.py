#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Python Virtual Environment Manager
A sophisticated tool for managing Python virtual environments.
Cross-platform support for Windows, macOS, and Linux.
Version: 2.3 - Enhanced Edition

New in 2.3:
- Auto-offer to install dependencies when activating environment
- Support for requirements.txt, requirements-dev.txt, pyproject.toml

New in 2.2:
- Auto-detect venv in current directory
- Show venv info (size, packages, Python version)
- Install from requirements.txt
- Uninstall packages
- Update all packages
- Search installed packages
"""

import os
import sys
import subprocess
import shutil
import time
import logging
import json
import argparse
import platform
import getpass
from pathlib import Path
from colorama import init, Fore, Style, Back
from tqdm import tqdm

# Platform-specific settings
PLATFORM = platform.system().lower()
IS_WINDOWS = PLATFORM == 'windows'
IS_MACOS = PLATFORM == 'darwin'
IS_LINUX = PLATFORM == 'linux'

# Get user home directory in a cross-platform way
HOME_DIR = str(Path.home())

# Initialize colorama with Windows support
init(autoreset=True, strip=False)

# Enhanced color constants
CYAN = Fore.CYAN
GREEN = Fore.GREEN + Style.BRIGHT
YELLOW = Fore.YELLOW
RED = Fore.RED
MAGENTA = Fore.MAGENTA + Style.BRIGHT
BLUE = Fore.BLUE + Style.BRIGHT
WHITE = Fore.WHITE + Style.BRIGHT
GRAY = Fore.WHITE + Style.DIM
PURPLE = Fore.MAGENTA
RESET = Style.RESET_ALL
HIGHLIGHT = Back.BLUE + Fore.WHITE + Style.BRIGHT
SECTION_HEADER = Back.CYAN + Fore.BLACK + Style.BRIGHT
HEADER_BG = Back.BLUE + Fore.WHITE + Style.BRIGHT
MENU_HEADER = Back.CYAN + Fore.BLACK + Style.BRIGHT
SECTION_BG = Back.MAGENTA + Fore.WHITE + Style.BRIGHT
OPTION_FG = Fore.GREEN + Style.BRIGHT
WARNING_BG = Back.YELLOW + Fore.BLACK + Style.BRIGHT
ERROR_BG = Back.RED + Fore.WHITE + Style.BRIGHT

def request_sudo_password():
    """Request sudo password at the start of the script."""
    print()
    print(f"{WARNING_BG} Sudo Access Required {RESET}")
    print()
    print(f"{YELLOW}This script requires sudo privileges for:{RESET}")
    print()
    print(f"{WHITE}1. Installing packages system-wide{RESET}")
    print(f"{WHITE}2. Managing protected directories{RESET}")
    print(f"{WHITE}3. Updating system Python installations{RESET}")
    print()
    print(f"{YELLOW}You can disable this prompt using --sudo-off{RESET}\n")
    # if config['sudo_off']:
    #     return
    """Request sudo password at the start of the script."""
    if os.geteuid() != 0:  # Check if not running as root
        print(f"{YELLOW}This script requires sudo privileges.{RESET}")
        try:
            password = getpass.getpass(f"{CYAN}Enter sudo password: {RESET}")
            cmd = ['sudo', '-S', 'echo', 'Sudo access granted']
            result = subprocess.run(cmd, input=f"{password}\n", text=True, capture_output=True)
            if result.returncode != 0:
                print(f"{RED}Invalid sudo password. Exiting.{RESET}")
                sys.exit(1)
            os.environ['SUDO_ASKPASS'] = '/bin/echo'
        except Exception as e:
            print(f"{RED}Failed to get sudo access: {e}{RESET}")
            sys.exit(1)

# Check if running a read-only CLI command (no sudo needed)
def needs_sudo():
    """Check if the current command needs sudo access."""
    read_only_args = ['--list', '--detect', '--info', '--packages', '--help', '-h', '--bunny']
    for arg in sys.argv[1:]:
        if arg in read_only_args or arg.startswith('--info=') or arg.startswith('--packages='):
            return False
    return True

# Request sudo password only when needed
if not platform.system().lower() == 'windows' and needs_sudo():
    # Skip sudo for read-only operations
    if len(sys.argv) > 1:
        request_sudo_password()
    # For interactive mode, we'll request sudo later if needed


def print_success(message):
    """Print a success message with a checkmark."""
    print(f"\n{GREEN}✓ {message}{RESET}")

def print_error(message):
    """Print an error message with an X."""
    print(f"\n{RED}✗ {message}{RESET}")

def print_warning(message):
    """Print a warning message with an exclamation mark."""
    print(f"\n{YELLOW}! {message}{RESET}")

def print_info(message):
    """Print an info message with an arrow."""
    print(f"{BLUE}→ {message}{RESET}")

def confirm_action(message="Are you sure?"):
    """Get confirmation from the user."""
    return input(f"{YELLOW}{message} (y/n): {RESET}").lower().startswith('y')

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

# Display a warning message with an exclamation mark.
def display_warning(message):
    """Print a warning message with an exclamation mark."""
    print(f"\n{YELLOW}! {message}{RESET}")

# Configuration and Logging Setup
LOG_DIR = '/Users/ranger/.db/logs'
if not os.path.exists(LOG_DIR):
    display_warning(f"Directory {LOG_DIR} does not exist. Files will be saved in the script's folder.")
    LOG_DIR = os.getcwd()
elif not os.access(LOG_DIR, os.W_OK):
    display_warning(f"No write permission for {LOG_DIR}. Files will be saved in the script's folder.")
    LOG_DIR = os.getcwd()

# Setup logging first
LOG_FILE = os.path.join(LOG_DIR, 'venv_manager.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration file setup
CONFIG_DIR = os.path.join("/Users/ranger/.db/configs")
CONFIG_FILE = os.path.join(CONFIG_DIR, 'venv_manager_config.json')
DEFAULT_CONFIG = {
    'python_version': sys.version.split()[0],
    'show_animations': True,
    'confirm_deletions': True,
    'venv_location': 'current',  # or 'custom'
    'custom_venv_path': str(Path.home() / '.venvs'),
    'auto_activate': True,
    'theme': 'default'
}

def load_config():
    """Load configuration from file or create default if not exists."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                loaded_config = json.load(f)
                # Merge with defaults to ensure all required keys exist
                config = {**DEFAULT_CONFIG, **loaded_config}
                logging.info(f"Configuration loaded from {CONFIG_FILE}")
                return config
        else:
            # Create default config file
            save_config(DEFAULT_CONFIG)
            logging.info(f"Created new configuration file at {CONFIG_FILE}")
            return DEFAULT_CONFIG
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error loading config from {CONFIG_FILE}: {e}")
        display_warning(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        logging.info(f"Configuration saved to {CONFIG_FILE}")
        return True
    except IOError as e:
        logging.error(f"Error saving config to {CONFIG_FILE}: {e}")
        display_warning(f"Error saving config: {e}")
        return False

# Initialize configuration
config = load_config()

def show_spinner(seconds, text="Processing"):
    """Show a spinning cursor while processing."""
    spinners = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    for _ in range(int(seconds * 10)):
        for spinner in spinners:
            sys.stdout.write(f'\r{CYAN}{spinner} {text}...{RESET}')
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write('\r' + ' ' * (len(text) + 15) + '\r')
    sys.stdout.flush()

def show_progress(task_name, steps=50):
    """Show a progress bar with customized styling."""
    print(f"\n{CYAN}⚡ {task_name}...{RESET}")
    for _ in tqdm(range(steps), 
                 desc=f"{WHITE}{task_name}{RESET}",
                 bar_format='{l_bar}{bar:30}{r_bar}',
                 colour='green'):
        time.sleep(0.02)
    print()

def check_admin_requirements():
    """Check and explain admin requirements based on platform."""
    admin_needed = False
    explanation = ""
    
    if IS_WINDOWS:
        # Check if running with admin privileges
        try:
            import ctypes
            # Properly handle Windows-specific code to avoid Pylance errors
            if IS_WINDOWS and hasattr(ctypes, 'windll'):  # type: ignore
                # This code only runs on Windows
                shell32 = ctypes.WinDLL('shell32')  # type: ignore
                admin_needed = not shell32.IsUserAnAdmin()
            else:
                admin_needed = False
            explanation = (
                "Administrator privileges may be required on Windows to:\n"
                "1. Install packages globally\n"
                "2. Create environments in protected directories\n"
                "3. Modify system-wide Python installations"
            )
        except Exception:
            admin_needed = False
    elif IS_LINUX or IS_MACOS:
        # Check if user has sudo privileges
        try:
            subprocess.run(['sudo', '-n', 'true'], check=True, capture_output=True)
            admin_needed = False
        except:
            admin_needed = True
            explanation = (
                f"{'sudo' if IS_LINUX else 'administrator'} privileges may be required to:\n"
                "1. Install packages system-wide\n"
                "2. Modify protected directories\n"
                "3. Update system Python installations"
            )
    
    if admin_needed:
        print_warning(explanation)
        print_info("You can still use most features without privileges")
    
    return admin_needed

def print_header():
    """Print a beautiful header with version and additional info."""
    clear_screen()
    print(f"{MAGENTA}╔══════════════════════════════════════════════╗{RESET}")
    print(f"{MAGENTA}║{HEADER_BG}         Python Virtual Environment Manager   {RESET}{MAGENTA}║{RESET}")
    print(f"{MAGENTA}║{WHITE}            Version 2.3 - Enhanced            {RESET}{MAGENTA}║{RESET}")
    print(f"{MAGENTA}╚══════════════════════════════════════════════╝{RESET}")
    
    print(f"{MENU_HEADER} System Information {RESET}")
    print(f"{BLUE}OS:     {WHITE}{platform.system()} {platform.release()}{RESET}")
    print(f"{BLUE}Python: {WHITE}{sys.version.split()[0]}{RESET}")
    print(f"{BLUE}venv:   {WHITE}{'Available' if has_venv() else 'Not found'}{RESET}")
    print()

def has_venv():
    """Check if venv module is available."""
    try:
        subprocess.run([sys.executable, "-m", "venv", "--help"], 
                      capture_output=True, 
                      check=True)
        return True
    except:
        return False

def get_venv_path():
    """Get the path where virtual environments should be created."""
    if config['venv_location'] == 'custom':
        path = Path(config['custom_venv_path'])
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    return os.getcwd()

def check_existing_venvs():
    """Get list of Python virtual environments."""
    venv_path = get_venv_path()
    venvs = []
    
    for d in os.listdir(venv_path):
        full_path = os.path.join(venv_path, d)
        if os.path.isdir(full_path):
            if (os.path.exists(os.path.join(full_path, 'Scripts')) or  # Windows
                os.path.exists(os.path.join(full_path, 'bin'))):       # Unix
                venvs.append(d)
    
    return sorted(venvs)

def show_activation_instructions(venv_name):
    """Show how to activate a virtual environment."""
    venv_path = os.path.join(get_venv_path(), venv_name)

    if IS_WINDOWS:
        cmd = os.path.join(venv_path, 'Scripts', 'activate.bat')
        relative_cmd = f".\\{venv_name}\\Scripts\\activate.bat"
    else:
        cmd = f"source {os.path.join(venv_path, 'bin', 'activate')}"
        relative_cmd = f"source {venv_name}/bin/activate"

    print(f"\n{CYAN}You can activate this environment in two ways:{RESET}")
    print(f"\n{GREEN}1. Using full path:{RESET}")
    print(f"{GREEN}{cmd}{RESET}")
    print(f"\n{GREEN}2. From the current directory:{RESET}")
    print(f"{GREEN}{relative_cmd}{RESET}")
    print(f"\n{YELLOW}Note: The shorter command works when you're in the same directory as the venv{RESET}")

    # Log both activation commands
    logging.info(f"Action: Created activation commands - Full: {cmd}, Relative: {relative_cmd}")

    # Check for requirements.txt and offer to install
    check_and_offer_requirements_install(venv_name)

    return cmd, relative_cmd

def check_and_offer_requirements_install(venv_name):
    """Check for requirements.txt and offer to install dependencies."""
    cwd = os.getcwd()

    # Check for various requirement files
    req_files = []
    for f in ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt', 'dev-requirements.txt']:
        if os.path.exists(os.path.join(cwd, f)):
            req_files.append(f)

    # Also check for pyproject.toml with dependencies
    has_pyproject = os.path.exists(os.path.join(cwd, 'pyproject.toml'))

    if not req_files and not has_pyproject:
        return

    # Show what was found
    print(f"\n{CYAN}📦 Dependency files found in current directory:{RESET}")
    for f in req_files:
        print(f"   {GREEN}• {f}{RESET}")
    if has_pyproject:
        print(f"   {GREEN}• pyproject.toml{RESET}")

    # Ask if user wants to install
    if len(req_files) == 1 and not has_pyproject:
        if confirm_action(f"Install from {req_files[0]}?"):
            install_requirements_into_venv(venv_name, req_files[0])
    elif req_files or has_pyproject:
        print(f"\n{YELLOW}Would you like to install dependencies into '{venv_name}'?{RESET}")
        options = []
        for i, f in enumerate(req_files, 1):
            print(f"{WHITE}{i}. Install from {f}{RESET}")
            options.append(f)
        if has_pyproject:
            print(f"{WHITE}{len(options)+1}. Install from pyproject.toml (pip install -e .){RESET}")
            options.append('pyproject.toml')
        if len(req_files) > 1:
            print(f"{WHITE}{len(options)+1}. Install all requirements files{RESET}")
        print(f"{WHITE}0. Skip{RESET}")

        choice = input(f"{CYAN}Enter choice: {RESET}").strip()

        if choice == '0' or not choice:
            print_info("Skipping dependency installation")
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                selected = options[idx]
                if selected == 'pyproject.toml':
                    install_pyproject_into_venv(venv_name)
                else:
                    install_requirements_into_venv(venv_name, selected)
            elif idx == len(options) and len(req_files) > 1:
                # Install all requirements files
                for f in req_files:
                    install_requirements_into_venv(venv_name, f)

def install_requirements_into_venv(venv_name, req_file):
    """Install dependencies from requirements.txt into venv."""
    venv_path = os.path.join(get_venv_path(), venv_name)

    if IS_WINDOWS:
        pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
    else:
        pip_path = os.path.join(venv_path, 'bin', 'pip')

    try:
        show_progress(f"Installing from {req_file}")
        subprocess.run(
            [pip_path, 'install', '-r', req_file],
            check=True,
            capture_output=True
        )
        print_success(f"Dependencies from {req_file} installed successfully!")
        logging.info(f"Installed dependencies from {req_file} into {venv_name}")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install from {req_file}")
        logging.error(f"Failed to install from {req_file}: {e}")

def install_pyproject_into_venv(venv_name):
    """Install package from pyproject.toml in editable mode."""
    venv_path = os.path.join(get_venv_path(), venv_name)

    if IS_WINDOWS:
        pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
    else:
        pip_path = os.path.join(venv_path, 'bin', 'pip')

    try:
        show_progress("Installing from pyproject.toml")
        subprocess.run(
            [pip_path, 'install', '-e', '.'],
            check=True,
            capture_output=True
        )
        print_success("Package installed from pyproject.toml successfully!")
        logging.info(f"Installed from pyproject.toml into {venv_name}")
    except subprocess.CalledProcessError as e:
        print_error("Failed to install from pyproject.toml")
        logging.error(f"Failed to install from pyproject.toml: {e}")

def create_venv(name=None, with_pip=True):
    """Create a new virtual environment."""
    if not name:
        name = input(f"{YELLOW}Enter virtual environment name: {RESET}")
    
    if not name.replace('_', '').isalnum():
        print_error("Environment name must be alphanumeric or contain underscores")
        return None
    
    venv_path = os.path.join(get_venv_path(), name)
    
    try:
        show_progress(f"Creating virtual environment '{name}'")
        cmd = [sys.executable, "-m", "venv"]
        cmd.append(venv_path)
        
        subprocess.run(cmd, check=True, capture_output=True)
        print_success(f"Virtual environment '{name}' created successfully!")
        
        # Ask user if they want to activate now
        activate_now = input(f"\n{YELLOW}Would you like to activate this environment now? (y/n): {RESET}").lower().startswith('y')
        
        full_cmd, relative_cmd = show_activation_instructions(name)
        
        if activate_now:
            print(f"\n{CYAN}To activate, copy and run this command in your terminal:{RESET}")
            print(f"{GREEN}{relative_cmd}{RESET}")
            
            # Log the user's choice
            logging.info(f"Action: User chose to activate environment {name} immediately")
        else:
            print(f"\n{YELLOW}You can activate the environment later using the commands above{RESET}")
            logging.info(f"Action: User chose to activate environment {name} later")
        
        # Log the creation and full path
        logging.info(f"Action: Created virtual environment at {venv_path}")
        return name
        
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create virtual environment: {e}")
        logging.error(f"Failed to create virtual environment {name}: {e}")
        return None

def show_deactivation_instructions():
    """Show how to deactivate a virtual environment."""
    print(f"\n{CYAN}To deactivate the current environment, run:{RESET}")
    print(f"{GREEN}deactivate{RESET}")
    print(f"{YELLOW}Note: Run this command in your terminal when done{RESET}")

def delete_venv(name):
    """Delete a virtual environment."""
    if not config['confirm_deletions'] or input(
        f"{RED}Are you sure you want to delete '{name}'? (y/n): {RESET}"
    ).lower().startswith('y'):
        try:
            venv_path = os.path.join(get_venv_path(), name)
            show_progress(f"Deleting virtual environment '{name}'")
            shutil.rmtree(venv_path)
            print_success(f"Virtual environment '{name}' deleted successfully")
            
            # Enhance logging to include full paths and actions
            logging.info(f"Action: Deleted virtual environment at {venv_path}")
        except Exception as e:
            print_error(f"Failed to delete virtual environment: {e}")
            logging.error(f"Failed to delete virtual environment {name}: {e}")
    else:
        print_warning("Deletion cancelled")

def list_packages(venv_name):
    """List installed packages in a virtual environment."""
    try:
        if IS_WINDOWS:
            pip = os.path.join(get_venv_path(), venv_name, 'Scripts', 'pip.exe')
        else:
            pip = os.path.join(get_venv_path(), venv_name, 'bin', 'pip')
        
        show_spinner(1, "Retrieving package list")
        result = subprocess.run(
            [pip, 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"\n{CYAN}Packages in virtual environment '{venv_name}':{RESET}")
        print(f"{WHITE}{result.stdout}{RESET}")
        logging.info(f"Listed packages for: {venv_name}")
    except subprocess.CalledProcessError:
        print_error("Failed to list packages")
        logging.error(f"Failed to list packages for {venv_name}")

def export_requirements(venv_name):
    """Export installed packages to requirements.txt."""
    try:
        if IS_WINDOWS:
            pip = os.path.join(get_venv_path(), venv_name, 'Scripts', 'pip.exe')
        else:
            pip = os.path.join(get_venv_path(), venv_name, 'bin', 'pip')
        
        output_file = f"{venv_name}_requirements.txt"
        show_progress("Exporting requirements")
        
        result = subprocess.run(
            [pip, 'freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        
        with open(output_file, 'w') as f:
            f.write(result.stdout)
        
        print_success(f"Requirements exported to {output_file}")
        
        # Enhance logging to include full paths and actions
        logging.info(f"Action: Exported requirements to {output_file}")
    except Exception as e:
        print_error(f"Failed to export requirements: {e}")
        logging.error(f"Failed to export requirements for {venv_name}: {e}")

def install_package(venv_name):
    """Install a package in the virtual environment."""
    package = input(f"{YELLOW}Enter package name (and version if needed, e.g. 'requests==2.25.1'): {RESET}")
    
    try:
        if IS_WINDOWS:
            pip = os.path.join(get_venv_path(), venv_name, 'Scripts', 'pip.exe')
        else:
            pip = os.path.join(get_venv_path(), venv_name, 'bin', 'pip')
        
        show_progress(f"Installing {package}")
        subprocess.run(
            [pip, 'install', package],
            check=True,
            capture_output=True
        )
        print_success(f"Package '{package}' installed successfully")
        
        # Enhance logging to include full paths and actions
        logging.info(f"Action: Installed package {package} in {venv_path}")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install package: {e}")
        logging.error(f"Failed to install {package} in {venv_name}: {e}")

def upgrade_pip(venv_name):
    """Upgrade pip in the virtual environment."""
    try:
        if IS_WINDOWS:
            pip = os.path.join(get_venv_path(), venv_name, 'Scripts', 'pip.exe')
        else:
            pip = os.path.join(get_venv_path(), venv_name, 'bin', 'pip')
        
        show_progress("Upgrading pip")
        subprocess.run(
            [pip, 'install', '--upgrade', 'pip'],
            check=True,
            capture_output=True
        )
        print_success("Pip upgraded successfully")
        logging.info(f"Upgraded pip in {venv_name}")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to upgrade pip: {e}")
        logging.error(f"Failed to upgrade pip in {venv_name}: {e}")

def detect_local_venv():
    """Auto-detect virtual environment in current directory."""
    cwd = os.getcwd()
    common_venv_names = ['venv', 'env', '.venv', '.env', 'virtualenv']

    detected = []
    for name in common_venv_names:
        venv_path = os.path.join(cwd, name)
        if os.path.isdir(venv_path):
            if (os.path.exists(os.path.join(venv_path, 'Scripts')) or
                os.path.exists(os.path.join(venv_path, 'bin'))):
                detected.append(name)

    # Also check for any directory that looks like a venv
    for d in os.listdir(cwd):
        if d not in detected and d not in common_venv_names:
            full_path = os.path.join(cwd, d)
            if os.path.isdir(full_path):
                if (os.path.exists(os.path.join(full_path, 'Scripts')) or
                    os.path.exists(os.path.join(full_path, 'bin'))):
                    # Check for pyvenv.cfg to confirm it's a venv
                    if os.path.exists(os.path.join(full_path, 'pyvenv.cfg')):
                        detected.append(d)

    return detected

def get_venv_size(venv_path):
    """Calculate the size of a virtual environment."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(venv_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)

    # Convert to human readable
    for unit in ['B', 'KB', 'MB', 'GB']:
        if total_size < 1024:
            return f"{total_size:.1f} {unit}"
        total_size /= 1024
    return f"{total_size:.1f} TB"

def get_venv_python_version(venv_name):
    """Get Python version used in a virtual environment."""
    venv_path = os.path.join(get_venv_path(), venv_name)
    pyvenv_cfg = os.path.join(venv_path, 'pyvenv.cfg')

    if os.path.exists(pyvenv_cfg):
        with open(pyvenv_cfg, 'r') as f:
            for line in f:
                if line.startswith('version'):
                    return line.split('=')[1].strip()
    return "Unknown"

def count_packages(venv_name):
    """Count installed packages in a virtual environment."""
    try:
        if IS_WINDOWS:
            pip = os.path.join(get_venv_path(), venv_name, 'Scripts', 'pip.exe')
        else:
            pip = os.path.join(get_venv_path(), venv_name, 'bin', 'pip')

        result = subprocess.run(
            [pip, 'list', '--format=freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        packages = [p for p in result.stdout.strip().split('\n') if p]
        return len(packages)
    except:
        return 0

def show_venv_info(venv_name):
    """Display detailed information about a virtual environment."""
    venv_path = os.path.join(get_venv_path(), venv_name)

    print(f"\n{SECTION_HEADER} Virtual Environment Info {RESET}\n")

    # Basic info
    print(f"{BLUE}Name:           {WHITE}{venv_name}{RESET}")
    print(f"{BLUE}Path:           {WHITE}{venv_path}{RESET}")
    print(f"{BLUE}Python Version: {WHITE}{get_venv_python_version(venv_name)}{RESET}")
    print(f"{BLUE}Size:           {WHITE}{get_venv_size(venv_path)}{RESET}")
    print(f"{BLUE}Packages:       {WHITE}{count_packages(venv_name)}{RESET}")

    # Check for requirements.txt
    req_file = os.path.join(os.path.dirname(venv_path), 'requirements.txt')
    if os.path.exists(req_file):
        print(f"{BLUE}Requirements:   {GREEN}Found (requirements.txt){RESET}")
    else:
        print(f"{BLUE}Requirements:   {YELLOW}Not found{RESET}")

    # Activation command
    if IS_WINDOWS:
        activate_cmd = f".\\{venv_name}\\Scripts\\activate.bat"
    else:
        activate_cmd = f"source {venv_name}/bin/activate"

    print(f"\n{CYAN}Quick Activate:{RESET}")
    print(f"{GREEN}{activate_cmd}{RESET}")

    logging.info(f"Displayed info for venv: {venv_name}")

def install_requirements(venv_name):
    """Install packages from requirements.txt."""
    venv_path = os.path.join(get_venv_path(), venv_name)

    # Look for requirements.txt in common locations
    possible_paths = [
        os.path.join(os.path.dirname(venv_path), 'requirements.txt'),
        os.path.join(get_venv_path(), 'requirements.txt'),
        'requirements.txt'
    ]

    req_file = None
    for path in possible_paths:
        if os.path.exists(path):
            req_file = path
            break

    if not req_file:
        req_file = input(f"{YELLOW}Enter path to requirements.txt: {RESET}")
        if not os.path.exists(req_file):
            print_error("Requirements file not found")
            return

    try:
        if IS_WINDOWS:
            pip = os.path.join(venv_path, 'Scripts', 'pip.exe')
        else:
            pip = os.path.join(venv_path, 'bin', 'pip')

        # Count packages to install
        with open(req_file, 'r') as f:
            pkg_count = len([l for l in f.readlines() if l.strip() and not l.startswith('#')])

        print(f"\n{CYAN}Installing {pkg_count} packages from {req_file}...{RESET}")
        show_progress(f"Installing packages", steps=pkg_count * 10)

        result = subprocess.run(
            [pip, 'install', '-r', req_file],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print_success(f"Installed packages from {req_file}")
            logging.info(f"Installed requirements from {req_file} to {venv_name}")
        else:
            print_error(f"Some packages failed to install")
            print(f"{YELLOW}{result.stderr}{RESET}")

    except Exception as e:
        print_error(f"Failed to install requirements: {e}")
        logging.error(f"Failed to install requirements in {venv_name}: {e}")

def uninstall_package(venv_name):
    """Uninstall a package from the virtual environment."""
    # First list packages
    list_packages(venv_name)

    package = input(f"\n{YELLOW}Enter package name to uninstall: {RESET}")

    if not package:
        print_warning("No package specified")
        return

    confirm = input(f"{RED}Are you sure you want to uninstall '{package}'? (y/n): {RESET}")
    if not confirm.lower().startswith('y'):
        print_warning("Uninstall cancelled")
        return

    try:
        if IS_WINDOWS:
            pip = os.path.join(get_venv_path(), venv_name, 'Scripts', 'pip.exe')
        else:
            pip = os.path.join(get_venv_path(), venv_name, 'bin', 'pip')

        show_progress(f"Uninstalling {package}")
        subprocess.run(
            [pip, 'uninstall', '-y', package],
            check=True,
            capture_output=True
        )
        print_success(f"Package '{package}' uninstalled successfully")
        logging.info(f"Uninstalled {package} from {venv_name}")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to uninstall package: {e}")
        logging.error(f"Failed to uninstall {package} from {venv_name}: {e}")

def update_all_packages(venv_name):
    """Update all packages in the virtual environment."""
    try:
        if IS_WINDOWS:
            pip = os.path.join(get_venv_path(), venv_name, 'Scripts', 'pip.exe')
        else:
            pip = os.path.join(get_venv_path(), venv_name, 'bin', 'pip')

        # Get list of outdated packages
        print(f"\n{CYAN}Checking for outdated packages...{RESET}")
        result = subprocess.run(
            [pip, 'list', '--outdated', '--format=json'],
            capture_output=True,
            text=True
        )

        outdated = json.loads(result.stdout) if result.stdout else []

        if not outdated:
            print_success("All packages are up to date!")
            return

        print(f"\n{YELLOW}Found {len(outdated)} outdated packages:{RESET}")
        for pkg in outdated:
            print(f"  {BLUE}{pkg['name']}: {WHITE}{pkg['version']} → {GREEN}{pkg['latest_version']}{RESET}")

        confirm = input(f"\n{YELLOW}Update all packages? (y/n): {RESET}")
        if not confirm.lower().startswith('y'):
            print_warning("Update cancelled")
            return

        show_progress("Updating packages", steps=len(outdated) * 20)

        for pkg in outdated:
            subprocess.run(
                [pip, 'install', '--upgrade', pkg['name']],
                capture_output=True
            )

        print_success(f"Updated {len(outdated)} packages")
        logging.info(f"Updated {len(outdated)} packages in {venv_name}")

    except Exception as e:
        print_error(f"Failed to update packages: {e}")
        logging.error(f"Failed to update packages in {venv_name}: {e}")

def search_packages(venv_name):
    """Search for packages in PyPI."""
    query = input(f"{YELLOW}Enter search term: {RESET}")

    if not query:
        print_warning("No search term provided")
        return

    try:
        if IS_WINDOWS:
            pip = os.path.join(get_venv_path(), venv_name, 'Scripts', 'pip.exe')
        else:
            pip = os.path.join(get_venv_path(), venv_name, 'bin', 'pip')

        print(f"\n{CYAN}Searching PyPI for '{query}'...{RESET}")
        show_spinner(2, "Searching")

        # pip search is deprecated, use pip index versions instead or show installed
        # Let's search in installed packages instead
        result = subprocess.run(
            [pip, 'list'],
            capture_output=True,
            text=True,
            check=True
        )

        matches = []
        for line in result.stdout.split('\n'):
            if query.lower() in line.lower():
                matches.append(line)

        if matches:
            print(f"\n{GREEN}Found {len(matches)} matching installed packages:{RESET}")
            for match in matches:
                print(f"  {WHITE}{match}{RESET}")
        else:
            print(f"{YELLOW}No installed packages match '{query}'{RESET}")
            print(f"{CYAN}Tip: Use 'pip install {query}' to install from PyPI{RESET}")

        logging.info(f"Searched for '{query}' in {venv_name}")

    except Exception as e:
        print_error(f"Search failed: {e}")

def show_settings():
    """Display and modify settings."""
    while True:
        print_header()
        print(f"{SECTION_HEADER} Current Settings {RESET}\n")
        
        for key, value in config.items():
            print(f"{BLUE}{key}: {WHITE}{value}{RESET}")
        
        print(f"\n{YELLOW}Options:{RESET}")
        print(f"{GREEN}1. Change venv location (current/custom){RESET}")
        print(f"{GREEN}2. Set custom venv path{RESET}")
        print(f"{GREEN}3. Toggle auto-activation{RESET}")
        print(f"{GREEN}4. Toggle animations{RESET}")
        print(f"{GREEN}5. Toggle deletion confirmation{RESET}")
        print(f"{GREEN}6. Save and return{RESET}")
        
        choice = input(f"\n{YELLOW}Enter choice: {RESET}")
        
        if choice == '1':
            loc = input(f"{YELLOW}Enter location type (current/custom): {RESET}")
            if loc in ['current', 'custom']:
                config['venv_location'] = loc
        elif choice == '2':
            path = input(f"{YELLOW}Enter custom venv path: {RESET}")
            config['custom_venv_path'] = path
        elif choice == '3':
            config['auto_activate'] = not config['auto_activate']
        elif choice == '4':
            config['show_animations'] = not config['show_animations']
        elif choice == '5':
            config['confirm_deletions'] = not config['confirm_deletions']
        elif choice == '6':
            save_config(config)
            break

def show_help():
    """Display help information."""
    print_header()
    print(f"{SECTION_HEADER} Available Commands {RESET}\n")
    
    help_sections = [
        ("Environment Management", [
            ("Create", "Create a new virtual environment"),
            ("Activate", "Show activation instructions"),
            ("Deactivate", "Show deactivation instructions"),
            ("Delete", "Remove a virtual environment"),
            ("List", "Show all virtual environments")
        ]),
        ("Package Management", [
            ("Install", "Install a new package"),
            ("List Packages", "Show installed packages"),
            ("Export", "Save requirements.txt"),
            ("Upgrade Pip", "Update pip to latest version")
        ]),
        ("Settings", [
            ("Location", "Change where venvs are stored"),
            ("Auto-activate", "Toggle automatic activation"),
            ("Confirm Delete", "Toggle deletion confirmation")
        ])
    ]
    
    for section, items in help_sections:
        print(f"{PURPLE}{section}:{RESET}")
        for cmd, desc in items:
            print(f"{BLUE}{cmd:15}{RESET} - {WHITE}{desc}{RESET}")
        print()
    
    if IS_WINDOWS:
        print(f"\n{YELLOW}Note: On Windows, use 'activate.bat' to activate environments{RESET}")
    else:
        print(f"\n{YELLOW}Note: Use 'source bin/activate' to activate environments{RESET}")
    
    input(f"\n{YELLOW}Press Enter to continue...{RESET}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Python Virtual Environment Manager v2.3 - A powerful tool for managing Python venvs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
================================================================================
                    PYTHON VIRTUAL ENVIRONMENT MANAGER v2.3
================================================================================

QUICK START:
  %(prog)s                             Launch interactive menu
  %(prog)s --list                      List all virtual environments
  %(prog)s --create myenv              Create new venv 'myenv'
  %(prog)s --detect                    Detect venv in current directory
  %(prog)s --info myenv                Show details about 'myenv'

--------------------------------------------------------------------------------
ENVIRONMENT MANAGEMENT:
--------------------------------------------------------------------------------
  --create NAME             Create a new Python virtual environment
                            Creates in: ~/.virtualenvs/NAME (configurable)
                            Example: %(prog)s --create myproject

  --delete NAME             Delete an existing virtual environment
                            Example: %(prog)s --delete old_project

--------------------------------------------------------------------------------
INFORMATION & DISCOVERY:
--------------------------------------------------------------------------------
  --list                    List all available virtual environments
                            Shows package count for each venv
                            Example: %(prog)s --list

  --detect                  Auto-detect venv in current directory
                            Finds: venv/, .venv/, env/, .env/, virtualenv/
                            Example: %(prog)s --detect

  --info NAME               Show detailed environment info:
                            - Path, Python version, size, package count
                            - Whether requirements.txt exists
                            Example: %(prog)s --info myenv

  --packages NAME           List all packages installed in a venv
                            Example: %(prog)s --packages myenv

--------------------------------------------------------------------------------
PACKAGE MANAGEMENT:
--------------------------------------------------------------------------------
  --install-req NAME        Install packages from requirements.txt
                            Looks for requirements.txt in current directory
                            Example: %(prog)s --install-req myenv

  --update NAME             Update all outdated packages in venv
                            Example: %(prog)s --update myenv

  --upgrade NAME            Upgrade pip to the latest version
                            Example: %(prog)s --upgrade myenv

--------------------------------------------------------------------------------
EXPORT & BACKUP:
--------------------------------------------------------------------------------
  --export NAME             Export installed packages to requirements.txt
                            Creates: NAME_requirements.txt
                            Example: %(prog)s --export myenv

--------------------------------------------------------------------------------
DISPLAY OPTIONS:
--------------------------------------------------------------------------------
  --no-color                Disable colored output (for piping/scripts)

--------------------------------------------------------------------------------
INTERACTIVE MENU OPTIONS (when run without arguments):
--------------------------------------------------------------------------------
  Environment:
    1.  Create new virtual environment
    2.  Activate environment (shows activation command)
    3.  Deactivate environment
    4.  Delete environment
    5.  Show venv info (size, packages, version)

  Packages:
    6.  List packages
    7.  Install from requirements.txt
    8.  Uninstall a package
    9.  Update all packages
    10. Search installed packages
    11. Export requirements.txt
    12. Upgrade pip

  Tools:
    13. Detect venv in current directory
    14. Switch to conda_setup

  System:
    15. Settings
    16. Help
    17. Exit

--------------------------------------------------------------------------------
AUTO-INSTALL FEATURE:
--------------------------------------------------------------------------------
  When you activate a venv, the script checks for dependency files
  in your current directory and offers to install them:

  - requirements.txt         -->  pip install -r requirements.txt
  - requirements-dev.txt     -->  pip install -r requirements-dev.txt
  - pyproject.toml           -->  pip install -e . (editable install)

--------------------------------------------------------------------------------
ACTIVATION COMMANDS (shown after selecting an environment):
--------------------------------------------------------------------------------
  Linux/macOS:    source ~/.virtualenvs/myenv/bin/activate
  Windows:        .\\myenv\\Scripts\\activate.bat

  To deactivate:  deactivate

--------------------------------------------------------------------------------
TIPS:
--------------------------------------------------------------------------------
  * Venvs are stored in ~/.virtualenvs/ by default
  * Run from your project folder to auto-detect local venvs
  * Use --detect to find venv folders in your project
  * Use --info to check venv size before deleting
  * Switch to conda_setup (option 14) for Conda management

================================================================================
        """
    )

    # Environment Management
    env_group = parser.add_argument_group('Environment Management')
    env_group.add_argument('--create', help="Create a new virtual environment", metavar='NAME')
    env_group.add_argument('--delete', help="Delete an environment", metavar='NAME')

    # Information & Discovery
    info_group = parser.add_argument_group('Information & Discovery')
    info_group.add_argument('--list', help="List all virtual environments", action='store_true')
    info_group.add_argument('--detect', help="Detect venv in current directory", action='store_true')
    info_group.add_argument('--info', help="Show detailed venv info (path, size, packages)", metavar='NAME')
    info_group.add_argument('--packages', help="List all packages in venv", metavar='NAME')

    # Package Management
    pkg_group = parser.add_argument_group('Package Management')
    pkg_group.add_argument('--install-req', help="Install from requirements.txt", metavar='NAME')
    pkg_group.add_argument('--update', help="Update all outdated packages", metavar='NAME')
    pkg_group.add_argument('--upgrade', help="Upgrade pip to latest version", metavar='NAME')

    # Export & Backup
    export_group = parser.add_argument_group('Export & Backup')
    export_group.add_argument('--export', help="Export requirements.txt", metavar='NAME')

    # Display Options
    display_group = parser.add_argument_group('Display Options')
    display_group.add_argument('--no-color', help="Disable colored output", action='store_true')

    # Easter Eggs
    easter_group = parser.add_argument_group('Easter Eggs')
    easter_group.add_argument('--bunny', action='store_true',
                             help="🐰 A surprise awaits...")

    return parser.parse_args()

def rainbow_bunny():
    """Display a rainbow-colored bunny!"""
    colors = [RED, YELLOW, GREEN, CYAN, BLUE, MAGENTA]
    bunny_art = r"""
           /\ /|
          |||| |
           \ | \
       _ _ /  ()()
     /    \   =>*<=
   /|      \   /
   \|     /__| |
     \_____) \__)
    """
    print()
    lines = bunny_art.split('\n')
    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        print(f"{color}{line}{RESET}")

    print(f"\n{MAGENTA}🐰 Bunny says: 'Virtual environments are virtually awesome!' 🐰{RESET}")
    print(f"{CYAN}   Easter egg found! Rangers lead the way!{RESET}\n")

def main_menu():
    """Main program menu."""
    while True:
        existing_venvs = check_existing_venvs()
        local_venvs = detect_local_venv()
        print_header()

        # Show local venv detection
        if local_venvs:
            print(f"{HIGHLIGHT} 📁 Local venv detected in current directory! {RESET}")
            for venv in local_venvs:
                pkg_count = count_packages(venv)
                py_ver = get_venv_python_version(venv)
                print(f"   {GREEN}→ {venv}{RESET} ({CYAN}Python {py_ver}{RESET}, {YELLOW}{pkg_count} packages{RESET})")
            print()

        if existing_venvs:
            print(f"{SECTION_HEADER} Available Virtual Environments {RESET}")
            for i, venv in enumerate(existing_venvs, 1):
                pkg_count = count_packages(venv)
                print(f"{GREEN}{i}. {venv}{RESET} ({GRAY}{pkg_count} packages{RESET})")
        else:
            print(f"{YELLOW}No virtual environments found{RESET}")

        print(f"\n{SECTION_HEADER} Menu Options {RESET}")
        menu_items = [
            ("Environment", [
                "Create new virtual environment",
                "Activate environment",
                "Deactivate environment",
                "Delete environment",
                "Show venv info (size, packages, version)"
            ]),
            ("Packages", [
                "List installed packages",
                "Install package",
                "Install from requirements.txt",
                "Uninstall package",
                "Update all packages",
                "Search packages",
                "Export requirements.txt",
                "Upgrade pip"
            ]),
            ("Additional Tools", [
                "Switch to Conda Environment Manager"
            ]),
            ("System", [
                "Settings",
                "Help"
            ])
        ]
        
        # Update menu color display
        current_index = 1
        for section, items in menu_items:
            print(f"\n{PURPLE}{section}:{RESET}")
            for item in items:
                print(f"{GREEN}{current_index}. {WHITE}{item}{RESET}")
                current_index += 1
        
        print(f"\n{RED}0. Exit{RESET}")
        
        valid_choices = [str(i) for i in range(current_index)] + ['0']
        choice = input(f"\n{GREEN}Enter your choice: {RESET}")
        
        if choice == '0':
            if input(f"{YELLOW}Are you sure you want to exit? (y/n): {RESET}").lower().startswith('y'):
                print_success("Goodbye!")
                logging.info("Program terminated normally")
                show_spinner(1, "Exiting")
                return 'exit'

        # Environment section (1-5)
        elif choice == '1':
            create_venv()
        elif choice == '2' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                show_activation_instructions(existing_venvs[venv_num-1])
        elif choice == '3' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                show_deactivation_instructions()
        elif choice == '4' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                delete_venv(existing_venvs[venv_num-1])
        elif choice == '5' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                show_venv_info(existing_venvs[venv_num-1])

        # Packages section (6-13)
        elif choice == '6' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                list_packages(existing_venvs[venv_num-1])
        elif choice == '7' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                install_package(existing_venvs[venv_num-1])
        elif choice == '8' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                install_requirements(existing_venvs[venv_num-1])
        elif choice == '9' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                uninstall_package(existing_venvs[venv_num-1])
        elif choice == '10' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                update_all_packages(existing_venvs[venv_num-1])
        elif choice == '11' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                search_packages(existing_venvs[venv_num-1])
        elif choice == '12' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                export_requirements(existing_venvs[venv_num-1])
        elif choice == '13' and existing_venvs:
            venv_num = int(input(f"{YELLOW}Enter environment number: {RESET}"))
            if 1 <= venv_num <= len(existing_venvs):
                upgrade_pip(existing_venvs[venv_num-1])

        # Additional Tools (14)
        elif choice == '14':
            return 'switch_to_conda'

        # System section (15-16)
        elif choice == '15':
            show_settings()
        elif choice == '16':
            show_help()

        if choice not in ['14', '15', '16']:  # Don't wait after certain options
            input(f"\n{YELLOW}Press Enter to continue...{RESET}")

def main():
    """Main entry point."""
    args = parse_args()

    # Handle color disable
    if args.no_color:
        init(strip=True)

    # Easter egg check first (no requirements needed)
    if args.bunny:
        rainbow_bunny()
        return

    try:
        if not has_venv():
            print_error("Python venv module is not available")
            sys.exit(1)

        if args.create:
            create_venv(args.create)
        elif args.delete:
            delete_venv(args.delete)
        elif args.list:
            venvs = check_existing_venvs()
            if venvs:
                print(f"{MENU_HEADER} Available Environments {RESET}")
                for i, env in enumerate(venvs, 1):
                    pkg_count = count_packages(env)
                    print(f"{GREEN}{i}. {env}{RESET} ({GRAY}{pkg_count} packages{RESET})")
            else:
                print(f"{YELLOW}No environments found{RESET}")
        elif args.detect:
            local_venvs = detect_local_venv()
            if local_venvs:
                print(f"{GREEN}📁 Found venv in current directory:{RESET}")
                for venv in local_venvs:
                    pkg_count = count_packages(venv)
                    py_ver = get_venv_python_version(venv)
                    size = get_venv_size(os.path.join(os.getcwd(), venv))
                    print(f"   {CYAN}→ {venv}{RESET}")
                    print(f"     Python: {py_ver}")
                    print(f"     Packages: {pkg_count}")
                    print(f"     Size: {size}")
            else:
                print(f"{YELLOW}No venv detected in current directory{RESET}")
        elif args.info:
            show_venv_info(args.info)
        elif args.packages:
            list_packages(args.packages)
        elif args.install_req:
            install_requirements(args.install_req)
        elif args.update:
            update_all_packages(args.update)
        elif args.export:
            export_requirements(args.export)
        elif args.upgrade:
            upgrade_pip(args.upgrade)
        else:
            # Handle script switching in a loop
            while True:
                result = main_menu()
                if result == 'switch_to_conda':
                    conda_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conda_setup.py')
                    if os.path.exists(conda_script):
                        print_info("Switching to Conda Environment Manager...")
                        logging.info("User switched to Conda Environment Manager")
                        try:
                            # Instead of running a new process, return to let the other script take over
                            return 'switch_to_conda'
                        except subprocess.CalledProcessError as e:
                            print_error(f"Failed to launch Conda Environment Manager: {e}")
                    else:
                        print_error("Conda Environment Manager script not found")
                else:
                    # Normal exit
                    sys.exit(0)
            
    except KeyboardInterrupt:
        print(f"\n{GREEN}Program terminated by user. Goodbye!{RESET}")
        logging.info("Program terminated by user")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Create a wrapper to handle script switching
    while True:
        result = main()
        if result == 'switch_to_conda':
            # Try to switch to conda script
            conda_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conda_setup.py')
            if os.path.exists(conda_script):
                try:
                    subprocess.run([sys.executable, conda_script], check=True)
                except subprocess.CalledProcessError:
                    print_error("Failed to switch to Conda Manager")
                    sys.exit(1)
            else:
                print_error("Conda Manager script not found")
                sys.exit(1)
        else:
            # Normal exit
            break