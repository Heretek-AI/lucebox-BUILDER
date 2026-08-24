# lucebox-BUILDER

Nightly binary builds of [lucebox](https://github.com/Luce-Org/lucebox) for every supported GPU platform, attached to GitHub Releases with sequential `b####` tags. Modeled on the [ROCmFPX-BUILDER](https://github.com/Heretek-AI/ROCmFPX-BUILDER) pattern.

## What each nightly contains

Every release ships Linux x86_64 zips; ROCm archives bundle all required runtime libraries with `$ORIGIN` rpath — **unpack anywhere and run**, no `LD_LIBRARY_PATH` or system ROCm install needed (the host GPU driver is still required at runtime).

| Asset | Backend | Covers |
|---|---|---|
| `lucebox-b####-linux-cuda12-x64.zip` | CUDA 12.8 fat binary | sm_75 / sm_80 / sm_86 / sm_89 / sm_90 / sm_120 (2080 Ti → RTX 5090) |
| `lucebox-b####-linux-rocm-gfx1151-x64.zip` | HIP | Strix Halo / Ryzen AI MAX+ 395 — host ROCm ≥ 6.4.1 |
| `lucebox-b####-linux-rocm-gfx1100-x64.zip` | HIP | Radeon RX 7900 XTX / RDNA3 |
| `lucebox-b####-linux-rocm-gfx1201-x64.zip` | HIP | Radeon AI PRO R9700 / RDNA4 |

## Usage

```bash
unzip lucebox-b1000-linux-cuda12-x64.zip -d lucebox && cd lucebox/bin
./dflash_server /path/to/model.gguf --port 8080
# optional speculative decoding:
./dflash_server model.gguf --draft draft.gguf --port 8080
```

## Workflow

`.github/workflows/build-lucebox.yml`:

- **Nightly cron** at 13:00 UTC, plus manual `workflow_dispatch` (overridable CUDA arches, gfx targets, ROCm version, lucebox ref, optional rocWMMA Phase-2 kernels and CPU unit tests) and PR builds (no release).
- HIP toolchains come from AMD's [TheRock](https://rocm.nightlies.amd.com/tarball-multi-arch/) dist tarballs (`latest` auto-detects the newest published version per gfx target). CUDA builds use nvcc 12.8 via the Jimver action.
- Non-blocking GPU smoke tests run on self-hosted runners when configured (see below); a flaky device never blocks a release.

### Self-hosted smoke-test configuration

Set these **repository variables** to enable GPU smoke tests (JSON arrays of runner labels):

| Variable | Example |
|---|---|
| `LUCEBOX_RUNNERS_GFX1151` | `["stx-halo", "Linux"]` |
| `LUCEBOX_RUNNERS_GFX1201` | `["r9700", "Linux"]` |
| `LUCEBOX_RUNNERS_GFX1100` | unset → skipped |

Optionally set `LUCEBOX_SMOKE_MODEL_URL` to override the smoke GGUF.

## Scope exclusions

- Windows builds (upstream CI covers compile-only on Windows today).
- The megakernel PyTorch extension (`optimizations/megakernel`) — Python extension built against torch cu128 wheels; use upstream docker images or build locally.
- GB10 `sm_121` (needs CUDA ≥ 12.9), Jetson Thor `sm_110` (CUDA ≥ 13, ARM64) — future extensions.
- Pre-Turing NVIDIA arches (< sm_75): excluded by upstream by design.
- `gfx942` (MI300X) / `gfx90a` (MI200): listed in upstream Dockerfile but untested upstream; not in the matrix.
- `gfx1200`: allowed as a dispatch-input experiment but untested upstream.
