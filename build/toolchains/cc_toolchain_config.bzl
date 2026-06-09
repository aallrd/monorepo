"""Shared helpers for fixed-path C++ toolchain configurations."""

load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load(
    "@rules_cc//cc:cc_toolchain_config_lib.bzl",
    "action_config",
    "feature",
    "flag_group",
    "flag_set",
    "tool",
    "tool_path",
)
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")
load("@rules_cc//cc/toolchains:cc_toolchain_config_info.bzl", "CcToolchainConfigInfo")

_COMPILE_ACTIONS = [
    ACTION_NAMES.assemble,
    ACTION_NAMES.c_compile,
    ACTION_NAMES.cpp_compile,
    ACTION_NAMES.preprocess_assemble,
]

_LINK_ACTIONS = [
    ACTION_NAMES.cpp_link_dynamic_library,
    ACTION_NAMES.cpp_link_executable,
    ACTION_NAMES.cpp_link_nodeps_dynamic_library,
]

def _flag_feature(name, actions, flags, enabled = True, with_features = []):
    if not flags:
        return None

    return feature(
        name = name,
        enabled = enabled,
        flag_sets = [
            flag_set(
                actions = actions,
                flag_groups = [flag_group(flags = flags)],
                with_features = with_features,
            ),
        ],
    )

def _mode_feature(name, compile_flags, link_flags):
    flag_sets = []
    if compile_flags:
        flag_sets.append(
            flag_set(
                actions = _COMPILE_ACTIONS,
                flag_groups = [flag_group(flags = compile_flags)],
            ),
        )
    if link_flags:
        flag_sets.append(
            flag_set(
                actions = _LINK_ACTIONS,
                flag_groups = [flag_group(flags = link_flags)],
            ),
        )

    return feature(
        name = name,
        enabled = False,
        flag_sets = flag_sets,
    )

def _link_action_configs(tool_paths):
    linker = tool_paths.get("ld")
    if not linker:
        return []

    return [
        action_config(
            action_name = action,
            enabled = True,
            tools = [tool(path = linker)],
        )
        for action in _LINK_ACTIONS
    ]

def _fixed_cc_toolchain_config_impl(ctx):
    features = [
        _flag_feature("default_compile_flags", _COMPILE_ACTIONS, ctx.attr.compile_flags),
        _flag_feature(
            "warnings_as_errors",
            _COMPILE_ACTIONS,
            ctx.attr.warnings_as_errors_flags,
            enabled = False,
        ),
        _flag_feature("default_link_flags", _LINK_ACTIONS, ctx.attr.link_flags),
        _mode_feature("dbg", ctx.attr.dbg_compile_flags, ctx.attr.dbg_link_flags),
        _mode_feature("fastbuild", ctx.attr.fastbuild_compile_flags, ctx.attr.fastbuild_link_flags),
        _mode_feature("opt", ctx.attr.opt_compile_flags, ctx.attr.opt_link_flags),
    ]

    if ctx.attr.supports_pic:
        features.append(feature(name = "supports_pic", enabled = True))

    features = [item for item in features if item != None]

    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        features = features,
        toolchain_identifier = ctx.attr.toolchain_identifier,
        host_system_name = ctx.attr.host_system_name,
        target_system_name = ctx.attr.target_system_name,
        target_cpu = ctx.attr.target_cpu,
        target_libc = ctx.attr.target_libc,
        compiler = ctx.attr.compiler,
        abi_version = ctx.attr.abi_version,
        abi_libc_version = ctx.attr.abi_libc_version,
        tool_paths = [
            tool_path(name = name, path = path)
            for name, path in ctx.attr.tool_paths.items()
        ],
        action_configs = _link_action_configs(ctx.attr.tool_paths),
        builtin_sysroot = ctx.attr.builtin_sysroot,
        cxx_builtin_include_directories = ctx.attr.cxx_builtin_include_directories,
    )

fixed_cc_toolchain_config = rule(
    implementation = _fixed_cc_toolchain_config_impl,
    attrs = {
        "abi_libc_version": attr.string(mandatory = True),
        "abi_version": attr.string(mandatory = True),
        "builtin_sysroot": attr.string(),
        "compile_flags": attr.string_list(),
        "compiler": attr.string(mandatory = True),
        "cxx_builtin_include_directories": attr.string_list(),
        "dbg_compile_flags": attr.string_list(),
        "dbg_link_flags": attr.string_list(),
        "fastbuild_compile_flags": attr.string_list(),
        "fastbuild_link_flags": attr.string_list(),
        "host_system_name": attr.string(mandatory = True),
        "link_flags": attr.string_list(),
        "opt_compile_flags": attr.string_list(),
        "opt_link_flags": attr.string_list(),
        "supports_pic": attr.bool(default = True),
        "target_cpu": attr.string(mandatory = True),
        "target_libc": attr.string(mandatory = True),
        "target_system_name": attr.string(mandatory = True),
        "tool_paths": attr.string_dict(mandatory = True),
        "toolchain_identifier": attr.string(mandatory = True),
        "warnings_as_errors_flags": attr.string_list(),
    },
    provides = [CcToolchainConfigInfo],
)
