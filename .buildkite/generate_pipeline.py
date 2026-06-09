#!/usr/bin/env python3

import json
import os
from pathlib import Path


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


def yaml_key(value):
    return json.dumps(str(value))


def yaml_scalar(value):
    if isinstance(value, (dict, list)):
        return None
    if isinstance(value, str):
        if "\n" in value:
            return None
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    raise TypeError(f"Unsupported YAML value: {value!r}")


def append_multiline_string(lines, value, indent):
    spaces = " " * indent
    for line in value.splitlines():
        lines.append(f"{spaces}{line}")
    if value.endswith("\n"):
        lines.append(spaces)


def append_yaml(lines, value, indent=0):
    spaces = " " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            scalar = yaml_scalar(item)
            if scalar is not None:
                lines.append(f"{spaces}{yaml_key(key)}: {scalar}")
            elif isinstance(item, str):
                lines.append(f"{spaces}{yaml_key(key)}: |")
                append_multiline_string(lines, item, indent + 2)
            else:
                lines.append(f"{spaces}{yaml_key(key)}:")
                append_yaml(lines, item, indent + 2)
        return

    if isinstance(value, list):
        for item in value:
            scalar = yaml_scalar(item)
            if scalar is not None:
                lines.append(f"{spaces}- {scalar}")
            elif isinstance(item, str):
                lines.append(f"{spaces}- |")
                append_multiline_string(lines, item, indent + 2)
            else:
                lines.append(f"{spaces}-")
                append_yaml(lines, item, indent + 2)
        return

    scalar = yaml_scalar(value)
    if scalar is None:
        lines.append(f"{spaces}|")
        append_multiline_string(lines, value, indent + 2)
    else:
        lines.append(f"{spaces}{scalar}")


def dump_yaml(value):
    lines = []
    append_yaml(lines, value)
    return "\n".join(lines) + "\n"


def main():
    with (ROOT / "build" / "ci" / "images.json").open("r", encoding="utf-8") as handle:
        config = json.load(handle)

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

    print(dump_yaml({"steps": steps}), end="")


if __name__ == "__main__":
    main()
