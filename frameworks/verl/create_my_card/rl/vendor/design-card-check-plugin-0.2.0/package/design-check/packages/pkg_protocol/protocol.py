"""PROTOCOL./STRUCT.* —— 结构/协议规则（E-09 系）。

- ``PROTOCOL.MESSAGE_COUNT``：genui 消息完整性（E-09a）。三条齐全 = pass；
  仅缺 updateDataModel 且 createSurface/updateComponents 在场 = 「多步走」生成形态
  （评测集 README「晓峰——多步走」分支明示仅两条消息）。2026-08-24 owner 裁决：
  多步走形态移出本阶段检出（与 check_text_overflow 同构：MS 分支 62 文件全为此
  形态，属生成链路分支差异而非单卡缺陷），不再产出 finding；绑定类检查
  （依赖 updateDataModel / dataModelSchema）自然跳过语义不变；其余缺消息组合
  仍为 P0 协议违规。
- ``PROTOCOL.VERSION`` / ``PROTOCOL.CATALOG_ID``：genui 信封字段协议常量校验
  （E-43/E-44）。依据：宿主管线 scripts/preview/*.py 的 CATALOG 常量
  ``ohos.a2ui.extended.catalog.form`` 与全部生成样本的 ``"version": "v0.9"``
  （外层 CreateMyCard 仓库只读引用，AGENTS.md source-of-truth #3）。
"""
from __future__ import annotations

from typing import Dict, List

from validators.dsl import GenuiCard
from validators.finding import Finding, P0, P1
from validators.rules import register
from validators.rules._common import make

EXPECTED_OPS = ("createSurface", "updateComponents", "updateDataModel")

#: 宿主管线 genui 信封字段协议常量（见 scripts/preview/generate_*_eval.py）
EXPECTED_GENUI_VERSION = "v0.9"
EXPECTED_CATALOG_ID = "ohos.a2ui.extended.catalog.form"


def _present_ops(card: GenuiCard) -> Dict[str, dict]:
    """按消息名返回在场（非空）的 genui 记录。"""
    return {
        op: rec for op, rec in (
            ("createSurface", card.create_surface),
            ("updateComponents", card.update_components),
            ("updateDataModel", card.update_data_model),
        ) if rec
    }


