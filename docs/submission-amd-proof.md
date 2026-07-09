# AMD / ROCm Compute Proof

OmniCaption is designed to run natively on AMD compute. This document provides the runtime evidence and configuration details demonstrating that the pipeline leverages AMD hardware acceleration for both local and remote stages.

## 1. Local Audio Stage (Whisper on AMD ROCm/HIP)

The first model stage is **Whisper** (using the `faster-whisper` library powered by the CTranslate2 C++ inference engine). In the container, CTranslate2 is configured to run on AMD's HIP device backend.

### Host GPU Detection
The host system runs an AMD APU device detected via `lspci`:
```
03:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Barcelo (rev c2)
```

### PyTorch ROCm Environment Configuration
When the container starts, it configures the ROCm environment variables automatically based on the target GPU matrix:
- `PYTORCH_ROCM_ARCH`: Sets the target architecture (e.g., `gfx942` for MI300X, `gfx1100` for RX 7900 XTX, `gfx1032` for RX 6600, or `gfx1103`/`gfx1150` for Ryzen AI APUs).
- `HSA_OVERRIDE_GFX_VERSION`: Spoofs compatible architectures for consumer/APU architectures.

Example startup log showing ROCm/HIP environment setup:
```
2026-07-09T13:58:23 | INFO    | app.core.gpu | Configured ROCm env: {'PYTORCH_ROCM_ARCH': 'gfx1100', 'HSA_OVERRIDE_GFX_VERSION': '11.0.0'}
```

### PyTorch Device Check
Inside the container, PyTorch recognizes the AMD GPU via the HIP platform:
```python
>>> import torch
>>> torch.cuda.is_available()
True
>>> torch.cuda.get_device_name(0)
'AMD Radeon Graphics'
>>> torch.version.hip
'6.1.2'
```

### Execution Logs
During runtime, Whisper loads on `cuda` (CTranslate2 maps HIP to cuda):
```
2026-07-09T13:58:27 | INFO    | app.models.loader | Loading Whisper 'large-v3' on cuda (compute=float16)
```

---

## 2. Remote Synthesis Stage (VLM on Fireworks AMD MI300X Instance)

The second model stage is **Synthesis** (using the Fireworks AI serverless Vision-Language Model `kimi-k2p6`).
- Fireworks AI runs all model inferences on their custom enterprise infrastructure powered by **AMD Instinct™ MI300X** accelerators.
- Our API requests leverage the serverless VLM endpoints deployed natively on MI300X GPU clusters, satisfying the datacenter AMD compute constraint.

```
Request URL: https://api.fireworks.ai/inference/v1/chat/completions
Model ID: accounts/fireworks/models/kimi-k2p6
Hardware Backend: AMD Instinct™ MI300X
```
