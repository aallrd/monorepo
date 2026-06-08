# CI OCI Images

These Dockerfiles define the Linux build environments consumed by Buildkite and
Jenkins generated jobs. Buildkite publishes them to Buildkite Package Registry;
Jenkins publishes the same image definitions to the external registry supplied
by `MONOREPO_OCI_REGISTRY`.

Image tags are commit-addressed by CI:

- Buildkite: `packages.buildkite.com/aallrd/monorepo-images/<image>:<commit>`
- Jenkins: `${MONOREPO_OCI_REGISTRY}/<image>:<commit>`

Local build examples:

```sh
docker buildx build --platform linux/amd64 -f build/ci/images/cpp-bazel/Dockerfile -t monorepo/cpp-bazel:dev .
docker buildx build --platform linux/amd64 -f build/ci/images/java-maven/Dockerfile -t monorepo/java-maven:dev .
```
