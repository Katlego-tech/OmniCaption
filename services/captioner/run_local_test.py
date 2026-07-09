"""End-to-end local test script to run the real pipeline with Fireworks AI (T085)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 1. Load root .env file manually into os.environ
root_dir = Path(__file__).resolve().parents[2]
env_file = root_dir / ".env"
if env_file.exists():
    print(f"Loading environment from {env_file}...")
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            if "=" in line:
                key, val = line.split("=", 1)
                if "#" in val:
                    val = val.split("#", 1)[0]
                os.environ[key.strip()] = val.strip()
else:
    print("WARNING: Root .env file not found.")

# 2. Configure local input/output directories in scratch
scratch_dir = Path(__file__).resolve().parent / "tests" / "scratch"
input_dir = scratch_dir / "input"
output_dir = scratch_dir / "output"
work_dir = scratch_dir / "work"

input_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)
work_dir.mkdir(parents=True, exist_ok=True)

# Override Settings paths via OMNICAPTION_ env variables
os.environ["OMNICAPTION_INPUT_DIR"] = str(input_dir)
os.environ["OMNICAPTION_OUTPUT_DIR"] = str(output_dir)
os.environ["OMNICAPTION_WORK_DIR"] = str(work_dir)

# 3. Create a single-task tasks.json manifest in input_dir
tasks_data = [
    {
        "task_id": "v1_smoke_test",
        "video_url": "https://storage.googleapis.com/amd-hackathon-clips/1860079-uhd_2560_1440_25fps.mp4",
        "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"],
    }
]
tasks_file = input_dir / "tasks.json"
tasks_file.write_text(json.dumps(tasks_data, indent=2), encoding="utf-8")
print(f"Wrote local test task to {tasks_file}")

# 4. Import and run main entry point
from app.main import run  # noqa: E402

print("Starting end-to-end pipeline run...")
exit_code = run()
print(f"Pipeline finished with exit code: {exit_code}")

# 5. Print results output if successful
results_file = output_dir / "results.json"
if results_file.exists():
    print("\n--- results.json Output ---")
    print(results_file.read_text(encoding="utf-8"))
else:
    print("\nERROR: results.json was not generated.")
    sys.exit(1)
