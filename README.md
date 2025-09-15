# ⚡ ApiBrute

> 🔥 _“Fast. Silent. Effective. Just like it should be.”_  

🛠️ A lightning-fast, lightweight endpoint brute-forcer written in Python using `asyncio` + `httpx`.  
Built for hackers, pentesters, and curious minds — by **kaifcodec**.

---

## 🚀 Features

- ⚡ **Async-powered** — 10x faster than traditional scanners  
- 📂 **Built-in wordlist** — zero setup needed  
- 🎯 **Targets API & admin routes** effortlessly  
- 🧠 **Minimal, readable code** — tweak it your way  
- 💻 Works on **Linux, Windows, and Termux**

---
## 📦 Requirements (python packages)
```bash
httpx
colorama
```

## 📦 Install

```bash
pip install -r requirements.txt
```
Or for manual installation:

```bash
pip install httpx
pip install colorama

```
---

## 🔧 Usage

### Main script
```bash
cd ApiBrute
python apibrute.py 
```
`Then follow the on screen commands`

### Wordlist Generator 
```bash
cd ApiBrute/wordlist_generator
python3 generate_worlist.py --help
```
```bash
usage: generate_worlist.py [-h] [--verbs VERBS] [--nouns NOUNS] [--prefixes PREFIXES]
                           [--versions VERSIONS] [--suffixes SUFFIXES] [--case CASE] [--no-plural]
                           [--max MAX] [-o OUTPUT] [--seed SEED] [--tech TECH]

Generate API endpoint wordlist with rich variations.

options:
  -h, --help            show this help message and exit
  --verbs VERBS         Path to verbs file (one per line).
  --nouns NOUNS         Path to nouns file (one per line).
  --prefixes PREFIXES   Path to prefixes file.
  --versions VERSIONS   Path to versions file.
  --suffixes SUFFIXES   Path to suffixes file.
  --case CASE           Comma list of case styles.
  --no-plural           Disable noun pluralization.
  --max MAX             Max patterns to emit.
  -o OUTPUT, --output OUTPUT
                        Output file.
  --seed SEED           Path to seed endpoints to include (one per line).
  --tech TECH           Comma list of tech hints (e.g., laravel,spring,django,express).
```
_Optional: Plug in your own wordlist · just modify the script._

---

## 🐍 Example Output

```
[200] https://target.com/api/login
[403] https://target.com/admin
[301] https://target.com/config
```

---

## ✨ Why?

Because waiting is boring.  
Because most scanners are too loud, too slow, or too bloated.  
This tool is fast, focused, and made for action.

---

## 👨‍💻 Author

Created with focus & fire by **kaifcodec**  
- ⚔️ GitHub: [github.com/kaifcodec](https://github.com/kaifcodec)
- ⚔️ Email: kaifcodec@gmail.com
---

## 📜 License

MIT — Use it. Fork it. Break stuff responsibly. 😎
