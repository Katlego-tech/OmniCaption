# docs/19-notebook-environment — ROCm 7.2 + vLLM 0.16.0 + PyTorch 2.9 Notebook Implementation Plan

This document details the configuration, deployment, and testing steps for running OmniCaption on the organizer-provided high-performance notebook environment. 

---

## 1. Environment Reconnaissance & Verification
The first step is to execute a diagnostics cell to verify the exact GPU capabilities, VRAM sizes, and ROCm runtime details available in the notebook.

```python
# Cell 1: Verify system capabilities and hardware alignment
import subprocess
import os
import torch

print("=" * 60)
print("SYSTEM RECONNAISSANCE & DIAGNOSTICS")
print("=" * 60)

# 1. GPU info
print("\n--- AMD GPU Detection ---")
os.system("rocm-smi --showid --showproductname 2>/dev/null || echo 'rocm-smi not found'")
os.system("rocminfo 2>/dev/null | grep -E 'Name:|Marketing' | head -10")

# 2. ROCm version
print("\n--- ROCm SDK Version ---")
os.system("cat /opt/rocm/.info/version 2>/dev/null || echo 'ROCm version file not found'")

# 3. PyTorch ROCm Backend
print("\n--- PyTorch + ROCm/HIP Verification ---")
print(f"PyTorch version:  {torch.__version__}")
print(f"ROCm available:   {torch.cuda.is_available()}")
print(f"Device count:     {torch.cuda.device_count()}")
for i in range(torch.cuda.device_count()):
    props = torch.cuda.get_device_properties(i)
    print(f"  Device {i}: {props.name}")
    print(f"    Gfx Arch: {torch.cuda.get_device_name(i)}")
    print(f"    Total VRAM: {props.total_mem / 1e9:.2f} GB")

# 4. vLLM serving
print("\n--- vLLM Version ---")
try:
    import vllm
    print(f"vLLM version: {vllm.__version__}")
except ImportError:
    print("vLLM is not present on Python path.")

# 5. Host Memory
print("\n--- System Memory ---")
os.system("free -h | head -2")
```

---

## 2. Dependency Setup
The notebook environment has PyTorch 2.9 and vLLM 0.16.0 pre-installed. We install the remaining pipeline components, specifically `faster-whisper`, `CTranslate2`, `ffmpeg`, and `opencv-python-headless`.

```python
# Cell 2: Install required application dependencies
import subprocess
import sys

print("Installing system and Python requirements...")
# 1. Install ffmpeg for audio extraction
subprocess.run(["apt-get", "update", "-qq"], check=True)
subprocess.run(["apt-get", "install", "-y", "-qq", "ffmpeg"], check=True)

# 2. Install application python packages
subprocess.run([
    sys.executable, "-m", "pip", "install", "--quiet",
    "faster-whisper>=1.1.0",
    "opencv-python-headless>=4.8.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "requests>=2.31.0",
], check=True)

# 3. Validate CTranslate2's compute backends
import ctranslate2
print(f"CTranslate2 version: {ctranslate2.__version__}")
supported_backends = ctranslate2.get_supported_compute_types("cuda")
print(f"Supported compute types (HIP/CUDA): {supported_backends}")
```

---

## 3. Clone Repository & Environment Configuration
Clone the repository and set the environment variables to target the local directories instead of the container volumes `/input` and `/output`.

```python
# Cell 3: Clone code and configure paths
import os
import shutil

# Clone if not already present in the workspace
if not os.path.exists("OmniCaption"):
    print("Cloning OmniCaption repository...")
    os.system("git clone https://github.com/Katlego-tech/OmniCaption.git")

# Change directory to the captioner pipeline root
os.chdir("OmniCaption/services/captioner")

# Configure pipeline to run in notebook local mode
os.environ["FIREWORKS_API_KEY"] = "YOUR_FIREWORKS_API_KEY"  # <-- Replace with your Fireworks Key
os.environ["OMNICAPTION_WHISPER_MODEL_SIZE"] = "large-v3"    # Leverage VRAM on high-end hardware
os.environ["OMNICAPTION_INPUT_DIR"] = "/tmp/omnicaption/input"
os.environ["OMNICAPTION_OUTPUT_DIR"] = "/tmp/omnicaption/output"
os.environ["HF_HUB_OFFLINE"] = "0"                          # Allow model downloads for first setup

# Clean/Create directories
os.makedirs("/tmp/omnicaption/input", exist_ok=True)
os.makedirs("/tmp/omnicaption/output", exist_ok=True)
print("Environment configured.")
```

---

## 4. Manifest Writing (Sample Tasks)
Write a mock task list matching the Act II evaluation format.

