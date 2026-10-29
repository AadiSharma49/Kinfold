import json

from kinfold_training.train_dpo import load_dataset_dict


def test_load_dataset_dict_parses_jsonl_into_columns(tmp_path):
    path = tmp_path / "pairs.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {"prompt": "p1", "chosen": "c1", "rejected": "r1", "duel_id": "d1", "category": "code"},
                {"prompt": "p2", "chosen": "c2", "rejected": "r2", "duel_id": "d2", "category": "debate"},
            ]
        ),
        encoding="utf-8",
    )

    data = load_dataset_dict(path)

    assert data == {
        "prompt": ["p1", "p2"],
        "chosen": ["c1", "c2"],
        "rejected": ["r1", "r2"],
    }
