# Research Polyglot Monorepo

[![Build status](https://badge.buildkite.com/bc2e90bee424f87053e9f0a85974ab93957f14d52432e3d9a1.svg)](https://buildkite.com/aallrd/monorepo)

This repository is a research polyglot monorepo focused on C++ and Java. It is
not intended to be a product application; it is a working codebase for studying
development experience, collaboration, and SDLC practices at the scale of
hundreds of developers.

The goal is to try practical, modern solutions around this kind of codebase and
understand which ones could be brought into a corporate engineering environment.
That includes local development, build systems, CI, testing, review workflows,
dependency management, security, release, provenance, observability, and the
day-to-day ergonomics of working in a large shared repository.

No final assumption is made about self-hosted versus SaaS services. That choice
is part of the research landscape: data boundaries, compliance, integration
depth, operational ownership, cache placement, network topology, cost, and
developer workflow constraints will shape what is viable.

The current codebase seeds two language/build-system slices:

- `sample_cpp`: a Bzlmod-based Bazel C++20 project.
- `sample-java`: a Maven-based Java 17 project under `components/sample`.

The C++ slice is split into monorepo-style library and program packages:

- `lib/sample`: the reusable C++ library and its tests.
- `progs/app`: the CLI binary that depends on `lib/sample`.

The C++ slice has repo-owned native toolchain declarations for:

- Homebrew LLVM/Clang on macOS arm64.
- GCC 11 Toolset on RHEL 8 amd64.
- Clang on RHEL 8 amd64 for UBSan builds.
- Visual Studio 2022 Build Tools on Windows amd64.

Run builds from the repository root inside the matching pinned build environment.
On this MacBook, the macOS environment is the host itself with Homebrew LLVM
22.1.6 installed:

```sh
bazel build //...
bazel test //...
```

Useful C++ labels:

```sh
bazel build //lib/sample:sample_cpp
bazel build //progs/app:sample_cpp
bazel test //lib/sample:greeting_test
```

Normal builds resolve Bzlmod dependencies from `MODULE.bazel.lock` and allow
Bazel to fetch missing external repositories as needed. Updating dependency
versions is an explicit maintenance workflow:

```sh
bazel mod tidy --lockfile_mode=update
```

## Toolchain Contract

Each pinned environment must expose the documented toolchain roots:

- macOS arm64: `/opt/homebrew/Cellar/llvm/22.1.6`
  - Homebrew LLVM/Clang 22.1.6.
  - Homebrew Clang config at `/opt/homebrew/Cellar/llvm/22.1.6/etc/clang/arm64-apple-darwin25.cfg`.
  - Command Line Tools SDK at `/Library/Developer/CommandLineTools/SDKs/MacOSX26.sdk`.
  - Uses macOS system libc++ at link time, matching the Homebrew recommendation.
- RHEL 8 amd64: `/opt/toolchains/gcc-rhel-amd64`
  - Symlinked or mapped to `/opt/rh/gcc-toolset-11`.
- RHEL 8 amd64 Clang: `/opt/toolchains/clang-rhel-amd64`
  - Used for `--config=linux-clang-ubsan`.
  - Provides UBSan for Linux CI.
- Windows amd64: `C:/toolchains/msvc-windows-amd64`
  - Visual Studio 2022 Build Tools.
  - Windows SDK values are placeholders and must be filled before using the
    Windows local development build.

Linux and macOS use Bazel's sandboxed strategy with network denied by default.
The macOS toolchain is intentionally host-local to this MacBook's Homebrew LLVM
install, not a portable CI image contract.
Warnings are errors for first-party C++ packages through the Bazel-native
`warnings_as_errors` C++ toolchain feature. External dependencies do not opt into
that feature, so compiler upgrades do not break the research codebase on
upstream warning churn.
On macOS, `-Wcharacter-conversion` is left as a warning because Homebrew Clang
22 reports it from GoogleTest headers included by test sources.
Windows builds do not claim local Bazel action sandboxing; Windows hermeticity
comes from pinned runners/images, fixed tool roots, no ambient action env, and
the checked-in Bazel lockfile.

## CI

`build/ci/images.yaml` is the single source for Linux CI jobs, OCI image build
definitions, Docker-capable Buildkite queues, and Jenkins Kubernetes pod
runtime metadata. CI runs only on Linux:

- `linux_gcc` is the default GCC build/test job.
- `linux_clang_ubsan` is the Clang UBSan build/test job.
- `java_maven` is the Java 17 Maven `verify` job.

macOS and Windows are local development platforms, not CI jobs.

Buildkite uses `.buildkite/generate_pipeline.py`; the bootstrap step installs
Python packages from `build/ci/requirements.txt`, writes the generated pipeline
to an artifact, validates it with `pipeline upload --dry-run`, and uploads it
with `--replace`. Generated Buildkite jobs keep queue selection separate from
the build environment: queues provide Docker-capable capacity, while the pinned
Docker plugin runs each job inside the OCI image declared in `images.yaml`.
On non-`main` branches, generated Buildkite steps use `if_changed` scopes from
`images.yaml` so unrelated C++ and Java slices can be skipped. `main` builds
omit `if_changed` and run the full generated matrix.
Jenkins assumes the Pipeline Utility Steps plugin for `readYaml` and the JUnit
plugin for Maven Surefire report publishing.

## Java Maven Slice

The Java Maven slice is intentionally separate from the Bazel C++ build so the
research codebase can model multiple build systems in one monorepo:

```sh
mvn test
mvn package
```

Maven is configured by `.mvn/maven.config` to use the repo-local
`.m2/repository` cache instead of `~/.m2/repository`.

## Verification

These commands passed on the MacBook Homebrew LLVM toolchain:

```sh
bazel build //build/toolchains:validate_current_toolchain
bazel build //...
bazel test //...
tools/buildifier/check.sh
```
