#!/usr/bin/env bash
set -euo pipefail

files=()
while IFS= read -r file; do
  files+=("$file")
done < <(
  find . \
    \( -path ./third_party/bazel -o -path './bazel-*' \) -prune -o \
    \( -name BUILD -o -name BUILD.bazel -o -name '*.bzl' -o -name MODULE.bazel \) \
    -type f -print
)

if [[ ${#files[@]} -eq 0 ]]; then
  exit 0
fi

bazel build @buildifier_prebuilt//:buildifier >/dev/null
execroot="$(bazel info execution_root)"
buildifier_rel="$(bazel cquery --output=files @buildifier_prebuilt//:buildifier 2>/dev/null)"
buildifier_rel="${buildifier_rel%%$'\n'*}"

"${execroot}/${buildifier_rel}" --mode=check --lint=warn "${files[@]}"
