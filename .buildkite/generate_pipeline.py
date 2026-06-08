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


def image_publish_step(key, image, registry, commit):
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

    return {
        "label": f":docker: publish {image['name']}",
        "key": f"publish_image_{key}",
        "agents": {"queue": image["runner"]["buildkite_queue"]},
        "env": {
            BUILDKITE_OCI_LOGIN_ENV: "1",
            BUILDKITE_REGISTRY_ENV: registry,
        },
        "command": "set -euo pipefail\n" + login_command + "\n" + build_command,
    }


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

    steps = []
    for name, image in ci["images"].items():
        steps.append(image_publish_step(name, image, registry, commit))

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
        if job.get("artifacts"):
            step["artifact_paths"] = job["artifacts"]
        steps.append(step)

    print(yaml.safe_dump({"steps": steps}, sort_keys=False), end="")


if __name__ == "__main__":
    main()
