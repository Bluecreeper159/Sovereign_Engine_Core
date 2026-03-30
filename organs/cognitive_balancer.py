import os
import sys
import json
import re
import shlex
import subprocess
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
# Avoid circular import by treating main.py as a loosely coupled sibling
import main

class CognitiveBalancer:
    """
    Cognitive Load Balancer Organ
    
    A structural implementation of the Trio Pattern used to scale local LLM reasoning.
    When a directive exceeds the model's unconstrained reasoning capacity (e.g., broad 
    "find the problem" tasks across 50k codebases), the Balancer intercepts the prompt,
    uses the fast local model to extract targeted investigation scopes, maps it to 
    sub-agents, and synthesizes the outputs into a highly constrained 2k token context
    for the primary mutation loop.
    """
    
    def __init__(self):
        self.fast_model = os.getenv("ACTIVE_MODEL", "auto")

    def should_intercept(self, prompt: str, context: str) -> bool:
        """Heuristic assessing if the task demands Load Balancing."""
        # Force intercept if operator uses explicit broad instructions combining 
        # both "memory ledger" and broad "codebase/solution" phrases without targets
        words = prompt.lower()
        needs_memory = "memory" in words or "ledger" in words or "hot.md" in words
        needs_scan = "bottleneck" in words or "identify" in words or "review" in words or "propose" in words
        
        explicit_target = "<read>" in prompt or "<read_block>" in prompt
        
        # Trigger Sharding if it's an unconstrained broad scan
        if needs_memory and needs_scan and not explicit_target:
            return True
            
        return False

    def decompose_task(self, prompt: str) -> list[dict]:
        """Phase 1: Ask the fast local model to decompose the intent into scoped targets."""
        print("[BALANCER] Phase 1: Structural Decomposition triggered...")
        
        extractor_sys = """
You are the internal Cognitive Load Balancer.
Your goal is to parse a massive unconstrained user directive and break it into exactly TWO highly constrained sub-tasks.

Task 1: The Diagnostics Task (e.g., reading logs or memory to find the bottleneck).
Task 2: The Physical Task (e.g., executing a bash command to find the file paths relevant to Task 1).

Reply ONLY in this exact JSON array format:
[
  {"agent": "Diagnostic", "prompt": "Identify the core failure class in the memory ledger.", "command": "cat ~/.gemini/memory/hot.md ~/.gemini/memory/events.jsonl | tail -n 50"},
  {"agent": "Physical Mapper", "prompt": "Find all Python files in the Sovereign Core containing EVOLVE-BLOCK markers.", "command": "grep -rn 'EVOLVE-BLOCK' /home/frost/Desktop/Agent_System/Sovereign_Engine_Core/main.py"}
]
"""
        try:
            raw_out = main.llm_inference(prompt, extractor_sys, model_override=self.fast_model)
            
            # Extract JSON array
            json_str = re.search(r'\[\s*\{.*?\}\s*\]', raw_out, re.DOTALL)
            if json_str:
                return json.loads(json_str.group(0))
            else:
                # Fallback static decomposition if json parsing fails
                print("[BALANCER] JSON parse failed. Using static fallback shard schema.")
                return [
                    {"agent": "Diagnostic", "prompt": "Identify the core failure.", "command": "cat ~/.gemini/memory/hot.md"},
                    {"agent": "Physical", "prompt": "Find main.py EVOLVE markers.", "command": "grep -n 'EVOLVE-BLOCK' /home/frost/Desktop/Agent_System/Sovereign_Engine_Core/main.py"}
                ]
        except Exception as e:
            print(f"[BALANCER ERROR] Decomposition failed: {e}")
            return []

    def execute_sub_task(self, subtask: dict) -> str:
        """Phase 2: Execute the scoped context gathering."""
        print(f"[BALANCER] Phase 2: Dispatching {subtask['agent']}...")
        
        try:
            # 1. Gather raw execution context (bypassing LLM optical generation overhead completely)
            res = subprocess.run(subtask['command'], shell=True, capture_output=True, text=True, timeout=10)
            raw_context = res.stdout[-4000:] if res.stdout else res.stderr[-4000:]
            
            # 2. Ask local model to synthesize just this specific subset of data
            synth_sys = f"You are the {subtask['agent']} sub-agent. Given the raw command output below, address the prompt directly: '{subtask['prompt']}'\n\nCOMMAND OUTPUT:\n{raw_context}"
            
            summary = main.llm_inference("Analyze the raw context and output a purely factual synthesis. No conversational filler.", synth_sys, model_override=self.fast_model)
            return f"--- Sub-Task [{subtask['agent']}] Synthesized Intelligence ---\n{summary}\n"
        except Exception as e:
            return f"--- Sub-Task [{subtask['agent']}] Failed to Gather Intelligence ---\nError: {str(e)}\n"

    def shard_and_synthesize(self, original_prompt: str, original_context: str) -> str:
        """
        Main entry point. Takes raw massive task, shards it, 
        and returns a highly compressed, pre-digested systemic context.
        """
        subtasks = self.decompose_task(original_prompt)
        if not subtasks:
             # If sharding fails, fallback to passing unmodified context natively.
             return original_context
             
        synthesized_context = original_context + "\n\n=== COGNITIVE LOAD BALANCER INTELLIGENCE INJECTION ===\n"
        
        # In a production distributed daemon, use asyncio.gather here.
        # Running sequentially for isolated safety.
        for t in subtasks:
            synthesized_context += self.execute_sub_task(t) + "\n"
            
        synthesized_context += "=== END INTELLIGENCE ===\n\nCRITICAL DIRECTIVE: You MUST use the Synthesized Intelligence provided above to write and execute the solution autonomously, circumventing the need to physically scan large files yourself."
        
        print("[BALANCER] Phase 3: Synthesis Complete. Bridging back to main execution loop.")
        return synthesized_context
