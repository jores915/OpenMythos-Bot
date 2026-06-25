"""
OpenMythos Training — Fine-tuning loop
=======================================
Peut être déclenché via l'API POST /train.
"""

import asyncio
import logging
import time
from typing import Optional

import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


async def run_finetune(
    dataset: str = "roneneldan/TinyStories",
    steps: int = 1000,
    batch_size: int = 32,
    seq_len: int = 256,
    lr: float = 3e-4,
    device: str = "cpu",
):
    """Lance un fine-tuning asynchrone."""
    from open_mythos import MythosConfig, OpenMythos
    from open_mythos.tokenizer import MythosTokenizer

    logger.info(f"Starting fine-tuning: {dataset}, {steps} steps")

    cfg = MythosConfig(
        vocab_size=32000, dim=512, n_heads=8, n_kv_heads=2,
        max_seq_len=seq_len + 1, max_loop_iters=4,
        prelude_layers=1, coda_layers=1, attn_type="mla",
        kv_lora_rank=128, q_lora_rank=256, qk_rope_head_dim=32,
        qk_nope_head_dim=64, v_head_dim=64, n_experts=16,
        n_shared_experts=2, n_experts_per_tok=4, expert_dim=512, lora_rank=8,
    )
    model = OpenMythos(cfg).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, betas=(0.9, 0.95))
    tok = MythosTokenizer()

    # Stream dataset
    try:
        from datasets import load_dataset
        raw = load_dataset(dataset, split="train", streaming=True)
    except Exception as e:
        logger.error(f"Cannot load dataset {dataset}: {e}")
        return

    buffer: list[int] = []
    step = 0
    model.train()

    for sample in raw:
        text = sample.get("text", "")
        if not text:
            continue
        buffer.extend(tok.encode(text))
        if len(buffer) < seq_len + 1:
            continue

        # Build batch from buffer
        n_pairs = len(buffer) // (seq_len + 1)
        if n_pairs == 0:
            continue

        pairs = []
        for i in range(min(n_pairs, batch_size)):
            s = i * (seq_len + 1)
            chunk = buffer[s:s + seq_len + 1]
            if len(chunk) == seq_len + 1:
                pairs.append(chunk)

        if not pairs:
            buffer = buffer[-(seq_len + 1):]
            continue

        xs = torch.tensor([p[:-1] for p in pairs], dtype=torch.long, device=device)
        ys = torch.tensor([p[1:] for p in pairs], dtype=torch.long, device=device)

        optimizer.zero_grad()
        logits = model(xs, n_loops=2)
        loss = F.cross_entropy(logits.view(-1, cfg.vocab_size), ys.view(-1))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        step += 1
        if step % 100 == 0:
            logger.info(f"Step {step}/{steps} — loss: {loss.item():.4f}")

        # Yield control to event loop
        if step % 10 == 0:
            await asyncio.sleep(0)

        # Trim buffer
        buffer = buffer[batch_size * (seq_len + 1):]

        if step >= steps:
            break

    logger.info(f"Fine-tuning complete. Final loss: {loss.item():.4f}")
    # Save checkpoint
    torch.save(model.state_dict(), f"checkpoint_{int(time.time())}.pt")
    logger.info("Checkpoint saved.")
