# Manual Build Instructions

Local builds mirroring exactly what the CI workflow does. All commands assume Linux x86_64.

## CUDA (fat binary)

Requires: GCC ≥ 11, CMake ≥ 3.21, Ninja, CUDA toolkit ≥ 12.8 (12.8 for sm_120).

```bash
git clone --depth 1 --single-branch --branch main https://github.com/Luce-Org/lucebox.git
cd lucebox/server

# Driver stub for linking (real driver only needed at runtime). Skip if you
# have a real NVIDIA driver installed.
mkdir -p /tmp/cuda-stubs
ln -sf "$CUDA_PATH/targets/x86_64-linux/lib/stubs/libcuda.so" /tmp/cuda-stubs/libcuda.so.1
export LD_LIBRARY_PATH=/tmp/cuda-stubs:$LD_LIBRARY_PATH

cmake -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
  -DCMAKE_CUDA_ARCHITECTURES="75;80;86;89;90;120" \
  -DDFLASH27B_ENABLE_BSA=OFF \
  -DDFLASH27B_FA_ALL_QUANTS=OFF
cmake --build build --target test_dflash dflash_server test_server_unit -j$(nproc)
```

Binaries land in `build/bin` (`dflash_server`, `test_dflash`, `test_server_unit`, `share/status.html`). To enable BSA speculative-prefill, init the submodule and drop `-DDFLASH27B_ENABLE_BSA=OFF`:

```bash
cd .. && git submodule update --init --depth 1 server/deps/Block-Sparse-Attention && cd server
```

BSA requires all target arches ≥ sm_80.

## HIP

Requires a ROCm install with hipblas, rocblas, rocprim, hipcub headers.

### Option A — TheRock dist tarball (same as CI)

```bash
# Pick your target; version example shown, or scrape the index for latest:
base="https://rocm.nightlies.amd.com/tarball-multi-arch"
curl -s "$base/" | grep -oP 'therock-dist-linux-gfx1151-[0-9a-z.]+' | sort -u | tail   # list versions
sudo mkdir -p /opt/rocm
curl -sL "$base/therock-dist-linux-gfx1151-7.2.0a20260801.tar.gz" \
  | sudo tar --use-compress-program=gzip -xf - -C /opt/rocm --strip-components=1

export HIP_PATH=/opt/rocm ROCM_PATH=/opt/rocm HIP_PLATFORM=amd
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:/opt/rocm/llvm/lib:${LD_LIBRARY_PATH:-}

cd lucebox/server
cmake -B build -G Ninja \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
  -DDFLASH27B_GPU_BACKEND=hip \
  -DDFLASH27B_HIP_ARCHITECTURES=gfx1151 \
  -DDFLASH27B_HIP_SM80_EQUIV=OFF \
  -DDFLASH27B_FA_ALL_QUANTS=OFF \
  -DDFLASH27B_ENABLE_BSA=OFF \
  -DCMAKE_HIP_FLAGS=-DDFLASH_WAVE_SIZE=32
cmake --build build --target test_dflash dflash_server test_server_unit -j$(nproc)
```

### Option B — distro ROCm via apt (needed for rocwmma Phase-2 kernels)

TheRock nightly tarballs may not ship `rocwmma` headers; the apt repo does:

```bash
sudo apt-get install -y hipblas-dev hipcub-dev rocblas-dev rocprim-dev rocwmma-dev libcurl4-openssl-dev
# ROCm under /usr on some distros:
cmake -B build -G Ninja \
  ... same flags as Option A but without the clang/compiler overrides ...
  -DDFLASH27B_HIP_SM80_EQUIV=ON \
  -DROCM_PATH=/usr
```

### Runtime bundling for portable zips

```bash
cd build/bin
for f in /opt/rocm/lib/libhipblas.so* /opt/rocm/lib/librocblas.so* \
         /opt/rocm/lib/libamdhip64.so* /opt/rocm/lib/libhsa-runtime64.so* \
         /opt/rocm/lib/libamd_comgr*.so* /opt/rocm/lib/librocprofiler-register.so*; do
  cp $f . 2>/dev/null || true
done
cp -r /opt/rocm/lib/rocblas/library rocblas/library 2>/dev/null || true
# catch-all: copy whatever else the loader complains about
python3 utils/gather_required_libs.py --dest-dir "$(pwd)" --binary dflash_server
for file in *.so* dflash_server test_dflash test_server_unit; do
  [ -f "$file" ] && [ ! -L "$file" ] && patchelf --set-rpath '$ORIGIN' "$file"
done
```

## Platform caveats (from upstream)

- **gfx1151 needs ROCm ≥ 6.4.1.** Running a 6.4.x userspace against a ROCm 7.x host driver can segfault at model load — rebuild with a matching-major ROCm (`rocm_version` dispatch input).
- **gfx1200 and gfx1201 are NOT code-object compatible** — one binary per chip.
- On PIE-linking distros add `-DCMAKE_EXE_LINKER_FLAGS=-no-pie`.
- Dual-GPU single binary: `-DDFLASH27B_HIP_ARCHITECTURES='gfx1151;gfx1201' -DGGML_HIP_GRAPHS=ON`.
