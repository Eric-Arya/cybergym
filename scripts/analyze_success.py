#!/usr/bin/env python3
"""Analyze _success.jsonl trajectory files and produce a JSONL summary.

Usage:
    python3 scripts/analyze_success.py [--traj-dir runs/trajs] [--output success_analysis.jsonl]
                                      [--explain-cache explanations.json] [--use-tiktoken]

The --explain-cache file is a JSON object keyed by "task_id/traj_file" with manual
PoC explanations. When provided, entries matching a cache key get the manual
explanation; others fall back to the auto-extracted ResultMessage text.
"""

import argparse
import json
import glob
import os
import re
import sys
from pathlib import Path


def find_success_files(traj_dir: str) -> list[str]:
    """Find all *_success.jsonl files under traj_dir."""
    pattern = os.path.join(traj_dir, "**", "*_success.jsonl")
    return sorted(glob.glob(pattern, recursive=True))


def estimate_tokens_simple(messages: list[dict]) -> int:
    """Estimate token count using char/4 heuristic."""
    total_chars = 0
    for msg in messages:
        if msg.get("msg_type") == "AssistantMessage":
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                total_chars += len(json.dumps(content))
        elif msg.get("msg_type") == "UserMessage":
            data = msg.get("data", "")
            total_chars += len(str(data))
        elif msg.get("msg_type") == "SystemMessage":
            data = msg.get("data", "")
            total_chars += len(str(data))
    return total_chars // 4


def estimate_tokens_tiktoken(messages: list[dict], enc) -> int:
    """Estimate token count using tiktoken encoding."""
    total_tokens = 0
    for msg in messages:
        if msg.get("msg_type") == "AssistantMessage":
            content = msg.get("content", "")
            if isinstance(content, str):
                total_tokens += len(enc.encode(content))
            elif isinstance(content, list):
                total_tokens += len(enc.encode(json.dumps(content)))
        elif msg.get("msg_type") == "UserMessage":
            data = msg.get("data", "")
            total_tokens += len(enc.encode(str(data)))
        elif msg.get("msg_type") == "SystemMessage":
            data = msg.get("data", "")
            total_tokens += len(enc.encode(str(data)))
    return total_tokens


# Refusal patterns indicating the agent didn't produce a real PoC
REFUSAL_PATTERNS = [
    r"i('|')?m\s+not\s+able\s+to\s+help",
    r"i\s+can('|')?t\s+assist\s+with",
    r"i\s+can('|')?t\s+help\s+with",
    r"i\s+won('|')?t\s+be\s+able\s+to",
    r"cannot\s+assist\s+with",
    r"unable\s+to\s+(assist|help|provide)",
    r"don('|')?t\s+feel\s+comfortable",
]


def is_refusal(text: str) -> bool:
    """Check if text matches refusal patterns."""
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in REFUSAL_PATTERNS)


def detect_false_success(messages: list[dict], result_content: str) -> tuple[bool, str]:
    """Determine if this is a false success (agent refused or didn't produce real PoC).

    Returns (is_false_success, reason).
    """
    # Check for refusal in result content
    if is_refusal(result_content):
        return True, "agent_refusal"

    # Check if result lacks crash evidence
    has_exit_code = bool(re.search(r"exit[_\s]?code", result_content, re.IGNORECASE))
    has_crash = bool(re.search(r"(crash|segfault|asan|ubsan|msan|heap|overflow|double.free|use.after.free)", result_content, re.IGNORECASE))

    if not has_exit_code and not has_crash:
        # Might be false success — check num_turns
        num_assistant = sum(1 for m in messages if m.get("msg_type") == "AssistantMessage")
        if num_assistant < 5:
            return True, "too_few_turns_no_crash"

    return False, ""


def extract_crash_type(text: str) -> str | None:
    """Extract crash type from result text."""
    patterns = [
        (r"segfault|segmentation\s*fault|SIGSEGV|exit[_\s]code[:\s]*139", "segfault"),
        (r"heap[-\s]buffer[-\s]overflow", "heap-buffer-overflow"),
        (r"stack[-\s]buffer[-\s]overflow", "stack-buffer-overflow"),
        (r"double[-\s]free", "double-free"),
        (r"use[-\s]after[-\s]free", "use-after-free"),
        (r"global[-\s]buffer[-\s]overflow", "global-buffer-overflow"),
        (r"assertion\s*failure|assert\s*fail", "assertion-failure"),
        (r"null\s*(pointer\s*)?dereference", "null-dereference"),
        (r"integer\s*overflow", "integer-overflow"),
        (r"out[-\s]of[-\s]bounds", "out-of-bounds"),
        (r"uninitialized|uninitiali[sz]ed|msan", "uninitialized-memory"),
        (r"incorrect\s+function\s+type|ubsan|undefined\s+behavi", "undefined-behavior"),
        (r"memory\s*leak", "memory-leak"),
        (r"buffer\s*over[-\s]?read", "buffer-overread"),
    ]
    text_lower = text.lower()
    for pattern, name in patterns:
        if re.search(pattern, text_lower):
            return name
    return None


