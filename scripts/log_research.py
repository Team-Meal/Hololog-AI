"""
Claude Code PostToolUse / Stop 훅이 호출하는 research.md 자동 로거.
외부 패키지 없이 stdlib만 사용.
"""
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

RESEARCH_FILE = Path(__file__).parent.parent / "research.md"

_CATEGORY_MAP = {
    "app/rag/":          "RAG",
    "app/agent/":        "AGENT",
    "app/api/":          "API",
    "app/main.py":       "API",
    "app/core/config":   "CONFIG",
    ".env":              "CONFIG",
    ".claude/":          "HARNESS",
    "scripts/":          "HARNESS",
}


def _category(file_path: str) -> str:
    for pattern, cat in _CATEGORY_MAP.items():
        if pattern in file_path.replace("\\", "/"):
            return cat
    return "IMPROVEMENT"


def _short_desc(tool_name: str, tool_input: dict, file_path: str) -> str:
    if tool_name == "Edit":
        new = tool_input.get("new_string", "")
        first = next((l.strip() for l in new.splitlines() if l.strip()), "")
        snippet = first[:60] + ("..." if len(first) > 60 else "")
        return f"{Path(file_path).name} 수정 — {snippet}" if snippet else f"{Path(file_path).name} 수정"
    if tool_name == "Write":
        content = tool_input.get("content", "")
        first = next((l.strip() for l in content.splitlines() if l.strip()), "")
        snippet = first[:60] + ("..." if len(first) > 60 else "")
        return f"{Path(file_path).name} 작성 — {snippet}" if snippet else f"{Path(file_path).name} 작성"
    return f"{Path(file_path).name}"


def append_entry(text: str) -> None:
    with open(RESEARCH_FILE, "a", encoding="utf-8") as f:
        f.write(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["file", "stop"], required=True)
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    hook_data: dict = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            hook_data = json.loads(raw)
    except Exception:
        pass

    if args.mode == "file":
        tool_name = hook_data.get("tool_name", "Unknown")
        tool_input = hook_data.get("tool_input", {})
        file_path = tool_input.get("file_path", tool_input.get("path", "?"))
        cat = _category(file_path)
        desc = _short_desc(tool_name, tool_input, file_path)
        append_entry(f"[{now}] [{cat}] {desc}\n")

    elif args.mode == "stop":
        append_entry(f"\n---\n[{now}] [SESSION] 세션 종료\n---\n")

    print("OK")


if __name__ == "__main__":
    main()
