
import os
import sys
import time
import signal
import subprocess
import shutil
from pathlib import Path
from colorama import init, Fore, Style

# Initialize colorama
init()

def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗ ██████╗ ███████╗███╗   ███╗██╗ ██████╗              ║
    ║  ██╔════╝██╔═══██╗██╔════╝████╗ ████║██║██╔════╝              ║
    ║  ██║     ██║   ██║███████╗██╔████╔██║██║██║                   ║
    ║  ██║     ██║   ██║╚════██║██║╚██╔╝██║██║██║                   ║
    ║  ╚██████╗╚██████╔╝███████║██║ ╚═╝ ██║██║╚██████╗              ║
    ║   ╚═════╝ ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝ ╚═════╝              ║
    ║                                                               ║
    ║         🚀 COSMIC AI - UNIFIED LAUNCHER                       ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(Fore.CYAN + banner + Style.RESET_ALL)

def log(msg, level="info"):
    if level == "info":
        print(f"{Fore.GREEN}  ✨ [INFO] {msg}{Style.RESET_ALL}")
    elif level == "warn":
        print(f"{Fore.YELLOW}  ⚠️  [WARN] {msg}{Style.RESET_ALL}")
    elif level == "error":
        print(f"{Fore.RED}  ❌ [ERROR] {msg}{Style.RESET_ALL}")
    elif level == "sys":
        print(f"{Fore.MAGENTA}  💻 [SYSTEM] {msg}{Style.RESET_ALL}")

def is_process_running(process_name):
    # Simple check if a process is running (Windows specific basic check)
    call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
    try:
        output = subprocess.check_output(call).decode()
        return process_name in output
    except:
        return False

def main():
    print_banner()
    
    ollama_process = None
    backend_process = None
    ollama_started_by_us = False  # Track if we started Ollama

    try:
        # Determine paths relative to this script
        script_dir = Path(__file__).parent.absolute()
        backend_dir = script_dir / "Backend"

        # 1. Start Ollama (if not running)
        log("Checking Ollama status...", "sys")
        if is_process_running("ollama.exe"):
             log("Ollama is already running.", "info")
        else:
             if shutil.which("ollama"):
                 log("Starting Ollama server...", "sys")
                 # Start hidden
                 startupinfo = subprocess.STARTUPINFO()
                 startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                 startupinfo.wShowWindow = subprocess.SW_HIDE
                 
                 try:
                     ollama_process = subprocess.Popen(
                         ["ollama", "serve"], 
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                         startupinfo=startupinfo,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL
                     )
                     ollama_started_by_us = True  # Mark that we started it
                     time.sleep(3)  # Wait for startup
                     
                     # Verify it started
                     if ollama_process.poll() is None:
                         log("Ollama started successfully ✓", "info")
                     else:
                         log("Ollama process ended unexpectedly", "warn")
                         ollama_process = None
                         ollama_started_by_us = False
                 except Exception as e:
                     log(f"Failed to start Ollama: {e}", "error")
                     ollama_process = None
                     ollama_started_by_us = False
             else:
                 log("Ollama executable not found in PATH. Skipping local LLM support.", "warn")

        # 2. Start Backend
        log("Initializing FastAPI Backend...", "sys")
        print(f"{Fore.CYAN}     ├─ Vector Database: FAISS HNSW{Style.RESET_ALL}")
        print(f"{Fore.CYAN}     ├─ Knowledge Graph: Neo4j (Graph Database){Style.RESET_ALL}")
        print(f"{Fore.CYAN}     ├─ Chunking: Agentic Semantic Analysis{Style.RESET_ALL}")
        print(f"{Fore.CYAN}     └─ LLM: Azure OpenAI (GPT-5){Style.RESET_ALL}")
        
        if not backend_dir.exists():
            log(f"Backend directory not found at: {backend_dir}", "error")
            return

        # We run uvicorn as a subprocess
        cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        
        backend_process = subprocess.Popen(
            cmd,
            cwd=str(backend_dir),
            env=os.environ.copy()
        )
        
        log("Backend started successfully ✓", "info")
        log("API Server: http://localhost:8000", "info")
        log("API Docs: http://localhost:8000/docs", "info")
        log("Press Ctrl+C to stop all services", "sys")
        
        # 3. Monitor Loop
        while True:
            if backend_process.poll() is not None:
                log("Backend process ended unexpectedly.", "error")
                break
            time.sleep(1)

    except KeyboardInterrupt:
        log("\nStopping services...", "sys")
    except Exception as e:
        log(f"Unexpected error: {e}", "error")
    finally:
        # Cleanup
        if backend_process:
            log("Stopping Backend...", "sys")
            try:
                backend_process.terminate()
                backend_process.wait(timeout=5)
                log("Backend stopped ✓", "info")
            except Exception as e:
                log(f"Error stopping backend: {e}", "warn")
                try:
                    backend_process.kill()
                except:
                    pass
        
        # Only kill Ollama if WE started it
        if ollama_started_by_us and ollama_process:
            log("Stopping Ollama (started by us)...", "sys")
            try:
                # Try graceful termination first
                ollama_process.terminate()
                try:
                    ollama_process.wait(timeout=3)
                    log("Ollama stopped gracefully ✓", "info")
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop
                    log("Force killing Ollama...", "sys")
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(ollama_process.pid)], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL)
                    log("Ollama force stopped ✓", "info")
            except Exception as e:
                log(f"Error stopping Ollama: {e}", "warn")
        elif is_process_running("ollama.exe") and not ollama_started_by_us:
            log("Ollama was already running before launcher - leaving it running", "info")
        
        log("Shutdown complete. 👋", "info")

if __name__ == "__main__":
    main()

