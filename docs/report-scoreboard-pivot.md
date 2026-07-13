# Report: Project OmniCaption Status Update
**For**: Tumo (via Claude)  
**From**: VoxPersona Team (OmniCaption / Katlego via Gemini)  
**Subject**: Fix for Timeout Error and Strategic Pivot to Recover Track 2 Quality (Scoreboard Crisis)  
**Date**: 2026-07-13  

---

## 1. Executive Summary: Good News, and Urgent News
The timeout issue with the auto-judge has been successfully resolved; OmniCaption now executes successfully within the submission window. However, this fix introduced a severe quality regression, causing our submission to place **93rd on the scoreboard**.

Our pipeline was previously highly performant but violated the execution limit. To pass the judge, we implemented aggressive timeout reductions. This achieved speed (passing the judge) but sacrificed the complex style synthesis required for Track 2 (Formal, Sarcastic, etc.), resulting in the current low score.

Our diagnosis is clear: The current models are fast, but they are no longer "smart" about stylistic nuance. We must now fine-tune these models to specialized behavioral adapters, teaching them to recover quality while maintaining their current execution speed.

---

## 2. Stage-by-Stage Quality Audit
To isolate the quality leakage, we have audited the current execution pipeline:

### A. Audio Stage (Whisper STT)
*   **The Status**: Currently utilizing the optimized `large-v3-turbo` model on CTranslate2-HIP or falling back to `base` on local CPU runs.
*   **The Issue**: Truncated segments or high Voice Activity Detection (VAD) filter thresholds sometimes skip quiet speech or background dialogue, feeding empty or sparse transcripts to the synthesis engine. 
*   **The Pivot**: Adjust VAD parameters and explore a lightweight whisper model size (like `medium` or `small` quantized to `int8`) that preserves word error rate (WER) on tricky clips.

### B. Vision Stage (Keyframe Extraction)
*   **The Status**: Using OpenCV scene change thresholds to extract exactly 8 keyframes.
*   **The Issue**: Static keyframes fail to capture fast motion, camera pans, or text overlays, leading to captions that ignore critical visual progression.
*   **The Pivot**: Introduce motion-intensity metadata to select more representative keyframes, or pass low-resolution keyframe grids to the VLM to stay within the token budget.

### C. Synthesis Stage (VLM Prompting & Styling)
*   **The Status**: Offloaded to cloud-based serverless models or using fast local fallbacks. Style prompt instructions were heavily pruned to prevent token limits and timing overflows.
*   **The Issue**: The VLM output is fast but flat. The sarcastic tone lacks bite, and the humorous tech/non-tech captions repeat generic jokes rather than grounding them in the clip's unique events.

---

## 3. The Path Forward: Style Finetuning & Quantization
To push into the Top 50, we propose a strategic transition from generic zero-shot prompting to specialized, lightweight behavioral adapters.

### A. Golden Dataset Assembly
We will generate a synthetic dataset of **500–1,000 highly curated video-caption pairs** using larger VLMs (like GPT-4o or Gemini 1.5 Pro) with uncapped stylistic instructions. These captions will serve as the "golden ground truth" for training.

### B. Parameter-Efficient Finetuning (PEFT)
We will target smaller, open-source vision-language models:
*   **Candidate Models**: `Qwen2-VL-7B-Instruct` or `Gemma-3-8B-IT` (when released).
*   **Method**: LoRA / QLoRA (4-bit quantization during training) targeting the self-attention and projection layers.
*   **Objective**: Train the VLM to strictly output the four required styles (`formal`, `sarcastic`, `humorous_tech`, `humorous_non_tech`) in structured JSON in a single forward pass, bypassing the need for multi-shot prompting.

### C. Container Optimization (ROCm / vLLM)
*   **Pruning**: Continue utilizing Tumo's PyTorch-free CTranslate2-HIP engine for transcription to save space.
*   **Serving**: Pack the quantized VLM adapter into the final container and serve it locally using a high-throughput, ROCm-native library (like `vLLM-ROCm` or `llama.cpp` with HIP acceleration).
*   **Memory Handoff**: Retain our sequential loading rule to ensure VRAM is reclaimed when transitioning from Whisper to the local VLM.
