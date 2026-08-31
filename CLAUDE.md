# lucebox-BUILDER

Nightly binary-release builder for https://github.com/Luce-Org/lucebox (Linux x86_64, CUDA + HIP), modeled on the ROCmFPX-BUILDER workflow pattern. Upstream is cloned fresh in CI; the local `lucebox/` directory is an untracked scratch clone (gitignored).

## Key files

- `.github/workflows/build-lucebox.yml` — the whole pipeline: prepare-matrix → build-cuda / build-rocm (matrix) → smoke-test (self-hosted, non-blocking) → create-release.
- `.github/actions/smoke-test-lucebox/action.yml` — GPU smoke test composite action.
- `utils/gather_required_libs.py` — loader-error probe loop for runtime lib bundling.
- `docs/manual_instructions.md` — local builds mirroring CI flags.

## Workflow invariants

- **Tarball naming**: TheRock `tarball-multi-arch` dists, mapped chip → prefix in prepare-matrix. Single-chip dists exist only for gfx115x; RDNA3/RDNA4 come from family dists — `gfx1100→therock-dist-linux-gfx110X-all-*`, `gfx1201`/`gfx1200→therock-dist-linux-gfx120X-all-*`, `gfx1151→therock-dist-linux-gfx1151-*`. There are NO per-chip `gfx1100-*`/`gfx1201-*` tarballs upstream; never invent them. The compile target stays single-gfx (`-DDFLASH27B_HIP_ARCHITECTURES=<chip>`), so shipped binaries remain per-gfx even though the toolchain came from a family dist.
- **gfx allowlist**: `gfx1151 gfx1100 gfx1201 gfx1200` (last one untested upstream). Reject anything else in prepare-matrix.
- **BSA always OFF** (`-DDFLASH27B_ENABLE_BSA=OFF`): avoids the Block-Sparse-Attention submodule entirely and matches HIP builds where CMake forces it off anyway.
- **CUDA arches need BOTH flags**: `-DDFLASH27B_USER_CUDA_ARCHITECTURES=<list>` AND `-DCMAKE_CUDA_ARCHITECTURES=<list>`. server/CMakeLists.txt force-overwrites `CMAKE_CUDA_ARCHITECTURES` from its own auto-resolved list (70;75;86 + 120) unless the USER var is set — passing only one silently drops sm_80/89/90.
- **Binaries land flat in `server/build/`, not `build/bin/`**: upstream sets `CMAKE_RUNTIME_OUTPUT_DIRECTORY=${CMAKE_BINARY_DIR}` (ggml DLL/SO load requirement). Stage a portable `dist/` tree (`dist/bin` incl. collected `libggml*.so*`, `share/status.html`, `libcudart.so.12` on CUDA; `dist/bin/rocblas/library`; `dist/kpacks`) and upload that.
- **`.kpack` handling**: newer TheRock splits kernel packs into `/opt/rocm/.kpack/<name>_<gfx>.kpack`; rocm_kpack resolves `../.kpack/...` relative to each loading library, so packs must be a SIBLING of `bin/` at runtime. upload-artifact@v4 drops hidden dirs → stage as `dist/kpacks/`, rename to `.kpack` inside the artifact dir right before zipping (with `shopt -s dotglob`).
- **`-DCMAKE_HIP_FLAGS=-DDFLASH_WAVE_SIZE=32` unconditional on HIP builds** (gfx1151 requires wave32).
- **rocWMMA is bundled in TheRock dists** (`include/rocwmma/`) — verified 2026-08: no apt install needed for `DFLASH27B_HIP_SM80_EQUIV=ON`; keep the header-probe fail-fast anyway.
- **CUDA**: nvcc 12.8.0 via Jimver/cuda-toolkit + libcuda.so.1 stub symlink or linking fails (`undefined reference to cuMem*`). Bundle `libcudart.so.12`.
- **ROCm runtime bundling**: lean list (hipblas/rocblas+library tree/amdhip64/hsa/comgr/rocprofiler-register/sysdeps set); `gather_required_libs.py` is the catch-all; no hipBLASLt/rocsolver/LLVM needed.
- **Nondeterministic values live in prepare-matrix**: TheRock version detection (once per distinct prefix), upstream commit hash, smoke matrix. Build/release jobs are pure consumers — per-leg job outputs race when several matrix legs finish.
- **Releases**: sequential `b%04d` tags scanned from existing releases (start b1000), tag-exists guard for idempotency, assets named `lucebox-<TAG>-linux-{cuda12|rocm-<gfx>}-x64.zip`.
- Smoke tests: `continue-on-error: true`, never in release `needs` gating; runner labels from repo vars `LUCEBOX_RUNNERS_GFX1151/_GFX1201/_GFX1100/_CUDA` — targets without a configured variable simply don't get a smoke leg (never fall back to a sentinel label; it queues forever).

## Verification

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-lucebox.yml'))"
python3 -c "import yaml; yaml.safe_load(open('.github/actions/smoke-test-lucebox/action.yml'))"
python3 -m py_compile utils/gather_required_libs.py
actionlint .github/workflows/build-lucebox.yml   # if installed
```
