#!/usr/bin/env python3
import argparse
import itertools
import re
from pathlib import Path


DEFAULT_VERBS = [
    "get","list","create","update","delete","add","remove","set","reset","verify",
    "auth","login","logout","register","refresh","upload","download","search",
    "assign","unassign","enable","disable","status","profile","settings"
]

DEFAULT_NOUNS = [
    "user","users","account","session","token","tokens","auth","oauth","sso",
    "password","mfa","otp","email","phone","asset","assets","file","files",
    "report","reports","role","roles","permission","permissions","policy","policies",
    "order","orders","product","products","invoice","invoices","payment","payments",
    "device","devices","log","logs","alert","alerts","incident","incidents",
    "config","configs","setting","settings","profile","profiles","team","teams",
    "admin","dashboard","analytics","metrics","health","status","version","system"
]

DEFAULT_PREFIXES = ["api","api-docs","graphql","gql","internal","public","private","admin","backend","v1","v2","v3"]
DEFAULT_VERSIONS = ["", "v1", "v2", "v3", "v4", "v5", "v1.1", "v2.0"]
DEFAULT_SUFFIXES = ["", "list","info","detail","search","export","import","verify","status"]

COMMON_SINGLETONS = [
    "/graphql", "/gql", "/swagger", "/openapi.json", "/api-docs", "/api-docs/v1/openapi.json",
    "/health", "/healthz", "/ready", "/live", "/metrics"
]

CASE_STYLES = ["plain", "snake", "kebab", "camel"]


def _flatten_to_str(parts):
    flat = []
    for p in parts:
        if p is None:
            continue
        if isinstance(p, (list, tuple)):
            for x in p:
                if x is None:
                    continue
                flat.append(str(x))
        else:
            flat.append(str(p))
    # remove empty strings
    return [s for s in flat if s]

def to_style(parts, style):
    parts = _flatten_to_str(parts)
    if not parts:
        return ""

    if style == "plain":
        return "/".join(parts)
    if style == "snake":
        return "/".join(p.replace("-", "_") for p in parts)
    if style == "kebab":
        return "/".join(p.replace("_", "-") for p in parts)
    if style == "camel":
        def camel_token(tok, first=False):
            s = str(tok)
            words = re.sub(r"[_\\-]+", " ", s).split()
            if not words:
                return ""
            head_word = words[0]
            head = head_word.lower() if first else head_word.capitalize()
            tail = "".join(w.capitalize() for w in words[1:])
            return head + tail
        segs = [camel_token(seg, first=(i == 0)) for i, seg in enumerate(parts)]
        return "/".join(segs)
    return "/".join(parts)

def pluralize(noun):
    if noun.endswith("s"):
        return noun
    if noun.endswith("y") and noun[-2:] not in ("ay","ey","iy","oy","uy"):
        return noun[:-1] + "ies"
    if noun.endswith(("ch","sh","x","z","o")):
        return noun + "es"
    return noun + "s"

def expand_nouns(nouns, enable_plural=True):
    out = set(nouns)
    if enable_plural:
        for n in nouns:
            out.add(pluralize(n))
    return sorted(out)

def load_list_file(path):
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return [x.strip() for x in p.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]

def prefix_has_version(pref: str) -> bool:
    pref = str(pref).strip().lower()
    if not pref.startswith("v"):
        return False
    rest = pref[1:]
    return bool(re.fullmatch(r"[0-9]+(\\.[0-9]+)*", rest))


