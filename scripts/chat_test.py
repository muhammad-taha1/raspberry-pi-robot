"""Bring-up bench for the chat GGUF — reply text, tok/s, latency, peak RSS.

    python scripts/chat_test.py --model ~/robot/models/LFM2.5-350M-Q4_K_M.gguf
    python scripts/chat_test.py --model ~/robot/models/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf

Prompts are grouped so two models' output can be diffed by eye:
- greetings: short small talk, checks tone/brevity.
- harder: joke / meaning of life / poem — asks that push past small talk and
  tend to expose a small model's incoherence.
- tool_style: device commands like "turn on the light". In production these
  never reach the chat model (Needle dispatches them first), but
  LlamaCppChat.reply() must still behave if Needle ever misses one —
  NO_ACTION tells the model to say plainly it can't act. A model that instead
  claims "Done!" or "The light is on now" is failing that instruction and
  would mislead the person as if the robot had actually moved.

MULTI_TURN_PROMPTS ends in "tell me a joke" to check whether unrelated earlier
turns flatten a later reply — that's what set HISTORY_TURNS to 2.
"""

from __future__ import annotations

import argparse
import resource
import time
from collections import deque

from llama_cpp import Llama

from robotd.models.chat import HISTORY_TURNS, NO_ACTION, PERSONA

PROMPT_GROUPS = {
    "greetings": ["hi", "hello", "good morning", "bye"],
    "harder": [
        "tell me a joke",
        "what's the meaning of life?",
        "write me a short poem",
        "tell me about yourself",
    ],
    "tool_style": [
        "turn on the light",
        "turn off the light",
        "can you move forward?",
    ],
}

MULTI_TURN_PROMPTS = [
    "its dark",
    "can you brighten the room?",
    "turn on the light",
    "tell me a joke",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    print(f"loading {args.model} ...")
    load_start = time.monotonic()
    llm = Llama(model_path=args.model, n_ctx=1024, n_threads=4, verbose=False)
    print(f"loaded in {time.monotonic() - load_start:.2f}s")

    def ask(messages: list[dict]) -> tuple[str, float, int]:
        start = time.monotonic()
        result = llm.create_chat_completion(
            messages=messages,
            max_tokens=80,
            temperature=0.1,
            top_k=50,
            repeat_penalty=1.05,
        )
        elapsed = time.monotonic() - start
        reply = result["choices"][0]["message"]["content"].strip()
        return reply, elapsed, result.get("usage", {}).get("completion_tokens", 0)

    for group, prompts in PROMPT_GROUPS.items():
        print(f"\n--- {group} (no history) ---")
        for prompt in prompts:
            reply, elapsed, tokens = ask(
                [
                    {"role": "system", "content": PERSONA},
                    {"role": "system", "content": NO_ACTION},
                    {"role": "user", "content": prompt},
                ]
            )
            peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

            print(f"\nprompt: {prompt!r}")
            print(f"reply: {reply!r}")
            tps = tokens / elapsed if elapsed else 0.0
            print(f"tokens: {tokens}  latency: {elapsed:.2f}s  tps: {tps:.1f}")
            print(f"peak_rss_mb: {peak_rss_mb:.1f}")

    print("\n--- multi-turn sequence (shared history window) ---")
    history: deque[tuple[str, str]] = deque(maxlen=HISTORY_TURNS)
    for prompt in MULTI_TURN_PROMPTS:
        messages = [{"role": "system", "content": PERSONA}]
        for user, assistant in history:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "system", "content": NO_ACTION})
        messages.append({"role": "user", "content": prompt})

        reply, elapsed, tokens = ask(messages)
        history.append((prompt, reply))

        print(f"\nyou: {prompt!r}")
        print(f"reply: {reply!r}  ({tokens} tokens, {elapsed:.2f}s)")


if __name__ == "__main__":
    main()
