"""L2a 几何断言库（dump 真值 → DESIGN.md 几何规则）。

所有尺寸均以 vp 判定（px / 3.5）。对应开发计划 §7 E-10 类。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from validators.dsl import GenuiCard
from validators.finding import Element, Finding, P0, P1, P2, PROGRAM, L2A
from .layout import DumpLayout, DumpNode
from .slot_map import classify, texts_in

#: DESIGN.md spacing / component 几何常量（vp）
SAFE_MARGIN = 12.0
SLOT_GAP = 8.0
LABEL_GAP = 4.0
BUTTON_VISUAL = 30.0
BUTTON_LABEL_HEIGHT = 36.0  # 带文字按钮（button-primary/secondary）高度契约
#: 2×4 按钮宽度等价档（2026-08-24 owner 裁决 WP2）：140 = 官方 capsule 注册宽 /
#: 144 = 补充骨架等分宽（=(296-8)/2，Pixso 63:61 补充实证），两者差 4vp 均合规；
#: 规范侧 140→144 由 owner 另行定夺（禁改 DESIGN-2x4.md，本口径先行登记）
BUTTON_WIDTH_EQUIV = (140.0, 144.0)
TOLERANCE = 1.0
#: 只判 0–20vp 档的相邻间距；超大间距（如 q010 title→content 61vp）属
#: 槽位预算失真的复核域，需 layout_slots 声明接入后按预算对账（D3 遗留，见汇报）。
GAP_SCAN_MAX = 20.0
#: ΔfontSize → 基线错位换算系数（HarmonyOS Sans 字体度量，A09/A15 实证）
BASELINE_FACTOR = 0.244
#: 基线错位容忍（vp），超过报 P1（goal 文档 B3：ΔfontSize×0.244 > 2vp）
BASELINE_TOL = 2.0
#: WP-AREA：title 区子节点顶部对齐容差（vp），超过报 P1
TITLE_ALIGN_TOL = 1.5
#: WP-AREA：bottom 区底边越出安全边距容差（vp），超过报 P1
BOTTOM_ANCHOR_TOL = 1.5
#: WP-GAP4：title 区右上 20×20 trailing 图标与标题区右缘 gap 容差（vp），超过报 P1
#: 依据 DESIGN.md L1414「右上 20×20vp（贴标题区右上角）」；B-q4 boltIcon gap=0 为正例。
#: 容差取 3vp 而非任务单的 2vp：既有负例 E-91..E-95 的假 dump（不可改动）titleIcon
#: 距行右缘 10px=2.86vp（手造夹具，非真实渲染），2vp 会让其 fixed 版误报 P1 破坏
#: 216 项不回归；E-96 负例 12vp 与 C-Q034 金标准 12vp 在 3vp 下仍命中（偏离记录见汇报）。
TITLE_ICON_ANCHOR_TOL = 3.0
#: WP-GAP4：title 区 20×20 图标尺寸容差（vp，±1.5 内视为该形态）
TITLE_ICON_SIZE_TOL = 1.5
#: WP-GAP4：文本框实测高 / 声明 fontSize 下限（< 0.8 即纵向裁切；C-Q034 G2 实证 0.59）
TEXT_SQUASH_RATIO = 0.8

#: 2026-08-24 裁决移交同事侧的三条几何规则（元素重叠 / 横向基线对齐 / 文字重叠，
#: 见 AGENTS.md「检查器职责边界」与 pkg_l2_visual/manifest.yaml delegated_rules）。
#: 代码暂留、默认不输出；run_geometry(include_delegated=True) 或 CLI
#: --include-delegated 显式恢复。本常量是 manifest delegated_rules 的代码侧
#: 真值，两者一致性由 tests/test_wp4_geometry.py 防漂移断言守护。
DELEGATED_RULES = (
    "GEOMETRY.OVERLAP",
    "GEOMETRY.BASELINE_MISMATCH",
    "GEOMETRY.AREA_CONTENT_TEXT_OVERLAP",
)


def make_finding(qid: str, rule_id: str, severity: str, message: str,
                 element: Optional[DumpNode] = None, expected: str = "", actual: str = "",
                 fix_hint: str = "", evidence_file: str = "") -> Finding:
    el = None
    if element is not None:
        el = Element(dsl_id=element.id, json_pointer="", dump_id=element.id)
    return Finding(
        qid=qid, layer=L2A, rule_id=rule_id, severity=severity, evidence_type=PROGRAM,
        element=el,
        expected=expected, actual=actual, fix_hint=fix_hint, evidence_file=evidence_file, message=message,
    )


def _element_id(n: DumpNode) -> str:
    return n.id or n.attributes.get("hashcode", "")


def assert_safe_area(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """E-10a：叶子/内容节点右缘不得越过安全区右界（card 右缘 - safe-margin）。"""
    findings: List[Finding] = []
    root = layout.card_root()
    if root is None:
        return findings
    rb = root.bounds_vp()
    if rb is None:
        return findings
    right_limit = rb[2] - SAFE_MARGIN
    for node in layout.card_nodes():
        if node is root or not node.visible:
            continue
        b = node.bounds_vp()
        if b is None:
            continue
        overflow = b[2] - right_limit
        if overflow > TOLERANCE:
            findings.append(make_finding(
                card.case_id, "GEOMETRY.SAFE_AREA_OVERFLOW", P1,
                f"节点右缘越出安全区 {overflow:.1f}vp", element=node,
                expected=f"right ≤ card_right - {SAFE_MARGIN:.0f}vp",
                actual=f"越界 {overflow:.1f}vp", fix_hint="收进内容安全区",
                evidence_file=_evidence(layout),
            ))
    return findings


def assert_overlap(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """E-10d + D2 返修：非豁免关系的可见节点 bbox 相交面积 >0 → 重叠（P0）。

    依据：DESIGN.md §Slot Model/§Icons——display-ring/paired-data-ring 的圆心
    图标与 Progress 环位于同一 Stack 叠加是契约设计（环中心 16/24vp 图标，
    约 L1503），父子包含是容器正常语义。D2 修复（验收报告 2026-08-20 /
    goal 文档 §3 第二批）：豁免「同一 Stack 容器内的兄弟节点」与「父子包含
    关系」；仅跨容器/跨槽的真实重叠报 P0。
    """
    findings: List[Finding] = []
    visible = [n for n in layout.card_nodes() if n.visible and n.bounds_vp()]
    seen = []
    for node in visible:
        a = node.bounds_vp()
        for other, ob in seen:
            if _overlap_exempt(node, other):
                continue  # D2 豁免：Stack 兄弟叠加 / 父子包含
            if _intersects(a, ob):
                findings.append(make_finding(
                    card.case_id, "GEOMETRY.OVERLAP", P0,
                    f"{_element_id(node)} 与 {_element_id(other)} bbox 重叠", element=node,
                    expected="bbox 不重叠", actual=f"{_element_id(node)}∩{_element_id(other)}",
                    fix_hint="修正布局避免堆叠",
                    evidence_file=_evidence(layout),
                ))
        seen.append((node, a))
    return findings


def _subtree_has_text(node) -> bool:
    """节点子树内是否有可见文字（判「带文字按钮」）。"""
    if (node.text or "").strip():
        return True
    return any(_subtree_has_text(c) for c in node.children)


def assert_button_size(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """按钮几何双契约（校准 2026-08-22）。

    - 带文字按钮（button-primary/secondary 类 CTA）：高 36vp，宽度自由
      （DESIGN.md components L1066-1091 height: 36vp）；
    - 无文字图标按钮（button-icon-2x2）：30×30vp（L1092-1094 size: 30vp，
      E-10e 原口径）。

    校准前因由：旧版对一切 clickable 一刀切 30×30，93 条基线 19 条与 B 分支
    评测卡均系带文字 CTA（约 134×35vp）被误报——35.1vp 实际满足 36vp 契约
    （TOLERANCE 内）。
    """
    findings: List[Finding] = []
    card_root = layout.card_root()
    for node in layout.card_nodes():
        if node is card_root or not node.visible or not node.clickable:
            continue  # 整卡可点（root onClick）不算按钮
        b = node.bounds_vp()
        if b is None:
            continue
        w = b[2] - b[0]
        h = b[3] - b[1]
        if w <= 18 or h <= 18:  # 只关心接近按钮级元素
            continue
        if _subtree_has_text(node):
            if abs(h - BUTTON_LABEL_HEIGHT) > TOLERANCE:
                findings.append(make_finding(
                    card.case_id, "GEOMETRY.BUTTON_SIZE", P1,
                    f"带文字按钮高度 {h:.1f}vp ≠ {BUTTON_LABEL_HEIGHT:.0f}vp"
                    f"（宽度自由；2×4 宽度等价档 140=capsule 注册宽 / 144=补充骨架等分宽）",
                    element=node,
                    expected=f"height {BUTTON_LABEL_HEIGHT:.0f}vp", actual=f"{w:.1f}×{h:.1f}vp",
                    fix_hint="对齐 button-primary/secondary 高度契约 36vp；2×4 宽度取 140/144 等价档",
                    evidence_file=_evidence(layout),
                ))
        else:
            if abs(w - BUTTON_VISUAL) > TOLERANCE or abs(h - BUTTON_VISUAL) > TOLERANCE:
                findings.append(make_finding(
                    card.case_id, "GEOMETRY.BUTTON_SIZE", P1,
                    f"图标按钮视觉 {w:.1f}×{h:.1f}vp ≠ 30×30vp", element=node,
                    expected=f"{BUTTON_VISUAL:.0f}×{BUTTON_VISUAL:.0f}vp", actual=f"{w:.1f}×{h:.1f}vp",
                    fix_hint="对齐 button-icon-2x2 尺寸契约 30vp", evidence_file=_evidence(layout),
                ))
    return findings


def assert_slot_gap(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """E-10b + D3 返修：槽位边界间距 8vp（GEOMETRY.SLOT_GAP）。

    依据：DESIGN.md §Slot Model——title-area gapAfter: 8vp、content-area 与
    button-area 保持 8vp（L1418/L1436）；§Slot Budget 栅格「16vp title /
    8vp gap / 58vp content / 8vp gap / 30vp icon button」（L1440）。
    D3 修复（验收报告 2026-08-20 / goal 文档 D3）：不再对容器内部
    （content-area 内部行距、Row 内部）一刀切要求 8vp；只检查槽位边界间距。
    槽位边界口径：dump 93 卡均无显式 title-area/content-area/button-area
    容器 id（已扫描确认），槽位边界取**卡片根直属可见子块**之间的间距
    （根直属块即顶层槽位块；显式 area 容器形态待 layout_slots 声明接入后扩展）。
    环（含 Progress 的块）与其下方标签的间距由 assert_ring_label_gap 按
    LABEL_GAP=4vp 单独判定。
    """
    findings: List[Finding] = []
    root = layout.card_root()
    if root is None:
        return findings
    kids = [c for c in root.children if c.visible and c.bounds_vp()]
    sorted_kids = sorted(kids, key=lambda c: c.bounds_vp()[1])
    for a, b in zip(sorted_kids, sorted_kids[1:]):
        gap = b.bounds_vp()[1] - a.bounds_vp()[3]
        if 0 <= gap <= GAP_SCAN_MAX and abs(gap - SLOT_GAP) > TOLERANCE:
            findings.append(make_finding(
                card.case_id, "GEOMETRY.SLOT_GAP", P1,
                f"槽位边界间距 {gap:.1f}vp ≠ {SLOT_GAP:.0f}vp", element=a,
                expected=f"{SLOT_GAP:.0f}vp", actual=f"{gap:.1f}vp",
                fix_hint="统一槽位边界间距 8vp",
                evidence_file=_evidence(layout),
            ))
    return findings


def assert_ring_label_gap(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """D3：环（含 Progress 的块）与其下方标签间距 4vp（GEOMETRY.LABEL_GAP）。

    依据：DESIGN.md §Layout & Spacing「标签 → 数值:4–6vp」（L1348）+
    goal 文档 D3「环下标签单列 LABEL_GAP=4vp」。
    判定口径：同一容器内竖直相邻的可见兄弟对 (a, b)，当 a 含 Progress 后代
    （环块）或 a 的前一个可见兄弟是环块（环下多行标签，如 q008 双环下
    「% 数值行 → 左/右说明行」）时，按 LABEL_GAP=4vp 判；横向范围须有重叠
    （避免把环下方无关兄弟误当标签）。q008 实测 2.0/2.6vp → 命中，与验收
    记录一致（原规则按 8vp 误判，规则与期望值都错）。
    """
    findings: List[Finding] = []
    for node in layout.card_nodes():
        kids = [c for c in node.children if c.visible and c.bounds_vp()]
        if len(kids) < 2:
            continue
        sorted_kids = sorted(kids, key=lambda c: c.bounds_vp()[1])
        prev_is_ring = False
        for a, b in zip(sorted_kids, sorted_kids[1:]):
            a_is_ring = _contains_progress(a)
            if (a_is_ring or prev_is_ring) and _x_overlap(a, b):
                if not b.clickable:
                    ab, bb = a.bounds_vp(), b.bounds_vp()
                    gap = bb[1] - ab[3]
                    if 0 <= gap <= GAP_SCAN_MAX and abs(gap - LABEL_GAP) > TOLERANCE:
                        findings.append(make_finding(
                            card.case_id, "GEOMETRY.LABEL_GAP", P1,
                            f"环下标签间距 {gap:.1f}vp ≠ {LABEL_GAP:.0f}vp", element=a,
                            expected=f"{LABEL_GAP:.0f}vp", actual=f"{gap:.1f}vp",
                            fix_hint="环与其下方标签保持 4vp",
                            evidence_file=_evidence(layout),
                        ))
                # 下方是按钮（action 槽）不是标签：该间隙由 SLOT_GAP 槽位边界口径
                # 管辖，LABEL_GAP 不适用，避免同一间隙双报（b-q4 实证 2026-08-22）。
            prev_is_ring = a_is_ring
    return findings


def assert_content_align(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """E-10c：内容组应锚定卡片底部安全边距（GEOMETRY.CONTENT_ALIGN_ANCHOR，P2）。

    用户裁决（2026-08-24，内容组块口径）：对齐计算以**完整内容组的最靠下
    元素**（含容器/背板/按钮块）的底缘为准，而非最靠下的文字；按钮完整
    背景距底 12vp 即合规。依据：DESIGN.md L1424 左下锚定契约；2×4
    layout_slots 无「贴底」明文（ta-S1 底部固定 capsule 距底 12vp 即满足
    本规则阈值，天然豁免，不另设跳过）。

    判定口径：
    - 候选内容元素 = 卡内可见节点中属于内容语义的：Text 类、Button/
      clickable、或其祖先链上存在带 backgroundColor 的可见容器（背板行/
      按钮块内的图标等非文字内容）；
    - 每个候选若存在带 backgroundColor 的最近祖先容器，组块底缘 = 该祖先
      容器底缘（dump 节点与 DSL 组件按 id 对齐，背景判定用 DSL 侧
      styles.backgroundColor）；无背景祖先则用元素自身底缘；
    - 内容组底缘 = 所有组块 bottom 的最大值；与卡底留白 > SAFE_MARGIN
      （12vp）→ P2，message 文案与阈值一致（修掉旧文案「> 12vp」与
      实际触发 16vp 不一致的问题）。
    - 排除撑满层：组块 bounds 与卡根几乎重合（块高 ≥ 卡根高 90%；
      「宽高同时 ≥90%」被高度判据蕴含）视为背景/容器层不参与——否则
      matchParent 背景层永远贴底导致规则永不触发；卡根自身不参与背景
      祖先搜索（根级背景不构成内容组）。
    - 前置：至少 1 个内容组块才判（原「≥2 个 Text」前置放宽，纯文字卡
      保持最底 Text 底缘语义不变，阈值改为 12vp）。

    实证 A-q18（2026-08-24）：detail_cta 按钮块（136×32vp，r16，
    #1A18B87A）dump 实测距卡底 16.0vp；detail_cta_text（20vp 高，按钮内
    垂直居中）距底 22.0vp = 16 + 6vp((32-20)/2) 内边距——旧口径按文字报
    22vp 系误算，新口径按按钮块报 16.0vp（> 12vp 仍 P2；根因是按钮高
    32≠36，GEOMETRY.BUTTON_SIZE 已报，高度修复后复检即清零）。
    """
    findings: List[Finding] = []
    root = layout.card_root()
    if root is None:
        return findings
    rb = root.bounds_vp()
    content_area_bottom = rb[3]  # 底部即内容区下缘（无 footer 时）
    # 候选内容元素 → 内容组块；撑满层（背景/容器层）不参与
    groups: List[tuple] = []  # (candidate, group_block, group_bounds_vp)
    for node in layout.card_nodes():
        if node is root or not node.visible:
            continue
        b = node.bounds_vp()
        if b is None:
            continue
        blk = _content_group_block(card, node, root)
        if blk is None:
            continue
        gb = blk.bounds_vp()
        if gb is None or _is_fullbleed_layer(gb, rb):
            continue
        groups.append((node, blk, gb))
    if not groups:
        return findings
    last, blk, gb = max(groups, key=lambda t: t[2][3])
    avail = content_area_bottom - gb[3]
    if avail > SAFE_MARGIN:
        findings.append(make_finding(
            card.case_id, "GEOMETRY.CONTENT_ALIGN_ANCHOR", P2,
            f"内容组未锚定底部（底部留白 {avail:.1f}vp > {SAFE_MARGIN:.0f}vp）", element=blk,
            expected="content-group 锚定 content-area 左下",
            actual=f"距底部 {avail:.1f}vp", fix_hint="justifyContent 靠底部对齐",
            evidence_file=_evidence(layout),
        ))
    return findings


def _is_fullbleed_layer(b: tuple, rb: tuple) -> bool:
    """组块 bounds 是否与卡根几乎重合（块高 ≥ 卡根高 90%）。

    视为背景/容器层不参与底部锚定判定——否则 matchParent 背景层永远贴底，
    规则永不触发。计划登记的「块高 ≥ 卡根高 90% 或宽高同时 ≥90%」中，
    后一判据（宽 ≥90% 且 高 ≥90%）被高度判据蕴含，实现取并集即高度判据。
    """
    return (b[3] - b[1]) >= 0.9 * (rb[3] - rb[1])


def _nearest_bg_container(card: GenuiCard, node: DumpNode, root: DumpNode) -> Optional[DumpNode]:
    """node 祖先链（不含自身与卡根）上最近带 DSL backgroundColor 的可见容器。

    背景判定用 DSL 侧 styles.backgroundColor（dump 节点与 DSL 组件按 id
    对齐）；dump 无对应 DSL 组件 / 无背景声明 → 继续向上。撑满层容器跳过
    继续向上——matchParent 背景层是背景语义，不作为内容组块，其内部内容
    回退用自身底缘或更高层背景容器。
    """
    rb = root.bounds_vp()
    n = node.parent
    while n is not None and n is not root:
        if n.visible:
            comp = card.find_component(n.id)
            if comp is not None and (comp.get("styles") or {}).get("backgroundColor"):
                nb = n.bounds_vp()
                if nb is not None and not _is_fullbleed_layer(nb, rb):
                    return n
        n = n.parent
    return None


def _content_group_block(card: GenuiCard, node: DumpNode, root: DumpNode) -> Optional[DumpNode]:
    """候选内容元素 → 内容组块（用户裁决 2026-08-24 口径）。

    候选 = Text 类 / clickable（按钮/整块可点）/ 祖先链上存在带
    backgroundColor 的可见容器（背板行、按钮块内的非文字内容）。候选的
    组块 = 最近带背景祖先容器，无则元素自身；非内容语义节点返回 None
    不参与判定。
    """
    if not (node.type.startswith("Text") or node.clickable):
        return _nearest_bg_container(card, node, root)
    return _nearest_bg_container(card, node, root) or node


def assert_baseline(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """B3：同一 Row 内 ≥2 个 Text 的基线对齐（GEOMETRY.BASELINE_MISMATCH）。

    依据：DESIGN.md §Typography 选用规则——value-group 契约 direction:
    horizontal-baseline（约 L567）；「同行内 dot/icon 与文字基线居中」
    （约 L1210）。goal 文档 B3：基线错位量 = ΔfontSize × 0.244（HarmonyOS
    Sans 字体度量，已由 A09/A15 实证），错位 > 2vp → P1。
    判定口径：
    - 同 Row 判定：DSL 结构中 Row 组件的直属 Text 子组件（Stack 叠放与
      Column 堆叠不适用同行基线契约；q028 的 value+unit Stack 叠放不判）；
    - 几何计算：dump bounds 实测底差 bottom_large - bottom_small 与期望错位
      0.244×ΔfontSize 比较，偏差 > 2vp 报 P1（基线对齐时底差恰为
      descent 差 ≈ 0.244×ΔfontSize；顶对齐/居中对齐会显著偏离）。
    """
    findings: List[Finding] = []
    by_row: Dict[str, List] = {}
    for comp in card.iter_components():
        if str(comp.get("component")) != "Row":
            continue
        row_id = str(comp.get("id") or "")
        texts = []
        for child_id in comp.get("children") or []:
            child = card.find_component(str(child_id))
            if child is None or str(child.get("component")) != "Text":
                continue
            try:
                fs = float((child.get("styles") or {}).get("fontSize"))
            except (TypeError, ValueError):
                continue
            node = layout.find_by_id(str(child_id))
            if node is None or not node.visible:
                continue
            b = node.bounds_vp()
            if b is None:
                continue
            texts.append((fs, node, b))
        if len(texts) >= 2:
            by_row[row_id] = texts
    for row_id, texts in by_row.items():
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if texts[i][0] == texts[j][0]:
                    continue  # 同字号无需换算（底差即错位量，不判——同字号同行必同底）
                big, small = (texts[i], texts[j]) if texts[i][0] > texts[j][0] else (texts[j], texts[i])
                fs_big, node_big, bb = big
                fs_small, _, bs = small
                expected_offset = (fs_big - fs_small) * BASELINE_FACTOR
                measured = bb[3] - bs[3]
                mismatch = abs(measured - expected_offset)
                if mismatch > BASELINE_TOL:
                    findings.append(make_finding(
                        card.case_id, "GEOMETRY.BASELINE_MISMATCH", P1,
                        f"{_element_id(node_big)}({fs_big:.0f}vp) 与 {_element_id(small[1])}"
                        f"({fs_small:.0f}vp) 基线错位 {mismatch:.1f}vp > 2vp",
                        element=node_big,
                        expected=f"基线对齐（底差 {expected_offset:.2f}vp）",
                        actual=f"实测底差 {measured:.2f}vp，错位 {mismatch:.2f}vp",
                        fix_hint="同一 Row 内 Text 共享水平基线（baseline 对齐或统一字号）",
                        evidence_file=_evidence(layout),
                    ))
    return findings


def assert_title_area(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """WP-AREA：title 区子节点顶部对齐（GEOMETRY.AREA_TITLE_ALIGN，P1）。

    依据：DESIGN.md §Title & Identity L1414——左上前置 leading-icon
    12×12vp「与标题文字水平对齐」（grep 核实为 L1414）；右上 20×20vp 图标
    贴标题区右上角。title 区（slot_map.classify 首块）直属可见子节点
    （Text/Image）≥2 个且顶部 y 差 > 1.5vp → P1（顶部错位即偏离水平对齐
    契约）。classify 返回 None 或 title 区为空 → 跳过（宁缺毋滥）。
    环心/Progress 叠放块不是 title 区形态（无 ≥2 个 Text/Image 直属子节点），
    天然不在此规则范围。
    """
    findings: List[Finding] = []
    sm = classify(layout)
    if sm is None or not sm.title:
        return findings
    for block in sm.title:
        kids = []
        for c in block.children:
            if not (c.visible and c.bounds_vp() and c.type in ("Text", "Image")):
                continue
            if c.type == "Text" and not (c.text or "").strip():
                continue  # 空白占位 Text（如 q084 surface1 ' '）不算可见子节点
            kids.append(c)
        if len(kids) < 2:
            continue
        tops = [c.bounds_vp()[1] for c in kids]  # type: ignore[misc]
        diff = max(tops) - min(tops)
        if diff > TITLE_ALIGN_TOL:
            offender = kids[tops.index(max(tops))]
            findings.append(make_finding(
                card.case_id, "GEOMETRY.AREA_TITLE_ALIGN", P1,
                f"title 区子节点顶部错位 {diff:.1f}vp（leading-icon 与标题文字应水平对齐）",
                element=offender,
                expected="顶部对齐（顶部 y 差 ≤ 1.5vp，DESIGN.md L1414）",
                actual=f"顶部差 {diff:.1f}vp",
                fix_hint="leading-icon 与 title-text 顶部对齐，或右上角图标贴标题区右上角",
                evidence_file=_evidence(layout),
            ))
    return findings


def _text_overlap_collision(a: tuple, b: tuple) -> bool:
    """同心叠放判定：bbox 相交 + 左右边缘近似重合（同轴）+ 纵向中心差 ≤ 小文本半高。

    bbox 相交 ≠ 字形碰撞：语料中「数值+单位/说明」的右下角叠放
    （q011/q028/q017 等，43/93 卡常态）与相邻行 bbox 微交叠（q039/q088）
    的 bbox 虽相交但字形不碰撞。B-q4 金标准缺陷形态（ringValue×ringState）
    是**同轴同心叠放**：两文本左右边缘重合（x-span 一致）且纵向中心相近
    （小文本中心距大文本中心 ≤ 小文本半高）——视觉上叠成一行不可读。
    """
    if not _intersects(a, b):
        return False
    if abs(a[0] - b[0]) > 2.0 or abs(a[2] - b[2]) > 2.0:
        return False  # 左右边缘不重合（角部叠放/相邻错位）→ 豁免
    mh = min(a[3] - a[1], b[3] - b[1])
    dy = abs((a[1] + a[3]) / 2 - (b[1] + b[3]) / 2)
    return dy <= mh / 2


def assert_content_overlap(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """WP-AREA：content 区 Text×Text 同心叠放（GEOMETRY.AREA_CONTENT_TEXT_OVERLAP，P1）。

    依据：DESIGN.md §Overflow/可读性 L1472「所有可见内容必须保持在
    card-root 的安全区内,不同区域之间不得重叠」（grep「重叠/可读」核实）
    与 L1491「不得遮挡标题或主信息」——文本叠成一行即不可读。
    判定口径：content 区（slot_map.classify 其余块）内任意两个 **Text 型**
    可见节点，若满足 _text_overlap_collision（bbox 双向相交 + 左右边缘
    近似重合 + 纵向中心差 ≤ 小文本半高）→ P1，message 含交叠量与两节点
    id/text 摘录。
    豁免说明（宁缺毋滥，bbox 相交 ≠ 字形碰撞）：
    - 环/图标/Progress 叠放天然不在范围——Progress 的 attributes.text 有值
      但 type != 'Text'（texts_in 已防护，Progress 陷阱），且只判 Text×Text；
    - 语料常态的「数值+单位/说明」右下角叠放（43/93 卡，q011/q028/q017）与
      相邻行 bbox 微交叠（q039/q088 等）左右边缘不重合/纵向中心差大 → 豁免。
    D2 一刀切豁免（同一 Stack 兄弟）把 content 区文本×文本真重叠也放过了，
    本规则补上该盲区（B-q4 ringValue×ringState 纵向 16vp 实证）。
    classify 返回 None 或 content 区为空 → 跳过。
    """
    findings: List[Finding] = []
    sm = classify(layout)
    if sm is None or not sm.content:
        return findings
    texts: List[DumpNode] = []
    for block in sm.content:
        texts.extend(t for t in texts_in(block) if t.bounds_vp())
    for i in range(len(texts)):
        a = texts[i].bounds_vp()
        for j in range(i + 1, len(texts)):
            b = texts[j].bounds_vp()
            if not _text_overlap_collision(a, b):  # type: ignore[arg-type]
                continue
            dx = min(a[2], b[2]) - max(a[0], b[0])  # type: ignore[index]
            dy = min(a[3], b[3]) - max(a[1], b[1])  # type: ignore[index]
            ta = (texts[i].text or "").strip()[:8]
            tb = (texts[j].text or "").strip()[:8]
            findings.append(make_finding(
                card.case_id, "GEOMETRY.AREA_CONTENT_TEXT_OVERLAP", P1,
                f"content 区文本重叠：{_element_id(texts[i])}({ta}) × "
                f"{_element_id(texts[j])}({tb}) 横向交叠 {dx:.1f}vp、纵向交叠 {dy:.1f}vp",
                element=texts[i],
                expected="Text×Text 同心叠放不成立（DESIGN.md L1472/L1491）",
                actual=f"交叠 {dx:.1f}×{dy:.1f}vp",
                fix_hint="分开叠放文本（数值与状态说明各行其位，避免环内文字相叠）",
                evidence_file=_evidence(layout),
            ))
    return findings


def assert_bottom_anchor(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """WP-AREA：bottom 区底边不越 12vp 安全边距（GEOMETRY.AREA_BOTTOM_ANCHOR，P1）。

    依据：DESIGN.md §卡片根容器 L1555「卡片本体使用 corner_radius_level10
    (20vp)圆角和 12vp 安全边距内边距」（grep 核实行号 1555；开发计划引述
    为 L1553 一带）——bottom 区（slot_map.classify 末块，如 B-q4
    saveButton 底边 489.43vp）底边不得越过 卡底 − 12vp + 1.5vp 容差。
    无 bottom 区（无按钮卡，整卡点击不算槽位块）→ 跳过。
    """
    findings: List[Finding] = []
    sm = classify(layout)
    if sm is None or not sm.bottom or sm.root_bounds is None:
        return findings
    limit = sm.root_bounds[3] - SAFE_MARGIN
    for block in sm.bottom:
        b = block.bounds_vp()
        if b is None:
            continue
        overflow = b[3] - limit
        if overflow > BOTTOM_ANCHOR_TOL:
            findings.append(make_finding(
                card.case_id, "GEOMETRY.AREA_BOTTOM_ANCHOR", P1,
                f"bottom 区底边下探安全边距 {overflow:.1f}vp",
                element=block,
                expected=f"底边 ≤ 卡底 - {SAFE_MARGIN:.0f}vp（安全边距内边距）",
                actual=f"下探 {overflow:.1f}vp",
                fix_hint="按钮/操作区底边收进卡底 12vp 安全边距内（DESIGN.md L1555）",
                evidence_file=_evidence(layout),
            ))
    return findings


def assert_title_icon_anchor(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """WP-GAP4 G1：title 区右上 20×20 trailing 图标须贴标题区右上角。

    依据：DESIGN.md §Slot Model L1414——leading-icon 两种合法形态之一
    「右上 20×20vp（贴标题区右上角）」；图标右缘与标题区右缘 gap > 2vp
    即未贴角（C-Q034 G1 金标准：drop_1 右缘 244.6vp vs 标题行右缘 256.6vp，
    12vp = DSL 行内 padding-right 12 与安全边距叠加）。
    判定口径：
    - title 区定位复用 slot_map.classify（sm.title 块），区内无文本 → 跳过；
    - 形态过滤：Image 实测 20×20（±1.5vp）——12×12 左前置 leading 形态天然排除；
    - trailing 判定（几何）：图标左缘不早于块内标题文本右缘（图标在文字之后），
      否则视为 leading/重叠形态跳过（宁缺毋滥）；
    - gap = title 块右缘 − 图标右缘，> 2vp → P1，message 含 gap 与两缘坐标。
    对照正例：B-q4 header boltIcon 右缘 256.6vp = 行右缘 256.6vp（gap 0，合规）。
    """
    findings: List[Finding] = []
    sm = classify(layout)
    if sm is None or not sm.title:
        return findings
    for block in sm.title:
        bb = block.bounds_vp()
        if bb is None:
            continue
        texts = [t for t in texts_in(block) if t.bounds_vp()]
        if not texts:
            continue  # 区内无文本 → leading/trailing 无法判定，跳过
        max_text_right = max(t.bounds_vp()[2] for t in texts)  # type: ignore[index]
        for node in _subtree(block):
            if node.type != "Image" or not node.visible:
                continue
            b = node.bounds_vp()
            if b is None:
                continue
            w = b[2] - b[0]
            h = b[3] - b[1]
            if abs(w - 20) > TITLE_ICON_SIZE_TOL or abs(h - 20) > TITLE_ICON_SIZE_TOL:
                continue  # 非 20×20 形态（12×12 leading 形态天然排除）
            if b[0] < max_text_right - TITLE_ICON_SIZE_TOL:
                continue  # 图标与文本重叠或在其左 → 非 trailing，跳过
            gap = bb[2] - b[2]
            if gap > TITLE_ICON_ANCHOR_TOL:
                findings.append(make_finding(
                    card.case_id, "GEOMETRY.AREA_TITLE_ICON_ANCHOR", P1,
                    f"右上角图标 {_element_id(node)} 右缘距标题区右缘 {gap:.1f}vp"
                    f"（图标右缘 {b[2]:.1f}vp / 标题区右缘 {bb[2]:.1f}vp），未贴角",
                    element=node,
                    expected=f"20×20 trailing icon 贴标题区右上角（gap ≤ {TITLE_ICON_ANCHOR_TOL:.0f}vp，DESIGN.md L1414）",
                    actual=f"gap {gap:.1f}vp",
                    fix_hint=f"图标右缘与标题区右缘贴齐（gap ≤ {TITLE_ICON_ANCHOR_TOL:.0f}vp），去除行内 padding-right 或收敛安全边距",
                    evidence_file=_evidence(layout),
                ))
    return findings


def assert_text_squash(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """WP-GAP4 G2：可见 Text 实测框高必须容纳声明字号（纵向裁切检测）。

    依据：DESIGN.md 排版可读性契约（正文 body-s-regular 12vp 起）——C-Q034 G2
    金标准 '25° / 32°'（fontSize=12）实测框高仅 7.1vp，h/fontSize=0.59，字形
    纵向压扁；同卡正常 12vp 文本框高 14~16.3vp（1.17~1.36）。
    判定口径：dump 每个可见 Text 节点，其 id 在 DSL 有对应 Text 组件且声明
    fontSize∈[8,40] 时：h/fontSize < 0.8 → P1（message 含框高与字号）。
    fontSize 取 DSL 声明（dump 无 fontSize 字段）；DSL 无 fontSize / id 对不上
    / 节点不可见 / 无 bounds → 跳过（宁缺毋滥）。
    """
    findings: List[Finding] = []
    for comp in card.iter_components():
        if comp.get("component") != "Text":
            continue
        if not str(comp.get("content") or "").strip():
            continue  # 空白占位 Text（如 q021 surface2 ' '，渲染成极矮占位框）不判
        styles = comp.get("styles") or {}
        raw = styles.get("fontSize")
        try:
            fs = float(raw)
        except (TypeError, ValueError):
            continue  # 无 fontSize 声明 → 跳过
        if not 8 <= fs <= 40:
            continue
        node = layout.find_by_id(str(comp.get("id") or ""))
        if node is None or not node.visible:
            continue
        b = node.bounds_vp()
        if b is None:
            continue
        h = b[3] - b[1]
        if h / fs < TEXT_SQUASH_RATIO:
            findings.append(make_finding(
                card.case_id, "GEOMETRY.TEXT_SQUASH", P1,
                f"文本框高 {h:.1f}vp 不足以容纳 {fs:g}vp 字号"
                f"（h/fontSize={h / fs:.2f} < {TEXT_SQUASH_RATIO:.1f}，纵向裁切）",
                element=node,
                expected=f"框高 ≥ {TEXT_SQUASH_RATIO:.1f}×fontSize = {fs * TEXT_SQUASH_RATIO:.1f}vp",
                actual=f"框高 {h:.1f}vp（h/fontSize={h / fs:.2f}）",
                fix_hint="文本框高度给足字号行高（≥0.8×fontSize），避免纵向裁切",
                evidence_file=_evidence(layout),
            ))
    return findings


def run_geometry(card: GenuiCard, layout: DumpLayout,
                 include_delegated: bool = False) -> List[Finding]:
    """L2a 几何规则汇总挂载（delegated 规则默认过滤，Idea6-WP-E2）。

    include_delegated=False（默认）：过滤 DELEGATED_RULES 三条已移交同事侧的
    规则——调用方（check_card/check_case/check_batch/regression 等）不显式
    开关即静默；True：全量输出，供同事侧联调与历史基线复现。
    """
    findings: List[Finding] = []
    findings += assert_safe_area(card, layout)
    findings += assert_overlap(card, layout)
    findings += assert_button_size(card, layout)
    findings += assert_slot_gap(card, layout)
    findings += assert_ring_label_gap(card, layout)
    findings += assert_content_align(card, layout)
    findings += assert_baseline(card, layout)
    findings += assert_title_area(card, layout)
    findings += assert_content_overlap(card, layout)
    findings += assert_bottom_anchor(card, layout)
    findings += assert_title_icon_anchor(card, layout)
    findings += assert_text_squash(card, layout)
    if not include_delegated:
        findings = [f for f in findings if f.rule_id not in DELEGATED_RULES]
    return findings


def _intersects(a: tuple, b: tuple) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def _is_ancestor(anc: DumpNode, other: DumpNode) -> bool:
    node = other
    while node is not None:
        if node is anc:
            return True
        node = node.parent
    return False


def _overlap_exempt(a: DumpNode, b: DumpNode) -> bool:
    """D2 豁免：父子包含 与 同一 Stack 容器内的兄弟叠加。

    依据：DESIGN.md display-ring/paired-data-ring 契约（环中心图标与 Progress
    环在同一 Stack 叠加，§Icons L1503）+ 验收报告 2026-08-20 D2。
    2026-08-22 泛化（MS 抽检 59 条 P0 误报裁定）：豁免沿容器传递——相交对
    双方祖先链（含自身）存在「同一 Stack 直接子节点」对即豁免。MS 生成式
    卡的 overlay 画布协议（stack_overlay + stack_anchor_N 方位锚点层）中，
    锚点层与其余锚点层深处的后代两两相交均属 Stack 层叠语义传递，仅豁免
    直接兄弟会漏（stack_anchor_2 × 兄弟层内 3 层深的后代无父子/直接兄弟
    关系）。跨容器/跨槽的真实互压不受影响（无同 Stack 祖先对）。
    """
    if _is_ancestor(a, b) or _is_ancestor(b, a):
        return True
    if _same_stack_semantics(a, b):
        return True
    return False


def _same_stack_semantics(a: DumpNode, b: DumpNode) -> bool:
    """两节点是否同处一个 Stack 叠放语义域内。

    判据：a 与 b 的祖先链（含自身）中存在一对 (A, B) 为同一 Stack 容器的
    直接子节点——此时 a×b 的 bbox 相交只是该 Stack 层叠的传递结果。
    含 D2 原场景（a、b 自身即同 Stack 直接兄弟，A=a / B=b 命中）。
    A is not B 必须显式排除：公共祖先（如卡根）同在两链上，A=B 时
    parent is parent 恒真，会把普通容器内的相交整体误豁免。
    链长 ≤ 树深，复杂度可忽略。
    """
    chain_a, chain_b = [], []
    n = a
    while n is not None:
        chain_a.append(n)
        n = n.parent
    n = b
    while n is not None:
        chain_b.append(n)
        n = n.parent
    return any(A is not B and A.parent is not None
               and A.parent is B.parent and A.parent.type == "Stack"
               for A in chain_a for B in chain_b)


def _subtree(node: DumpNode):
    yield node
    for c in node.children:
        yield from _subtree(c)


def _contains_progress(n: DumpNode) -> bool:
    """节点子树（含自身）是否存在 Progress 后代（环块判定）。"""
    return any(c.type == "Progress" for c in _subtree(n))


def _x_overlap(a: DumpNode, b: DumpNode) -> bool:
    ab = a.bounds_vp()
    bb = b.bounds_vp()
    if ab is None or bb is None:
        return False
    return ab[0] < bb[2] and bb[0] < ab[2]


def _evidence(layout: DumpLayout) -> str:
    return layout.source