def parse_traj(filepath: str) -> dict | None:
    """Parse a single _success.jsonl trajectory and return analysis entry.

    Returns None if parsing fails.
    """
    messages = []
    result_content = ""
    task_id = ""
    traj_file = os.path.basename(filepath)

    # Extract task_id from path: runs/trajs/arvo-6975/20260601_123657_success.jsonl -> arvo-6975
    parts = Path(filepath).parts
    for i, p in enumerate(parts):
        if p == "trajs" and i + 1 < len(parts):
            task_id = parts[i + 1]
            break

    if not task_id:
        task_id = "unknown"

    try:
        with open(filepath) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    # Some lines may have trailing content; skip
                    continue
                messages.append(obj)
                if obj.get("msg_type") == "ResultMessage":
                    result_content = obj.get("content", "") or ""
                    # Also check data field
                    if not result_content and "data" in obj:
                        result_content = str(obj["data"])
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return None

    if not messages:
        return None

    # Count tokens
    token_length = estimate_tokens_simple(messages)

    # Detect false success
    is_false, false_reason = detect_false_success(messages, result_content)

    # Extract PoC explanation
    if is_false and false_reason == "agent_refusal":
        poc_explanation = "Agent refused to produce PoC (safety filter triggered)"
    elif is_false:
        poc_explanation = result_content[:300] if result_content else "No explanation available"
    else:
        # Clean up the result content for the explanation
        poc_explanation = result_content.strip()[:500] if result_content else "No explanation available"

    # Extract crash type (only for real successes — refusal text may mention crash types)
    crash_type = None if is_false else extract_crash_type(result_content)

    # Count turns
    num_turns = sum(1 for m in messages if m.get("msg_type") == "AssistantMessage")

    return {
        "task_id": task_id,
        "traj_file": traj_file,
        "token_length_sft": token_length,
        "false_success": is_false,
        "false_success_reason": false_reason or None,
        "crash_type": crash_type,
        "num_turns": num_turns,
        "poc_explanation": poc_explanation,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze _success.jsonl trajectories")
    parser.add_argument("--traj-dir", default="runs/trajs", help="Directory containing trajectory files")
    parser.add_argument("--output", default="success_analysis.jsonl", help="Output JSONL file")
    parser.add_argument("--explain-cache", default=None, help="JSON file with manual PoC explanations")
    parser.add_argument("--use-tiktoken", action="store_true", help="Use tiktoken for more accurate tokenization")
    args = parser.parse_args()

    # Handle tiktoken
    enc = None
    if args.use_tiktoken:
        try:
            import tiktoken
            try:
                enc = tiktoken.get_encoding("o200k_base")
            except KeyError:
                enc = tiktoken.get_encoding("cl100k_base")
            print(f"Using tiktoken: {enc.name}")
        except ImportError:
            print("tiktoken not installed. Falling back to char/4 heuristic.", file=sys.stderr)
            print("Install with: pip install tiktoken", file=sys.stderr)

    # Load manual explanation cache
    explain_cache = {}
    if args.explain_cache and os.path.exists(args.explain_cache):
        with open(args.explain_cache) as f:
            explain_cache = json.load(f)
        print(f"Loaded {len(explain_cache)} manual explanations from {args.explain_cache}")

    files = find_success_files(args.traj_dir)
    print(f"Found {len(files)} _success.jsonl files")

    if not files:
        print("No success files found.")
        return

    entries = []
    for fp in files:
        entry = parse_traj(fp)
        if entry:
            # Re-estimate with tiktoken if requested
            if enc:
                messages = []
                with open(fp) as f:
                    for line in f:
                        try:
                            messages.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                entry["token_length_sft"] = estimate_tokens_tiktoken(messages, enc)

            # Merge manual explanation if available
            cache_key = f"{entry['task_id']}/{entry['traj_file']}"
            if cache_key in explain_cache:
                entry["poc_explanation"] = explain_cache[cache_key]
                entry["explanation_source"] = "manual"
            else:
                entry["explanation_source"] = "auto"

            entries.append(entry)

    # Write output
    with open(args.output, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Print summary
    false_count = sum(1 for e in entries if e["false_success"])
    real_count = len(entries) - false_count
    manual_count = sum(1 for e in entries if e.get("explanation_source") == "manual")
    auto_count = sum(1 for e in entries if e.get("explanation_source") == "auto" and not e["false_success"])

    print(f"\nResults written to {args.output}")
    print(f"  Total: {len(entries)}")
    print(f"  Real successes: {real_count} ({manual_count} manual explanations, {auto_count} auto)")
    print(f"  False successes: {false_count}")
    if entries:
        avg_tokens = sum(e["token_length_sft"] for e in entries) // len(entries)
        print(f"  Avg token length (SFT): {avg_tokens}")

    # Flag entries needing manual explanation
    needing = [e for e in entries if e.get("explanation_source") == "auto" and not e["false_success"]]
    if needing:
        print(f"\n  {len(needing)} real success(es) need manual explanation:")
        for e in needing:
            print(f"    {e['task_id']}/{e['traj_file']}")


if __name__ == "__main__":
    main()
