"""COPY.* —— 文案长度规则（E-06）。"""
from __future__ import annotations

import re
from typing import Dict, List

from validators.dsl import GenuiCard
from validators.finding import Finding, P1
from validators.rules import register
from validators.rules._common import make

#: 去除数据绑定与空白后的有效文本
_BIND_RE = re.compile(r"\{\{\s*\$\{.*?\}\s*\}\}")


def _plain_text(value) -> str:
    if not isinstance(value, str):
        return ""
    return _BIND_RE.sub("", value).strip()


@register("COPY.TITLE_MAX_CHARS")
def check_title_max(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """标题类文本（小节标题，字重 500/700 的小型文本）不得超过 titleMaxChars=6（E-06）。"""
    limit = int((contract.get("copy_limits") or {}).get("titleMaxChars", 6))
    findings: List[Finding] = []
    for comp in card.iter_components():
        if comp.get("component") != "Text":
            continue
        content = comp.get("content")
        plain = _plain_text(content)
        if not plain:
            continue
        weight = (comp.get("styles") or {}).get("fontWeight")
        # 标题：500 及以上字重、长度 ≤ 2 行常规句子——这里近似取小字号/中等列表头
        if weight in (500, 700) and len(plain) > limit and "button" not in str(comp.get("id", "")).lower():
            findings.append(
                make(
                    card, "COPY.TITLE_MAX_CHARS",
                    f"标题文案 {len(plain)} 字 > titleMaxChars={limit}",
                    comp.get("id"), severity=P1,
                    expected=f"≤ {limit} 字",
                    actual=f"{len(plain)} 字: {plain}",
                    fix_hint="精简标题",
                )
            )
    return findings


@register("COPY.ACTION_LABEL_MAX_CHARS")
def check_action_label_max(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """按钮/操作文案不得超过 actionLabelMaxChars=4（E-06）。"""
    limit = int((contract.get("copy_limits") or {}).get("actionLabelMaxChars", 4))
    findings: List[Finding] = []
    for comp in card.iter_components():
        if comp.get("component") != "Text":
            continue
        cid = str(comp.get("id", "")).lower()
        is_action = "button" in cid or "action" in cid or comp.get("onClick")
        if not is_action:
            continue
        plain = _plain_text(comp.get("content"))
        if plain and len(plain) > limit:
            findings.append(
                make(
                    card, "COPY.ACTION_LABEL_MAX_CHARS",
                    f"操作文案 {len(plain)} 字 > actionLabelMaxChars={limit}",
                    comp.get("id"), severity=P1,
                    expected=f"≤ {limit} 字",
                    actual=f"{len(plain)} 字: {plain}",
                    fix_hint="精简操作文案",
                )
            )
    return findings
