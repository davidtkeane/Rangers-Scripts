#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Conda Environment Manager
A sophisticated tool for managing Conda and Python virtual environments.
Cross-platform support for Windows, macOS, and Linux.
Version: 5.6
Author: Your Name
Date: January 2026
Description:
This script provides a command-line interface for creating, managing, and deleting Conda environments.
It includes enhanced color support, better terminal compatibility, and improved multiplatform handling.
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
from pathlib import Path
from colorama import init, Fore, Style, Back
from tqdm import tqdm
import getpass

# Platform-specific settings
PLATFORM = platform.system().lower()
IS_WINDOWS = PLATFORM == 'windows'
IS_MACOS = PLATFORM == 'darwin'
IS_LINUX = PLATFORM == 'linux'

# Get user home directory in a cross-platform way
HOME_DIR = str(Path.home())

def setup_colors():
    """Configure color support based on platform and environment."""
    # Check if we should disable colors
    if '--no-color' in sys.argv or os.environ.get('NO_COLOR'):
        init(strip=True)
        return False
    
    # Windows needs convert=True, others don't
    init(
        autoreset=True,
        strip=IS_WINDOWS,
        convert=IS_WINDOWS
    )
    
    # Verify color support
    if not verify_color_support():
        init(strip=True)
        return False
    
    return True

def verify_color_support():
    """Verify the terminal actually supports colors."""
    if IS_WINDOWS:
        return True
    
    # Unix-like systems
    return (
        sys.stdout.isatty() and
        os.environ.get('TERM') != 'dumb' and
        os.environ.get('COLORTERM', '') in ('truecolor', '24bit', 'yes', 'true', '1')
    )

# Initialize colors
COLORS_ENABLED = setup_colors()

# Enhanced color constants with fallbacks
if COLORS_ENABLED:
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
else:
    # Fallback values when colors are disabled
    CYAN = GREEN = YELLOW = RED = MAGENTA = BLUE = WHITE = GRAY = PURPLE = ''
    RESET = HIGHLIGHT = SECTION_HEADER = HEADER_BG = MENU_HEADER = ''
    SECTION_BG = OPTION_FG = WARNING_BG = ERROR_BG = ''


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

def needs_sudo():
    """Check if the current command needs sudo access."""
    read_only_args = ['--list', '--help', '-h', '--no-color', '--info', '--detect', '--packages', '--search', '--bunny']
    for arg in sys.argv[1:]:
        if arg in read_only_args:
            return False
    return True

if not platform.system().lower() == 'windows' and needs_sudo():  # Only on Unix-like systems
    request_sudo_password()


# Define print functions early to avoid reference errors
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

# Configuration and Logging Setup
LOG_DIR = '/Users/ranger/.db/logs'
if not os.path.exists(LOG_DIR):
    print_warning(f"Log directory {LOG_DIR} does not exist. Files will be saved in the script's folder.")
    LOG_DIR = os.getcwd()
elif not os.access(LOG_DIR, os.W_OK):
    print_warning(f"No write permission for {LOG_DIR}. Files will be saved in the script's folder.")
    LOG_DIR = os.getcwd()

