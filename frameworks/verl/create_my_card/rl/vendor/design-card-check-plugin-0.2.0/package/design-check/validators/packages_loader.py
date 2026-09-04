"""检测包装载器（Idea2-WP-B 2026-08-26）。

「发现已装包 → applicability 可见 → 执行」的最小形态：

- 扫描 ``packages/*/manifest.yaml``，产出可用包清单与规则归属；
- manifest 是包身份真值：YAML 解析失败 / 必填字段缺失 / 与注册表不一致
  均**显式抛错**（不做静默降级）；
- applicability（card_size / inputs）目前是声明口径，实际门禁仍由规则
  自身逻辑兜底（如 layout_2x4._slots 的 card_size 检查）——本层只做
  声明 + 装载器可见，不改判定行为；
- 一致性断言（assert_manifest_consistency）：registry: rules 的包，
  manifest 规则清单 ⊆ 注册表且并集 == 注册表全量（防漂移）；registry:
  static 的包对照 rule_category 的静态规则列表逐包相等。

PyYAML 缺失时降级到内置 manifest 子集解析器（_parse_manifest_yaml）——五包
manifest 实际仅用嵌套 dict / list / 标量 / 注释 / 引号字符串子集，解析后跑
_load_yaml 既有结构断言兜底；解析结果若与 YAML 语义不符会在一致性断言中暴露。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

_REQUIRED_FIELDS = ("id", "version", "description", "rules", "applicability", "depends")


# ---------------------------------------------------------------------------
# 无 PyYAML 环境的降级解析（Idea6-WP-R1 2026-08-27）
# ---------------------------------------------------------------------------

def _strip_comment(line: str) -> str:
    """去掉行尾注释（引号外的第一个 # 起）；全行注释返回空串。"""
    out: list = []
    quote = ""
    prev = ""
    for ch in line:
        if quote:
            if ch == quote and prev != "\\":
                quote = ""
            out.append(ch)
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
        prev = ch
    return "".join(out).rstrip()


def _parse_scalar(text: str):
    """标量值：flow 列表 [a, b] → list[str]；引号串去引号；其余原样保留为 str。

    刻意不做 int/float/bool 推断：五包 manifest 的值全部是标识符/版本号/
    描述文本，无数值真值；保守保 str 避免误转（如 card_size 的 2x2）。
    """
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [] if not inner else [_parse_scalar(p) for p in inner.split(",")]
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def _parse_block(lines, i, indent):
    """递归缩进解析。lines 元素为 (indent, content)；返回 (value, next_i)。"""
    is_list = lines[i][1].startswith("- ")
    if is_list:
        seq: list = []
        while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
            seq.append(_parse_scalar(lines[i][1][2:]))
            i += 1
        return seq, i
    mapping: Dict[str, object] = {}
    while i < len(lines):
        ind, content = lines[i]
        if ind < indent:
            break
        key, _, rest = content.partition(":")
        rest = rest.strip()
        i += 1
        if rest:
            mapping[key.strip()] = _parse_scalar(rest)
        elif i < len(lines) and lines[i][0] > ind:
            mapping[key.strip()], i = _parse_block(lines, i, lines[i][0])
        else:
            mapping[key.strip()] = None
    return mapping, i


def _parse_manifest_yaml(text: str) -> Dict:
    """内置 YAML 子集解析器：顶层级映射 + 嵌套 dict/list/标量（无锚点/多行块）。"""
    lines = []
    for raw in text.splitlines():
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        lines.append((indent, stripped.strip()))
    value, i = _parse_block(lines, 0, lines[0][0]) if lines else (None, 0)
    if isinstance(value, dict) and i >= len(lines):
        return value
    raise ValueError("manifest 子集解析失败：顶层必须是完整闭合的映射")


def _packages_root() -> Path:
    """packages/ 目录（design-check/packages，与本文件同根）。"""
    return Path(__file__).resolve().parent.parent / "packages"


def _parse_via_yaml(path: Path) -> Dict:
    import yaml  # PyYAML
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"manifest 解析失败: {path}: {exc}") from exc
    return data


