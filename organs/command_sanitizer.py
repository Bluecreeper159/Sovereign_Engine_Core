"""
organs/command_sanitizer.py
Sovereign Engine — Callosum Command Sanitizer
Intercepts blocking/infinite Unix commands before they reach the execution gate.
Prevents hanging tool calls from locking the Cortex Callosum dispatch threads.

Wire into: invoke_agent's <execute> tag handler, BEFORE subprocess dispatch.
Also wire into: CortexCallosum's parallel sub-task dispatcher.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Blocking pattern registry
# ---------------------------------------------------------------------------
# Each entry: (pattern, human_readable_reason, safe_alternative)
BLOCKING_PATTERNS: list[tuple[str, str, str]] = [
    # Infinite follow/stream modes
    (r'journalctl\s+.*\s-f\b',       "journalctl -f streams indefinitely",         "journalctl --no-pager -n 100 --since='5 minutes ago'"),
    (r'journalctl\s+-f\b',           "journalctl -f streams indefinitely",         "journalctl --no-pager -n 100"),
    (r'\btail\s+-f\b',               "tail -f streams indefinitely",               "tail -n 100"),
    (r'\btail\s+.*--follow\b',       "tail --follow streams indefinitely",         "tail -n 100"),

    # Watch / continuous polling
    (r'\bwatch\s+',                  "watch polls continuously without exit",      "Run the command once directly"),

    # Ping without count limit
    (r'\bping\b(?!.*\s-c\s)(?!.*-c\d)', "ping without -c count runs forever",    "ping -c 4 <host>"),

    # Netcat listeners
    (r'\bnc\b.*-l\b',                "netcat in listen mode blocks forever",       "Use a socket timeout: nc -l -w 5"),
    (r'\bncat\b.*-l\b',              "ncat in listen mode blocks forever",         "Use a socket timeout: ncat -l -w 5"),

    # Continuous capture tools
    (r'\btcpdump\b(?!.*-c\s)',       "tcpdump without -c count streams forever",   "tcpdump -c 50 ..."),
    (r'\bwireshark\b',               "wireshark requires GUI and blocks",          "Use tshark -c 50 for CLI capture"),
    (r'\btshark\b(?!.*-c\s)',        "tshark without -c count streams forever",    "tshark -c 50 ..."),

    # Interactive / REPL processes
    (r'\bpython3?\s*$',              "bare python opens an interactive REPL",      "python3 -c '...' or python3 script.py"),
    (r'\bipython\b',                 "ipython opens an interactive REPL",          "python3 -c '...'"),
    (r'\bnode\s*$',                  "bare node opens an interactive REPL",        "node -e '...' or node script.js"),
    (r'\bsqlite3\b(?!.*<)',          "sqlite3 without input opens interactive shell", "sqlite3 db.sqlite '.tables'"),
    (r'\bpsql\b(?!.*-c\s)(?!.*-f)', "psql without -c or -f opens interactive shell", "psql -c 'SELECT ...'"),
    (r'\bmysql\b(?!.*-e\s)',         "mysql without -e opens interactive shell",   "mysql -e 'SELECT ...'"),

    # Sleep / deliberate blocking
    (r'\bsleep\s+(?:inf|infinity)\b', "sleep infinity blocks forever",             "Use a bounded sleep: sleep 5"),

    # Dangerous stream redirects that can fill disk
    (r'>\s*/dev/sd[a-z]',            "direct write to block device is dangerous",  "Never write directly to block devices"),
    (r'dd\b.*of=/dev/sd[a-z]',       "dd to block device can destroy data",        "Verify target carefully before using dd"),
]

# Compile all patterns once at import time
_COMPILED: list[tuple[re.Pattern, str, str]] = [
    (re.compile(pat, re.IGNORECASE), reason, alt)
    for pat, reason, alt in BLOCKING_PATTERNS
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SanitizationResult:
    safe: bool
    command: str
    matched_pattern: Optional[str] = None
    reason: Optional[str] = None
    alternative: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def rejection_message(self) -> str:
        """
        Formatted rejection traceback injected back into the organism's context.
        Mirrors the style of Blast Chamber rejections for consistency.
        """
        lines = [
            "[CommandSanitizer] EXECUTION BLOCKED — Hanging command detected.",
            f"  Command   : {self.command}",
            f"  Reason    : {self.reason}",
            f"  Pattern   : {self.matched_pattern}",
            f"  Fix       : {self.alternative}",
            "",
            "This failure class has been flagged for CortexDB injection.",
            "Rewrite the <execute> call using the suggested alternative before retrying.",
        ]
        return "\n".join(lines)

    def cortexdb_lesson(self) -> str:
        """One-line lesson string for hot.md / CortexDB injection."""
        return (
            f"CommandSanitizer blocked hanging command '{self.command[:60]}'. "
            f"Reason: {self.reason}. Use: {self.alternative}"
        )


# ---------------------------------------------------------------------------
# Core sanitizer
# ---------------------------------------------------------------------------

class CommandSanitizer:
    """
    Stateless command sanitizer. Wire a single instance into invoke_agent.

    Usage:
        sanitizer = CommandSanitizer()
        result = sanitizer.check(command_string)
        if not result.safe:
            return result.rejection_message()   # inject into organism context
            # also fire result.cortexdb_lesson() into memory API
    """

    def check(self, command: str) -> SanitizationResult:
        """
        Scan a command string against all blocking patterns.
        Returns a SanitizationResult — always check .safe before dispatching.
        """
        cmd = command.strip()

        for compiled_pat, reason, alternative in _COMPILED:
            if compiled_pat.search(cmd):
                return SanitizationResult(
                    safe=False,
                    command=cmd,
                    matched_pattern=compiled_pat.pattern,
                    reason=reason,
                    alternative=alternative,
                )

        return SanitizationResult(safe=True, command=cmd)

    def batch_check(self, commands: list[str]) -> list[SanitizationResult]:
        """Check multiple commands — useful for Callosum parallel dispatch validation."""
        return [self.check(cmd) for cmd in commands]

    def add_pattern(self, pattern: str, reason: str, alternative: str):
        """
        Runtime pattern injection — lets the organism teach the sanitizer
        new blocking patterns via CortexDB lessons without a code restart.
        """
        compiled = re.compile(pattern, re.IGNORECASE)
        _COMPILED.append((compiled, reason, alternative))


# ---------------------------------------------------------------------------
# XML primitive handler — wire into invoke_agent's <execute> dispatch
# ---------------------------------------------------------------------------

def handle_execute_sanitization(
    sanitizer: CommandSanitizer,
    command: str,
) -> tuple[bool, str]:
    """
    Drop-in gate for the <execute> tag handler in invoke_agent.

    Returns:
        (True, command)   — safe to dispatch
        (False, message)  — blocked; inject message into organism context
    """
    result = sanitizer.check(command)
    if result.safe:
        return True, command
    return False, result.rejection_message()


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sanitizer = CommandSanitizer()

    test_commands = [
        # Should be BLOCKED
        "journalctl -f --since=2026-03-28 | grep Evolution",
        "journalctl --since=yesterday -f",
        "tail -f /var/log/syslog",
        "watch -n 1 df -h",
        "ping google.com",
        "nc -l -p 4444",
        "tcpdump -i eth0",
        "python3",
        "sleep infinity",

        # Should be SAFE
        "journalctl --no-pager -n 100 --since='5 minutes ago'",
        "tail -n 50 /var/log/syslog",
        "ping -c 4 google.com",
        "tcpdump -c 50 -i eth0",
        "python3 -c 'print(\"hello\")'",
        "python3 /path/to/script.py",
        "ps aux | grep uvicorn",
        "grep -r 'EVOLVE-BLOCK' /home/frost/sovereign/",
        "cat ~/.gemini/memory/hot.md",
        "ls -la /home/frost/sovereign/organs/",
    ]

    print("=" * 65)
    print("CommandSanitizer Smoke Test")
    print("=" * 65)

    blocked = 0
    passed  = 0

    for cmd in test_commands:
        result = sanitizer.check(cmd)
        status = "🚫 BLOCKED" if not result.safe else "✅ SAFE   "
        print(f"\n{status} | {cmd[:55]}")
        if not result.safe:
            print(f"          Reason : {result.reason}")
            print(f"          Fix    : {result.alternative}")
            blocked += 1
        else:
            passed += 1

    print("\n" + "=" * 65)
    print(f"Results: {blocked} blocked / {passed} safe / {len(test_commands)} total")
