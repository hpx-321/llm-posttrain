"""TYPE.* —— 字号/字重档位规则（E-03 字号 + E1 字重维度 + 按钮排版分档）。

E1 依据（DESIGN.md §Typography，行号以实际 grep 为准）：
- 完整 45 角色矩阵 L1295-1315：15 档 × Regular/Medium/Bold 三档字重；
- 3 档字重 L1273-1276：regular 400 / medium 500 / bold 700；
- metric 档位 L1319：metric-primary 40vp/700、metric-primary-with-support 32vp/700；
- 第四种字重禁令 L1665：不要引入第四种字重；
- 20vp+ 不放大 L1327-1329：系统字号缩放（0.8x–1.3x）下宿主运行时行为，
  genui DSL 无字体缩放属性可判定（不可判定部分降级为文档说明，不臆报）；
  若产物尝试声明缩放类样式键，由 CATALOG.STYLE_KEY_UNREGISTERED（P2）兜底拦截。

TYPE.BUTTON_TYPOGRAPHY（2026-08-24 owner 裁决，B-q6 驱动）：
- DESIGN.md front-matter typography.body-m-*/body-s-*（fontSize 14/12）
  +《操作 Action》「按钮文案默认 body-m-regular；超过 6 个字时降级
  body-s-regular」。
"""
from __future__ import annotations

from typing import Dict, List

from validators.dsl import GenuiCard
from validators.finding import Finding, P0, P1
from validators.rules._common import make
from validators.rules import register

GLOBAL_MIN_FONT = 8

#: 45 角色矩阵档位尺寸（DESIGN.md L1295-1315）：display 56/48/38 · title 30/24/20 ·
#: subtitle 18/16/14 · body 16/14/12 · caption 12/10/8
ROLE_SIZES = frozenset((56, 48, 38, 30, 24, 20, 18, 16, 14, 12, 10, 8))
#: 3 档字重（DESIGN.md L1273-1276）：regular 400 / medium 500 / bold 700
ROLE_WEIGHTS = frozenset((400, 500, 700))
#: metric 档位（DESIGN.md §选用规则 L1319）：40/32 仅登记 700，不开放其它字重
METRIC_WEIGHTS = {40: frozenset((700,)), 32: frozenset((700,))}


