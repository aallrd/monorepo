#!/usr/bin/env python3

import os
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:
    raise SystemExit(
        "PyYAML is required to generate the Buildkite pipeline. "
        "Install build/ci/requirements.txt before running this script."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DOCKER_PLUGIN = "docker#v5.13.0"
BUILDKITE_REGISTRY_ENV = "MONOREPO_BUILDKITE_OCI_REGISTRY"
BUILDKITE_OCI_LOGIN_ENV = "MONOREPO_BUILDKITE_OCI_LOGIN"


def buildkite_ref(registry, image, commit):
    return f"{registry}/{image['name']}:{commit}"


def unique_values(values):
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def expand_change_scopes(ci, scope_names):
    scopes = ci.get("change_scopes", {})
    patterns = []
    for scope_name in scope_names:
        if scope_name not in scopes:
            raise SystemExit(f"Unknown Buildkite change scope: {scope_name}")
        scope_patterns = scopes[scope_name]
        if not isinstance(scope_patterns, list) or not scope_patterns:
            raise SystemExit(f"Buildkite change scope {scope_name!r} must be a non-empty list")
        patterns.extend(scope_patterns)
    return unique_values(patterns)


def scoped_patterns(ci, item):
    return expand_change_scopes(ci, item.get("change_scopes", []))


def should_emit_if_changed(ci, branch):
    config = ci.get("if_changed", {})
    if not config.get("enabled", False):
        return False
    return branch not in config.get("run_all_branches", [])


def apply_if_changed(step, patterns, enabled):
    if enabled and patterns:
        step["if_changed"] = patterns
    return step


def image_publish_patterns(ci, image_key):
    scope_names = []
    for job in ci["jobs"].values():
        if job["image"] == image_key:
            scope_names.extend(job.get("change_scopes", []))
    return expand_change_scopes(ci, unique_values(scope_names))


def image_publish_step(key, image, registry, commit, if_changed_patterns, emit_if_changed):
    ref = buildkite_ref(registry, image, commit)
    cache_ref = f"{registry}/{image['name']}:buildcache"
    login_command = (
        f'buildkite-agent oidc request-token --audience "https://{registry}" '
        f'--lifetime 300 | docker login "{registry}" '
        "--username buildkite --password-stdin"
    )
    build_command = " \\\n  ".join(
        [
            "docker buildx build",
            f"--platform {image['platform']}",
            f"--file {image['dockerfile']}",
            f"--tag {ref}",
            f"--cache-from type=registry,ref={cache_ref}",
            f"--cache-to type=registry,ref={cache_ref},mode=max",
            "--push",
            image["context"],
        ]
    )

    step = {
        "label": f":docker: publish {image['name']}",
        "key": f"publish_image_{key}",
        "agents": {"queue": image["runner"]["buildkite_queue"]},
        "command": "set -euo pipefail\n" + login_command + "\n" + build_command,
    }
    return apply_if_changed(step, if_changed_patterns, emit_if_changed)


def docker_plugin(image_ref, job):
    return {
        DOCKER_PLUGIN: {
            "image": image_ref,
            "entrypoint": "",
            "user": "root",
            "workdir": "/workdir",
            "command": [
                "bash",
                "-lc",
                "set -euo pipefail\n" + "\n".join(job["commands"]),
            ],
        },
    }


def main():
    with (ROOT / "build" / "ci" / "images.yaml").open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    ci = config["ci"]
    registry = ci["registries"]["buildkite"]["ref_prefix"]
    commit = os.environ.get("BUILDKITE_COMMIT", "local")
    branch = os.environ.get("BUILDKITE_BRANCH", "local")
    emit_if_changed = should_emit_if_changed(ci, branch)

    steps = []
    for name, image in ci["images"].items():
        steps.append(
            image_publish_step(
                name,
                image,
                registry,
                commit,
                image_publish_patterns(ci, name),
                emit_if_changed,
            )
        )

    for name, job in ci["jobs"].items():
        image_key = job["image"]
        image = ci["images"][image_key]
        image_ref = buildkite_ref(registry, image, commit)
        step = {
            "label": job.get("label", name),
            "key": name,
            "agents": {"queue": job["runner"]["buildkite_queue"]},
            "depends_on": f"publish_image_{image_key}",
            "env": {
                BUILDKITE_OCI_LOGIN_ENV: "1",
                BUILDKITE_REGISTRY_ENV: registry,
            },
            "plugins": [docker_plugin(image_ref, job)],
        }
        apply_if_changed(step, scoped_patterns(ci, job), emit_if_changed)
        if job.get("artifacts"):
            step["artifact_paths"] = job["artifacts"]
        steps.append(step)

    print(yaml.safe_dump({"steps": steps}, sort_keys=False), end="")


if __name__ == "__main__":
    main()
