"""ASSET.* —— 图标/素材规则（E-08）。"""
from __future__ import annotations

from typing import Dict, List

from validators.dsl import GenuiCard
from validators.finding import Finding, P0, P1
from validators.rules import register
from validators.rules._common import make

_REMOTE_SRC_HINTS = ("http://", "https://", "data:")
_EMOJI_HINTS = ("☀", "☁", "⭐", "🚀", "🌧", "☔", "💧", "🔥", "⚡", "⏰", "✅", "❌", "🔔")
_CANDIDATE_KEYS = ("assetCandidates",)


def _asset_candidates(card: GenuiCard) -> List[str]:
    srcs = []
    for key in _CANDIDATE_KEYS:
        items = card.task_spec.get(key) or []
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("src"), str):
                srcs.append(item["src"])
    return srcs


@register("ASSET.EMOJI_ICON")
def check_emoji_icon(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """禁止用 emoji 当图标（E-08 P0）。"""
    findings: List[Finding] = []
    for comp in card.iter_components():
        content = comp.get("content") or ""
        if any(h in content for h in _EMOJI_HINTS):
            findings.append(
                make(
                    card, "ASSET.EMOJI_ICON",
                    f"用 emoji 当图标: {content!r}", comp.get("id"), severity=P0,
                    expected="使用 icon_assets 注册的 SVG 图标",
                    actual=f"emoji: {content!r}",
                    fix_hint="替换为标准化 SVG 图标或短文本",
                )
            )
    return findings


@register("ASSET.REMOTE_SRC")
def check_remote_src(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """禁止网络图（E-08 P0）。"""
    findings: List[Finding] = []
    for comp in card.iter_components():
        src = comp.get("src") or (comp.get("styles") or {}).get("src")
        if isinstance(src, str) and any(src.startswith(h) for h in _REMOTE_SRC_HINTS):
            findings.append(
                make(
                    card, "ASSET.REMOTE_SRC",
                    f"网络图不放行: {src}", comp.get("id"), severity=P0,
                    expected="本地 resources/base/media 资源",
                    actual=src,
                    fix_hint="改用本地已登记素材",
                )
            )
    return findings


@register("ASSET.UNDECLARED")
def check_undeclared_src(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """Image src 必须来自 task-spec assetCandidates（E-08 P1）。"""
    candidates = set(_asset_candidates(card))
    if not candidates:
        return []
    findings: List[Finding] = []
    for comp in card.iter_components():
        if comp.get("component") != "Image":
            continue
        src = comp.get("src")
        if isinstance(src, str) and src not in candidates:
            findings.append(
                make(
                    card, "ASSET.UNDECLARED",
                    f"Image src 不在 assetCandidates: {src}", comp.get("id"), severity=P1,
                    expected="src ∈ assetCandidates",
                    actual=src,
                    fix_hint="改从 assetCandidates 选择",
                )
            )
    return findings


@register("ASSET.HERO_ICON_CONTRACT")
def check_hero_icon(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """56vp hero 视觉（大图标）必须用 icon_weather1 组件契约（E-08 P1）。"""
    findings: List[Finding] = []
    for comp in card.iter_components():
        if comp.get("component") != "Image":
            continue
        styles = comp.get("styles") or {}
        w, h = styles.get("width"), styles.get("height")
        is_hero_size = (str(w).endswith("56") or str(h).endswith("56")) or w == 56 or h == 56
        if is_hero_size:
            if "weather" not in str(comp.get("src", "")).lower() and "dataviz" not in str(comp.get("src", "")).lower():
                findings.append(
                    make(
                        card, "ASSET.HERO_ICON_CONTRACT",
                        f"hero 大图标需用 icon_weather1/数据可视化资产: {comp.get('src')}",
                        comp.get("id"), severity=P1,
                        expected="icon_weather1 | dataviz",
                        actual=str(comp.get("src")),
                        fix_hint="按 hero.visualTextVariant 契约选用",
                    )
                )
    return findings