@register("PROTOCOL.MESSAGE_COUNT")
def check_message_count(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """genui 消息完整性（E-09a）。

    2026-08-24 owner 裁决：多步走生成形态（createSurface+updateComponents 在场、
    缺 updateDataModel）移出本阶段检出——与 check_text_overflow 同构，MS 分支
    62 文件全为此形态，属生成链路分支差异而非单卡缺陷，不再产出 finding；
    绑定类检查（依赖 updateDataModel / dataModelSchema）自然跳过语义不变。
    其余缺消息组合（缺 createSurface / updateComponents 等）仍为 P0 协议违规。
    """
    present = _present_ops(card)
    missing = [op for op in EXPECTED_OPS if op not in present]
    if not missing:
        return []
    if missing == ["updateDataModel"]:
        # 「晓峰——多步走」分支形态：createSurface+updateComponents 在场、
        # 无数据绑定消息。2026-08-24 裁决移出检出（纯噪音），静默。
        return []
    return [
        make(
            card, "PROTOCOL.MESSAGE_COUNT",
            f"genui message 应 3 条，实际 {len(present)} 条（缺 {', '.join(missing)}）",
            severity=P0,
            expected=3,
            actual=len(present),
            fix_hint="补齐 createSurface/updateComponents/updateDataModel 三行",
        )
    ]


@register("PROTOCOL.VERSION")
def check_version(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """每条在场 genui 消息必须带 version=v0.9（E-43；宿主管线协议常量）。"""
    findings: List[Finding] = []
    for op, rec in _present_ops(card).items():
        v = rec.get("version")
        if v != EXPECTED_GENUI_VERSION:
            findings.append(
                make(
                    card, "PROTOCOL.VERSION",
                    f"{op} 消息 version 应为 {EXPECTED_GENUI_VERSION!r}，实际 {v!r}",
                    severity=P0,
                    expected=EXPECTED_GENUI_VERSION,
                    actual=str(v),
                    fix_hint=f"version 置为 {EXPECTED_GENUI_VERSION}",
                )
            )
    return findings


@register("PROTOCOL.CATALOG_ID")
def check_catalog_id(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """createSurface.catalogId 必须为宿主管线 CATALOG 常量（E-44）。"""
    if not card.create_surface:
        return []  # 缺 createSurface 由 MESSAGE_COUNT 报告
    cs = card.create_surface.get("createSurface") if isinstance(card.create_surface, dict) else {}
    cid = cs.get("catalogId")
    if cid != EXPECTED_CATALOG_ID:
        return [
            make(
                card, "PROTOCOL.CATALOG_ID",
                f"createSurface.catalogId 应为 {EXPECTED_CATALOG_ID!r}，实际 {cid!r}",
                severity=P0,
                expected=EXPECTED_CATALOG_ID,
                actual=str(cid),
                fix_hint=f"catalogId 置为 {EXPECTED_CATALOG_ID}",
            )
        ]
    return []


@register("PROTOCOL.DANGLING_CHILD")
def check_dangling_child(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """children 引用的组件 id 必须存在（E-09 P0）。"""
    known = set()
    for comp in card.iter_components():
        cid = comp.get("id")
        if cid:
            known.add(cid)
    findings: List[Finding] = []
    for comp in card.iter_components():
        children = comp.get("children") or []
        if not isinstance(children, list):
            continue
        for ref in children:
            if isinstance(ref, str) and ref not in known:
                findings.append(
                    make(
                        card, "PROTOCOL.DANGLING_CHILD",
                        f"children 引用不存在的组件: {ref}", comp.get("id"), severity=P0,
                        expected=f"child id ∈ {{known ids}}",
                        actual=f"引用 {ref!r} 不存在",
                        fix_hint="修正 children 引用",
                    )
                )
    return findings


@register("STRUCT.SIZE_MISMATCH")
def check_size_mismatch(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """task-spec size 与 DSL 布局预算不一致的启发式（E-09 P1）。"""
    # 说明：本项目当前全是 2x2；此规则保留扩展点。2x4 卡若 root 用 2x2 预算（如
    # 高度明显 <320vp）则报警。
    return []


@register("STRUCT.ROOT_CONTAINER")
def check_root_container(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """card-root 必须存在且为容器组件（Column/Row/Stack）。

    校准记录（2026-08-22 验收）：旧版要求根必须 Column——DESIGN.md §卡片根容器
    （L1551-1557）只约束画布/背景/圆角/边距/点击，无组件类型明文；第一次评测
    A 分支 40 卡 Stack 根、B 分支 11 卡 Row 根均为可正常渲染的合法形态（93 条
    数据集恰全为 Column）。故放宽为「容器类型即可」，非容器根（Text/Image 等）
    仍是结构性 P0。
    根解析口径：优先 id=root；缺失时回退到唯一的 ``*_root`` 后缀组件
    （「晓峰——多步走」分支生成式根 id 形如 cardgenerated_*_root）；
    回退不唯一仍按缺根报。
    """
    root = card.find_component("root")
    if root is None:
        roots = [c for c in card.iter_components() if str(c.get("id") or "").endswith("_root")]
        root = roots[0] if len(roots) == 1 else None
    if root is None:
        return [make(card, "STRUCT.ROOT_CONTAINER", "缺少 id=root 的根容器", severity=P0)]
    if root.get("component") not in ("Column", "Row", "Stack"):
        return [
            make(card, "STRUCT.ROOT_CONTAINER", f"根容器应为容器组件（Column/Row/Stack），实际 {root.get('component')}",
                 "root", severity=P0, actual=root.get("component"), fix_hint="根容器用 Column/Row/Stack 容器")
        ]
    return []


@register("STRUCT.IDS_UNIQUE")
def check_ids_unique(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """组件 id 必须唯一。"""
    seen = {}
    for comp in card.iter_components():
        cid = comp.get("id")
        if cid:
            seen[cid] = seen.get(cid, 0) + 1
    out: List[Finding] = []
    for cid, count in seen.items():
        if count > 1:
            out.append(make(card, "STRUCT.IDS_UNIQUE", f"id={cid!r} 出现 {count} 次", cid, severity=P1,
                            actual=f"{count} 次", fix_hint="确保 id 唯一"))
    return out


def check_text_overflow(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """Text textOverflow=ellipsis 数据门禁 —— 已按 owner 决策移出本轮检出范围（2026-08-22）。

    移除原因：①DESIGN.md 无「每个 Text 必须设 ellipsis」明文（规范口径是
    《Overflow Resolution》L1478 按优先级删减内容、禁 clip-to-hide 掩盖）；
    ②A/B/MS 分支管线系统性不输出该属性，属管线级缺失而非逐卡设计错误，
    不应在当前轮次逐卡检出（B 分支 443 条/98 卡）。函数保留备查，如需
    恢复：把下方 @register 装饰器还原即可。
    """
    return []
