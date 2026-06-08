FROM gcr.io/bazel-public/bazel:9.1.1

USER root

ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      binutils \
      ca-certificates \
      clang \
      coreutils \
      curl \
      diffutils \
      findutils \
      g++ \
      gcc \
      git \
      gzip \
      libc++-dev \
      libc++abi-dev \
      lld \
      llvm \
      make \
      openjdk-21-jre-headless \
      patch \
      tar \
      unzip \
      xz-utils \
      zip \
    && rm -rf /var/lib/apt/lists/*

RUN set -euo pipefail; \
    gcc_version="$(gcc -dumpversion | cut -d. -f1)"; \
    gcc_triplet="$(gcc -dumpmachine)"; \
    gcc_root="/opt/toolchains/gcc-rhel-amd64/root/usr"; \
    mkdir -p \
      "$gcc_root/bin" \
      "$gcc_root/include/c++" \
      "$gcc_root/lib/gcc/x86_64-redhat-linux/11"; \
    ln -sfn /usr/bin/gcc "$gcc_root/bin/gcc"; \
    ln -sfn /usr/bin/g++ "$gcc_root/bin/g++"; \
    ln -sfn /usr/bin/gcc-ar "$gcc_root/bin/gcc-ar"; \
    ln -sfn /usr/bin/cpp "$gcc_root/bin/cpp"; \
    ln -sfn /usr/bin/gcov "$gcc_root/bin/gcov"; \
    ln -sfn /usr/bin/ld "$gcc_root/bin/ld"; \
    ln -sfn /usr/bin/nm "$gcc_root/bin/gcc-nm"; \
    ln -sfn /usr/bin/objcopy "$gcc_root/bin/objcopy"; \
    ln -sfn /usr/bin/objdump "$gcc_root/bin/objdump"; \
    ln -sfn /usr/bin/strip "$gcc_root/bin/strip"; \
    if command -v dwp >/dev/null 2>&1; then ln -sfn "$(command -v dwp)" "$gcc_root/bin/dwp"; fi; \
    if [ -d "/usr/include/c++/${gcc_version}" ]; then \
      if [ -d "/usr/include/${gcc_triplet}/c++/${gcc_version}" ]; then \
        ln -sfn "/usr/include/${gcc_triplet}/c++/${gcc_version}" \
          "/usr/include/c++/${gcc_version}/x86_64-redhat-linux"; \
      fi; \
      ln -sfn "/usr/include/c++/${gcc_version}" "$gcc_root/include/c++/11"; \
    fi; \
    if [ -d "/usr/lib/gcc/${gcc_triplet}/${gcc_version}/include" ]; then \
      ln -sfn "/usr/lib/gcc/${gcc_triplet}/${gcc_version}/include" \
        "$gcc_root/lib/gcc/x86_64-redhat-linux/11/include"; \
    fi

RUN set -euo pipefail; \
    clang_root="/opt/toolchains/clang-rhel-amd64"; \
    mkdir -p \
      "$clang_root/bin" \
      "$clang_root/include/c++" \
      "$clang_root/lib/clang/REPLACE_WITH_CLANG_RESOURCE_VERSION" \
      "$clang_root/sysroot/usr" \
      "$clang_root/sysroot/lib64"; \
    for tool in clang clang++ llvm-ar llvm-cov llvm-dwp llvm-nm llvm-objcopy llvm-objdump llvm-strip; do \
      if command -v "$tool" >/dev/null 2>&1; then \
        ln -sfn "$(command -v "$tool")" "$clang_root/bin/$tool"; \
      fi; \
    done; \
    if [ -d /usr/include/c++/v1 ]; then \
      ln -sfn /usr/include/c++/v1 "$clang_root/include/c++/v1"; \
    elif [ -d /usr/include/c++ ]; then \
      ln -sfn /usr/include/c++ "$clang_root/include/c++/v1"; \
    fi; \
    ln -sfn "$(clang -print-resource-dir)/include" \
      "$clang_root/lib/clang/REPLACE_WITH_CLANG_RESOURCE_VERSION/include"; \
    ln -sfn /usr/include "$clang_root/sysroot/usr/include"; \
    ln -sfn /usr/lib "$clang_root/sysroot/usr/lib"; \
    ln -sfn /usr/lib64 "$clang_root/sysroot/usr/lib64"; \
    ln -sfn /lib "$clang_root/sysroot/lib"; \
    ln -sfn /lib64 "$clang_root/sysroot/lib64"

ENV PATH="/opt/toolchains/gcc-rhel-amd64/root/usr/bin:/opt/toolchains/clang-rhel-amd64/bin:${PATH}"

WORKDIR /workdir