def _load_yaml(path: Path) -> Dict:
    # PyYAML 可用 → safe_load（开发态现状）；缺失 → 内置子集解析器降级
    # （分发态 npm bundle 不执行 pip install，manifest 是单一真值不转 JSON）。
    try:
        import yaml  # noqa: F401
        has_yaml = True
    except ImportError:
        has_yaml = False
    if has_yaml:
        data = _parse_via_yaml(path)
    else:
        try:
            data = _parse_manifest_yaml(path.read_text(encoding="utf-8"))
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"manifest 解析失败: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"manifest 顶层必须是映射: {path}")
    for field in _REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"manifest 缺少必填字段 {field!r}: {path}")
    if not data["rules"]:
        raise ValueError(f"manifest rules 不能为空: {path}")
    return data


def load_manifests(refresh: bool = False) -> List[Dict]:
    """扫描 packages/*/manifest.yaml，按包 id 排序返回清单（带 _dir 指回包目录）。"""
    cached = globals().get("_MANIFEST_CACHE")
    if cached is not None and not refresh:
        return cached
    root = _packages_root()
    if not root.is_dir():
        raise FileNotFoundError(f"packages 目录不存在: {root}")
    out: List[Dict] = []
    for pkg_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        manifest = pkg_dir / "manifest.yaml"
        if not manifest.is_file():
            continue  # 非包目录（如 __pycache__）跳过
        data = _load_yaml(manifest)
        if data["id"] != pkg_dir.name.replace("_", "-"):
            raise ValueError(
                f"manifest id {data['id']!r} 与目录名 {pkg_dir.name!r} 不一致: {manifest}")
        data = dict(data)
        data["_dir"] = pkg_dir
        out.append(data)
    if not out:
        raise FileNotFoundError(f"packages 下未发现任何 manifest.yaml: {root}")
    out.sort(key=lambda m: m["id"])
    globals()["_MANIFEST_CACHE"] = out
    return out


def packages_meta() -> List[Dict[str, object]]:
    """meta.packages 用包摘要（id / version / 规则数 / applicability / depends）。"""
    return [
        {
            "id": m["id"],
            "version": m.get("version", ""),
            "rules": len(m["rules"]),
            "applicability": m["applicability"],
            "depends": m["depends"],
        }
        for m in load_manifests()
    ]


def rule_owner() -> Dict[str, str]:
    """rule_id → 包 id 归属表（同一 rule_id 多包声明时报错）。"""
    owner: Dict[str, str] = {}
    for m in load_manifests():
        for rid in m["rules"]:
            if rid in owner and owner[rid] != m["id"]:
                raise ValueError(f"规则 {rid} 同时声明于 {owner[rid]} 与 {m['id']}")
            owner[rid] = m["id"]
    return owner


def assert_manifest_consistency() -> None:
    """manifest ↔ 注册表一致性断言（启动时 / 单测调用，防漂移）。

    - registry: rules 的包：manifest rules ⊆ validators.rules._RULES，
      且各包并集 == _RULES 全量（一条不多、一条不少）；
    - registry: static 的包：对照 rule_category 静态列表逐包相等
      （pkg-l2-visual → GEOMETRY_RULES ∪ RECONCILE_RULES）。
    """
    from .rule_category import GEOMETRY_RULES, RECONCILE_RULES
    from .rules import _RULES

    manifests = load_manifests()
    registry_union: set = set()
    static_union: set = set()
    for m in manifests:
        declared = set(m["rules"])
        if m.get("registry") == "rules":
            unknown = declared - set(_RULES)
            if unknown:
                raise ValueError(
                    f"manifest {m['id']} 声明了注册表中不存在的规则: {sorted(unknown)}")
            registry_union |= declared
        else:  # static
            static_union |= declared
    missing = set(_RULES) - registry_union
    if missing:
        raise ValueError(f"注册表规则未被任何 manifest 声明: {sorted(missing)}")
    l2_expected = GEOMETRY_RULES | RECONCILE_RULES
    if static_union != l2_expected:
        raise ValueError(
            f"pkg-l2-visual manifest 规则集与静态列表不一致: "
            f"多 {sorted(static_union - l2_expected)} / 少 {sorted(l2_expected - static_union)}")
