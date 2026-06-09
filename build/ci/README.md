# CI Image Contract

`images.json` is the source of truth for the current CI runtime contract:
Linux CI queues, OCI image build definitions, Buildkite change scopes, command
lists, test report paths, artifact paths, Buildkite registry metadata, and
Jenkins Kubernetes runtime metadata.

This contract is part of the broader SDLC exploration for a C++ and Java
polyglot monorepo. It does not imply a final self-hosted, SaaS, or hybrid CI
decision. Provider-specific adapters should stay thin so the repository can
compare platform options without rewriting build semantics.

CI runs on Linux only. macOS and Windows are local development platforms and are
documented under `local_development` so their toolchain contracts stay visible
without entering the Buildkite/Jenkins matrix.

Linux has multiple jobs:

- `linux_gcc` is the default RHEL amd64 job and runs normal `bazel build //...`
  and `bazel test //...`.
- `linux_clang_ubsan` selects `--config=linux-clang-ubsan` and is the UBSan
  job, because UBSan is provided by the Linux Clang toolchain rather than GCC in
  this environment.
- `java_maven` runs the root Maven aggregator with
  `mvn --batch-mode --no-transfer-progress verify`. Maven uses the repo-local
  `.m2/repository` configured by `.mvn/maven.config`.

Image definitions are repo-owned Dockerfiles. Buildkite publishes them to
Buildkite Package Registry with `docker buildx build --push`; Jenkins publishes
the same Dockerfiles to `MONOREPO_OCI_REGISTRY` with Kaniko.

Buildkite generated steps use `if_changed` on non-`main` branches to avoid
running unrelated monorepo slices. The generated pipeline omits `if_changed` on
`main`, so post-merge builds remain full validation. Change scopes are declared
in `images.json`:

- `global` covers Buildkite and CI contract files. Any match runs all generated
  Buildkite image publish and job steps.
- `cpp` covers Bazel, C++ source, C++ toolchains, Buildifier, and the C++
  build image.
- `java` covers Maven configuration, Java source, and the Java/Maven build
  image.

Image publish steps use the union of their dependent job scopes. This keeps
commit-tagged image publication aligned with the jobs that pull those images.

Provider-specific behavior stays in the thin CI adapters:

- Buildkite uploads paths from each job's `artifacts` field with
  `artifact_paths`.
- Buildkite publishes each image to
  `packages.buildkite.com/aallrd/monorepo-images/<image>:<commit>`, then runs
  each job through the pinned Docker plugin from that commit image.
- Buildkite evaluates `if_changed` during `buildkite-agent pipeline upload`.
  The bootstrap step sets `BUILDKITE_GIT_DIFF_BASE=origin/main` and
  `BUILDKITE_FETCH_DIFF_BASE=true` so feature branches compare against a fresh
  default branch ref.
- Buildkite uses OIDC to authenticate to Buildkite Package Registry. Generated
  jobs opt into a `.buildkite/hooks/pre-command` Docker login before pulling
  private images.
- Buildkite disables image entrypoints before running each generated command
  under Bash. This keeps images with CLI entrypoints, such as the public Bazel
  image, from interpreting the CI script as tool arguments.
- Buildkite runs generated containers as `root` so public images with non-root
  default users can still write Bazel and Maven outputs into the checked-out
  workspace mounted by the agent.
- Jenkins publishes images in Kubernetes pods running
  `martizih/kaniko:v1.27.5-debug`, using the `monorepo-oci-docker-config`
  secret for registry auth.
- Jenkins runs each matrix job in a fresh Kubernetes pod whose `build` container
  uses the commit-tagged image published by the image stage.
- Buildkite dry-runs the generated pipeline, uploads it as an artifact for
  audit/debugging, and then uploads it with `--replace` so retries do not create
  duplicate pending steps.
- The static Buildkite bootstrap step lives in `.buildkite/pipeline.yml`. It
  runs the stdlib-only generator with Python; Buildkite supplies
  `buildkite-agent`.
- Jenkins publishes Surefire XML from `reports.junit` with `junit` and archives
  paths from `artifacts`.

Before relying on CI as a production signal:

1. Ensure the Buildkite queue keys in `images.json` exist in the target cluster
   and run Docker-capable agents.
2. Create the Buildkite Package Registry `monorepo-images` and grant this
   pipeline `read_packages` and `write_packages` through its OIDC policy.
3. Ensure Buildkite agents are at least 3.117.0 so `if_changed` and
   `BUILDKITE_FETCH_DIFF_BASE` are both supported.
4. Ensure Jenkins exposes `MONOREPO_OCI_REGISTRY` and has the Kubernetes secret
   `monorepo-oci-docker-config` in the Jenkins agent namespace.
5. Pin or mirror public base image tags by digest once the project leaves
   exploration mode.
6. Ensure the Java/Maven image includes Bash, Git, JDK 21, and Maven 3.9.
7. Ensure each C++ Linux image exposes the normalized toolchain root expected by
   the Bazel toolchains under `build/toolchains` and provides Bazel/Bazelisk.
8. Ensure Jenkins has the Kubernetes, Pipeline Utility Steps, and JUnit plugins.
