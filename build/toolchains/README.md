# C++ Toolchains

The toolchains in this directory are repo-owned Bazel `cc_toolchain`
declarations. They intentionally reference fixed absolute paths provided by the
pinned execution environment instead of discovering compilers from `PATH`,
`CC`, `CXX`, `DEVELOPER_DIR`, or `VCINSTALLDIR`.

The implementation is native-only:

- `clang_macos_arm64` runs on this macOS arm64 MacBook and targets macOS arm64.
- `gcc_rhel_amd64` runs on Linux amd64 and targets Linux amd64 as the default
  Linux compiler.
- `clang_rhel_amd64` runs on Linux amd64 and targets Linux amd64 for Clang
  builds, including UBSan.
- `msvc_windows_amd64` runs on Windows amd64 and targets Windows amd64.

Linux uses compiler-specific platform constraints:

- `//build/platforms:rhel_amd64_gcc` selects the GCC toolchain.
- `//build/platforms:rhel_amd64_clang` selects the Clang toolchain.

The plain Linux platform-specific config uses GCC by default. Pass
`--config=linux-clang` to select the Clang toolchain, or
`--config=linux-clang-ubsan` for the Clang UBSan configuration.

## macOS Host Toolchain

The macOS toolchain is intentionally host-local rather than image-local:

- LLVM root: `/opt/homebrew/Cellar/llvm/22.1.6`
- Compiler: Homebrew LLVM/Clang 22.1.6
- Clang config: `/opt/homebrew/Cellar/llvm/22.1.6/etc/clang/arm64-apple-darwin25.cfg`
- SDK: `/Library/Developer/CommandLineTools/SDKs/MacOSX26.sdk`
- Static archive tool: `llvm-libtool-darwin`

The toolchain links against macOS system libc++ with `-lc++`, following the
Homebrew caveat that system libc++/libunwind are usually preferable on macOS.
Homebrew Clang 22 reports `-Wcharacter-conversion` from GoogleTest headers, so
that warning remains visible but is not promoted to an error.

The validation target checks the normalized toolchain root for the active target
platform:

```sh
bazel build //build/toolchains:validate_current_toolchain
```

The Windows toolchain contains SDK placeholders. Replace the SDK values and keep
the normalized `C:/toolchains/msvc-windows-amd64` wrappers stable before
using the Windows local development build.
