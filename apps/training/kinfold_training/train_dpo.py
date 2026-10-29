"""DPO + LoRA pipeline test — proves the mechanism works end to end on a
genuinely tiny model, on CPU. This is NOT meant to produce a useful model;
it's meant to prove the plumbing (export -> dataset -> DPO -> LoRA adapter)
actually runs before any real GPU time or a real base model gets involved.

Needs heavy packages NOT installed by default (torch, transformers, trl,
peft, datasets — torch alone is a real download even CPU-only). Install
them deliberately, once you're ready to actually run this:

    uv sync --group train

Then:

    uv run python -m kinfold_training.train_dpo \
        --data ../api/data/preference_pairs.jsonl \
        --base-model hf-internal-testing/tiny-random-gpt2 \
        --output ./output/pipeline-test

Do not point --base-model at a real, large open-weight model and do not
run this on a rented GPU without separate approval — see docs/decisions.md,
2026-10-29 ("Do not spend money on GPUs").
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_dataset_dict(data_path: Path) -> dict[str, list[str]]:
    prompts, chosen, rejected = [], [], []
    for line in data_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        prompts.append(row["prompt"])
        chosen.append(row["chosen"])
        rejected.append(row["rejected"])
    return {"prompt": prompts, "chosen": chosen, "rejected": rejected}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="JSONL from export_preference_pairs.py")
    parser.add_argument(
        "--base-model",
        default="hf-internal-testing/tiny-random-gpt2",
        help="A genuinely tiny model for pipeline testing, not a real base model.",
    )
    parser.add_argument("--output", type=Path, default=Path("./output/pipeline-test"))
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()

    # Imported here, not at module level, so this file can be linted and
    # imported (e.g. load_dataset_dict, used elsewhere) without the train
    # dependency group installed.
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import DPOConfig, DPOTrainer

    data = load_dataset_dict(args.data)
    if len(data["prompt"]) == 0:
        raise SystemExit(
            f"No preference pairs in {args.data}. Run scripts/export_preference_pairs.py "
            "against a database with at least one resolved, open-weight-vs-open-weight, "
            "non-draw duel first."
        )
    dataset = Dataset.from_dict(data)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(args.base_model)
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["c_attn"] if "gpt2" in args.base_model else None,
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    dpo_config = DPOConfig(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        learning_rate=1e-4,
        logging_steps=1,
        report_to=[],
    )

    trainer = DPOTrainer(
        model=model,
        args=dpo_config,
        train_dataset=dataset,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(str(args.output))
    print(f"Pipeline test complete. LoRA adapter saved to {args.output}")
    print(
        "This proves the DPO+LoRA mechanism runs end to end — it is not a "
        "useful model. See this file's own docstring before pointing it at "
        "a real base model or any paid GPU time."
    )


if __name__ == "__main__":
    main()
