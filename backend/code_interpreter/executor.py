import os
import sys
import subprocess
import tempfile
from typing import Tuple, List

def execute_code(code: str) -> Tuple[bool, str, List[str]]:
    """
    Execute Python code in a controlled environment.
    
    Returns:
        Tuple containing:
        - Success status (bool)
        - Output or error message (str)
        - List of missing packages if any (List[str])
    """
    # Create a temporary file for the code in a temp directory
    temp_dir = os.path.join(tempfile.gettempdir(), "mcp_code_exec")
    os.makedirs(temp_dir, exist_ok=True)
    
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', dir=temp_dir) as temp_file:
        temp_file.write(code)
        temp_filename = temp_file.name
        
        # Save a copy of the code for debugging
        debug_file_path = os.path.join(temp_dir, "last_executed_code.py")
        with open(debug_file_path, 'w', encoding='utf-8') as debug_file:
            debug_file.write(code)
    
    try:
        # Get the current directory - we'll need to ensure code can access files in the original paths
        current_dir = os.getcwd()
        
        # Add current directory to PYTHONPATH to help with imports
        env = os.environ.copy()
        python_path = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = f"{current_dir}{os.pathsep}{python_path}"
        
        # Redirect stdout and stderr
        result = subprocess.run(
            [sys.executable, temp_filename],
            capture_output=True,
            text=True,
            timeout=60,  # Extended timeout for complex analysis
            env=env,
            cwd=current_dir  # Execute from current directory to maintain path references
        )
        
        # Check for errors
        if result.returncode != 0:
            # Try to identify missing packages
            missing_packages = []
            error_output = result.stderr
            
            if "ModuleNotFoundError: No module named" in error_output:
                # Extract package name from error message
                for line in error_output.split('\n'):
                    if "ModuleNotFoundError: No module named" in line:
                        package = line.split("'")[1]
                        missing_packages.append(package)
            
            return False, error_output, missing_packages
        
        # Success
        return True, result.stdout, []
    
    except subprocess.TimeoutExpired:
        return False, "Execution timed out after 60 seconds", []
    except Exception as e:
        return False, f"Error executing code: {str(e)}", []
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_filename)
        except:
            pass  # Ignore errors when cleaning up


def install_packages(packages: List[str]) -> Tuple[bool, str]:
    """Install required packages using pip."""
    if not packages:
        return True, "No packages to install"
    
    try:
        # Install packages using pip
        packages_str = " ".join(packages)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + packages,
            capture_output=True,
            text=True,
            timeout=120  # Allow up to 2 minutes for installation
        )
        
        if result.returncode != 0:
            return False, f"Failed to install packages: {result.stderr}"
        
        return True, f"Successfully installed: {packages_str}"
    
    except Exception as e:
        return False, f"Error installing packages: {str(e)}"