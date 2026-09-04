"""pkg-elements —— 元素合法性包（真值 = DESIGN.md token 层）。

规则：COLOR.* / GRADIENT.* / SCENE.* / VISUAL.CONTRAST / ICON.* / ASSET.* /
CATALOG.* / SHAPE.* / TYPE.* / COPY.* / SEMANTIC.*（场景启发式）。
数据：data/color_profile.json、data/media_icons.json（vendored 渲染工程清单）。
规则模块由 validators/rules/__init__.py 统一按历史顺序导入注册。
"""
