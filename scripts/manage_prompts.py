from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from langfuse import Langfuse
from app.prompt_management import DEFAULT_PROMPT_TEMPLATE

V1_TEMPLATE = DEFAULT_PROMPT_TEMPLATE
V2_TEMPLATE = (
    "[System: Answer concisely and accurately based strictly on the provided docs.]\n"
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}"
)
PROMPT_NAME = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")


def get_client() -> Langfuse:
    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        raise ValueError("Thiếu LANGFUSE_PUBLIC_KEY hoặc LANGFUSE_SECRET_KEY trong .env")
    return Langfuse(public_key=public_key, secret_key=secret_key, host=host)


def init_prompts(client: Langfuse) -> None:
    print(f"--- Khởi tạo Prompt '{PROMPT_NAME}' ---")
    # Tạo v1 với labels baseline & production
    p1 = client.create_prompt(
        name=PROMPT_NAME,
        prompt=V1_TEMPLATE,
        type="text",
        labels=["baseline", "production"],
        commit_message="v1: baseline prompt with feature, docs, message",
    )
    print(f"Created Prompt v{p1.version} with labels: {getattr(p1, 'labels', ['baseline', 'production'])}")

    # Tạo v2 với label candidate
    p2 = client.create_prompt(
        name=PROMPT_NAME,
        prompt=V2_TEMPLATE,
        type="text",
        labels=["candidate"],
        commit_message="v2: candidate prompt with system instructions",
    )
    print(f"Created Prompt v{p2.version} with labels: {getattr(p2, 'labels', ['candidate'])}")


def promote_candidate(client: Langfuse) -> None:
    print(f"--- Chuyển label 'production' sang Candidate (v2) ---")
    candidate_prompt = client.get_prompt(PROMPT_NAME, label="candidate")
    v2 = candidate_prompt.version
    client.update_prompt(
        name=PROMPT_NAME,
        version=v2,
        new_labels=["candidate", "production"],
    )
    print(f"Updated v{v2} labels to: ['candidate', 'production']")


def rollback_to_baseline(client: Langfuse) -> None:
    print(f"--- Rollback label 'production' về Baseline (v1) ---")
    baseline_prompt = client.get_prompt(PROMPT_NAME, label="baseline")
    v1 = baseline_prompt.version
    client.update_prompt(
        name=PROMPT_NAME,
        version=v1,
        new_labels=["baseline", "production"],
    )
    print(f"Rolled back production label to v{v1} (labels: ['baseline', 'production'])")


def show_status(client: Langfuse) -> None:
    print(f"--- Trạng thái Prompt '{PROMPT_NAME}' ---")
    for label in ["production", "baseline", "candidate"]:
        try:
            p = client.get_prompt(PROMPT_NAME, label=label)
            labels = getattr(p, "labels", [])
            print(f"Label '{label}': Version {p.version} | Labels: {labels}")
            print(f"  Template:\n{p.prompt}\n")
        except Exception as e:
            print(f"Label '{label}': Không tìm thấy ({e})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quản lý prompt versioning và labels trên Langfuse")
    parser.add_argument("--init", action="store_true", help="Tạo prompt v1 (baseline, production) và v2 (candidate)")
    parser.add_argument("--promote", action="store_true", help="Chuyển label production sang v2 (candidate)")
    parser.add_argument("--rollback", action="store_true", help="Rollback label production về v1 (baseline)")
    parser.add_argument("--status", action="store_true", help="Xem trạng thái các labels và versions")
    args = parser.parse_args()

    client = get_client()

    if args.init:
        init_prompts(client)
    elif args.promote:
        promote_candidate(client)
    elif args.rollback:
        rollback_to_baseline(client)
    elif args.status:
        show_status(client)
    else:
        show_status(client)


if __name__ == "__main__":
    main()
