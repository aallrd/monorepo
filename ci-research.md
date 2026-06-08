# CI Research For Large Polyglot Monorepos

This note is part of the broader SDLC research for this C++ and Java polyglot
monorepo. The target shape is a large corporate monorepo with hundreds of
developers, multiple languages, multiple build systems, and a need for fast,
reliable collaboration.

The goal is to evaluate practical, state of the art CI and collaboration
patterns that could be brought into an internal corporate environment. This note
does not assume the final platform must be self-hosted or SaaS. Hosting model,
data residency, compliance, network topology, operational ownership, ecosystem
integrations, and cost will be major factors in the final landscape decision and
will shape what is possible.

The concrete architecture below studies one important reference scenario:
CloudBees/Jenkins Enterprise with Kubernetes-based, fully ephemeral agent pods.
The same evaluation style should be applied to SaaS CI providers, hybrid
offerings, and build-system-native services before making a final decision.

The core framing is three layers:

1. Source materialization: get the right files onto an agent quickly.
2. Work selection: avoid building and testing the whole monorepo on every change.
3. Shared build, dependency, and artifact reuse: reuse safe outputs across pods,
   branches, and teams.

## Reference Scenario: Jenkins/Kubernetes

In this reference scenario, the CI runner infrastructure is Kubernetes-based.
Jenkins provisions fully ephemeral pods for builds, and those pods disappear
after the build finishes.

That means persistent agent workspaces are not the main optimization. Anything
stored only in the pod workspace or container filesystem is disposable.

Useful reuse must live outside the pod:

- Internal Git mirrors or Git proxy services.
- Object storage for dependency caches.
- Build-system-native remote caches.
- Artifact registries.
- Container registries and Docker/BuildKit cache backends.

The controller should orchestrate jobs, manage credentials, and store job
metadata. It should not execute builds, hold large caches, or act as the durable
artifact backend.

## Architecture View

```text
                    ┌──────────────────────────────┐
                    │ CloudBees / Jenkins Control  │
                    │ - controllers / operations    │
                    │ - schedules pipelines         │
                    │ - credentials + RBAC          │
                    │ - no durable build workspace  │
                    └───────────────┬──────────────┘
                                    │
                                    │ provisions pods
                                    ▼
              ┌────────────────────────────────────────┐
              │ Kubernetes Agent Pods                  │
              │ - ephemeral per build/stage            │
              │ - tool containers                      │
              │ - temporary workspace volume           │
              │ - no long-term cache ownership         │
              └───────────────┬────────────────────────┘
                              │
        ┌─────────────────────┼──────────────────────┐
        │                     │                      │
        ▼                     ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌──────────────────┐
│ Git Layer     │    │ Cache Layer     │    │ Artifact Layer   │
│ mirror/proxy  │    │ object storage  │    │ registry/storage │
│ repo bundles  │    │ build caches    │    │ reports/packages │
└───────────────┘    └─────────────────┘    └──────────────────┘
        │                     │                      │
        ▼                     ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌──────────────────┐
│ Git forge     │    │ MinIO/S3/NFS    │    │ Nexus/Artifactory│
│ GitHub/GitLab │    │ Redis optional  │    │ OCI registry     │
└───────────────┘    └─────────────────┘    └──────────────────┘
```

## Layer 1: Source Materialization

For a 6 GB monorepo, a fresh clone in every pod is too expensive. Since pods are
ephemeral, the Git acceleration layer needs to be outside the pod.

Candidate options:

- Internal Git mirror or proxy service close to the Kubernetes cluster.
- Optional repo bundle snapshots to seed clones faster.
- Optional node-local Git mirror DaemonSet if cache locality becomes worth the
  operational complexity.
- Optional shared Git object cache via PVC, used carefully because concurrency
  and cleanup can be tricky.

Candidate default for this reference scenario:

```text
Ephemeral pod -> fetch/clone from internal Git mirror -> checkout exact SHA
```

This avoids depending on a branch landing on a specific warm agent.

Avoid treating a persistent workspace as the core solution in this environment.
With ephemeral pods, pod-local state disappears and cannot be relied on for
cross-build reuse.

## Layer 2: Work Selection

Jenkins should not encode monorepo dependency rules directly. It should call a
repo-owned interface that knows how to reason about the repository's languages
and build systems.

Suggested interface:

```sh
./tools/ci/affected --base "$BASE_SHA" --head "$HEAD_SHA" --format json
./tools/ci/run-affected --profile pr --targets-file affected.json
```

The implementation can call ecosystem-specific tooling such as Gradle, Maven,
Nx, pnpm, Go tooling, CMake, Pants, Buck, Bazel, or custom dependency graph
services.

Recommended policy:

- Pull requests run affected builds/tests plus critical smoke checks.
- Merge queue runs broader validation.
- Main branch and nightly jobs run full or near-full coverage.
- Release jobs produce immutable artifacts from known SHAs.

This layer is what prevents teams from building the universe on every change.

## Layer 3: Shared Build, Dependency, And Artifact Reuse