```python
# Cell 4: Write sample task manifest
import json

tasks = [
    {
        "task_id": "v1",
        "video_url": "https://storage.googleapis.com/amd-hackathon-clips/3015510-uhd_3840_2160_24fps.mp4",
        "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
    },
    {
        "task_id": "v2",
        "video_url": "https://storage.googleapis.com/amd-hackathon-clips/13825391-uhd_3840_2160_30fps.mp4",
        "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
    }
]

tasks_path = "/tmp/omnicaption/input/tasks.json"
with open(tasks_path, "w") as f:
    json.dump(tasks, f, indent=2)

print(f"Tasks manifest written to: {tasks_path}")
```

---

## 5. Execution of the Pipeline (FastAPI-Equivalent Run)
Import the pipeline classes directly and run them inline. This logs timing metrics and writes the output files.

```python
# Cell 5: Run the 6-stage pipeline
import sys
import time
import json

# Add current folder to path
sys.path.insert(0, ".")

from app.core.config import get_settings
from app.core.gpu import assert_amd
from app.core.schema import Task
from app.pipeline.orchestrator import CaptionPipeline
from app.pipeline.output import validate_and_write

# Log the active hardware profile (device, gfx arch, VRAM)
assert_amd(enforced=False)

cfg = get_settings()

# Read input task list
with open(cfg.tasks_path, "r") as f:
    raw_tasks = json.load(f)
tasks = [Task(**t) for t in raw_tasks]

# Run orchestrator
start_time = time.monotonic()
pipeline = CaptionPipeline(cfg)
results = pipeline.run(tasks)
pipeline.close()

elapsed = time.monotonic() - start_time

# Write output results (schema-validated + atomic)
validate_and_write(results, cfg.results_path)

print(f"\n============================================================")
print(f"Pipeline executed in {elapsed:.2f} seconds.")
print(f"Results written to: {cfg.results_path}")
print(f"============================================================")
```

---

## 6. Result Verification & Verification Checkpoints
Examine the output payload to confirm captions are fully populated and not backfilled with fallback errors.

```python
# Cell 6: Verify and print output JSON content
import json

with open("/tmp/omnicaption/output/results.json", "r") as f:
    results_data = json.load(f)

print(json.dumps(results_data, indent=2))

# Verify accuracy checklist
print("\n--- Verifying Output Integrity ---")
for task in results_data:
    task_id = task["task_id"]
    for style, caption in task["captions"].items():
        if caption.strip() == "" or "synthesis failed" in caption.lower():
            print(f"❌ Task {task_id} style '{style}': Caption is empty or fallback.")
        else:
            print(f"✅ Task {task_id} style '{style}': Valid caption generated.")
```

---

## 7. Serving Local VLMs with vLLM (Optional)
If the notebook has high VRAM available (e.g., MI210 with 64GB or MI300X with 192GB), you can serve a local VLM (like `google/gemma-3-12b-it` or `google/gemma-3-27b-it` in FP16/BF16) using vLLM in a background process, pointing the synthesis stage to this server instead of Fireworks AI.

### Launch local vLLM Server (Background Terminal Cell)
```python
# Cell 7a: Launch local OpenAI-compatible VLM server using vLLM
import subprocess
import time
import requests

MODEL = "google/gemma-3-12b-it"  # Adjust model size depending on available GPU VRAM
PORT = 8085

# Launch the vLLM server in the background
proc = subprocess.Popen([
    "python", "-m", "vllm.entrypoints.openai.api_server",
    "--model", MODEL,
    "--port", str(PORT),
    "--tensor-parallel-size", "1",
    "--max-model-len", "4096",
    "--trust-remote-code",
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

print(f"Launching vLLM server with model: {MODEL} on port {PORT}...")

# Wait until the health check endpoint returns 200
for i in range(180):
    try:
        res = requests.get(f"http://localhost:{PORT}/health", timeout=2)
        if res.status_code == 200:
            print(f"Server is ready after {i} seconds!")
            break
    except requests.exceptions.RequestException:
        time.sleep(1)
else:
    print("Server launch timed out. Check processes.")
```

### Route Pipeline to Local vLLM
```python
# Cell 7b: Reconfigure env to use local vLLM endpoint
import os

os.environ["OMNICAPTION_FIREWORKS_API_URL"] = "http://localhost:8085/v1"
os.environ["OMNICAPTION_FIREWORKS_VLM_MODEL"] = "google/gemma-3-12b-it"
os.environ["FIREWORKS_API_KEY"] = "local-compute-bypassed"

print("Pipeline redirected to local vLLM endpoint.")
```
Re-running **Cell 5** after executing the above config change will redirect all caption synthesis tasks to your locally-hosted ROCm-powered vLLM container.