@register("TYPE.FONT_SIZE_STEP")
def check_font_size(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """Text fontSize 必须落在 typography 45 角色字号集内；低于 8vp 即 P0。"""
    findings: List[Finding] = []
    allowed = set(contract.get("allowed_font_sizes") or [])
    if not allowed:
        return findings
    for comp in card.iter_components():
        if comp.get("component") != "Text":
            continue
        styles = comp.get("styles") or {}
        raw = styles.get("fontSize")
        if raw is None or not isinstance(raw, (int, float)):
            continue
        size = int(raw)
        if size < GLOBAL_MIN_FONT:
            findings.append(
                make(
                    card, "TYPE.FONT_SIZE_STEP",
                    f"fontSize={size}vp 低于全局最小 {GLOBAL_MIN_FONT}vp",
                    comp.get("id"), severity=P0,
                    expected=f">= {GLOBAL_MIN_FONT}vp",
                    actual=f"{size}vp",
                    fix_hint="放大到最小可读字号",
                )
            )
        elif size not in allowed:
            findings.append(
                make(
                    card, "TYPE.FONT_SIZE_STEP",
                    f"fontSize={size}vp 不在 typography 字号集",
                    comp.get("id"), severity=P1,
                    expected=" ".join(str(s) for s in sorted(allowed)),
                    actual=f"{size}vp",
                    fix_hint="改为最近的规范字号",
                )
            )
    return findings


#: value-group 档位（DESIGN.md §选用规则 1319）：
#: 主数字 metric-primary 40/700（无辅助信息）或 metric-primary-with-support 32/700；
#: 单位与辅助信息 body-s-regular 12/400。
VALUE_PRIMARY_SIZES = (40, 32)
VALUE_PRIMARY_WEIGHT = 700
VALUE_UNIT_SIZE = 12
VALUE_UNIT_WEIGHT = 400
#: 识别阈值：同 Row 内 Text 字号差 ≥12 且较大字号 ≥24 视为「主数字+单位」组
_GROUP_SIZE_GAP = 12
_GROUP_MIN_PRIMARY = 24


@register("TYPE.VALUE_GROUP_TIER")
def check_value_group_tier(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """E2：数字+单位组的档位契约（§选用规则 1319）。"""
    from .icon import _comp_index, _resolved_children

    findings: List[Finding] = []
    index = _comp_index(card)
    for comp in index.values():
        if comp.get("component") != "Row":
            continue
        sized = []
        for t in _resolved_children(index, comp):
            if t.get("component") != "Text":
                continue
            fs = (t.get("styles") or {}).get("fontSize")
            if isinstance(fs, (int, float)) and not isinstance(fs, bool):
                sized.append((t, float(fs)))
        if len(sized) < 2:
            continue
        sized.sort(key=lambda p: -p[1])
        primary, p_fs = sized[0]
        second_fs = sized[1][1]
        if p_fs - second_fs < _GROUP_SIZE_GAP or p_fs < _GROUP_MIN_PRIMARY:
            continue
        pw = (primary.get("styles") or {}).get("fontWeight")
        if int(p_fs) not in VALUE_PRIMARY_SIZES:
            findings.append(
                make(
                    card, "TYPE.VALUE_GROUP_TIER",
                    f"主数字 fontSize={p_fs:g}vp 不在 metric 档位（40 无辅助 / 32 有辅助）",
                    primary.get("id"), severity=P1,
                    expected=f"fontSize ∈ {VALUE_PRIMARY_SIZES} / weight {VALUE_PRIMARY_WEIGHT}",
                    actual=f"fontSize={p_fs:g} / weight={pw}",
                    fix_hint="按 §选用规则 1319 选 metric-primary(40/700) 或 with-support(32/700)",
                )
            )
        if pw != VALUE_PRIMARY_WEIGHT:
            findings.append(
                make(
                    card, "TYPE.VALUE_GROUP_TIER",
                    f"主数字 fontWeight={pw} 应为 {VALUE_PRIMARY_WEIGHT}",
                    primary.get("id"), severity=P1,
                    expected=f"fontWeight {VALUE_PRIMARY_WEIGHT}",
                    actual=f"fontWeight={pw}",
                    fix_hint="主数字用 700 字重（§选用规则 1319）",
                )
            )
        for unit, u_fs in sized[1:]:
            uw = (unit.get("styles") or {}).get("fontWeight")
            if u_fs != VALUE_UNIT_SIZE or uw not in (VALUE_UNIT_WEIGHT, None):
                findings.append(
                    make(
                        card, "TYPE.VALUE_GROUP_TIER",
                        f"单位 fontSize={u_fs:g}/weight={uw} 应为 body-s-regular {VALUE_UNIT_SIZE}/{VALUE_UNIT_WEIGHT}",
                        unit.get("id"), severity=P1,
                        expected=f"{VALUE_UNIT_SIZE}vp / {VALUE_UNIT_WEIGHT}",
                        actual=f"{u_fs:g}vp / {uw}",
                        fix_hint="单位改用 body-s-regular 12/400（§选用规则 1319）",
                    )
                )
    return findings


@register("TYPE.BUTTON_TYPOGRAPHY")
def check_button_typography(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """按钮文案字号分档：≤6 字 body-m 14fp；>6 字 body-s 12fp（P1）。

    依据：DESIGN.md front-matter typography.body-m-*/body-s-*（fontSize 14/12）
    +《操作 Action》「按钮文案默认 body-m-regular；超过 6 个字时降级
    body-s-regular」；2026-08-24 owner 裁决（B-q6 驱动）立项。超字数另有
    COPY 类规则管辖，本规则只判档位。

    判定口径：
    - 按钮识别与 SHAPE.BUTTON_RADIUS 一致：非卡根 onClick 且 button-like
      （复用 icon._is_button_like / _comp_index / _parent_map）；
    - 原生 Button：label 字数 ≤6 → styles.fontSize 应 14，>6 → 应 12；
    - 组合按钮：子树内 Text（沿 _resolved_children 递归）content 非空且
      字数 ≤6 → fontSize 应 14，>6 → 应 12；
    - fontSize 未声明 / 非数值 → 不判（宁缺毋滥）；
    - 行距不判：DESIGN.md typography token 无 lineHeight 值、无金标准锚点，
      待金标准登记 lineHeight 档位后另行立项。
    """
    from .icon import _comp_index, _is_button_like, _parent_map, _resolved_children

    findings: List[Finding] = []
    index = _comp_index(card)
    parents = _parent_map(index)

    def _check_size(comp: Dict[str, Any], text_len: int, what: str) -> None:
        """单处文案字号档位比对（声明才判）。"""
        fs = (comp.get("styles") or {}).get("fontSize")
        if fs is None or isinstance(fs, bool) or not isinstance(fs, (int, float)):
            return  # 未声明 / 非数值不判（宁缺毋滥）
        exp = 14 if text_len <= 6 else 12
        if int(fs) == exp:
            return
        tier = "body-m-* 14fp（≤6 字）" if text_len <= 6 else "body-s-* 12fp（>6 字）"
        findings.append(
            make(
                card, "TYPE.BUTTON_TYPOGRAPHY",
                f"按钮{what}字数 {text_len}（{'≤6 用 body-m' if text_len <= 6 else '>6 降级 body-s'}），"
                f"fontSize={fs:g} 应为 {exp}",
                comp.get("id"), severity=P1,
                expected=f"fontSize={exp}（{tier}，DESIGN.md《操作 Action》）",
                actual=f"fontSize={fs:g}",
                fix_hint=f"fontSize 改为 {exp}：按钮文案默认 body-m-regular（14fp），"
                         f"超过 6 个字降级 body-s-regular（12fp）",
            )
        )

    def _scan_texts(comp: Dict[str, Any]) -> None:
        """沿 _resolved_children 递归扫描按钮子树内 Text。"""
        for child in _resolved_children(index, comp):
            if child.get("component") == "Text":
                content = child.get("content")
                if isinstance(content, str) and content.strip():
                    _check_size(child, len(content), "文案")
            _scan_texts(child)

    for btn in index.values():
        if not btn.get("onClick") or not _is_button_like(btn, parents):
            continue
        label = btn.get("label")
        if isinstance(label, str) and label.strip():
            _check_size(btn, len(label), "label")
        _scan_texts(btn)
    return findings


@register("TYPE.WEIGHT_MATRIX")
def check_weight_matrix(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """E1 字重维度：Text/Button 的 fontWeight 必须落在该字号档位的合法字重集。

    依据：
    - 45 角色矩阵（DESIGN.md L1295-1315）：每档尺寸只登记 Regular(400)/Medium(500)/Bold(700)；
    - 3 档字重（L1273-1276）；第四种字重禁令（L1665）；
    - metric 档位（L1319）：40vp/700（无辅助）与 32vp/700（有辅助）仅登记 700。

    判定口径：
    - fontWeight 缺省视为 regular 400（矩阵成员），不判；
    - 字号本身不在矩阵内（如 28vp）由 TYPE.FONT_SIZE_STEP 负责，本规则不重复报；
    - 「20vp+ 不放大」（L1327-1329）描述系统字号缩放（0.8x–1.3x）下宿主运行时的放大行为，
      genui DSL 无任何字体缩放属性可静态判定，故不为此发 finding（不臆报）；
      若产物尝试声明缩放类样式键（如 fontScale / textSizeAdjust），
      由 CATALOG.STYLE_KEY_UNREGISTERED（P2）兜底拦截。
    """
    findings: List[Finding] = []
    for comp in card.iter_components():
        if comp.get("component") not in ("Text", "Button"):
            continue
        styles = comp.get("styles") or {}
        raw_w = styles.get("fontWeight")
        if raw_w is None or not isinstance(raw_w, (int, float)) or isinstance(raw_w, bool):
            continue  # 缺省字重视为 regular 400
        weight = int(raw_w)
        if weight not in ROLE_WEIGHTS:
            findings.append(
                make(
                    card, "TYPE.WEIGHT_MATRIX",
                    f"fontWeight={weight} 不在三档字重（400/500/700）内",
                    comp.get("id"), severity=P1,
                    expected="fontWeight ∈ {400, 500, 700}",
                    actual=f"fontWeight={weight}",
                    fix_hint="改用 regular/medium/bold 三档（DESIGN.md L1273-1276；L1665 禁第四种字重）",
                )
            )
            continue
        raw_s = styles.get("fontSize")
        if raw_s is None or not isinstance(raw_s, (int, float)) or isinstance(raw_s, bool):
            continue
        size = int(raw_s)
        legal = METRIC_WEIGHTS.get(size) if size in METRIC_WEIGHTS else (
            ROLE_WEIGHTS if size in ROLE_SIZES else None)
        if legal is None:
            continue  # 字号不在矩阵内 → TYPE.FONT_SIZE_STEP 负责
        if weight in legal:
            continue
        if size in METRIC_WEIGHTS:
            message = f"fontSize={size}vp 属 metric 档位，fontWeight 必须为 700"
            expected = f"fontSize={size}vp → fontWeight 700"
        else:
            message = f"fontWeight={weight} 不在 fontSize={size}vp 档位的合法字重集"
            expected = f"fontSize={size}vp → fontWeight ∈ {{400, 500, 700}}"
        findings.append(
            make(
                card, "TYPE.WEIGHT_MATRIX", message,
                comp.get("id"), severity=P1,
                expected=expected,
                actual=f"fontSize={size}vp / fontWeight={weight}",
                fix_hint="按 45 角色矩阵选档（DESIGN.md L1295-1315；metric 档位见 L1319）",
            )
        )
    return findings
