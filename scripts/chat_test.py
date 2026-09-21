"""Bring-up bench for the chat GGUF — reply text, tok/s, latency, peak RSS.

    python scripts/chat_test.py --model ~/robot/models/LFM2.5-350M-Q4_K_M.gguf

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

PROMPTS = [
    "tell me a joke",
    "how are you?",
    "what's your name?",
    "tell me about yourself",
]

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

    print("--- cold prompts (no history) ---")
    for prompt in PROMPTS:
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
        print(f"tokens: {tokens}  latency: {elapsed:.2f}s  tps: {tokens / elapsed:.1f}")
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
