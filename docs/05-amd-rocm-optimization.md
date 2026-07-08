# 05 — AMD / ROCm Optimization

OmniCaption is **disqualified if it does not demonstrably use AMD compute.** This doc covers building
for ROCm, targeting the right GPU architecture, staying inside VRAM, and Track 3 serving tunables.

## CTranslate2-HIP build steps

faster-whisper runs on **CTranslate2 built with HIP** for AMD GPUs. Build for the host architecture:

1. Install the ROCm toolchain and PyTorch-ROCm in the build image.
2. Export the target arch **before compiling** CTranslate2-HIP:
   ```bash
   export PYTORCH_ROCM_ARCH=<gfx>   # e.g. gfx942 for MI300X
   ```
3. Compile CTranslate2 with HIP enabled, then install the Python bindings.
4. Verify faster-whisper picks the HIP device at runtime.

The arch must match the GPU the container will actually run on. Pick `<gfx>` from the table below.

## gfx target table

| GPU | gfx arch | VRAM | Class |
| --- | --- | --- | --- |
| MI300X | `gfx942` | 192 GB HBM3 | Datacenter |
| RX 7900 XTX | `gfx1100` | 24 GB | Workstation |
| RX 6600 | `gfx1032` | 8 GB | Consumer (tightest VRAM) |
| Ryzen AI 780M | `gfx1103` | shared | APU |
| Ryzen AI 890M | `gfx1150` | shared | APU |

## HSA_OVERRIDE_GFX_VERSION

For cards **not** in ROCm's supported list, force a compatible arch at runtime:

```bash
export HSA_OVERRIDE_GFX_VERSION=<major.minor.step>   # spoof a supported gfx
```

This makes ROCm treat an unlisted card as a nearby supported one. Use it when a consumer/APU part is
otherwise rejected by the runtime.

## VRAM sequential execution

The 8 GB RX 6600 is the binding constraint. Whisper and Gemma 4 E4B **never** co-reside in VRAM:
Stage 3 (Memory Reclamation) tears Whisper down with `del` / `gc.collect()` /
`torch.cuda.empty_cache()` before the VLM loads. See [01-architecture](01-architecture.md) and
[03-captioning-pipeline](03-captioning-pipeline.md). Gemma 4 runs **4-bit quantized** to fit the
smallest target.

## MI300X / vLLM serving tunables (Track 3)

For the "Video-Oracle" stretch serving **Gemma 4 31B** on MI300X via **vLLM-ROCm**:

```bash
export HIP_FORCE_DEV_KERNARG=1
export TORCH_BLAS_PREFER_HIPBLASLT=1
export SAFETENSORS_FAST_GPU=1
# vLLM flag:
--kv-cache-dtype fp8
# system: disable NUMA balancing
```

- `--kv-cache-dtype fp8` — halves KV-cache memory, enabling longer contexts / more concurrency.
- `HIP_FORCE_DEV_KERNARG=1` — lower kernel-arg latency on MI300X.
- `TORCH_BLAS_PREFER_HIPBLASLT=1` — prefer hipBLASLt for faster GEMMs.
- `SAFETENSORS_FAST_GPU=1` — faster weight load to GPU.
- Disable NUMA balancing to avoid page-migration jitter on the datacenter part.

These are Track 3 only; the Track 2 batch pipeline does not use vLLM.
