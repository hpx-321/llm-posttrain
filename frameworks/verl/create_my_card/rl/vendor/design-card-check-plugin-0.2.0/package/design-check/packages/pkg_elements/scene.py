"""SCENE.* / SEMANTIC.* —— 场景-渐变精确命中（A4 规则版）与语义评审启发式。

- SCENE.GRADIENT_EXACT（E-02d 规则版，L1，程序已证实）：query 关键词 → 场景判定 →
  card-root 背景渐变 stops 必须与「该场景登记预设」完全一致。
  依据：DESIGN.md §background_gradients（L69-171 登记 11 个预设）、正文《Card Background》
  精确映射（L1170）、《Do's and Don'ts》原样使用 stops（L1656）、组件契约 exactSceneMatchOnly（L1119）。
- SEMANTIC.SCENE_GRADIENT_MISMATCH（E-02d，L3 启发式/模型推断）：当 L1 规则版已对该卡
  作出判定（无论 pass/fail）时，本启发式跳过同主题报告，避免双报（机器确定性优先，
  正式语义链路由 LLM 复判/覆盖）。
- SEMANTIC.REDUNDANT_SIGNAL（E-13）：同一指标多处冗余表达。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from validators.dsl import GenuiCard
from validators.finding import Finding, MODEL, P1, P2, PROGRAM
from validators.rules import register
from validators.rules._common import make
from .gradient import _card_gradient, _normalize_colors_from_dsl, _match_preset

#: query 关键词 → 期望场景预设。关键词派生自 DESIGN.md background_gradients 段
#: 场景命名（front-matter L74-83）+ 正文《Card Background》精确映射（L1170）。
SCENE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    # L74 background_gradients.office-focus.scene = 办公效率-专注模式
    "office-focus": ("专注", "办公", "待办"),
    # L75 background_gradients.office-schedule.scene = 办公效率-日程管理
    "office-schedule": ("日程", "会议", "日历", "安排"),
    # L76 background_gradients.device-anti-addiction.scene = 设备管控-防沉迷
    "device-anti-addiction": ("防沉迷", "使用时长"),
    # L77 background_gradients.device-headphone-control.scene = 设备管控-耳机操控
    "device-headphone-control": ("耳机", "播控", "播放"),
    # L78 background_gradients.low-power-mode.scene = 低电量模式
    "low-power-mode": ("低电", "电量"),
    # L79 background_gradients.worry-free-cleanup.scene = 清理无忧
    "worry-free-cleanup": ("清理", "净化", "清理无忧"),
    # L80 background_gradients.weather.scene = 天气；L1170：天气使用 weather 径向渐变
    "weather": ("天气", "温度", "降雨", "雨", "降水"),
    # L81 background_gradients.rainy-weather.scene = 雨天天气；L1170：雨天天气使用 rainy-weather
    "rainy-weather": ("雨", "降雨", "降水"),
    # L82 background_gradients.sports-health.scene = 运动健康；L1170：运动健康使用 sports-health
    "sports-health": ("运动", "健康", "步数", "心率"),
    # L83 background_gradients.sleep.scene = 睡眠
    "sleep": ("睡眠", "睡", "醒来"),
}

#: rainy-weather 与 weather 关键词重叠（雨/降雨/降水），由 weather 命中 + 雨词覆盖得出
_RAINY_WORDS: Tuple[str, ...] = SCENE_KEYWORDS["rainy-weather"]


def detect_scene(query: str) -> Optional[str]:
    """query → 场景预设名。计分制（关键词出现次数求和）；同分时按 DESIGN.md 登记顺序
    （L69-171）优先；命中 weather 且 query 含雨词 → rainy-weather（L81）。判不出返回 None。"""
    if not query:
        return None
    counts: Dict[str, int] = {}
    for preset, kws in SCENE_KEYWORDS.items():
        if preset == "rainy-weather":
            continue  # 由 weather + 雨词覆盖得出
        counts[preset] = sum(query.count(k) for k in kws)
    best: Optional[str] = None
    best_n = 0
    for preset in SCENE_KEYWORDS:
        if preset == "rainy-weather":
            continue
        if counts[preset] > best_n:
            best, best_n = preset, counts[preset]
    if best is None or best_n == 0:
        return None
    if best == "weather" and any(k in query for k in _RAINY_WORDS):
        return "rainy-weather"
    return best


def _expected_stops_desc(contract: Dict, preset: str) -> str:
    spec = (contract.get("gradients") or {}).get(preset) or {}
    stops = spec.get("stops") or []
    return " → ".join(c for _, c in stops) or "(登记缺失)"


@register("SCENE.GRADIENT_EXACT")
def check_gradient_exact(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """L1：query 命中场景时，card-root 渐变 stops 必须精确等于该场景登记预设。

    依据：DESIGN.md L1119 exactSceneMatchOnly / L1170 精确映射 / L1656 原样使用 stops。
    query 缺失或场景判不出 → 跳过；无渐变由 GRADIENT.MISSING_FALLBACK 覆盖。
    """
    expected = detect_scene(query)
    if expected is None:
        return []  # query 缺失或场景判不出 → 跳过
    root = card.find_component("root")
    if root is None:
        return []
    ginfo = _card_gradient(root)
    if ginfo is None:
        return []  # 无渐变：GRADIENT.MISSING_FALLBACK 覆盖
    card_colors = _normalize_colors_from_dsl(ginfo[2])
    if not card_colors:
        return []  # stops 不可解析 → 无法比对，跳过
    chosen = _match_preset(contract, card_colors)
    chosen_base = chosen.split("#", 1)[0] if chosen else None
    if chosen_base == expected:
        return []  # 精确命中
    expected_stops = _expected_stops_desc(contract, expected)
    return [
        make(
            card, "SCENE.GRADIENT_EXACT",
            f"query 场景「{expected}」要求背景渐变 stops 与登记预设完全一致"
            f"（{expected_stops}），实际为 {chosen or '未注册渐变'}",
            "root", severity=P1, evidence_type=PROGRAM,
            expected=f"{expected} 登记 stops: {expected_stops}",
            actual=f"{ginfo[0]} {ginfo[1] or ''} stops {sorted(card_colors)}"
                   f"{'（命中 ' + chosen + '）' if chosen else '（未命中任何预设）'}",
            fix_hint=f"改用 {expected} 场景预设原样 stops（DESIGN.md L1170/L1656）",
        )
    ]


def _l1_determines(card: GenuiCard, contract: Dict, query: str) -> bool:
    """L1 SCENE.GRADIENT_EXACT 是否已对该卡作出判定（场景命中且渐变可比对）。"""
    if detect_scene(query) is None:
        return False
    root = card.find_component("root")
    if root is None:
        return False
    ginfo = _card_gradient(root)
    if ginfo is None:
        return False
    return bool(_normalize_colors_from_dsl(ginfo[2]))


@register("SEMANTIC.SCENE_GRADIENT_MISMATCH")
def check_scene_gradient(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """query 表达的场景应与所选渐变预设一致（E-02d，L3 启发式）。

    L1 规则版（SCENE.GRADIENT_EXACT）已判定（无论 pass/fail）时跳过，避免双报。
    """
    if _l1_determines(card, contract, query):
        return []
    if not query:
        return []
    expected = detect_scene(query)
    if expected is None:
        return []
    root = card.find_component("root")
    if root is None:
        return []
    ginfo = _card_gradient(root)
    if ginfo is None:
        return []
    card_colors = _normalize_colors_from_dsl(ginfo[2])
    chosen = _match_preset(contract, card_colors)
    if chosen and chosen.split("#", 1)[0] != expected:
        name = chosen
        # 排除天气场景下 weather/rainy-weather 的合法就近
        if expected in ("weather", "rainy-weather") and chosen in ("weather", "rainy-weather"):
            return []
        return [
            make(
                card, "SEMANTIC.SCENE_GRADIENT_MISMATCH",
                f"query 表达「{expected}」但用了「{name}」渐变",
                "root", severity=P1, evidence_type=MODEL,
                expected=expected,
                actual=name,
                fix_hint=f"改用 {expected} 场景渐变",
            )
        ]
    return []


@register("SEMANTIC.REDUNDANT_SIGNAL")
def check_redundant_signal(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """同一指标三处表达的启发式检测（E-13）。"""
    # 收集状态词 + 大数字 + 说明行
    status_words = {"超时", "已用", "完成", "剩余", "正常", "告警"}
    big_numbers = 0
    status_pill = 0
    has_aux_line = 0
    texts = []
    for comp in card.iter_components():
        if comp.get("component") != "Text":
            continue
        content = comp.get("content") or ""
        styles = comp.get("styles") or {}
        texts.append(content)
        if isinstance(styles.get("fontSize"), (int, float)) and styles["fontSize"] >= 24:
            big_numbers += 1
        if any(w in str(content) for w in status_words):
            status_pill += 1
        if isinstance(styles.get("fontSize"), (int, float)) and styles["fontSize"] <= 12:
            has_aux_line += 1
    if big_numbers >= 1 and status_pill >= 1 and has_aux_line >= 2:
        return [
            make(
                card, "SEMANTIC.REDUNDANT_SIGNAL",
                "同一指标被状态胶囊 + 大数字 + 辅助行多处冗余表达",
                severity=P2, evidence_type=MODEL,
                expected="单一主信号 + 必要辅助",
                actual=f"big_number={big_numbers}, status={status_pill}, aux_lines={has_aux_line}",
                fix_hint="按 DESIGN.md content_pruning 收敛为一个主表达",
            )
        ]
    return []
