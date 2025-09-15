import asyncio
import httpx
import os
import time
import platform
from collections import defaultdict, deque
from colorama import Fore, Style, init
import json
from datetime import datetime  # ADDED

base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, "version.json") , "r") as version_data:
    version_file = json.load(version_data)

init()
current_version = version_file.get("version")

class Colors:
    GREEN = Fore.GREEN
    RED = Fore.RED
    CYAN = Fore.CYAN
    YELLOW = Fore.YELLOW
    RESET = Style.RESET_ALL

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

DEFAULT_WORDLIST_CONTENT = """
admin
login
dashboard
index.php
test
api
v1
v2
v3
.git
.env
config.php
wp-admin
panel
robots.txt
sitemap.xml
user
public
""".strip()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_wordlist(path):
    try:
        if not os.path.exists(path):
            print(f"{Colors.YELLOW}[!] Wordlist file not found: {path}{Colors.RESET}")
            choice = input(f"{Colors.CYAN}[?]{Colors.RESET} Create a default wordlist at '{path}'? (y/n): ").strip().lower()
            if choice == 'y':
                with open(path, 'w') as f:
                    f.write(DEFAULT_WORDLIST_CONTENT + "\n")
                print(f"{Colors.GREEN}[+] Default wordlist created successfully.{Colors.RESET}")
            else:
                return []
        with open(path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"{Colors.RED}[ERR] Error loading wordlist: {e}{Colors.RESET}")
        return []

# Structured logging (queue + tickets)
class LogEvent:
    # type: 'start' or 'final' or 'plain'
    def __init__(self, ev_type, ticket=None, text="", color="", newline=True):
        self.ev_type = ev_type
        self.ticket = ticket
        self.text = text
        self.color = color
        self.newline = newline

async def log_writer(queue):
    last_text_by_ticket = {}
    def write_line(s):
        print(s, flush=True)
    while True:
        ev = await queue.get()
        if ev is None:
            break
        if ev.ev_type == "plain":
            write_line(f"{ev.color}{ev.text}{Colors.RESET}")
        elif ev.ev_type == "start":
            last_text_by_ticket[ev.ticket] = f"{ev.color}{ev.text}{Colors.RESET}"
            # print the starting line
            write_line(last_text_by_ticket[ev.ticket])
        elif ev.ev_type == "final":
            prev = last_text_by_ticket.get(ev.ticket, "")
            write_line(f"{ev.color}{ev.text}{Colors.RESET}")
            last_text_by_ticket.pop(ev.ticket, None)
        queue.task_done()

async def check_endpoint(session, semaphore, base_url, endpoint, rps_limit, queue, results_acc):
    url = f"{base_url}/{endpoint.lstrip('/')}"
    ticket = f"{time.time_ns()}-{endpoint}"

    async with semaphore:
        start_time = time.time()
        await queue.put(LogEvent("start", ticket=ticket, text=f"[~] Trying: {url}", color=Colors.YELLOW))
        try:
            res = await session.get(url, timeout=5.0, follow_redirects=False)
            status = res.status_code
            if status == 200:
                await queue.put(LogEvent("final", ticket=ticket, text=f"[+] OPEN : {url}", color=Colors.GREEN))
                results_acc["200"].append(url)
            elif status in (301, 302, 307, 308):
                await queue.put(LogEvent("final", ticket=ticket, text=f"[>] REDIRECT [{status}]: {url}", color=Colors.CYAN))
                results_acc["3xx"].append(f"{url} -> {status}")
            elif status in (401, 403):
                await queue.put(LogEvent("final", ticket=ticket, text=f"[!] FORBIDDEN [{status}]: {url}", color=Colors.YELLOW))
                results_acc["4xx_forbid"].append(f"{url} -> {status}")
            else:
                await queue.put(LogEvent("final", ticket=ticket, text=f"[-] Not Found [{status}]: {url}", color=Colors.RED))  # Do not store in results_acc
        except httpx.RequestError as e:
            await queue.put(LogEvent("final", ticket=ticket, text=f"[ERR] {url} → {e}", color=Colors.RED))
        finally:
            elapsed = time.time() - start_time
            if rps_limit > 0:
                delay_needed = (1.0 / rps_limit) - elapsed
                if delay_needed > 0:
                    await asyncio.sleep(delay_needed)