# Setup logging first
LOG_FILE = os.path.join(LOG_DIR, 'conda_manager.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration file setup
CONFIG_DIR = os.path.join("/Users/ranger/.db/configs")
CONFIG_FILE = os.path.join(CONFIG_DIR, 'conda_manager_config.json')
DEFAULT_CONFIG = {
    'python_version': '3.9',
    'show_animations': True,
    'confirm_deletions': True,
    'export_format': 'yaml',
    'theme': 'default'
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        return DEFAULT_CONFIG
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Error saving config: {e}")
        return False

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


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print a beautiful header with version and additional info."""
    clear_screen()
    print(f"{MAGENTA}╔══════════════════════════════════════════════╗{RESET}")
    print(f"{MAGENTA}║{HEADER_BG}        Conda Environment Manager             {RESET}{MAGENTA}║{RESET}")
    print(f"{MAGENTA}║{WHITE}                Version 5.6                   {RESET}{MAGENTA}║{RESET}")
    print(f"{MAGENTA}╚══════════════════════════════════════════════╝{RESET}")
    
    print(f"{MENU_HEADER} System Information {RESET}")
    print(f"{BLUE}OS:     {WHITE}{platform.system()} {platform.release()}{RESET}")
    print(f"{BLUE}Python: {WHITE}{sys.version.split()[0]}{RESET}")
    print(f"{BLUE}Conda:  {WHITE}{get_conda_version()}{RESET}")
    
    if check_admin_requirements():
        print(f"\n{WARNING_BG} Note: Some operations may require elevated privileges {RESET}")
    print()

def get_conda_version():
    """Get the installed Conda version."""
    try:
        result = subprocess.run(['conda', '--version'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        return result.stdout.strip().split()[-1]
    except:
        return "Not found"

def get_valid_input(prompt, validator=None, error_msg=None):
    """Get validated input from the user."""
    while True:
        value = input(f"{YELLOW}{prompt}: {RESET}").strip()
        if validator is None or validator(value):
            return value
        print(f"{RED}{error_msg or 'Invalid input'}{RESET}")

def confirm_action(message="Are you sure?"):
    """Get confirmation from the user."""
    return input(f"{YELLOW}{message} (y/n): {RESET}").lower().startswith('y')

def check_requirements():
    """Check if required tools are installed."""
    requirements = {
        'conda': ['conda', '--version'],
        'pip': ['pip', '--version']
    }
    
    for req, cmd in requirements.items():
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError:
            print_error(f"{req} is not installed or not found in PATH")
            sys.exit(1)

def check_existing_envs():
    """Get list of existing Conda environments."""
    try:
        result = subprocess.run(['conda', 'env', 'list'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        env_lines = result.stdout.splitlines()
        envs = []
        for line in env_lines:
            if line and not line.startswith('#'):
                env = line.split()[0]
                if '*' not in line:
                    envs.append(env)
        return envs
    except subprocess.CalledProcessError:
        print_error("Could not retrieve Conda environments")
        return []

def search_environments(query, environments):
    """Search for environments matching the query."""
    matches = [env for env in environments 
              if query.lower() in env.lower()]
    if matches:
        print(f"\n{CYAN}Found {len(matches)} matching environment(s):{RESET}")
        for i, env in enumerate(matches, 1):
            print(f"{GREEN}{i}. {env}{RESET}")
    else:
        print_warning("No matching environments found")
    return matches

def create_environment():
    """Create a new Conda environment."""
    print_header()
    print_info("Creating a new Conda environment")
    
    env_name = get_valid_input(
        "Enter environment name",
        lambda x: x and x.isalnum(),
        "Environment name must be alphanumeric"
    )
    
    python_version = get_valid_input(
        f"Enter Python version (press Enter for {config['python_version']})",
        lambda x: not x or x.count('.') <= 2,
        "Invalid Python version format"
    ) or config['python_version']
    
    try:
        show_progress("Creating environment")
        cmd = ['conda', 'create', '--name', env_name, f'python={python_version}', '-y']
        subprocess.run(cmd, check=True, capture_output=True)
        print_success(f"Environment '{env_name}' created successfully!")
        show_activation_instructions(env_name)
        logging.info(f"Created environment: {env_name} with Python {python_version}")
        return env_name
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create environment: {e}")
        logging.error(f"Failed to create environment {env_name}: {e}")
        return None

def delete_environment(env_name):
    """Delete a Conda environment."""
    if not config['confirm_deletions'] or confirm_action(
        f"Are you sure you want to delete '{env_name}'?"
    ):
        try:
            show_progress(f"Deleting environment '{env_name}'")
            subprocess.run(
                ['conda', 'env', 'remove', '--name', env_name, '-y'],
                check=True,
                capture_output=True
            )
            print_success(f"Environment '{env_name}' deleted successfully")
            logging.info(f"Deleted environment: {env_name}")
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to delete environment: {e}")
            logging.error(f"Failed to delete {env_name}: {e}")
    else:
        print_warning("Deletion cancelled")

def show_activation_instructions(env_name):
    """Show how to activate an environment."""
    cmd = f"conda activate {env_name}"
    print(f"\n{CYAN}To activate this environment, run:{RESET}")
    print(f"{GREEN}{cmd}{RESET}")
    print(f"{YELLOW}Note: Run this command in your terminal{RESET}")

    # Check for dependency files in current directory
    check_and_offer_install(env_name)

def check_and_offer_install(env_name):
    """Check for dependency files and offer to install them."""
    cwd = os.getcwd()

    # Check for various dependency files
    env_yml = None
    req_txt = None

    for f in ['environment.yml', 'environment.yaml', 'conda.yml', 'conda.yaml']:
        if os.path.exists(os.path.join(cwd, f)):
            env_yml = f
            break

    if os.path.exists(os.path.join(cwd, 'requirements.txt')):
        req_txt = 'requirements.txt'

    if not env_yml and not req_txt:
        return

    # Show what was found
    print(f"\n{CYAN}📦 Dependency files found in current directory:{RESET}")
    if env_yml:
        print(f"   {GREEN}• {env_yml}{RESET} (conda environment file)")
    if req_txt:
        print(f"   {GREEN}• {req_txt}{RESET} (pip requirements)")

    # Ask if user wants to install
    print(f"\n{YELLOW}Would you like to install dependencies into '{env_name}'?{RESET}")
    if env_yml and req_txt:
        print(f"{WHITE}1. Install from {env_yml} (conda){RESET}")
        print(f"{WHITE}2. Install from {req_txt} (pip){RESET}")
        print(f"{WHITE}3. Install both{RESET}")
        print(f"{WHITE}4. Skip{RESET}")
        choice = input(f"{CYAN}Enter choice (1-4): {RESET}").strip()

        if choice == '1':
            install_from_env_yml(env_name, env_yml)
        elif choice == '2':
            install_from_requirements(env_name, req_txt)
        elif choice == '3':
            install_from_env_yml(env_name, env_yml)
            install_from_requirements(env_name, req_txt)
        else:
            print_info("Skipping dependency installation")
    elif env_yml:
        if confirm_action(f"Install from {env_yml}?"):
            install_from_env_yml(env_name, env_yml)
    elif req_txt:
        if confirm_action(f"Install from {req_txt}?"):
            install_from_requirements(env_name, req_txt)

def install_from_env_yml(env_name, yml_file):
    """Install dependencies from environment.yml file."""
    try:
        show_progress(f"Installing from {yml_file}")
        # Use conda env update to install into existing environment
        subprocess.run(
            ['conda', 'env', 'update', '--name', env_name, '--file', yml_file, '--prune'],
            check=True,
            capture_output=True
        )
        print_success(f"Dependencies from {yml_file} installed successfully!")
        logging.info(f"Installed dependencies from {yml_file} into {env_name}")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install from {yml_file}")
        logging.error(f"Failed to install from {yml_file}: {e}")

def install_from_requirements(env_name, req_file):
    """Install dependencies from requirements.txt file."""
    try:
        show_progress(f"Installing from {req_file}")
        subprocess.run(
            ['conda', 'run', '-n', env_name, 'pip', 'install', '-r', req_file],
            check=True,
            capture_output=True
        )
        print_success(f"Dependencies from {req_file} installed successfully!")
        logging.info(f"Installed dependencies from {req_file} into {env_name}")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install from {req_file}")
        logging.error(f"Failed to install from {req_file}: {e}")

def show_deactivation_instructions():
    """Show how to deactivate the current environment."""
    print(f"\n{CYAN}To deactivate the current environment, run:{RESET}")
    print(f"{GREEN}conda deactivate{RESET}")
    print(f"{YELLOW}Note: Run this command in your terminal when done{RESET}")

def list_packages(env_name):
    """List all packages in an environment."""
    try:
        show_spinner(1, "Retrieving package list")
        result = subprocess.run(
            ['conda', 'list', '--name', env_name],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"\n{CYAN}Packages in environment '{env_name}':{RESET}")
        print(f"{WHITE}{result.stdout}{RESET}")
        logging.info(f"Listed packages for: {env_name}")
    except subprocess.CalledProcessError:
        print_error("Failed to list packages")
        logging.error(f"Failed to list packages for {env_name}")

def export_environment(env_name):
    """Export environment configuration."""
    try:
        output_file = f"{env_name}_environment.yml"
        show_progress("Exporting environment")
        subprocess.run(
            ['conda', 'env', 'export', '--name', env_name, '--file', output_file],
            check=True,
            capture_output=True
        )
        print_success(f"Environment exported to {output_file}")
        logging.info(f"Exported environment: {env_name}")
    except subprocess.CalledProcessError:
        print_error("Failed to export environment")
        logging.error(f"Failed to export {env_name}")

def export_requirements(env_name):
    """Export environment packages to requirements.txt with versions."""
    try:
        show_progress("Exporting requirements")
        output_file = f"{env_name}_requirements.txt"
        
        # Use pip list to get exact versions
        result = subprocess.run(
            ['conda', 'run', '-n', env_name, 'pip', 'freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        
        with open(output_file, 'w') as f:
            f.write(result.stdout)
            
        print_success(f"Requirements exported to {output_file}")
        logging.info(f"Exported requirements for: {env_name}")
    except subprocess.CalledProcessError:
        print_error("Failed to export requirements")
        logging.error(f"Failed to export requirements for {env_name}")

def clone_environment(source_env, target_env):
    """Clone an existing environment."""
    try:
        show_progress(f"Cloning environment '{source_env}' to '{target_env}'")
        subprocess.run(
            ['conda', 'create', '--name', target_env, '--clone', source_env, '-y'],
            check=True,
            capture_output=True
        )
        print_success(f"Environment cloned successfully to '{target_env}'")
        logging.info(f"Cloned environment from {source_env} to {target_env}")
    except subprocess.CalledProcessError:
        print_error("Failed to clone environment")
        logging.error(f"Failed to clone from {source_env} to {target_env}")

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

def update_environment(env_name):
    """Update all packages in an environment."""
    try:
        show_progress(f"Updating packages in '{env_name}'")
        subprocess.run(
            ['conda', 'update', '--name', env_name, '--all', '-y'],
            check=True,
            capture_output=True
        )
        print_success(f"Environment '{env_name}' updated successfully")
        logging.info(f"Updated all packages in: {env_name}")
    except subprocess.CalledProcessError:
        print_error("Failed to update environment")
        logging.error(f"Failed to update {env_name}")

def install_package(env_name, package):
    """Install a new package in the environment."""
    try:
        show_progress(f"Installing {package}")
        cmd = ['conda', 'install', '--name', env_name, package, '-y']
        subprocess.run(cmd, check=True, capture_output=True)
        print_success(f"Package '{package}' installed successfully")
        logging.info(f"Installed {package} in {env_name}")
    except subprocess.CalledProcessError:
        print_warning(f"Conda install failed, trying pip...")
        try:
            cmd = ['conda', 'run', '-n', env_name, 'pip', 'install', package]
            subprocess.run(cmd, check=True, capture_output=True)
            print_success(f"Package '{package}' installed successfully via pip")
            logging.info(f"Installed {package} via pip in {env_name}")
        except subprocess.CalledProcessError:
            print_error(f"Failed to install {package}")
            logging.error(f"Failed to install {package} in {env_name}")

def repair_environment(env_name):
    """Attempt to repair a broken environment."""
    try:
        show_progress(f"Repairing environment '{env_name}'")
        # First, try to remove any broken packages
        subprocess.run(
            ['conda', 'clean', '--all', '-y'],
            check=True,
            capture_output=True
        )
        # Then try to fix the environment
        subprocess.run(
            ['conda', 'install', '--name', env_name, '--rev', '0'],
            check=True,
            capture_output=True
        )
        print_success(f"Environment '{env_name}' repaired successfully")
        logging.info(f"Repaired environment: {env_name}")
    except subprocess.CalledProcessError:
        print_error("Failed to repair environment")
        logging.error(f"Failed to repair {env_name}")

def detect_local_conda_env():
    """Auto-detect conda environment in current directory."""
    cwd = os.getcwd()
    detected = []

    # Check for conda environment files
    env_files = ['environment.yml', 'environment.yaml', 'conda.yml', 'conda.yaml']
    for env_file in env_files:
        env_path = os.path.join(cwd, env_file)
        if os.path.exists(env_path):
            detected.append(('file', env_file, env_path))

    # Check for local conda env folders (rare but possible)
    local_env_names = ['conda_env', '.conda', 'env', '.env']
    for env_name in local_env_names:
        env_path = os.path.join(cwd, env_name)
        if os.path.isdir(env_path):
            # Check if it's a conda environment
            conda_meta = os.path.join(env_path, 'conda-meta')
            if os.path.isdir(conda_meta):
                detected.append(('local', env_name, env_path))

    return detected

def get_env_path(env_name):
    """Get the path to a conda environment."""
    try:
        result = subprocess.run(
            ['conda', 'env', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if line and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 2 and parts[0] == env_name:
                    return parts[-1]  # Path is usually the last column
        return None
    except subprocess.CalledProcessError:
        return None

def get_env_size(env_path):
    """Calculate the size of a conda environment."""
    if not env_path or not os.path.exists(env_path):
        return "Unknown"

    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(env_path):
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
    except Exception:
        return "Unknown"

def get_env_python_version(env_name):
    """Get the Python version in a conda environment."""
    try:
        result = subprocess.run(
            ['conda', 'run', '-n', env_name, 'python', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().replace('Python ', '')
    except subprocess.CalledProcessError:
        return "Unknown"

def count_env_packages(env_name):
    """Count installed packages in a conda environment."""
    try:
        result = subprocess.run(
            ['conda', 'list', '--name', env_name],
            capture_output=True,
            text=True,
            check=True
        )
        # Count non-empty, non-comment lines
        lines = [l for l in result.stdout.splitlines() if l and not l.startswith('#')]
        return len(lines)
    except subprocess.CalledProcessError:
        return 0

def show_env_info(env_name):
    """Display detailed information about a conda environment."""
    print_header()
    print(f"{SECTION_HEADER} Environment Information: {env_name} {RESET}\n")

    env_path = get_env_path(env_name)
    if not env_path:
        print_error(f"Environment '{env_name}' not found")
        return

    show_spinner(1, "Gathering environment info")

    python_version = get_env_python_version(env_name)
    env_size = get_env_size(env_path)
    package_count = count_env_packages(env_name)

    print(f"{BLUE}Name:           {WHITE}{env_name}{RESET}")
    print(f"{BLUE}Path:           {WHITE}{env_path}{RESET}")
    print(f"{BLUE}Python Version: {WHITE}{python_version}{RESET}")
    print(f"{BLUE}Size:           {WHITE}{env_size}{RESET}")
    print(f"{BLUE}Packages:       {WHITE}{package_count}{RESET}")

    # Check for requirements.txt or environment.yml
    req_files = ['requirements.txt', 'environment.yml', 'environment.yaml']
    cwd = os.getcwd()
    for req_file in req_files:
        if os.path.exists(os.path.join(cwd, req_file)):
            print(f"{BLUE}Found:          {WHITE}{req_file} in current directory{RESET}")

    logging.info(f"Displayed info for environment: {env_name}")

def uninstall_package(env_name, package):
    """Uninstall a package from a conda environment."""
    if confirm_action(f"Are you sure you want to uninstall '{package}' from '{env_name}'?"):
        try:
            show_progress(f"Uninstalling {package}")
            cmd = ['conda', 'remove', '--name', env_name, package, '-y']
            subprocess.run(cmd, check=True, capture_output=True)
            print_success(f"Package '{package}' uninstalled successfully")
            logging.info(f"Uninstalled {package} from {env_name}")
        except subprocess.CalledProcessError:
            print_warning(f"Conda uninstall failed, trying pip...")
            try:
                cmd = ['conda', 'run', '-n', env_name, 'pip', 'uninstall', package, '-y']
                subprocess.run(cmd, check=True, capture_output=True)
                print_success(f"Package '{package}' uninstalled via pip")
                logging.info(f"Uninstalled {package} via pip from {env_name}")
            except subprocess.CalledProcessError:
                print_error(f"Failed to uninstall {package}")
                logging.error(f"Failed to uninstall {package} from {env_name}")
    else:
        print_warning("Uninstall cancelled")

def search_env_packages(env_name, query):
    """Search for packages in a conda environment."""
    try:
        result = subprocess.run(
            ['conda', 'list', '--name', env_name],
            capture_output=True,
            text=True,
            check=True
        )

        matches = []
        for line in result.stdout.splitlines():
            if line and not line.startswith('#') and query.lower() in line.lower():
                matches.append(line)

        if matches:
            print(f"\n{CYAN}Found {len(matches)} package(s) matching '{query}':{RESET}\n")
            for match in matches:
                parts = match.split()
                if len(parts) >= 2:
                    print(f"{GREEN}{parts[0]:30}{WHITE}{parts[1]}{RESET}")
                else:
                    print(f"{GREEN}{match}{RESET}")
        else:
            print_warning(f"No packages matching '{query}' found in '{env_name}'")

        logging.info(f"Searched packages in {env_name} for '{query}'")
    except subprocess.CalledProcessError:
        print_error("Failed to search packages")
        logging.error(f"Failed to search packages in {env_name}")

def show_settings():
    """Display and modify settings."""
    while True:
        print_header()
        print(f"{MAGENTA}Current Settings:{RESET}\n")
        for key, value in config.items():
            print(f"{BLUE}{key}: {WHITE}{value}{RESET}")
        
        print(f"\n{YELLOW}Options:{RESET}")
        print(f"{GREEN}1. Change Python version{RESET}")
        print(f"{GREEN}2. Toggle animations{RESET}")
        print(f"{GREEN}3. Toggle deletion confirmation{RESET}")
        print(f"{GREEN}4. Change export format{RESET}")
        print(f"{GREEN}5. Save and return{RESET}")
        
        choice = get_valid_input("Enter choice", lambda x: x in '12345')
        
        if choice == '1':
            config['python_version'] = get_valid_input("Enter Python version")
        elif choice == '2':
            config['show_animations'] = not config['show_animations']
        elif choice == '3':
            config['confirm_deletions'] = not config['confirm_deletions']
        elif choice == '4':
            config['export_format'] = get_valid_input("Enter format (yaml/txt)")
        elif choice == '5':
            save_config(config)
            break

def show_help():
    """Display help information."""
    print_header()
    print(f"{SECTION_HEADER} Available Commands {RESET}\n")
    help_sections = [
        ("Conda Commands", [
            ("Create Environment", "Create a new Conda environment"),
            ("List/Search", "View or search existing environments"),
            ("Activate", "Show activation instructions"),
            ("Deactivate", "Show deactivation instructions"),
            ("Delete", "Remove an environment"),
            ("Export", "Save environment configuration"),
            ("Packages", "List installed packages"),
            ("Clone", "Create a copy of an environment"),
            ("Update", "Update all packages in an environment"),
            ("Repair", "Fix a broken environment")
        ]),
        ("Virtual Environment", [
            ("Create Venv", "Create a Python virtual environment"),
            ("Activate Venv", "Activate a virtual environment"),
            ("Deactivate Venv", "Deactivate current virtual environment")
        ]),
        ("System", [
            ("Settings", "Configure manager options"),
            ("Help", "Show this help menu"),
            ("Exit", "Quit the program")
        ])
    ]
    
    for section, items in help_sections:
        print(f"{PURPLE}{section}:{RESET}")
        for cmd, desc in items:
            print(f"{BLUE}{cmd:15}{RESET} - {WHITE}{desc}{RESET}")
        print()
    
    input(f"\n{YELLOW}Press Enter to continue...{RESET}")

def parse_args():
    """Parse command line arguments with enhanced options."""
    parser = argparse.ArgumentParser(
        description="Conda Environment Manager v5.6 - A powerful tool for managing Conda environments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
================================================================================
                         CONDA ENVIRONMENT MANAGER v5.6
================================================================================

QUICK START:
  %(prog)s                             Launch interactive menu
  %(prog)s --list                      List all conda environments
  %(prog)s --create myenv              Create new environment 'myenv'
  %(prog)s --info myenv                Show details about 'myenv'

--------------------------------------------------------------------------------
ENVIRONMENT MANAGEMENT:
--------------------------------------------------------------------------------
  --create ENV_NAME         Create a new conda environment
                            Example: %(prog)s --create myproject

  --delete ENV_NAME         Delete an existing environment (with confirmation)
                            Example: %(prog)s --delete old_project

  --clone SOURCE DEST       Clone an environment to a new name
                            Example: %(prog)s --clone myenv myenv_backup

  --update ENV_NAME         Update all packages in an environment
                            Example: %(prog)s --update myenv

  --repair ENV_NAME         Attempt to repair a broken environment
                            Example: %(prog)s --repair broken_env

--------------------------------------------------------------------------------
INFORMATION & DISCOVERY:
--------------------------------------------------------------------------------
  --list                    List all available conda environments
                            Example: %(prog)s --list

  --info ENV_NAME           Show detailed environment info:
                            - Path, Python version, size, package count
                            Example: %(prog)s --info myenv

  --detect                  Auto-detect conda files in current directory
                            Finds: environment.yml, conda.yml, requirements.txt
                            Example: %(prog)s --detect

  --packages ENV_NAME       List all packages installed in an environment
                            Example: %(prog)s --packages myenv

  --search ENV_NAME QUERY   Search for packages matching a query
                            Example: %(prog)s --search myenv numpy

--------------------------------------------------------------------------------
PACKAGE MANAGEMENT:
--------------------------------------------------------------------------------
  --install ENV_NAME PKG    Install a package (tries conda, then pip)
                            Example: %(prog)s --install myenv numpy
                            Example: %(prog)s --install myenv "pandas==2.0.0"

  --uninstall ENV_NAME PKG  Uninstall a package from environment
                            Example: %(prog)s --uninstall myenv old_package

--------------------------------------------------------------------------------
EXPORT & BACKUP:
--------------------------------------------------------------------------------
  --export ENV_NAME         Export environment to YAML file
                            Creates: ENV_NAME_environment.yml
                            Example: %(prog)s --export myenv

  --requirements ENV_NAME   Export to requirements.txt format
                            Creates: ENV_NAME_requirements.txt
                            Example: %(prog)s --requirements myenv

--------------------------------------------------------------------------------
DISPLAY OPTIONS:
--------------------------------------------------------------------------------
  --no-color                Disable colored output (for piping/scripts)
  --force-color             Force colored output even in non-TTY
  --sudo-off                Skip the sudo password prompt at startup

--------------------------------------------------------------------------------
INTERACTIVE MENU OPTIONS (when run without arguments):
--------------------------------------------------------------------------------
  1.  Create new Conda environment    10. Export requirements
  2.  List/Search environments        11. Clone environment
  3.  Show environment info           12. Update environment
  4.  Detect local conda files        13. Install package
  5.  Activate environment            14. Uninstall package
  6.  Delete environment              15. Repair environment
  7.  List packages                   16. Show deactivation instructions
  8.  Search packages                 17. Switch to venv_setup
  9.  Export environment              18-20. Settings/Help/Exit

--------------------------------------------------------------------------------
AUTO-INSTALL FEATURE:
--------------------------------------------------------------------------------
  When you activate an environment, the script checks for dependency files
  in your current directory and offers to install them:

  - environment.yml / conda.yml  -->  conda env update
  - requirements.txt             -->  pip install -r

--------------------------------------------------------------------------------
TIPS:
--------------------------------------------------------------------------------
  * Use 'conda activate ENV_NAME' to activate after seeing instructions
  * Run from your project folder to auto-detect dependency files
  * Use --info to check environment size before cloning/exporting
  * Switch to venv_setup (option 17) for Python venv management

================================================================================
        """
    )

    # Environment Management
    env_group = parser.add_argument_group('Environment Management')
    env_group.add_argument('--create', help="Create a new conda environment", metavar='ENV_NAME')
    env_group.add_argument('--delete', help="Delete an environment", metavar='ENV_NAME')
    env_group.add_argument('--clone', nargs=2, help="Clone environment", metavar=('SOURCE', 'DEST'))
    env_group.add_argument('--update', help="Update all packages in environment", metavar='ENV_NAME')
    env_group.add_argument('--repair', help="Attempt to repair broken environment", metavar='ENV_NAME')

    # Information & Discovery
    info_group = parser.add_argument_group('Information & Discovery')
    info_group.add_argument('--list', help="List all conda environments", action='store_true')
    info_group.add_argument('--info', help="Show environment info (path, size, packages)", metavar='ENV_NAME')
    info_group.add_argument('--detect', help="Auto-detect conda files in current directory", action='store_true')
    info_group.add_argument('--packages', help="List all packages in environment", metavar='ENV_NAME')
    info_group.add_argument('--search', nargs=2, help="Search packages in environment", metavar=('ENV_NAME', 'QUERY'))

    # Package Management
    pkg_group = parser.add_argument_group('Package Management')
    pkg_group.add_argument('--install', nargs=2, help="Install a package", metavar=('ENV_NAME', 'PACKAGE'))
    pkg_group.add_argument('--uninstall', nargs=2, help="Uninstall a package", metavar=('ENV_NAME', 'PACKAGE'))

    # Export & Backup
    export_group = parser.add_argument_group('Export & Backup')
    export_group.add_argument('--export', help="Export environment to YAML file", metavar='ENV_NAME')
    export_group.add_argument('--requirements', help="Export to requirements.txt format", metavar='ENV_NAME')

    # Display Options
    display_group = parser.add_argument_group('Display Options')
    display_group.add_argument('--no-color', help="Disable colored output", action='store_true')
    display_group.add_argument('--force-color', help="Force colored output", action='store_true')
    display_group.add_argument('--sudo-off', help="Disable sudo password prompt", action='store_true')

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

    print(f"\n{MAGENTA}🐰 Bunny says: 'Your environments are hopping along nicely!' 🐰{RESET}")
    print(f"{CYAN}   Easter egg found! Rangers lead the way!{RESET}\n")

def main_menu():
    """Main program menu."""
    args = parse_args()

    while True:
        existing_envs = check_existing_envs()
        print_header()
        
        if existing_envs:
            print(f"{SECTION_HEADER} Available Conda Environments {RESET}")
            print()
            for i, env in enumerate(existing_envs, 1):
                print(f"{GREEN}{i}. {WHITE}{env}{RESET}")
        else:
            print(f"{YELLOW}No Conda environments found{RESET}")
        
        print(f"\n{SECTION_HEADER} Menu Options {RESET}")
        menu_items = [
            ("Conda Environment", [
                "Create new Conda environment",
                "List/Search environments",
                "Show environment info",
                "Detect local conda files",
                "Activate environment",
                "Delete environment",
                "List packages",
                "Search packages",
                "Export environment",
                "Export requirements",
                "Clone environment",
                "Update environment",
                "Install package",
                "Uninstall package",
                "Repair environment",
                "Show deactivation instructions"
            ]),
            ("Additional Tools", [
                "Switch to Virtual Environment Manager"
            ]),
            ("System", [
                "Settings",
                "Help",
                "Exit"
            ])
        ]
        
        current_index = 1
        for section, items in menu_items:
            print(f"\n{PURPLE}{section}:{RESET}")
            for item in items:
                print(f"{GREEN}{current_index}. {WHITE}{item}{RESET}")
                current_index += 1
        
        choice = input(f"\n{CYAN}Enter your choice: {RESET}")

        if choice == str(current_index - 1) or choice == '20':  # Exit option
            if input(f"{CYAN}Are you sure you want to exit? (y/n): {RESET}").lower().startswith('y'):
                print_success("Goodbye!")
                logging.info("Program terminated normally")
                show_spinner(1, "Exiting")
                sys.exit(0)
        elif choice == '17':  # Switch to Virtual Environment Manager
            print_info("Switching to Virtual Environment Manager...")
            venv_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv_setup')
            if os.path.exists(venv_script):
                logging.info("User switched to Virtual Environment Manager")
                try:
                    subprocess.run([sys.executable, venv_script], check=True)
                    # After venv manager exits, return to conda menu
                    continue
                except subprocess.CalledProcessError as e:
                    print_error(f"Failed to launch Virtual Environment Manager: {e}")
            else:
                print_error("Virtual Environment Manager script not found")
            input(f"\n{YELLOW}Press Enter to continue...{RESET}")
        elif choice == '0':
            if confirm_action("Are you sure you want to exit?"):
                print_success("Goodbye!")
                logging.info("Program terminated normally")
                show_spinner(1, "Exiting")
                break
        elif choice == '1':
            env_name = create_environment()
        elif choice == '2':
            query = get_valid_input("Enter search term (or press Enter to list all)")
            search_environments(query, existing_envs)
        elif choice == '3' and existing_envs:  # Show environment info
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            show_env_info(existing_envs[int(env_num)-1])
        elif choice == '4':  # Detect local conda files
            detected = detect_local_conda_env()
            if detected:
                print(f"\n{CYAN}Detected conda environment files in current directory:{RESET}\n")
                for env_type, name, path in detected:
                    if env_type == 'file':
                        print(f"{GREEN}📄 {name}{RESET}")
                    else:
                        print(f"{GREEN}📁 {name}{RESET} (local conda env)")
            else:
                print_warning("No conda environment files found in current directory")
        elif choice == '5' and existing_envs:  # Activate environment
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            show_activation_instructions(existing_envs[int(env_num)-1])
        elif choice == '6' and existing_envs:  # Delete environment
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            delete_environment(existing_envs[int(env_num)-1])
        elif choice == '7' and existing_envs:  # List packages
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            list_packages(existing_envs[int(env_num)-1])
        elif choice == '8' and existing_envs:  # Search packages
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            query = get_valid_input("Enter search term")
            search_env_packages(existing_envs[int(env_num)-1], query)
        elif choice == '9' and existing_envs:  # Export environment
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            export_environment(existing_envs[int(env_num)-1])
        elif choice == '10' and existing_envs:  # Export requirements
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            export_requirements(existing_envs[int(env_num)-1])
        elif choice == '11' and existing_envs:  # Clone environment
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            clone_environment(existing_envs[int(env_num)-1], get_valid_input("Enter name for the new environment"))
        elif choice == '12' and existing_envs:  # Update environment
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            update_environment(existing_envs[int(env_num)-1])
        elif choice == '13' and existing_envs:  # Install package
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            install_package(existing_envs[int(env_num)-1], get_valid_input("Enter package name (and version if needed, e.g. 'numpy==1.21.0')"))
        elif choice == '14' and existing_envs:  # Uninstall package
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            package = get_valid_input("Enter package name to uninstall")
            uninstall_package(existing_envs[int(env_num)-1], package)
        elif choice == '15' and existing_envs:  # Repair environment
            env_num = get_valid_input(
                "Enter environment number",
                lambda x: x.isdigit() and 1 <= int(x) <= len(existing_envs)
            )
            repair_environment(existing_envs[int(env_num)-1])
        elif choice == '16':  # Show deactivation instructions
            show_deactivation_instructions()
        elif choice == '18':  # Settings
            show_settings()
        elif choice == '19':  # Help
            show_help()

        if choice not in ['18', '19']:  # Don't wait after settings or help
            input(f"\n{YELLOW}Press Enter to continue...{RESET}")

def main():
    """Main entry point with enhanced argument handling."""
    args = parse_args()

    # Handle color disable
    if args.no_color:
        init(strip=True)

    # Easter egg check first (no requirements needed)
    if args.bunny:
        rainbow_bunny()
        return

    try:
        check_requirements()

        if args.create:
            create_environment()
        elif args.delete:
            delete_environment(args.delete)
        elif args.list:
            envs = check_existing_envs()
            if envs:
                print(f"{MENU_HEADER} Available Environments {RESET}")
                for i, env in enumerate(envs, 1):
                    print(f"{GREEN}{i}. {env}{RESET}")
            else:
                print(f"{YELLOW}No environments found{RESET}")
        elif args.info:
            show_env_info(args.info)
        elif args.detect:
            detected = detect_local_conda_env()
            if detected:
                print(f"{MENU_HEADER} Detected Conda Environment Files {RESET}")
                for env_type, name, path in detected:
                    if env_type == 'file':
                        print(f"{GREEN}📄 {name}{RESET} - {WHITE}{path}{RESET}")
                    else:
                        print(f"{GREEN}📁 {name}{RESET} - {WHITE}{path}{RESET}")
            else:
                print(f"{YELLOW}No conda environment files detected in current directory{RESET}")
        elif args.export:
            export_environment(args.export)
        elif args.requirements:
            export_requirements(args.requirements)
        elif args.clone:
            clone_environment(args.clone[0], args.clone[1])
        elif args.update:
            update_environment(args.update)
        elif args.repair:
            repair_environment(args.repair)
        elif args.install:
            install_package(args.install[0], args.install[1])
        elif args.uninstall:
            uninstall_package(args.uninstall[0], args.uninstall[1])
        elif args.search:
            search_env_packages(args.search[0], args.search[1])
        elif args.packages:
            list_packages(args.packages)
        else:
            main_menu()
            
    except KeyboardInterrupt:
        print(f"\n{GREEN}Program terminated by user. Goodbye!{RESET}")
        logging.info("Program terminated by user")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
