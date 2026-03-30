import asyncio
import sys
import time
from pathlib import Path
from memory_api import MemoryAPI

from daemons.event_processor import _append_to_warm

def test_qa():
    print("[QA] Starting Verification...")
    
    api = MemoryAPI()
    
    # 1. Test event generation
    api.emit_event("test_qa", "Testing QA updates", project="qa_test")
    
    # 2. Test event_processor resilience to missing newlines
    path = Path("memory/projects/qa-test.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    # create a file ending abruptly at the marker
    path.write_text("## Recent Activity", encoding="utf-8")
    
    try:
        _append_to_warm("qa-test", {"type": "test", "content": "hello world", "ts": "2026-03-29"})
        print("[QA] event_processor explicitly handled trailing newline absence: PASS")
    except ValueError:
        print("[QA] event_processor crashed on missing newline: FAIL")
        sys.exit(1)
        
    print("[QA] Contents:", repr(path.read_text()))
    
    # 3. Test get_ledger_events PostgreSQL integration (doesn't crash)
    evs = api.get_ledger_events(limit=5)
    print(f"[QA] Fetched {len(evs)} events via API: PASS")
    
    print("[QA] All tests passed!")

if __name__ == '__main__':
    test_qa()
