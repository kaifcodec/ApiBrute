import httpx
import asyncio
import os
import time
from colorama import Fore, Style, init
import platform
# Initialize Colorama for cross-platform terminal colors
init()
current_version = "1.0.0"
# Terminal colors using Colorama
class Colors:
    GREEN = Fore.GREEN
    RED = Fore.RED
    CYAN = Fore.CYAN
    YELLOW = Fore.YELLOW
    RESET = Style.RESET_ALL

# Header for the script
HEADER = rf"""
{Colors.CYAN}
    _          _   ____             _
   / \   _ __ (_) | __ ) _ __ _   _| |_ ___
  / _ \ | '_ \| | |  _ \| '__| | | | __/ _ \ Author: kaifcodec
 / ___ \| |_) | | | |_) | |  | |_| | ||  __/ Email: kaifcodec@gmail.com
/_/   \_\ .__/|_| |____/|_|   \__,_|\__\___| Version: {current_version}
        |_|
{Colors.RESET}
{Colors.GREEN}Simple Async HTTP Endpoint Scanner by "kaifcodec"{Colors.RESET}
"""

# Default wordlist content if the file is not found
DEFAULT_WORDLIST_CONTENT = """
admin
login
dashboard
index.php
test
api
v1
.git
.env
config.php
wp-admin
panel
robots.txt
sitemap.xml
user
public
"""

# Function to clear the terminal screen
def clear_screen():
    # 'cls' for Windows, 'clear' for Unix/Linux/macOS
    os.system('cls' if os.name == 'nt' else 'clear')
def detect_os():
    """Detects and returns the operating system."""
    sys_name = platform.system()
    if sys_name == "Windows":
        return "Windows"
    elif sys_name == "Darwin":
        return "macOS"
    elif sys_name == "Linux":
        if "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ:
            return "Android (Termux/similar)"
        elif "WSL_DISTRO_NAME" in os.environ:
            return "Linux (WSL)"
        elif os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return f"Linux ({line.split('=')[1].strip().strip('\"')})"
        return "Linux"
    elif sys_name == "FreeBSD":
        return "FreeBSD"
    elif sys_name == "OpenBSD":
        return "OpenBSD"
    elif sys_name == "NetBSD":
        return "NetBSD"
    elif sys_name == "SunOS":
        return "SunOS (Solaris)"
    return f"Unknown ({sys_name})"
try:
  action = detect_os()
except Exception as err:
  print(err)
  pass

def log_usage(action, current_version):
    try:
        # This tool collects your IP just to know how distinct users this tool got
        # We ensure that your IP is kept safe in the backend database.
        # If you don't want to share your IP you can comment out that action below.
        ip = httpx.get("https://api.ipify.org").raise_for_status().text
    except:
        ip = "Unknown"
        pass
    payload = {
        "name": "ApiBrute",
        "function": action,
        "ip" : ip,
        "version": current_version,
    }

    try:
        _response = httpx.post(
            "https://tracker-api-od1b.onrender.com/log-error",
            json=payload,
            headers={"Content-Type": "application/json"},
        ).raise_for_status()
    except Exception as e:
        print(e)
        exit()


# Function to load the wordlist from a specified path
def load_wordlist(path):
    try:
        # Check if the wordlist file exists
        if not os.path.exists(path):
            print(f"{Colors.YELLOW}[!] Wordlist file not found: {path}{Colors.RESET}")
            choice = input(f"{Colors.CYAN}[?]{Colors.RESET} Create a default wordlist at '{path}'? (y/n): ").strip().lower()
            if choice == 'y':
                # Create the default wordlist if the user agrees
                with open(path, 'w') as f:
                    f.write(DEFAULT_WORDLIST_CONTENT.strip())
                print(f"{Colors.GREEN}[+] Default wordlist created successfully.{Colors.RESET}")
            else:
                return [] # Return empty list if user declines to create

        # Read endpoints from the wordlist file
        with open(path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"{Colors.RED}[ERR] Error loading wordlist: {e}{Colors.RESET}")
        return []

# Asynchronous function to check a single endpoint
async def check_endpoint(session, semaphore, endpoint, rps_limit):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    # Acquire the semaphore to limit concurrent requests
    async with semaphore:
        start_time = time.time() # Record the start time of the request
        print(f"{Colors.YELLOW}[~] Trying: {url}{Colors.RESET}")
        try:
            # Make the asynchronous HTTP GET request
            res = await session.get(url, timeout=5, follow_redirects=False)
            status = res.status_code

            # Print status based on HTTP response code
            if status == 200:
                print(f"{Colors.GREEN}[+] OPEN [{status}]: {url}{Colors.RESET}")
            elif status in [301, 302]:
                print(f"{Colors.CYAN}[>] REDIRECT [{status}]: {url}{Colors.RESET}")
            elif status in [401, 403]:
                print(f"{Colors.YELLOW}[!] FORBIDDEN [{status}]: {url}{Colors.RESET}")
            else:
                print(f"{Colors.RED}[-] Not Found [{status}]: {url}{Colors.RESET}")
        except httpx.RequestError as e:
            # Handle HTTPX request errors (e.g., network issues, timeouts)
            print(f"{Colors.RED}[ERR] {url} → {e}{Colors.RESET}")
        finally:
            # Enforce Requests Per Second (RPS) limit
            end_time = time.time() # Record the end time of the request
            elapsed_time = end_time - start_time
            if rps_limit > 0:
                # Calculate the delay needed to adhere to the RPS limit
                delay_needed = (1.0 / rps_limit) - elapsed_time
                if delay_needed > 0:
                    await asyncio.sleep(delay_needed) # Pause if needed