async def main():
    clear_screen()
    print(HEADER)

    base_url = input(f"{Colors.CYAN}[?]{Colors.RESET} Enter target URL (e.g., https://erp.example.com): ").strip().rstrip('/')
    if not base_url:
        print(f"{Colors.RED}[!] Target URL cannot be empty. Exiting...{Colors.RESET}")
        return

    wordlist_path = input(f"{Colors.CYAN}[?]{Colors.RESET} Enter wordlist file path {Colors.YELLOW}(Enter 0 for for using minimal wordlist.txt or 1 for all_in_one_wordlist.txt {Colors.RESET}: ").strip()
    if wordlist_path == "0":
        wordlist_path = os.path.join(base_dir, "wordlists", "wordlist.txt")
    elif wordlist_path == "1":
        wordlist_path = os.path.join(base_dir, "wordlists", "all_in_one_wordlist.txt")

    endpoints = load_wordlist(wordlist_path)
    if not endpoints:
        print(f"{Colors.RED}[!] No endpoints to scan. Exiting...{Colors.RESET}")
        return

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

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    merged_headers = {**default_headers, **custom_headers}

    try:
        max_workers = int(input(f"{Colors.CYAN}[?]{Colors.RESET} Enter max concurrent requests (default: 10): ").strip() or "10")
        if max_workers <= 0:
            print(f"{Colors.RED}[!] Max concurrent requests must be positive. Using default (10).{Colors.RESET}")
            max_workers = 10
    except ValueError:
        print(f"{Colors.RED}[!] Invalid input. Using default max concurrent requests (10).{Colors.RESET}")
        max_workers = 10

    try:
        rps_limit_input = input(f"{Colors.CYAN}[?]{Colors.RESET} Enter requests per second limit (0 for no limit, press enter for default: 0): ").strip() or "0"
        rps_limit = float(rps_limit_input)
        if rps_limit < 0:
            print(f"{Colors.RED}[!] RPS limit cannot be negative. Using no limit (0).{Colors.RESET}")
            rps_limit = 0.0
    except ValueError:
        print(f"{Colors.RED}[!] Invalid input. Using no RPS limit (0).{Colors.RESET}")
        rps_limit = 0.0

    print(f"\n{Colors.CYAN} Starting scan on: {base_url}{Colors.RESET}")
    print(f"{Colors.CYAN} Concurrency: {max_workers}, RPS Limit: {rps_limit if rps_limit > 0 else 'No Limit'}{Colors.RESET}")
    print(f"{Colors.CYAN} Headers used: {merged_headers}{Colors.RESET}")
    print(f"\n{Colors.GREEN} Total endpoints to scan: {len(endpoints)}{Colors.RESET}\n")

    results_acc = {
        "200": [],
        "3xx": [],
        "4xx_forbid": [],
    }

    queue = asyncio.Queue()
    writer_task = asyncio.create_task(log_writer(queue))

    async with httpx.AsyncClient(headers=merged_headers) as session:
        semaphore = asyncio.Semaphore(max_workers)
        tasks = [
            check_endpoint(session, semaphore, base_url, ep, rps_limit, queue, results_acc)
            for ep in endpoints
        ]

        # ADDED: handle Ctrl+C and still print/write partial results
        try:
            await asyncio.gather(*tasks)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        except Exception as e:
            await queue.put(LogEvent("plain", text=f"[ERR] Unhandled error: {e}", color=Colors.RED))

    # Stop writer
    await queue.put(None)
    await writer_task

    # ADDED: persist results regardless of completion
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    json_path = os.path.join(results_dir, f"apibrute_results_{ts}.json")
    txt_200 = os.path.join(results_dir, f"open_200_{ts}.txt")
    txt_3xx = os.path.join(results_dir, f"redirects_3xx_{ts}.txt")
    txt_4xx = os.path.join(results_dir, f"forbidden_401_403_{ts}.txt")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results_acc, f, ensure_ascii=False, indent=2)
        with open(txt_200, "w", encoding="utf-8") as f:
            f.write("\n".join(results_acc["200"]) + ("\n" if results_acc["200"] else ""))
        with open(txt_3xx, "w", encoding="utf-8") as f:
            f.write("\n".join(results_acc["3xx"]) + ("\n" if results_acc["3xx"] else ""))
        with open(txt_4xx, "w", encoding="utf-8") as f:
            f.write("\n".join(results_acc["4xx_forbid"]) + ("\n" if results_acc["4xx_forbid"] else ""))
        print(f"{Colors.CYAN}[i] Saved results: {json_path}{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}[ERR] Failed writing results: {e}{Colors.RESET}")

    # Final Summary (skip Not Found)
    if not results_acc["200"]:
        print(f"\n{Colors.RED}[-] Scan complete.{Colors.RESET}\n")
    else:
        print(f"\n{Colors.GREEN}[+] Scan complete.{Colors.RESET}\n")

    def section(title, items, color):
        print(f"{color}{title}{Colors.RESET}")
        if not items:
            print(f"{Colors.RED}(none){Colors.RESET}")
            return
        for it in items:
            print(f" - {it}")
        print(f" Total: {len(items)}\n")

    print(f"{Colors.CYAN}==== Results Summary (excluding Not Found) ===={Colors.RESET}")
    section("Open (200):", results_acc["200"], Colors.GREEN)
    section("Redirects (3xx):", results_acc["3xx"], Colors.CYAN)
    section("Forbidden/Unauthorized (401/403):", results_acc["4xx_forbid"], Colors.YELLOW)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Suppress duplicate traceback; main already saves and prints
        pass
