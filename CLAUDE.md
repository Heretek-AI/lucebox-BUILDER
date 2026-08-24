# lucebox-BUILDER

Nightly binary-release builder for https://github.com/Luce-Org/lucebox (Linux x86_64, CUDA + HIP), modeled on the ROCmFPX-BUILDER workflow pattern. Upstream is cloned fresh in CI; the local `lucebox/` directory is an untracked scratch clone (gitignored).

## Key files

- `.github/workflows/build-lucebox.yml` — the whole pipeline: prepare-matrix → build-cuda / build-rocm (matrix) → smoke-test (self-hosted, non-blocking) → create-release.
- `.github/actions/smoke-test-lucebox/action.yml` — GPU smoke test composite action.
- `utils/gather_required_libs.py` — loader-error probe loop for runtime lib bundling.
- `docs/manual_instructions.md` — local builds mirroring CI flags.

## Workflow invariants

- **Tarball naming**: plain per-gfx TheRock tarballs (`therock-dist-linux-gfx1151-*`, `therock-dist-linux-gfx1100-*`, `therock-dist-linux-gfx1201-*`). NO family `-all` aliases (unlike ROCmFPX-BUILDER) — we ship single-arch binaries.
- **gfx allowlist**: `gfx1151 gfx1100 gfx1201 gfx1200` (last one untested upstream). Reject anything else in prepare-matrix.
- **BSA always OFF** (`-DDFLASH27B_ENABLE_BSA=OFF`): avoids the Block-Sparse-Attention submodule entirely and matches HIP builds where CMake forces it off anyway.
- **`-DCMAKE_HIP_FLAGS=-DDFLASH_WAVE_SIZE=32` unconditional on HIP builds** (gfx1151 requires wave32).
- **CUDA**: nvcc 12.8.0 via Jimver/cuda-toolkit + libcuda.so.1 stub symlink or linking fails (`undefined reference to cuMem*`).
- **ROCm runtime bundling**: lean list (hipblas/rocblas+library tree/amdhip64/hsa/comgr/rocprofiler-register/sysdeps set); `gather_required_libs.py` is the catch-all; no hipBLASLt/rocsolver/LLVM needed.
- **Releases**: sequential `b%04d` tags scanned from existing releases (start b1000), tag-exists guard for idempotency, assets named `lucebox-<TAG>-linux-{cuda12|rocm-<gfx>}-x64.zip`.
- Smoke tests: `continue-on-error: true`, never in release `needs` gating; runner labels from repo vars `LUCEBOX_RUNNERS_GFX1151/_GFX1201/_GFX1100`.

## Verification

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-lucebox.yml'))"
python3 -c "import yaml; yaml.safe_load(open('.github/actions/smoke-test-lucebox/action.yml'))"
python3 -m py_compile utils/gather_required_libs.py
actionlint .github/workflows/build-lucebox.yml   # if installed
```