# Main asynchronous function to orchestrate the scanning process
async def main():
    clear_screen() # Clear screen for a clean interface
    print(HEADER) # Display the script header

    # Get target URL from user
    global BASE_URL # Declare BASE_URL as global to be accessible by check_endpoint
    BASE_URL = input(f"{Colors.CYAN}[?]{Colors.RESET} Enter target URL (e.g., https://erp.example.com): ").strip().rstrip('/')
    if not BASE_URL:
        print(f"{Colors.RED}[!] Target URL cannot be empty. Exiting...{Colors.RESET}")
        return

    # Get wordlist path from user, with a default option
    WORDLIST_PATH = input(f"{Colors.CYAN}[?]{Colors.RESET} Enter wordlist file path (Press enter for default 'wordlist.txt'): ").strip()
    if not WORDLIST_PATH:
        WORDLIST_PATH = "wordlist.txt"

    endpoints = load_wordlist(WORDLIST_PATH)

    if not endpoints:
        print(f"{Colors.RED}[!] No endpoints to scan. Exiting...{Colors.RESET}")
        return

    # Prompt for custom headers
    custom_headers = {}
    add_headers_choice = input(f"{Colors.CYAN}[?]{Colors.RESET} Do you want to add custom headers? (y/n): ").strip().lower()
    if add_headers_choice == 'y':
        print(f"{Colors.YELLOW}[!] Enter headers in 'Key:Value' format. Type 'done' when finished.{Colors.RESET}")
        while True:
            header_input = input(f"{Colors.CYAN}[?]{Colors.RESET} Header: ").strip()
            if header_input.lower() == 'done':
                break
            if ':' in header_input:
                key, value = header_input.split(':', 1)
                custom_headers[key.strip()] = value.strip()
            else:
                print(f"{Colors.RED}[!] Invalid header format. Use 'Key:Value'.{Colors.RESET}")
    
    # Define default headers
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    # Merge custom headers with default headers, custom headers take precedence
    merged_headers = {**default_headers, **custom_headers}

    # Get concurrency (max_workers) from user
    max_workers = 10
    try:
        max_workers = int(input(f"{Colors.CYAN}[?]{Colors.RESET} Enter max concurrent requests (default: 10): ").strip() or "10")
        if max_workers <= 0:
            print(f"{Colors.RED}[!] Max concurrent requests must be positive. Using default (10).{Colors.RESET}")
            max_workers = 10
    except ValueError:
        print(f"{Colors.RED}[!] Invalid input. Using default max concurrent requests (10).{Colors.RESET}")

    # Get Requests Per Second (RPS) limit from user
    rps_limit = 0
    try:
        rps_limit = float(input(f"{Colors.CYAN}[?]{Colors.RESET} Enter requests per second limit (0 for no limit, default: 0): ").strip() or "0")
        if rps_limit < 0:
            print(f"{Colors.RED}[!] RPS limit cannot be negative. Using no limit (0).{Colors.RESET}")
            rps_limit = 0
    except ValueError:
        print(f"{Colors.RED}[!] Invalid input. Using no RPS limit (0).{Colors.RESET}")

    # Display scan parameters
    print(f"\n{Colors.CYAN} Starting scan on: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.CYAN} Concurrency: {max_workers}, RPS Limit: {rps_limit if rps_limit > 0 else 'No Limit'}{Colors.RESET}")
    print(f"{Colors.CYAN} Headers used: {merged_headers}{Colors.RESET}")
    print(f"{Colors.CYAN} Total endpoints to scan: {len(endpoints)}{Colors.RESET}\n")

    # Create an asynchronous HTTP client session with the merged headers
    async with httpx.AsyncClient(headers=merged_headers) as session:
        # Create a semaphore to limit the number of concurrent tasks
        semaphore = asyncio.Semaphore(max_workers)
        
        # Create a list of asynchronous tasks for each endpoint
        tasks = [
            check_endpoint(session, semaphore, endpoint, rps_limit)
            for endpoint in endpoints
        ]
        
        # Run all tasks concurrently and wait for them to complete
        await asyncio.gather(*tasks)

    print(f"\n{Colors.GREEN}[+] Scan complete.{Colors.RESET}")

if __name__ == "__main__":
    log_usage(action , current_version)
    try:
        # Run the main asynchronous function
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle user interruption (Ctrl+C)
        print(f"\n{Colors.YELLOW}[!] Scan interrupted by user.{Colors.RESET}")