Layer 3 has three different cache types. They should not be collapsed into one
generic "cache the workspace" mechanism.

### Dependency Caches

Dependency caches avoid re-downloading third-party dependencies:

- npm, pnpm, or Yarn stores.
- Maven local repository and Gradle module cache.
- pip, uv, or Poetry caches.
- Cargo registry and Git cache.
- Go module cache.
- NuGet package cache.

These are good fits for provider or object-storage-backed caches. Cache keys
should be based on OS, toolchain/runtime version, and lockfile hashes.

Example key shape:

```text
linux-node20-pnpm-${hash(pnpm-lock.yaml)}
linux-java21-gradle-${hash(gradle.lockfile)}
linux-python312-pip-${hash(requirements.lock)}
```

### Build Output Caches

Build output caches are the real incremental-build layer. They should usually be
owned by each build system because the build system understands action/task
inputs, toolchains, environment, and outputs.

Examples:

- Gradle remote build cache.
- Nx Cloud or self-hosted Nx-compatible cache.
- Turborepo remote cache.
- sccache or ccache for C, C++, and Rust.
- Docker BuildKit registry-backed cache.
- Other language or build-system-native remote caches.

Jenkins should inject cache endpoints and credentials. It should not try to
cache arbitrary `build`, `target`, `dist`, or workspace directories as a generic
substitute for task-level caching.

### Pipeline Artifacts

Pipeline artifacts are durable outputs meant for humans, downstream jobs, or
deployment systems:

- Test reports.
- Coverage reports.
- Binaries.
- Packages.
- Container images.
- Release candidates.
- SBOMs and provenance metadata.

Small reports can be archived in Jenkins. Large or release-grade artifacts
should go to Nexus, Artifactory, MinIO/S3, or an OCI registry.

## Kubernetes Storage Requirements

Use separate storage classes or pod-template patterns for different needs:

- `emptyDir` workspace: fastest ordinary ephemeral workspace, deleted with pod.
- Dynamic PVC workspace: larger temporary workspace, deleted with pod.
- Existing shared PVC: only for carefully controlled shared caches.
- Object storage: preferred for shared dependency and build cache backends.

Important nuance: a dynamic PVC gives a pod more workspace capacity, but if it
is deleted with the pod, it is not a cross-build cache.

## Jenkins And CloudBees Requirements

Recommended Jenkins requirements:

- Kubernetes pod templates per workload class:
  - `linux-default`
  - `linux-large`
  - `linux-docker`
  - `linux-sanitizer`
  - `linux-release`
- Resource requests and limits per pod template.
- Dedicated service accounts and network policies for CI pods.
- Jenkins credentials for:
  - Git mirror access.
  - Object storage.
  - Artifact registry.
  - Container registry.
  - Build cache services.
- Shared Jenkins library or pipeline template for:
  - Source materialization.
  - Affected-work discovery.
  - Cache environment setup.
  - Artifact publication.
  - Report collection.

## Recommended CI Flow

```text
1. Jenkins provisions an ephemeral Kubernetes pod.
2. Pod receives an ephemeral workspace volume.
3. Pod materializes source from the internal Git mirror.
4. Repo tooling computes affected work.
5. Jenkins restores dependency caches from object storage or cache services.
6. Build systems use their remote task/output caches.
7. Selected builds and tests run.
8. Small reports are archived in Jenkins.
9. Large artifacts go to artifact or container registries.
10. Pod is deleted.
```

## Cache Write Policy

Shared caches need explicit trust boundaries:

```text
main branch:
  read shared cache
  write shared cache

trusted internal pull request:
  read shared cache
  optionally write to branch or PR namespace

untrusted pull request:
  read only, or use isolated/no shared cache

release:
  read cache allowed
  publish immutable artifacts

nightly:
  periodically run clean or low-cache builds to detect hidden cache dependence
```

## Practical Recommendation

For the CloudBees/Jenkins Enterprise reference scenario with ephemeral
Kubernetes pods:

```text
Ephemeral workspace for correctness.
Internal Git mirror for checkout speed.
Repo-owned target selection for avoiding unnecessary work.
Build-system-native remote caches for incremental build reuse.
Object storage for dependency caches.
Artifact and container registries for durable outputs.
```

Do not make Jenkins itself the cache brain. Jenkins should orchestrate the flow
and inject credentials. The monorepo and its build systems should own dependency
graphs, affected-work logic, and task-level cache correctness.

## Landscape Decision Inputs

The final SDLC landscape should compare self-hosted, SaaS, and hybrid options
against the same criteria:

- Developer feedback latency for common C++ and Java changes.
- Support for affected-work selection, remote execution, and remote caching.
- Source-code, dependency, artifact, and cache data residency.
- Security controls for trusted and untrusted changes.
- Integration with corporate identity, audit, policy, and compliance systems.
- Operational burden for platform teams.
- Cost model at hundreds-of-developers scale.
- Portability and exit strategy if a service or vendor changes direction.
- Quality of day-to-day collaboration workflows, including review, ownership,
  debugging, incident response, release, and traceability.
