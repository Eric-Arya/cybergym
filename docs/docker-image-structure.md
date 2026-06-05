# CyberGym Docker Image Structure

Inspected from `n132/arvo:10400-vul`, `cybergym/oss-fuzz:370689421-vul`, and `cybergym/oss-fuzz-base-runner:latest`.

---

## ARVO Image (`n132/arvo:<id>-{vul|fix}`)

Base: **Ubuntu 16.04 (Xenial)**

```
/
├── bin/arvo              # entrypoint script (bash)
├── out/                  # ~130 fuzzer binaries (ImageMagick coders), ~28MB each
│   ├── coder_MNG_fuzzer  # each coder_*_fuzzer processes a specific image format
│   ├── coder_PNG_fuzzer
│   ├── coder_TIFF_fuzzer
│   ├── coder_JPEG_fuzzer
│   ├── enhance_fuzzer
│   └── ...               # 130+ format-specific fuzzers
├── src/                  # compiled-from-source libraries
│   ├── build.sh          # replication script
│   ├── graphicsmagick/   # the target: ImageMagick fork
│   ├── freetype2/
│   ├── libpng/
│   ├── libtiff/
│   ├── libjpeg-turbo/
│   ├── libwebp/
│   ├── xz/
│   ├── zlib/
│   ├── bzip2-1.0.6.tar.gz
│   ├── afl/              # fuzzer engines
│   ├── honggfuzz/
│   └── libfuzzer/
├── work/                 # installed build artifacts
│   ├── bin/              # GraphicsMagick-cli, tiff2ps, cwebp, etc.
│   │   ├── gm -> GraphicsMagick
│   │   └── ...
│   ├── include/
│   ├── lib/
│   └── share/
└── usr/                  # standard Ubuntu 16.04 system (273 dpkg packages)
```

**Entrypoint:** `/bin/arvo` — sets ASAN/MSAN/UBSAN sanitizer options, then runs `fuzzer_binary /tmp/poc`. By default runs `coder_MNG_fuzzer`.

---

## OSS-Fuzz Image (`cybergym/oss-fuzz:<id>-{vul|fix}`)

Base: **Ubuntu 20.04 (Focal)**

```
/
├── usr/local/bin/run_poc  # entrypoint (bash, 87 bytes)
├── out/                   # compiled fuzzer binaries + seed corpora
│   ├── fuzz-eval          # ~87MB, the active fuzzer
│   ├── fuzz-css           # ~87MB
│   ├── fuzz-json
│   ├── fuzz-uri
│   ├── fuzz-xml
│   ├── fuzz-*_seed_corpus.zip
│   └── llvm-symbolizer
├── src/                   # build tree
│   ├── build.sh
│   ├── wt/                # target source (e.g., Wt web toolkit)
│   │   └── fuzz/          # fuzz harness source (.C files)
│   ├── aflplusplus/
│   ├── honggfuzz/
│   ├── libfuzzer/
│   └── fuzztest/
├── work/                  # (empty, build artifacts in /out)
├── fuzz-introspector/     # FuzzIntrospector tooling
├── opt/cifuzz/            # CI fuzz integration scripts
├── ccache/                # compiler cache
└── usr/                   # Ubuntu 20.04 system + clang toolchain
```

**Entrypoint:** `/usr/local/bin/run_poc` — runs `/out/fuzz-eval <poc_path>` (or the specific fuzzer for that task).

**Key env vars:** `FUZZING_ENGINE=libfuzzer`, `SANITIZER=address`, `CXX=clang++`.

---

## Base Runner Image (`cybergym/oss-fuzz-base-runner:latest`)

Base: **Ubuntu 20.04 (Focal)**

A minimal image with only the OSS-Fuzz toolchain (clang, llvm-symbolizer, llvm-profdata, coverage tools). No source, no fuzzer binaries. Used by binary-only mode — the actual binaries are bind-mounted from the host's `binary_dir/`.

```
/
├── usr/local/bin/
│   ├── llvm-symbolizer
│   ├── llvm-profdata
│   ├── llvm-cov
│   ├── coverage
│   ├── download_corpus
│   └── ...
├── out/    # (empty)
├── src/    # (empty)
├── work/   # (empty)
└── usr/    # Ubuntu 20.04 + clang toolchain
```

---

## Comparison

| Aspect | ARVO | OSS-Fuzz | Base Runner |
|--------|------|----------|-------------|
| OS | Ubuntu 16.04 | Ubuntu 20.04 | Ubuntu 20.04 |
| Size (vul) | 2-10 GB | 4-50 GB | 2.1 GB |
| Source in image | /src/* (full libraries) | /src/wt/ (target only) | none |
| Fuzzer count | ~130 per image | ~6 per image | 0 |
| Runner script | `/bin/arvo` | `/usr/local/bin/run_poc` | none |
| Fuzzer engine | libfuzzer (AFL, honggfuzz available) | libfuzzer | none |
| Binary per-fuzzer size | ~28 MB | ~87 MB | n/a |
