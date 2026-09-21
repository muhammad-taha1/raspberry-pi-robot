"""Bring-up spike for M6's chat model: loads a GGUF directly via llama.cpp and
prints reply text, decode tok/s, wall-clock latency, and peak RSS for a few
canned prompts — the exact failures that motivated M6 (jokes, greetings).

This is a hardware/model bring-up bench: it intentionally bypasses robotd's
models/ and actors so install and inference-speed faults can be diagnosed
directly, the same way brain_test.py does for Needle and voice_test.py does
for Piper. Run this on the Pi before pointing config/robot.toml's [chat]
section at a model — see docs/m6-research.md for the pass bar and for
recording the winning numbers.

    python scripts/chat_test.py --model /home/taha/robot/models/LFM2.5-350M-Q4_K_M.gguf

Settings below (temp, top_k, repeat_penalty) are from the LFM2.5 model card;
if you're testing Qwen3-0.6B-GGUF instead, add "/no_think" to --system or its
thinking-mode reasoning will be spoken instead of a short reply.
"""

from __future__ import annotations

import argparse
import resource
import time

from llama_cpp import Llama

PROMPTS = [
    "tell me a joke",
    "how are you?",
    "what's your name?",
    "tell me about yourself",
]

SYSTEM = (
    "You are a small desk companion robot. Answer in one or two short spoken "
    "sentences. Never output JSON, code, or invent tool names — just talk."
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--system", default=SYSTEM)
    parser.add_argument("--n-ctx", type=int, default=1024)
    parser.add_argument("--n-threads", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=80)
    args = parser.parse_args()

    print(f"loading {args.model} ...")
    load_start = time.monotonic()
    llm = Llama(
        model_path=args.model, n_ctx=args.n_ctx, n_threads=args.n_threads, verbose=False
    )
    print(f"loaded in {time.monotonic() - load_start:.2f}s")

    for prompt in PROMPTS:
        start = time.monotonic()
        result = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": args.system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=args.max_tokens,
            temperature=0.1,
            top_k=50,
            repeat_penalty=1.05,
        )
        elapsed = time.monotonic() - start

        reply = result["choices"][0]["message"]["content"].strip()
        usage = result.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        decode_tps = completion_tokens / elapsed if elapsed > 0 else 0.0
        peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

        print(f"\nprompt: {prompt!r}")
        print(f"reply: {reply!r}")
        print(f"tokens: {completion_tokens}  latency: {elapsed:.2f}s  decode_tps: {decode_tps:.1f}")
        print(f"peak_rss_mb: {peak_rss_mb:.1f}")


if __name__ == "__main__":
    main()