def combine_paths(prefixes, versions, verbs, nouns, suffixes, case_styles, max_patterns=500000):
    emitted = set()
    results = []

    def add(path):
        if path not in emitted:
            emitted.add(path)
            results.append(path)

    # Singletons
    for s in COMMON_SINGLETONS:
        add(s)

    # Roots /api, /api/v1, etc.
    for pref in prefixes:
        for ver in versions:
            for style in case_styles:
                base = [pref]
                if ver and not prefix_has_version(pref):
                    base.append(ver)
                root = "/" + to_style(base, style)
                add(root)

    # Noun trees: /api[/v]/noun[/suffix]
    for pref in prefixes:
        for ver in versions:
            for noun in nouns:
                for suf in suffixes:
                    for style in case_styles:
                        parts = [pref]
                        if ver and not prefix_has_version(pref):
                            parts.append(ver)
                        parts.append(noun)
                        if suf:
                            parts.append(suf)
                        path = "/" + to_style(parts, style)
                        add(path)
                        if len(emitted) >= max_patterns:
                            return results

    # Verb-noun styles: /api/v/user/create and /api/v/create/user
    for pref in prefixes:
        for ver in versions:
            for verb in verbs:
                for noun in nouns:
                    for style in case_styles:
                        parts1 = [pref]
                        if ver and not prefix_has_version(pref):
                            parts1.append(ver)
                        parts1 += [noun, verb]
                        add("/" + to_style(parts1, style))

                        parts2 = [pref]
                        if ver and not prefix_has_version(pref):
                            parts2.append(ver)
                        parts2 += [verb, noun]
                        add("/" + to_style(parts2, style))

                        if len(emitted) >= max_patterns:
                            return results
    return results

def main():
    ap = argparse.ArgumentParser(description="Generate API endpoint wordlist with rich variations.")
    ap.add_argument("--verbs", help="Path to verbs file (one per line).")
    ap.add_argument("--nouns", help="Path to nouns file (one per line).")
    ap.add_argument("--prefixes", help="Path to prefixes file.")
    ap.add_argument("--versions", help="Path to versions file.")
    ap.add_argument("--suffixes", help="Path to suffixes file.")
    ap.add_argument("--case", default="plain,snake,kebab,camel", help="Comma list of case styles.")
    ap.add_argument("--no-plural", action="store_true", help="Disable noun pluralization.")
    ap.add_argument("--max", type=int, default=500000, help="Max patterns to emit.")
    ap.add_argument("-o", "--output", default="api_wordlist_generated.txt", help="Output file.")
    ap.add_argument("--seed", help="Path to seed endpoints to include (one per line).")
    ap.add_argument("--tech", default="", help="Comma list of tech hints (e.g., laravel,spring,django,express).")
    args = ap.parse_args()

    verbs = load_list_file(args.verbs) or list(DEFAULT_VERBS)
    nouns = load_list_file(args.nouns) or list(DEFAULT_NOUNS)
    prefixes = load_list_file(args.prefixes) or list(DEFAULT_PREFIXES)
    versions = load_list_file(args.versions) or list(DEFAULT_VERSIONS)
    suffixes = load_list_file(args.suffixes) or list(DEFAULT_SUFFIXES)
    styles = [s.strip() for s in args.case.split(",") if s.strip()] or list(CASE_STYLES)

    # Tech-specific enrichment
    tech = {t.strip().lower() for t in args.tech.split(",") if t.strip()}
    if "laravel" in tech or "php" in tech:
        prefixes += ["storage"]
        nouns += ["artisan","queue","jobs","broadcasting","sanctum","telescope","horizon"]
    if "spring" in tech or "java" in tech:
        prefixes += ["actuator"]
        nouns += ["actuator","metrics","env","mappings","beans"]
    if "django" in tech or "python" in tech:
        nouns += ["admin","rest","schema","openapi","swagger"]
    if "express" in tech or "node" in tech:
        nouns += ["status","health","docs","swagger","openapi"]

    nouns = expand_nouns(sorted(set(nouns)), enable_plural=not args.no_plural)
    prefixes = sorted(set(prefixes))
    versions = sorted(set(versions))
    verbs = sorted(set(verbs))
    suffixes = sorted(set(suffixes))

    endpoints = combine_paths(
        prefixes=prefixes,
        versions=versions,
        verbs=verbs,
        nouns=nouns,
        suffixes=suffixes,
        case_styles=styles,
        max_patterns=args.max
    )

    seeds = load_list_file(args.seed)
    all_out = []
    seen = set()
    for e in itertools.chain(seeds, endpoints):
        e = e.strip()
        if not e:
            continue
        if not e.startswith("/"):
            e = "/" + e
        if e not in seen:
            seen.add(e)
            all_out.append(e)

    Path(args.output).write_text("\n".join(all_out) + "\n", encoding="utf-8")
    print(f"[+] Generated {len(all_out)} endpoints -> {args.output}")

if __name__ == "__main__":
    main()
