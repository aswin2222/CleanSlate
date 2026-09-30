"""Headless disaster recovery CLI script to invert an applied run back to original state."""
import sys
import os
import argparse
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.execution.ledger import TransformationLedger
from app.execution.rollback import RollbackEngine
from app.execution.canonical_hash import compute_canonical_hash


def main():
    parser = argparse.ArgumentParser(description="CleanSlate Headless Disaster Rollback CLI")
    parser.add_argument("--run-id", required=True, help="Run ID to invert")
    parser.add_argument("--input-file", required=False, help="Path to current cleaned dataset file")
    parser.add_argument("--output", required=True, help="Destination path for restored dataset")
    args = parser.parse_args()

    print(f"[*] Initializing ledger recovery for run {args.run_id}...")
    ledger = TransformationLedger(run_id=args.run_id)

    if not ledger.entries:
        print(f"[!] No entries found in ledger for run {args.run_id}.")
        sys.exit(1)

    initial_hash = ledger.entries[0].hash_before
    print(f"[*] Target original canonical hash: {initial_hash}")

    if args.input_file and os.path.exists(args.input_file):
        df = pd.read_csv(args.input_file)
    else:
        # Load from storage
        dataset_storage_path = os.path.join("storage", "datasets", f"{args.run_id}.csv")
        if os.path.exists(dataset_storage_path):
            df = pd.read_csv(dataset_storage_path)
        else:
            print("[!] No current dataset file found to invert.")
            sys.exit(1)

    engine = RollbackEngine(ledger=ledger, original_hash=initial_hash)
    result = engine.rollback_to(df, target_seq=0)

    if result.matches_original:
        print(f"[+] Rollback successful! Canonical SHA-256 MATCHES original state (100.0% fidelity).")
    else:
        print(f"[-] Warning: Hash mismatch. Original: {result.hash_original}, Restored: {result.hash_current}")

    result.restored_df.to_csv(args.output, index=False)
    print(f"[+] Recovered dataset written to {args.output}")


if __name__ == "__main__":
    main()
