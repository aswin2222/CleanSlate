"""CleanSlate Comprehensive Verification Harness (R1-R5, L1-L4)."""
import subprocess
import sys
import os
import time

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def run_step(step_name: str, cmd: list, cwd: str = ".") -> bool:
    print(f"\n{CYAN}======================================================================{RESET}")
    print(f"{CYAN}[RUNNING]{RESET} {step_name}")
    print(f"{YELLOW}Command:{RESET} {' '.join(cmd)}")
    print(f"{CYAN}======================================================================{RESET}")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=cwd, shell=True)
    duration = time.time() - t0
    if res.returncode == 0:
        print(f"{GREEN}[PASSED]{RESET} {step_name} in {duration:.2f}s")
        return True
    else:
        print(f"{RED}[FAILED]{RESET} {step_name} (exit code {res.returncode})")
        return False


def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")

    print(f"\n{CYAN}Starting CleanSlate Master Verification Suite...{RESET}\n")

    steps = [
        ("Phase 1: Ingestion & Profiling Unit Tests", ["pytest", "backend/tests/unit/test_phase1_ingestion_profiling.py"]),
        ("Phase 2: Mathematical Reversibility Property Tests (Hypothesis)", ["pytest", "backend/tests/property/test_reversibility_hypothesis.py"]),
        ("Phase 3: Multi-Component Loss Model Tests", ["pytest", "backend/tests/unit/test_phase3_loss_model.py"]),
        ("Phase 4: Semantic Inference & Planning Tests", ["pytest", "backend/tests/unit/test_phase4_inference_planning.py"]),
        ("Phase 5: Automated Testgen & Mutation Tests", ["pytest", "backend/tests/unit/test_phase5_testgen.py"]),
        ("Phase 6: Database, Auth & End-to-End API Tests", ["pytest", "backend/tests/api/test_api_endpoints.py"]),
        ("Phase 8: Adversarial Resilience Tests (25 Attack Vectors)", ["pytest", "backend/tests/adversarial/test_adversarial_suite.py"]),
        ("Phase 8: Empirical Benchmark & Corruptor Tests", ["pytest", "backend/tests/unit/test_phase8_benchmarks.py"]),
        ("Frontend: TypeScript Typecheck & Production Vite Bundle", ["npm", "run", "build"], frontend_dir),
    ]

    all_passed = True
    for step in steps:
        name = step[0]
        cmd = step[1]
        cwd = step[2] if len(step) > 2 else root_dir
        passed = run_step(name, cmd, cwd=cwd)
        if not passed:
            all_passed = False

    print(f"\n{CYAN}======================================================================{RESET}")
    if all_passed:
        print(f"{GREEN}ALL PHASES & REQUIREMENTS (R1-R5, L1-L4) VERIFIED SUCCESSFULLY!{RESET}")
    else:
        print(f"{RED}ONE OR MORE VERIFICATION STEPS FAILED. CHECK LOGS ABOVE.{RESET}")
    print(f"{CYAN}======================================================================{RESET}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
