"""Design Check — L1 确定性校验器（标准库 only）。

从 ``harmony-card-dsl-validation`` vendored 并按本项目演化：
- 本包是纯 Python、无副作用、无外部依赖的校验逻辑；
- 输入：``card.genui.jsonl`` + ``task-spec.json``；
- 依据：外层 ``DESIGN.md``（front-matter token + 正文规则）；
- 输出：带有 ``[P0/P1/P2]`` 严重级与 json-pointer 证据的 ``Issue`` 列表。
"""

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# L2 视觉包兼容别名（Idea2-WP-B 2026-08-26）：geometry/layout/slot_map/
# reconcile_lib 物理迁移至 packages/pkg_l2_visual/，旧路径 validators.<name>
# 经 sys.modules 别名指向新模块（存量脚本/测试零改动）。
# ---------------------------------------------------------------------------
def _install_l2_visual_aliases() -> None:
    import sys

    from packages import pkg_l2_visual
    from packages.pkg_l2_visual import geometry, layout, reconcile_lib, slot_map

    for name, mod in (("layout", layout), ("slot_map", slot_map),
                      ("geometry", geometry), ("reconcile_lib", reconcile_lib)):
        sys.modules[f"{__name__}.{name}"] = mod
        setattr(pkg_l2_visual, name, mod)
        globals()[name] = mod


_install_l2_visual_aliases()
del _install_l2_visual_aliases
