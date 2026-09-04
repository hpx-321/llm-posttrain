---
version: alpha
name: HarmonyOS A2UI Service Card
description: HarmonyOS 桌面 widget 服务卡片 2×4（320×160vp 宽卡）的设计系统——一眼扫读、一个主信息组至多一个辅助信息组、浅层任务入口；本文件是 2×4 产物的检验金标准，布局契约以标准 Layout 组合规则为准（权威来源：Pixso 布局抽象 item-id 60:280），2×2 的检验仍以 DESIGN.md 为准。
colors:
  brand: "#0A59F7FF"
  warning: "#E84026FF"
  alert: "#ED6F21FF"
  confirm: "#64BB5CFF"
  font_primary: "#000000E5"
  font_secondary: "#00000099"
  font_tertiary: "#00000066"
  font_fourth: "#00000033"
  font_emphasize: "#0A59F7FF"
  font_on_primary: "#FFFFFFFF"
  font_on_secondary: "#FFFFFF99"
  font_on_tertiary: "#FFFFFF66"
  font_on_fourth: "#FFFFFF33"
  icon_primary: "#000000E5"
  icon_secondary: "#00000099"
  icon_tertiary: "#00000066"
  icon_fourth: "#00000033"
  icon_emphasize: "#0A59F7FF"
  icon_sub_emphasize: "#0A59F766"
  icon_on_primary: "#FFFFFFFF"
  icon_on_secondary: "#FFFFFF99"
  icon_on_tertiary: "#FFFFFF66"
  icon_on_fourth: "#FFFFFF33"
  background_primary: "#FFFFFFFF"
  background_secondary: "#F1F3F5FF"
  background_tertiary: "#E5E5EAFF"
  background_fourth: "#D1D1D6FF"
  background_emphasize: "#0A59F7FF"
  comp_foreground_primary: "#000000FF"
  comp_background_primary: "#FFFFFFFF"
  comp_background_primary_contrary: "#FFFFFFFF"
  comp_background_gray: "#F1F3F5FF"
  comp_background_secondary: "#00000019"
  comp_background_list_card: "#FFFFFFFF"
  comp_background_tertiary: "#0000000C"
  comp_background_emphasize: "#0A59F7FF"
  comp_background_neutral: "#000000FF"
  comp_emphasize_secondary: "#0A59F733"
  comp_emphasize_tertiary: "#0A59F719"
  comp_divider: "#00000033"
  comp_common_contrary: "#FFFFFFFF"
  comp_background_focus: "#F1F3F5FF"
  comp_focused_primary: "#000000E5"
  comp_focused_secondary: "#00000099"
  comp_focused_tertiary: "#00000066"
  progress_ring_track: "#00000019"
  interactive_hover: "#0000000C"
  interactive_pressed: "#00000019"
  interactive_focus: "#0A59F7FF"
  interactive_active: "#0A59F7FF"
  interactive_select: "#0A59F733"
  interactive_click: "#00000019"
  comp_background_primary_transparent: "#FFFFFF00"
  scene_element_office_ink: "#0A59F7FF"
  scene_element_office_surface: "#0A59F719"
  scene_element_headphone_lime: "#A5D61DFF"
  scene_element_low_light: "#F9A01EFF"
  scene_weather_start: "#317AF7FF"
  scene_weather_end: "#46B1E3FF"
  scene_rainy_start: "#46484DFF"
  scene_rainy_end: "#467794FF"
  scene_sleep_start: "#AC49F5FF"
  scene_sleep_end: "#C386F0FF"
background_gradients:
  cssVariableNaming: "--bg-gradient-{preset-name}"
  baseLayer: "{colors.comp_background_primary}"
  composition: base-color-then-gradient-overlay
  office-focus:
    scene: 办公效率-专注模式
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: light-overlay-gradient, primaryHue: "#0A59F7FF" }
    stops:
      - { offset: 0%, color: "#0A59F719" }
      - { offset: 100%, color: "#FFFFFF00" }
    opaqueEquivalent:
      base: "{colors.comp_background_primary}"
      note: 基底为纯白宿主时的预合成等效表达（实现侧 flatten 写法）；仅适用 light 白宿主，暗色宿主不成立
      stops:
        - { offset: 0%, color: "#E7EFFEFF" }
        - { offset: 100%, color: "#FFFFFFFF" }
  office-schedule:
    scene: 办公效率-日程管理
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: light-overlay-gradient, primaryHue: "#E84026FF" }
    stops:
      - { offset: 0%, color: "#E8402619" }
      - { offset: 100%, color: "#FFFFFF00" }
    opaqueEquivalent:
      base: "{colors.comp_background_primary}"
      note: 基底为纯白宿主时的预合成等效表达（实现侧 flatten 写法）；仅适用 light 白宿主，暗色宿主不成立
      stops:
        - { offset: 0%, color: "#FDECEAFF" }
        - { offset: 100%, color: "#FFFFFFFF" }
  device-anti-addiction:
    scene: 设备管控-防沉迷
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: light-overlay-gradient, primaryHue: "#0A59F7FF" }
    stops:
      - { offset: 0%, color: "#00000019" }
      - { offset: 100%, color: "#FFFFFF00" }
    opaqueEquivalent:
      base: "{colors.comp_background_primary}"
      note: 基底为纯白宿主时的预合成等效表达（实现侧 flatten 写法）；仅适用 light 白宿主，暗色宿主不成立
      stops:
        - { offset: 0%, color: "#E6E6E6FF" }
        - { offset: 100%, color: "#FFFFFFFF" }
  device-headphone-control:
    scene: 设备管控-耳机操控
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: light-overlay-gradient, primaryHue: "#64BB5CFF" }
    stops:
      - { offset: 0%, color: "#64BB5C19" }
      - { offset: 100%, color: "#FFFFFF00" }
    opaqueEquivalent:
      base: "{colors.comp_background_primary}"
      note: 基底为纯白宿主时的预合成等效表达（实现侧 flatten 写法）；仅适用 light 白宿主，暗色宿主不成立
      stops:
        - { offset: 0%, color: "#F0F8EFFF" }
        - { offset: 100%, color: "#FFFFFFFF" }
  low-power-mode:
    scene: 低电量模式
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: light-overlay-gradient, primaryHue: "#F9A01EFF" }
    stops:
      - { offset: 0%, color: "#F9A01E19" }
      - { offset: 100%, color: "#FFFFFF00" }
    opaqueEquivalent:
      base: "{colors.comp_background_primary}"
      note: 基底为纯白宿主时的预合成等效表达（实现侧 flatten 写法）；仅适用 light 白宿主，暗色宿主不成立
      stops:
        - { offset: 0%, color: "#FEF6E9FF" }
        - { offset: 100%, color: "#FFFFFFFF" }
  worry-free-cleanup:
    scene: 清理无忧
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: light-overlay-gradient, primaryHue: "#F9A01EFF" }
    stops:
      - { offset: 0%, color: "#0A59F719" }
      - { offset: 100%, color: "#FFFFFF00" }
    opaqueEquivalent:
      base: "{colors.comp_background_primary}"
      note: 基底为纯白宿主时的预合成等效表达（实现侧 flatten 写法）；仅适用 light 白宿主，暗色宿主不成立
      stops:
        - { offset: 0%, color: "#E7EFFEFF" }
        - { offset: 100%, color: "#FFFFFFFF" }
  weather:
    scene: 天气
    type: radial
    center: top-center
    radius: farthest-corner
    buttonColorContext: { backgroundClass: colored-gradient, primaryHue: "#317AF7FF" }
    stops:
      - { offset: 0%, color: "#317AF7FF" }
      - { offset: 100%, color: "#46B1E3FF" }
  rainy-weather:
    scene: 雨天天气
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: colored-gradient, primaryHue: "#467794FF" }
    stops:
      - { offset: 0%, color: "#46484DFF" }
      - { offset: 100%, color: "#467794FF" }
  sports-health:
    scene: 运动健康
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: colored-gradient, primaryHue: "#ED6F21FF" }
    stops:
      - { offset: 0%, color: "#ED6F21FF" }
      - { offset: 100%, color: "#F9A01EFF" }
  sleep:
    scene: 睡眠
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: colored-gradient, primaryHue: "#AC49F5FF" }
    stops:
      - { offset: 0%, color: "#AC49F5FF" }
      - { offset: 100%, color: "#C386F0FF" }
  general-fallback:
    scene: 通用兜底
    type: linear
    direction: top-to-bottom
    angle: 180deg
    buttonColorContext: { backgroundClass: light-overlay-gradient, primaryHue: "#0A59F7FF" }
    stops:
      - { offset: 0%, color: "#0A59F719" }
      - { offset: 100%, color: "#FFFFFF00" }
    opaqueEquivalent:
      base: "{colors.comp_background_primary}"
      note: 基底为纯白宿主时的预合成等效表达（实现侧 flatten 写法）；仅适用 light 白宿主，暗色宿主不成立
      stops:
        - { offset: 0%, color: "#E7EFFEFF" }
        - { offset: 100%, color: "#FFFFFFFF" }
button_color_rules:
  appliesTo: all-buttons-on-gradient-card-backgrounds
  resolveFrom: "{background_gradients.*.buttonColorContext}"
  light-overlay-gradient:
    backgroundColor: card-primary-hue-at-10-percent
    foregroundColor: card-primary-hue-at-100-percent
    alphaHex: "19"
    preferredExamples:
      blue: { backgroundColor: "#0A59F719", foregroundColor: "#0A59F7FF" }
      red: { backgroundColor: "#E8402619", foregroundColor: "#E84026FF" }
      black: { backgroundColor: "#00000019", foregroundColor: "#000000FF" }
      green: { backgroundColor: "#64BB5C19", foregroundColor: "#64BB5CFF" }
      orange: { backgroundColor: "#F9A01E19", foregroundColor: "#F9A01EFF" }
    otherHues: derive-the-same-10-percent-and-100-percent-pair-from-card-primary-hue
  colored-gradient:
    backgroundColor: "#FFFFFFFF"
    foregroundColor: card-primary-hue-at-100-percent
  fallbackAllowed: false
card_element_color_recommendations:
  appliesTo: decorative-elements-status-dataviz-and-actions
  bodyTextRule: keep-font-primary-and-font-secondary
  office-focus:
    scenes: [office-focus]
    surface: "#0A59F719"
    primary: "#0A59F7FF"
    text: ["{colors.font_primary}", "{colors.font_secondary}"]
  office-schedule:
    scenes: [office-schedule]
    surface: "#E8402619"
    primary: "#E84026FF"
    text: ["{colors.font_primary}", "{colors.font_secondary}"]
  device-anti-addiction:
    scenes: [device-anti-addiction]
    surface: "#0A59F719"
    primary: "#0A59F7FF"
    text: ["{colors.font_primary}", "{colors.font_secondary}"]
  headphone-control:
    scenes: [device-headphone-control]
    primary: "#64BB5CFF"
    secondary: "#A5D61DFF"
  low-power-mode:
    scenes: [low-power-mode]
    primary: "#F9A01EFF"
  worry-free-cleanup:
    scenes: [worry-free-cleanup]
    primary: "#F9A01EFF"
    secondary: "#64BB5CFF"
  weather:
    scenes: [weather]
    primary: "#FFFFFFFF"
    secondary: "#FFFFFF99"
  rainy-weather:
    scenes: [rainy-weather]
    primary: "#FFFFFFFF"
    secondary: "#FFFFFF99"
  sports-health:
    scenes: [sports-health]
    primary: "#FFFFFFFF"
    secondary: "#FFFFFF99"
  sleep:
    scenes: [sleep]
    primary: "#FFFFFFFF"
    secondary: "#FFFFFF99"
themes:
  dark:
    brand: "#317AF7FF"
    warning: "#D94838FF"
    alert: "#DB6B42FF"
    confirm: "#5BA854FF"
    font_primary: "#FFFFFFE5"
    font_secondary: "#FFFFFF99"
    font_tertiary: "#FFFFFF66"
    font_fourth: "#FFFFFF33"
    font_emphasize: "#317AF7FF"
    font_on_primary: "#FFFFFFFF"
    font_on_secondary: "#FFFFFF99"
    font_on_tertiary: "#FFFFFF66"
    font_on_fourth: "#FFFFFF33"
    icon_primary: "#FFFFFFE5"
    icon_secondary: "#FFFFFF99"
    icon_tertiary: "#FFFFFF66"
    icon_fourth: "#FFFFFF33"
    icon_emphasize: "#317AF7FF"
    icon_sub_emphasize: "#317AF766"
    icon_on_primary: "#FFFFFFFF"
    icon_on_secondary: "#FFFFFF99"
    icon_on_tertiary: "#FFFFFF66"
    icon_on_fourth: "#FFFFFF33"
    background_primary: "#E5E5E5FF"
    background_secondary: "#191A1CFF"
    background_tertiary: "#202224FF"
    background_fourth: "#2E3033FF"
    background_emphasize: "#317AF7FF"
    comp_foreground_primary: "#E5E5E5FF"
    comp_background_primary: "#202224FF"
    comp_background_primary_contrary: "#E5E5E5FF"
    comp_background_gray: "#E5E5EAFF"
    comp_background_secondary: "#FFFFFF19"
    comp_background_list_card: "#FFFFFF19"
    progress_ring_track: "#FFFFFF19"
    comp_background_tertiary: "#FFFFFF19"
    comp_background_emphasize: "#317AF7FF"
    comp_background_neutral: "#FFFFFFFF"
    comp_emphasize_secondary: "#317AF733"
    comp_emphasize_tertiary: "#317AF719"
    comp_divider: "#FFFFFF33"
    comp_common_contrary: "#000000FF"
    comp_background_focus: "#000000FF"
    comp_focused_primary: "#FFFFFFE5"
    comp_focused_secondary: "#FFFFFF99"
    comp_focused_tertiary: "#FFFFFF66"
    interactive_hover: "#FFFFFF0C"
    interactive_pressed: "#FFFFFF19"
    interactive_focus: "#317AF7FF"
    interactive_active: "#317AF7FF"
    interactive_select: "#317AF733"
    interactive_click: "#FFFFFF19"
typography:
  # Display tier — 56 / 48 / 38
  display-l-regular: { fontFamily: HarmonyOS Sans SC, fontSize: 56vp, fontWeight: 400, letterSpacing: -0.01em }
  display-l-medium:  { fontFamily: HarmonyOS Sans SC, fontSize: 56vp, fontWeight: 500, letterSpacing: -0.01em }
  display-l-bold:    { fontFamily: HarmonyOS Sans SC, fontSize: 56vp, fontWeight: 700, letterSpacing: -0.01em }
  display-m-regular: { fontFamily: HarmonyOS Sans SC, fontSize: 48vp, fontWeight: 400, letterSpacing: -0.01em }
  display-m-medium:  { fontFamily: HarmonyOS Sans SC, fontSize: 48vp, fontWeight: 500, letterSpacing: -0.01em }
  display-m-bold:    { fontFamily: HarmonyOS Sans SC, fontSize: 48vp, fontWeight: 700, letterSpacing: -0.01em }
  display-s-regular: { fontFamily: HarmonyOS Sans SC, fontSize: 38vp, fontWeight: 400 }
  display-s-medium:  { fontFamily: HarmonyOS Sans SC, fontSize: 38vp, fontWeight: 500 }
  display-s-bold:    { fontFamily: HarmonyOS Sans SC, fontSize: 38vp, fontWeight: 700 }

  # Metric tier — 40 / 32；40vp 用于全卡唯一绝对主数值，32vp 用于双值或较长主数值（2×4 主数值常规 20-32vp）
  metric-primary: { fontFamily: HarmonyOS Sans SC, fontSize: 40vp, fontWeight: 700, letterSpacing: -0.01em }
  metric-primary-with-support: { fontFamily: HarmonyOS Sans SC, fontSize: 32vp, fontWeight: 700, letterSpacing: -0.01em }

  # Title tier — 30 / 24 / 20
  title-l-regular:   { fontFamily: HarmonyOS Sans SC, fontSize: 30vp, fontWeight: 400 }
  title-l-medium:    { fontFamily: HarmonyOS Sans SC, fontSize: 30vp, fontWeight: 500 }
  title-l-bold:      { fontFamily: HarmonyOS Sans SC, fontSize: 30vp, fontWeight: 700 }
  title-m-regular:   { fontFamily: HarmonyOS Sans SC, fontSize: 24vp, fontWeight: 400 }
  title-m-medium:    { fontFamily: HarmonyOS Sans SC, fontSize: 24vp, fontWeight: 500 }
  title-m-bold:      { fontFamily: HarmonyOS Sans SC, fontSize: 24vp, fontWeight: 700 }
  title-s-regular:   { fontFamily: HarmonyOS Sans SC, fontSize: 20vp, fontWeight: 400 }
  title-s-medium:    { fontFamily: HarmonyOS Sans SC, fontSize: 20vp, fontWeight: 500 }
  title-s-bold:      { fontFamily: HarmonyOS Sans SC, fontSize: 20vp, fontWeight: 700 }

  # Subtitle tier — 18 / 16 / 14
  subtitle-l-regular: { fontFamily: HarmonyOS Sans SC, fontSize: 18vp, fontWeight: 400 }
  subtitle-l-medium:  { fontFamily: HarmonyOS Sans SC, fontSize: 18vp, fontWeight: 500 }
  subtitle-l-bold:    { fontFamily: HarmonyOS Sans SC, fontSize: 18vp, fontWeight: 700 }
  subtitle-m-regular: { fontFamily: HarmonyOS Sans SC, fontSize: 16vp, fontWeight: 400 }
  subtitle-m-medium:  { fontFamily: HarmonyOS Sans SC, fontSize: 16vp, fontWeight: 500 }
  subtitle-m-bold:    { fontFamily: HarmonyOS Sans SC, fontSize: 16vp, fontWeight: 700 }
  subtitle-s-regular: { fontFamily: HarmonyOS Sans SC, fontSize: 14vp, fontWeight: 400 }
  subtitle-s-medium:  { fontFamily: HarmonyOS Sans SC, fontSize: 14vp, fontWeight: 500 }
  subtitle-s-bold:    { fontFamily: HarmonyOS Sans SC, fontSize: 14vp, fontWeight: 700 }

  # Body tier — 16 / 14 / 12
  body-l-regular:     { fontFamily: HarmonyOS Sans SC, fontSize: 16vp, fontWeight: 400 }
  body-l-medium:      { fontFamily: HarmonyOS Sans SC, fontSize: 16vp, fontWeight: 500 }
  body-l-bold:        { fontFamily: HarmonyOS Sans SC, fontSize: 16vp, fontWeight: 700 }
  body-m-regular:     { fontFamily: HarmonyOS Sans SC, fontSize: 14vp, fontWeight: 400 }
  body-m-medium:      { fontFamily: HarmonyOS Sans SC, fontSize: 14vp, fontWeight: 500 }
  body-m-bold:        { fontFamily: HarmonyOS Sans SC, fontSize: 14vp, fontWeight: 700 }
  body-s-regular:     { fontFamily: HarmonyOS Sans SC, fontSize: 12vp, fontWeight: 400 }
  body-s-medium:      { fontFamily: HarmonyOS Sans SC, fontSize: 12vp, fontWeight: 500 }
  body-s-bold:        { fontFamily: HarmonyOS Sans SC, fontSize: 12vp, fontWeight: 700 }

  # Caption tier — 12 / 10 / 8
  caption-l-regular:  { fontFamily: HarmonyOS Sans SC, fontSize: 12vp, fontWeight: 400 }
  caption-l-medium:   { fontFamily: HarmonyOS Sans SC, fontSize: 12vp, fontWeight: 500 }
  caption-l-bold:     { fontFamily: HarmonyOS Sans SC, fontSize: 12vp, fontWeight: 700 }
  caption-m-regular:  { fontFamily: HarmonyOS Sans SC, fontSize: 10vp, fontWeight: 400 }
  caption-m-medium:   { fontFamily: HarmonyOS Sans SC, fontSize: 10vp, fontWeight: 500 }
  caption-m-bold:     { fontFamily: HarmonyOS Sans SC, fontSize: 10vp, fontWeight: 700 }
  caption-s-regular:  { fontFamily: HarmonyOS Sans SC, fontSize:  8vp, fontWeight: 400 }
  caption-s-medium:   { fontFamily: HarmonyOS Sans SC, fontSize:  8vp, fontWeight: 500 }
  caption-s-bold:     { fontFamily: HarmonyOS Sans SC, fontSize:  8vp, fontWeight: 700 }
rounded:
  corner_radius_none: 0
  corner_radius_level1: 2vp
  corner_radius_level2: 4vp
  corner_radius_level3: 6vp
  corner_radius_level4: 8vp
  corner_radius_level5: 10vp
  corner_radius_level6: 12vp
  corner_radius_level7: 14vp
  corner_radius_level8: 16vp
  corner_radius_level9: 18vp
  corner_radius_level10: 20vp
  corner_radius_level11: 22vp
  corner_radius_level12: 24vp
  corner_radius_level16: 32vp
  capsule_full_action: 70vp
spacing:
  xxs: 2vp
  xs: 4vp
  sm: 6vp
  md: 8vp
  lg: 12vp
  xl: 16vp
  xxl: 24vp
  safe-margin: 12vp
icon_assets:
  sourceDirectory: resource/media
  catalog: resource/icons/catalog.json
  normalizedDirectory: resource/icons/normalized
  selection:
    functionalOrStatusIconSource: catalog-only
    semanticMatch: exact
    missingExactMatch: omit-icon-and-use-short-text
    allowApproximateSemanticSubstitution: false
    allowHandDrawnIconSvg: false
    allowEmojiAsIcon: false
    allowExternalIconLibrary: false
  rendering:
    htmlMode: inline-normalized-svg
    requiredAttribute: data-resource-icon
    monochromeColor: currentColor
    monochromeToken: "{colors.icon_*} / {themes.dark.icon_*}"
    multicolorEligibility: catalog-approved-only
  heroWeatherIcon:
    canonicalId: icon_weather1
    catalogEligibility: approved
    renderedSize: 56vp
    requiredAttribute: { data-hero-visual: weather-icon }
    usage: hero-weather-only
    standardLinearIconUpscaleAllowed: false
    preserveGeometry: true
  sizes:
    title-leading-icon-leading: 12vp
    title-icon-trailing-2x4: 16vp
    ring-unit-center-icon: 24vp
    hero-visual: 56vp
  svgClassification:
    resourceIconAttribute: data-resource-icon
    datavizAttribute: data-dataviz
    unclassifiedInlineSvgAllowed: false
    # `data-dataviz` 的值必须是下列已注册组件 id 之一；任何其它取值视为手绘数据可视化，机器按 unregistered_dataviz 拒收。
    allowedDatavizValues: [display-ring, paired-data-ring, linear-progress]
layout_slots:
  standardSource:
    authority: "Pixso 布局抽象（item-id 60:280，2026-08 定稿，18 张标准布局卡）"
    snapshot: "Design-guide/docs/pixso-layout-abstraction.md"
    precedence: "布局几何以该布局抽象为唯一权威；历史闭合式 132+12+152 / 190+12+86 / 112+16+160 与 padding 16 档废止"
  canvas:
    "2x4":
      width: 320vp
      height: 160vp
      root:
        component: Stack
        width: 320
        height: 160
        borderRadius: 20
        clip: true
        background: linearGradient-required
        linearGradientAngleDefault: 180
      contentRoot:
        component: "Column | Row"
        size: matchParent
        padding: 12
        paddingNote: "固定 12vp（布局抽象全量采用）；禁止 14/16/18/20"
      safeArea:
        padding12: { width: 296vp, height: 136vp }
      layoutMode: standard-layout-composition
  rootStructures:
    bare: { titleBar: none, content: "296×136", direction: horizontal-only }
    titledCompact: { titleBar: "296×17", gap: 4, content: "296×115" }
    titledRegular: { titleBar: "296×20", gap: 8, content: "296×108" }
    titledAction: { titleBar: "296×20", gap: 4, content: "296×72", actionGap: 4, capsule: "140×36", verticalAlign: top }
  splitRules:
    rowSplitFull: { gap: 12, widths: { 2: 142, 3: 90.67, 4: 65 }, formula: "(296-12*(n-1))/n", note: "bare 全量与整行三分/四分" }
    rowSplitContent: { gap: 8, widths296: { 2: 144, 3: 93.33, 4: 68 }, widths144: { 2: 68 }, note: "titled 二分与所有次级分栏" }
    columnSplit: { gap: 8, rows115: { 2: 53.5, 3: 33 }, rows108: { 2: 50 }, note: "content 内纵向分栏" }
    gridG4: { gap: 8, cell: "144×50", note: "2×2 网格，仅限 content 108" }
    radiusPolicy: "布局仅指示槽位（尺寸/分栏/gap），不登记内容区域圆角；圆角由组件契约与 rounded token 决定"
  standardVariants:
    bare-H2: { root: bare, structure: "H gap12 -> 2x[142x136]" }
    bare-H3: { root: bare, structure: "H gap12 -> 3x[90.67x136]" }
    bare-H4: { root: bare, structure: "H gap12 -> 4x[65x136]" }
    tc-S1: { root: titledCompact, structure: "1x[296x115]" }
    tc-S1-list3: { root: titledCompact, structure: "V gap8 -> 3x[296x33]" }
    tc-H2: { root: titledCompact, structure: "H gap8 -> 2x[144x115]" }
    tc-H2-V2: { root: titledCompact, structure: "left 144x115 + right V gap8 -> 2x[144x53.5]" }
    tc-H2-H2: { root: titledCompact, structure: "left 144x115 + right H gap8 -> 2x[68x115]" }
    tc-H2-V2H2: { root: titledCompact, structure: "left 144x115 + right V gap8 -> 144x53.5 + H gap8 -> 2x[68x53.5]" }
    tc-H2-G4: { root: titledCompact, structure: "left 144x115 + right V gap8 -> 2 rows[144x53.5] each H gap8 -> 2x[68x53.5]" }
    tr-H3: { root: titledRegular, structure: "H gap12 -> 3x[90.67x108]" }
    tr-H4: { root: titledRegular, structure: "H gap12 -> 4x[65x108]" }
    tr-G4: { root: titledRegular, structure: "V gap8 -> 2 rows each H gap8 -> 2x[144x50]" }
    tr-V2: { root: titledRegular, structure: "V gap8 -> 2x[296x50]" }
    tr-V2-H2: { root: titledRegular, structure: "top 296x50 + bottom H gap8 -> 2x[144x50]" }
    tr-V2-H3: { root: titledRegular, structure: "top 296x50 + bottom H gap8 -> 3x[93.33x50]" }
    tr-V2-H4: { root: titledRegular, structure: "top 296x50 + bottom H gap8 -> 4x[68x50]" }
    ta-S1: { root: titledAction, structure: "content 296x72 + capsule 140x36" }
  layoutRouting:
    select: exactly-one-standard-variant-per-card
    order:
      - "是否需要标题行：并列同构且无标题语义 -> bare；其余 -> titled"
      - "信息组数决定分栏数：1 -> S1；2 -> H2/V2；3 -> H3；4 -> H4/G4"
      - "主信息强且独立（大环/大数/焦点）-> 右侧分栏 H2 系；主信息横向长（进度/时间线/通栏列表）-> S1 系或 V2 系"
      - "需要按钮 -> ta-S1，或将 capsule 放入 >=144 宽的栏"
      - "辅助信息需要再分 -> 栏内 V2/H2/G4；最小块 68x50，其内不再分栏"
    forbidden: [invent-new-layouts, cross-variant-splicing, asymmetric-splits, add-regions-for-candidates]
    decisionOrder:
      - "判断信息关系（日程/待办/占比/进度/并列/序列/强状态/操作）"
      - "mustKeep 字段能否全部映射到所选变体的槽位"
      - "选择结构最简单的可用变体；承载不下时先删 shouldKeep"
  horizontalClosure:
    padding12-safe-width-296:
      - "142 + 12 + 142 = 296（bare 二分）"
      - "144 + 8 + 144 = 296（titled 二分与内容级二分）"
      - "90.67*3 + 12*2 = 296（整行三分）"
      - "65*4 + 12*3 = 296（整行四分）"
      - "93.33*3 + 8*2 = 296（次级三分）"
      - "68*4 + 8*3 = 296（次级四分）"
      - "68 + 8 + 68 = 144（144 栏内二分）"
    rowRule: "左右 padding + 子项宽度之和 + itemMargin 之和 <= 父宽度"
  verticalClosure:
    padding12-safe-height-136:
      - "bare：content 136"
      - "titled-compact：17 + 4 + 115 = 136；115 内 53.5 + 8 + 53.5 或 33*3 + 8*2"
      - "titled-regular：20 + 8 + 108 = 136；108 内 50 + 8 + 50"
      - "titled-action：20 + 4 + 72 + 4 + 36 = 136"
    columnRule: "子项高度之和 + itemMargin × (子项数 - 1) <= 安全内容高度；公式逐层适用，父容器 padding 计入"
    expandedRealHeights: { progressUnit-plain: 36vp, progressUnit-numeric-single: 48vp, progressUnit-numeric-single-caption: 74vp }
  titleRow:
    barHeight: { compact: 17vp, regular: 20vp }
    barWidth: 296vp
    barRadius: 16vp
    titleText: { fontSize: 12fp, fontWeight: 700, maxLines: 1 }
    withIcon: { leadingIconSize: "12x12vp", trailingIconSize: "16x16vp", isolationMin: 8vp }
  skeletonMappings:
    meeting-timeline:
      aka: single-event
      variant: tc-S1
      fits: "日程、会议、提醒"
      slots: "title bar + 全宽时间线区（TimelineUnit 宽 16，与事件文字列 itemMargin 10；单条事件 64-72 高，两条每条 46；事件标题 <= 20fp，时间/地点 14-16fp）"
      eventsMax: 2
      gaps: { titleToContent: 4 }
    todo-list:
      variant: tc-S1-list3
      fits: "待办事项、任务清单"
      item: { height: 33vp, background: light-gray, check: circle-placeholder, text: "single-line 14fp", rowsMax: 3 }
    event-with-action:
      variant: ta-S1
      fits: "下一日程、会议、操作入口"
      slots: "content 296×72（三行以内）+ capsule 140×36"
    large-ring:
      variant: tc-H2
      fits: "内存占用、睡眠评分、百分比总览"
      slots: "左栏 144×115 环区（RingUnit ≤92 居中，环下至多一行说明）+ 右栏 144×115 信息列"
      noRepeat: "环内读数不得在右栏重复；睡眠卡在环内评分与环内时长中二选一"
    strong-focus:
      variant: tc-H2
      fits: "运动倒计时、省电状态、睡眠状态等强情绪卡"
      slots: "左栏 144 焦点区 + 右栏 144 面板"
      strongBackground: "右侧 15%-20% 白色透明背板，文字白色；主数字/进度/说明左右分区"
      lightPanel: "浅色卡右侧用主题色 panel；有真实比例时 panel 内加 8vp ProgressUnit"
    split-two-column:
      variant: tc-H2-V2
      fits: "左侧日期或主信息 + 右侧两个日程/状态块"
      slots: "左栏 144×115 主信息 + 右栏 2×(144×53.5) 小卡（同色、同尺寸、同结构）"
      unitRule: "动态值与 %/°C 等单位放同一 Row，单位不得作为第三行 Text"
      weatherPlusAgenda: "天气 + 日程优先 tc-H2 两个 144×115 并列面板，不纵向堆窄条"
    primary-action-pair:
      variant: tc-H2-H2
      fits: "智能家居、导航、同一服务对象下两个并列操作"
      slots: "左栏 144 主状态/主读数 + 右栏 2×(68×115) ActionUnit tile"
      requires: "左侧主状态或主读数；右侧两操作同一服务对象、均有真实事件与匹配图标"
      fallback: "不足两个真实事件时改 split-two-column 或 ta-S1，禁止伪造操作"
    linear-progress:
      variant: tc-S1
      fits: "应用时长、今日进度、防沉迷"
      slots: "title bar + content 296×115 内 ProgressUnit 与详情（两个对比值用两个同色背板行；只有一个补充事实用单行 detail_area）"
    metric-series:
      fits: "三个城市天气、三个同构设备状态、三个短指标"
      variants: { twoItems: tc-H2, threeItems: tr-H3 }
      itemContract: "严格同构、同一种主题色 panel；每项最多图标 + 主值 + 短标签三层；耳机左右电量用 2 项模式，设备名放标题区"
    quad-rings:
      variant: tr-G4
      fits: "四个设备电量、四个同类占比"
      slots: "4×(144×50) 网格，每格 RingUnit size 40 + 文字列；countMax: 4"
    four-action-hub:
      eligibility: "用户逐项明确要求同一服务对象下 3-4 个同层级快捷操作（系统设置、音乐控制等）"
      variants: { noTitle: bare-H4, withTitle: tr-H4, underContent: tr-V2-H4 }
      actionRequirements: "精确 eventCandidate + 2-4 字短标签 + 可见 icon；副作用动作必须用户逐项明确要求"
      forbidden: [data-display, mixed-service-objects, fabricated-buttons, more-than-four-actions]
    info-device-card:
      aka: 信息卡/设备卡变体
      variants: { noAction: tc-S1, withAction: ta-S1 }
      fits: "设置、蓝牙、网络、系统入口等无真实数值主指标的卡"
      structure: "小标题 + 1-2 个浅色信息面板 + capsule"
      forbidden: "把「点击查看」「当前设置项」「调整设置」「选项」作为 30 号以上主标题"
  fullWidthSingleColumnAllowed: [tc-S1, tc-S1-list3, ta-S1]
  fullWidthRequirement: "S1 系变体的主内容或背板必须使用完整 296vp 安全宽度，不得挤在左半边"
  rightRegionRule: "H2 系变体右栏放真实辅助信息（指标、状态、时间地点、二级列表、RingUnit、ProgressUnit、ActionUnit）；没有真实信息时不编造右栏"
  bottomActionArea:
    height: 36vp
    width: 140vp
    carrier: "ActionUnit capsule（r70 全圆角）"
    placement: "titled-action 根结构固定槽位；或 >=144 宽的栏内；卡片底部安全区内，不贴圆角边缘、不被裁切"
    closure: "20 + 4 + 72 + 4 + 36 = 136"
    forbidden: "自写 36 以上高度；塞进已塞满指标的信息 Column"
  sidebarCapsule:
    width: 140vp
    narrowRule: "所在栏安全宽度 < 140vp 时改用 tc-H2（144 栏）承载 capsule，禁止把胶囊塞进窄栏小卡"
layout_constraints:
  allowContentOverlap: false
  allowCardOverflow: false
  maxHierarchyLevels: 3
  overflowResolution: remove-secondary-content
  forbiddenOverflowFixes:
    - shrink-font-below-token
    - compress-safe-margin
    - negative-margin
    - clip-to-hide-layout-failure
overflow_resolution_order:
  - shorten-action-labels
  - remove-non-actionable-numbers
  - remove-explanatory-copy
  - remove-chart-axis-labels
  - remove-chart-grid-lines
  - reduce-calendar-or-list-to-summary
  - remove-secondary-action
  - remove-duplicated-metric
  - collapse-status-to-icon
density:
  "2x4":
    factsMax: 4
    eventsMax: 2
    todoItemsMax: 3
    metricSeriesItems: "2-3"
    seriesItemsMax: 5
    quadRingCardsMax: 4
    explicitActionsDefaultMax: 2
    explicitActionsHubMax: 4
    visibleListRowsMax: 3
    visibleListRowsMaxWithChart: 2
interaction:
  defaultModel: conditional-by-button-presence
  allowedModels:
    - whole-card
    - content-and-action-group
  hotZoneModel:
    withoutButton:
      count: 1
      regions:
        - whole-card
    withButton:
      countFormula: 1 + explicit-action-count
      regions:
        - content-area
        - one-independent-region-per-button
      regionsMustNotOverlap: true
      feedbackMustBeIndependent: true
  allowedActionKinds:
    - open-detail
    - execute-single-command
    - toggle-single-state
  prohibitedPatterns:
    - complex-form
    - multi-step-flow
    - hidden-gesture-dependency
    - dense-button-grid
    - hover-required-interaction
  feedbackStates:
    required:
      - default
      - pressed
    conditional:
      selected: toggle-or-selection-only
      disabled: business-or-system-can-disable
      loading: action-has-async-wait
      success: action-exposes-success-feedback
      error: action-exposes-error-feedback
content_states:
  required:
    - normal
  conditional:
    loading: data-has-loading-phase
    empty: data-can-be-empty
    error: data-request-can-fail
    offline: service-depends-on-network
    stale: data-has-freshness-limit
    unauthenticated: service-requires-login
    unauthorized: service-requires-permission
    partial_data: partial-results-are-possible
    privacy_hidden: content-can-be-privacy-hidden
    service_unavailable: service-can-be-unavailable
  invariant:
    - state-change-must-not-resize-canvas
    - primary-intent-must-remain-identifiable
    - error-message-must-be-actionable-or-explanatory
size_adaptation:
  shrink_2x4_to_2x2:
    retain_in_order:
      - primary-state-or-value
      - required-context-label
      - primary-action-when-part-of-primary-intent
      - at-most-two-supporting-lines
    remove_in_order:
      - long-explanation
      - repeated-service-name
      - third-level-metadata
      - extra-action
      - dense-list
      - decorative-content
  expand_2x2_to_2x4:
    rules:
      - do-not-scale-original-layout
      - preserve-primary-information-dominance
      - add-only-related-time-trend-context-preview-or-clearer-action
      - preserve-whitespace-when-no-valuable-supporting-content
content_pruning:
  principle: necessary-actionable-only
  requiredBeforeLayout: true
  decisionFirstSelection:
    selectPrimaryActionBeforeContent: true
    retainTest: "删除此信息后，用户的下一步是否会改变？若不会，省略。"
    presentationBudget:
      - context-title
      - one-decision-signal
      - primary-action
    decisionSignal:
      chooseExactlyOne: state | value | short-sentence
      riskOrDeadline: fold-into-decision-signal-not-an-extra-line
      stateAndValueTogether: allowed-only-when-each-changes-the-next-action
    secondaryAction:
      default: omit
      allowedOnlyWhen: distinct-immediate-goal-and-does-not-compete-with-primary-action
  hierarchy:
    - primary-action-and-its-decision-signal
    - action-context-title
    - optional-supporting-info-that-changes-the-action
    - secondary-action-with-distinct-goal
    - explanatory-or-background-info
  nonActionableContent:
    default: omit
    examples:
      - repeated-value
      - precise-number-without-decision-impact
      - explanatory-sentence
      - demo-note-inside-card
      - decorative-status
  copyLimits:
    titleMaxChars: 6
    primarySentenceMaxChars: 12
    statusLabelMaxChars: 4
    actionLabelMaxChars: 4
  numericPolicy:
    maxPrimaryNumbers: 1
    seriesItemValuesAllowed: true
    seriesItemValuesNote: "同构序列（2-5 项）与四对比环每项可各自携带一个数值，不计入主数值上限"
    factsMax: 4
    omitIfNotNeededForAction: true
    preferThresholdStateOverExactDelta: true
    oneNumberIsACeilingNotATarget: true
browser_preview_shell:
  contractVersion: design-card-html-v1
  documentViewport:
    width: 1440px
    height: 1100px
    scalingAllowed: false
  requiredStructure:
    - preview-app
    - toolbar
    - preview-stage
    - preview-slot
    - widget
    - card-root
  toolbar:
    position: absolute
    x: 0px
    y: 0px
    width: 1440px
    height: 56px
  stage:
    position: absolute
    x: 0px
    y: 56px
    width: 1440px
    height: 1044px
  fixedSlots:
    "2x4": { x: 256px, y: 48px, width: 320px, height: 160px }
  requiredAttributes:
    document: data-artifact-contract="design-card-html-v1"
    slot: data-size="2x2 | 2x4"
    widget: data-size="2x2 | 2x4"
  caption:
    forbidden: true
    appliesTo: shell-level-caption-nodes-outside-card-root
    reason: |
      预览壳曾用 `.caption` 节点标注尺寸、尺寸别名、点击行为和主题切换提示
      (例如 "160×160vp · 2×2 · 整卡点击打开日历 · L/D 切换主题")。
      这类节点是开发调试元数据，不是卡片业务内容；审查台按 slot 坐标做
      定点裁切时，caption 若落在 slot 边界内或紧贴其下方会被裁进卡片画面，
      造成内部元数据泄露。产物中不得输出任何 shell-level caption 节点；
      尺寸、尺寸别名和点击行为的说明只能保留在 toolbar 区域。
widget_carrier:
  surface: desktop-widget
  role: glanceable-launch-surface
  not:
    - app-page
    - dashboard
    - modal
    - feed
    - form-flow
  interactionModel:
    primary: tap-to-open-app-or-feature
    secondary: one-step-explicit-action
    disallow:
      - multi-step-flow-inside-card
      - dense-navigation
      - scrollable-content
      - editable-form
      - tabbed-view
  contentModel:
    maxPrimaryIntent: 1
    showOnlyRuntimeSnapshot: true
    detailBelongsToDestinationApp: true
component_contracts:
  card-root:
    required: true
    allowedChildren:
      - identity
      - title
      - hero
      - supporting-content
      - status
      - progress
      - media
      - list
      - action
  identity:
    serviceLabel:
      placement: top-left
      showWhenContextRequires: true
      doNotRepeatAppName: true
    appIconAllowed: false
  title:
    required: true
    maxLines: 1
    requiredWhen: always
  hero:
    maxInstances: 1
    allowedKinds:
      - number
      - text
      - status
      - media
      - date
      - progress
    visualTextVariant:
      arrangement: horizontal
      visualPlacement: left
      visualSize: 56vp
      gap: "{spacing.lg}"
      allowedVisualKinds:
        - icon_weather1
        - dataviz
      weatherIconContract: "{icon_assets.heroWeatherIcon}"
      textBlockPlacement: right
      textBlockAllowedCombinations:
        - primary-text
        - supporting-text
        - primary-text + supporting-text
      semanticBindingRequired: true
      decorativeUseAllowed: false
      countsAsSingleHero: true
  supporting-content:
    mustExplainHeroOrAction: true
    unrelatedRecommendationsAllowed: false
  list:
    maxRowsBySize:
      "2x4": 3
    maxRowsWithChart:
      "2x4": 2
  action:
    explicitActionsBySize:
      "2x4": 2
    hubException:
      fourActionHub: "3-4 个由用户逐项明确要求、同一服务对象、同层级的快捷操作"
    carrier: "ActionUnit（state: capsule | tile），禁止基础 Button"
    actionGroupBySize:
      "2x4":
        arrangement:
          - single-capsule
          - two-tiles-horizontal
          - hub-row-3-4-tiles
    requiresClearLabelOrSymbol: true
    geometry:
      capsule: { height: 36vp, width: 140vp, radius: 70vp, radiusRule: full-capsule-fixed-70 }
      tile: { width: "64-80vp", height: "80-115vp", iconRequired: true }
      minimumVisualSize: 24
      minimumHotZone: 40
      unit: vp
    visualStyle:
      allowed:
        - ordinary-filled
      emphasizedAllowed: false
      useDirectTokenColorAssembly: true
      allowedShapes:
        - capsule
        - tile
  progress:
    allowedKinds:
      - ring
      - linear
    carriers: "RingUnit | ProgressUnit；禁止手写基础 Progress"
    ringUnit:
      allowedSizes: [40, 44, 52, 80, 92, 98]
      states: [center-text, center-icon, center-icon-below-text]
      semanticColors: [green, blue, orange, red]
      forbiddenColors: [purple]
      reading: "仅在需要显示环心或环下文字时使用"
      centerIcon: "必须来自 assetCandidates"
    progressUnit:
      states: [bar, numeric-single, numeric-single-caption, plain]
      requiresValueAndTotal: true
      captionMaxLines: 1
      expandedRealHeights: { plain: 36vp, numeric-single: 48vp, numeric-single-caption: 74vp }
    stateSelectionByDetail:
      noDetail: numeric-single-caption
      oneToTwoDetailLines: "numeric-single，且不再生成 caption"
    quadRingsNote: "quad-rings 骨架使用 4 个 40vp 对比环，不属单主焦点环"
  snapshot:
    mustMatchRealLayout: true
    rectangularWithoutBakedCorner: true
    lightAndDarkRequired: true
components:
  action-unit-capsule:
    carrier: "ActionUnit state capsule"
    label: "必填短文案，优先 2-4 字，不超过 6 字"
    onClick: "必填，call/args 逐字段复用 eventCandidates；动态参数用 {path}"
    height: 36vp
    width: 140vp
    rounded: "70vp（全圆角，capsule_full_action）"
    typography: "{typography.body-m-regular}"
    typographyFallback: "{typography.body-s-regular}"
    fallbackWhen: "text-length > 6"
    lightOverlayPair: "场景主色 10% 底（actionSurface）+ 100% 前景（actionInk）"
    strongBackgroundOverride: { actionInk: "#FFFFFFFF", actionSurface: "#33FFFFFF" }
    forbiddenProps: [height, padding, borderRadius, backgroundColor, fontColor]
    forbiddenPropsNote: "尺寸与颜色配对由转换器落地，产物侧不得手写；宽度固定 140vp，不再按父容器适配"
  action-unit-tile:
    carrier: "ActionUnit state tile"
    width: "64-80vp"
    height: "80-115vp"
    icon: "必填，来自 assetCandidates"
    label: "2-4 字短标签"
    converterGenerates: "同色背板 + 上图标 + 下标签"
    children: forbidden
  card-root:
    background:
      baseColor: "{colors.comp_background_primary}"
      sceneGradient:
        allowed: true
        exactSceneMatchOnly: true
        presets: [office-focus, office-schedule, device-anti-addiction, device-headphone-control, low-power-mode, worry-free-cleanup, weather, rainy-weather, sports-health, sleep, general-fallback]
        agentSelectBySceneSemantics: false
        fallbackPreset: general-fallback
        unregisteredSceneBehavior: general-fallback
        customGradient:
          allowed: false
        contrastRequirement: "text contrast >= 3:1"
    rounded: "{rounded.corner_radius_level10}"
    padding: "12vp 固定（由 content_root 承载，布局抽象全量采用 12vp 档）"
  list-row:
    typography: "{typography.body-m-regular}"
    height: 33vp
    padding: 10vp 12vp
    rounded: "{rounded.corner_radius_level4}"
    background: "{colors.comp_background_tertiary}"
  progress-ring-label:
    typography: "{typography.title-s-bold}"
    textColor: "{colors.font_primary}"
---

## Overview

本系统描述 **HarmonyOS 桌面 widget 服务卡片 `2×4`（320×160vp 宽卡）** 的视觉身份——可一眼扫读的横向桌面表面,承载**一条核心信息**（一个主信息组，至多一个辅助信息组），并**默认单一主操作；仅当次操作有独立且即时的用户目标时才附带**。品牌基调是**冷静、技术感、确定**:受控的场景渐变托起一个高对比的数据点,再用唯一一抹饱和强调色告诉用户"该做什么"。本文件是 2×4 产物的检验金标准;`2×2` 的检验以 `DESIGN.md` 为准。

目标读者是**任务驱动的扫读者**,看卡片的时间只有 1–2 秒。因此美学目标是**清晰优于装饰**:层级靠字号和唯一强调色建立,绝不靠装饰性效果。没有俏皮语气、没有密集仪表盘、没有与数据争抢注意力的视觉噪音。

本系统同时面向三个渲染目标——A2UI 结构、ArkTS / ArkUI 原生、浏览器预览壳——三者视为同等规范。

## Colors

调色板以**主题基底 + 受控场景渐变 + 登记元素点缀色**为基础。默认组件颜色必须按 token 名引用,**不得直接写 hex 值**,这样明暗主题才能在不改布局的前提下切换。`card-root` 先铺 `comp_background_primary` 基底（浅色主题为白、深色主题为深色）；明确命中 `background_gradients` 登记场景时叠加对应的浅色遮罩或不透明场景渐变，未命中时必须叠加 `general-fallback` 浅蓝遮罩，不得只呈现裸基底，也不得自行生成渐变。

`colors` 槽位里的值就是 **light 主题默认值**;`themes.dark` 槽位提供 dark 主题覆盖。渲染器在 dark 模式下用 `themes.dark` 中的同名 token 覆盖 `colors` 中的值;未在 `themes.dark` 中列出的 token 沿用 light 值。

### 角色 token 分类

- **brand**:品牌主色(`#0A59F7FF`),主操作与品牌强调的**唯一驱动色**。
- **status**:语义状态色。`warning` 红色(`#E84026FF`)对应风险/危险;`alert` 橙色(`#ED6F21FF`)对应一般提醒;`confirm` 绿色(`#64BB5CFF`)对应完成/确认。**`warning` 作为状态语义时不得用作品牌或装饰**,专用于风险与紧急状态;但同一 `#E84026FF` 色值在 `office-schedule` 场景里作为场景语义红(日程遮罩与主色)是被允许的,两者按角色区分,不互相冲突。
- **font**(`font_primary` / `font_secondary` / `font_tertiary` / `font_fourth` / `font_emphasize`):前景文本阶。`font_emphasize` 等同 `brand`,用于强调文字。
- **font_on**(`font_on_primary` / `font_on_secondary` / `font_on_tertiary` / `font_on_fourth`):反色文本阶,专用于品牌强调色面、反相表面、图片背景上的反白文字。
- **icon**(`icon_primary` / `icon_secondary` / `icon_tertiary` / `icon_fourth` / `icon_emphasize` / `icon_sub_emphasize`):图标阶。`icon_sub_emphasize` 是 40% 透明度的强调辅助图标色。
- **icon_on**(`icon_on_primary` / `icon_on_secondary` / `icon_on_tertiary` / `icon_on_fourth`):反色图标阶。
- **background**(`background_primary` / `background_secondary` / `background_tertiary` / `background_fourth` / `background_emphasize`):宿主背景与高亮背景阶,均为实色/不透明色。
- **background_gradients**:卡片根背景的受控遮罩注册表。每个预设按 `cssVariableNaming` 确定性注册为 CSS 变量；例如 `low-power-mode` 必须输出为 `--bg-gradient-low-power-mode`。注册表包含办公、设备、低电量、清理、天气、雨天、运动健康、睡眠等精确场景预设，以及唯一的 `general-fallback` 通用兜底；精确场景必须按映射选择，不做近似语义扩展。
- **comp**(`comp_foreground_primary` / `comp_background_primary` / `comp_background_primary_transparent` / `comp_background_primary_contrary` / `comp_background_gray` / `comp_background_secondary` / `comp_background_tertiary` / `comp_background_emphasize` / `comp_background_neutral` / `comp_common_contrary`):组件前景、组件背景、反色与中性强调色。`comp_background_primary` 同时承担卡片根背景基底与卡片内部组件表面，由明暗主题覆盖（浅色 `#FFFFFFFF` / 深色 `#202224FF`），卡片根背景跟随主题切换；`comp_background_primary_transparent` 是所有遮罩渐变的 0% 终点；`comp_background_emphasize` 是专注模式与清理无忧遮罩的纯色蓝。
- **focus**(`comp_background_focus` / `comp_focused_primary` / `comp_focused_secondary` / `comp_focused_tertiary`):获焦态背景与获焦态反色前景阶。
- **emphasize overlay**(`comp_emphasize_secondary` / `comp_emphasize_tertiary`):20% 与 10% 的品牌高亮背景。
- **comp_divider**:分割线颜色,明暗主题各自覆盖。
- **interactive**(`interactive_hover` / `interactive_pressed` / `interactive_focus` / `interactive_active` / `interactive_select` / `interactive_click`):通用交互态色。

### Card Background

`card-root` 的第一层为 `comp_background_primary`（浅色主题 `#FFFFFFFF` / 深色主题 `#202224FF`，跟随主题切换）。第二层使用注册表中的场景渐变：办公、设备、低电量、清理和通用 fallback 使用 10% 到透明的浅色遮罩；天气、雨天、运动健康、睡眠使用不透明的场景渐变。不得自行混合这两类规则，也不得用 CSS `opacity` 降低整张卡片的透明度。浅色遮罩类预设登记有 `opaqueEquivalent`（预合成等效 stops，如 `#E7EFFEFF` → `#FFFFFFFF`）：实现侧在纯白宿主上把遮罩渐变烘焙为不透明等效表达时，视为与原预设等价；该等价仅以 `comp_background_primary` 纯白基底为前提，暗色宿主不成立。

场景必须按下列映射精确选择：办公效率—专注模式使用 `office-focus` (`#0A59F719` → `#FFFFFF00`)；办公效率—日程管理使用 `office-schedule` (`#E8402619` → `#FFFFFF00`)；设备管控—防沉迷使用 `device-anti-addiction` (`#00000019` → `#FFFFFF00`)；设备管控—耳机操控使用 `device-headphone-control` (`#64BB5C19` → `#FFFFFF00`)；低电量模式使用 `low-power-mode` (`#F9A01E19` → `#FFFFFF00`)；清理无忧使用 `worry-free-cleanup` (`#0A59F719` → `#FFFFFF00`)。天气使用 `weather` 径向渐变 (`#317AF7FF` → `#46B1E3FF`)；雨天天气使用 `rainy-weather` (`#46484DFF` → `#467794FF`)；运动健康使用 `sports-health` (`#ED6F21FF` → `#F9A01EFF`)；睡眠使用 `sleep` (`#AC49F5FF` → `#C386F0FF`)。未命中任何精确场景时必须使用 `general-fallback` (`#0A59F719` → `#FFFFFF00`)，不得只呈现裸基底。

浏览器预览壳必须把 `background_gradients` 中的每个预设完整序列化到对应的 `--bg-gradient-*` 变量后,模型才可通过 `var(--bg-gradient-<preset-name>)` 调用。渲染时必须分别设置 `background-color: var(--comp-background-primary)` 与 `background-image: var(--bg-gradient-<preset-name>)`，不得用后者覆盖或省略基底。预设的类型、方向、stops 与 offset 都以注册表为准。引用未定义 CSS 变量属于产物完整性错误,该 attempt 不得写入成功 manifest。

### Card Element Color Recommendations

场景元素色用于卡片内部的装饰图形、状态点、数据可视化前景和操作元素，不能替代普通正文的一级、二级文本色。无现成装饰元素时可以保持克制，不为使用颜色而新增无语义图形。

- **办公效率 / 专注模式 (`office-focus`)**：装饰表面使用 `#0A59F719`，主点缀与操作元素前景使用 `#0A59F7FF`；正文继续使用一级、二级文本色。
- **办公效率 / 日程管理 (`office-schedule`)**：装饰表面使用 `#E8402619`，主点缀与操作元素前景使用 `#E84026FF`；正文继续使用一级、二级文本色。此处的红是 `office-schedule` 的场景语义红，不是 `warning` 状态红。
- **设备管控 / 防沉迷 (`device-anti-addiction`)**：基础装饰表面使用 `#0A59F719`，主点缀与操作元素前景使用 `#0A59F7FF`；正文继续使用一级、二级文本色。
- **耳机播控**：装饰、状态与图表前景以 `#64BB5CFF` 为主、`#A5D61DFF` 为辅。
- **低电量模式**：装饰与状态前景使用 `#F9A01EFF`。
- **清理无忧**：以 `#F9A01EFF` 为主、`#64BB5CFF` 为辅。
- **不透明场景渐变（`weather` / `rainy-weather` / `sports-health` / `sleep`）**：卡片整体是饱和渐变背景，装饰图形、状态点、数据可视化前景等元素主色一律使用反色 `#FFFFFFFF`（100%）与 `#FFFFFF99`（60%）作为主/次点缀；`buttonColorContext.primaryHue`（如 `#317AF7FF`、`#ED6F21FF` 等）只约束按钮文字与图标，不用于装饰元素。

#### 数据可视化前景（环形图、进度条、阶段条）

数据可视化的进度前景色按卡片背景类别区分，不得在两类背景之间混用：

- **浅色遮罩卡片**（`light-overlay-gradient`）：环形图进度弧、进度条填充、阶段条前景**必须使用卡片主色**（即该场景 `card_element_color_recommendations.primary`，如 `office-focus` 用 `#0A59F7FF`、`device-headphone-control` 用 `#64BB5CFF`、`low-power-mode` 用 `#F9A01EFF`）。**不得使用白色 `#FFFFFFFF` 或反色 `font_on_*` / `icon_on_*` token**——浅色遮罩接近白底，白色或反色前景不可见。当环形图承载语义状态时（如完成度=绿、低电量=黄），允许使用对应语义点缀色（`#64BB5CFF` / `#F9A01EFF`）替代主色，但不得使用白色。
- **不透明渐变卡片**（`colored-gradient`）：进度弧与填充使用反色 `#FFFFFFFF`，与装饰元素主色一致。
- **进度轨道（track）**：两类卡片统一使用中性 `progress_ring_track`（浅色 `#00000019` / 深色 `#FFFFFF19`，随主题翻转），不随场景主色变化；只有进度前景着色。

推荐色必须通过 `card_element_color_recommendations` 解析成卡片局部变量，不得改写全局 `font_primary` / `font_secondary`。同一卡片最多使用登记的两个点缀色；数据可视化轨道继续使用中性 track token，只有进度、选中或状态前景使用点缀色。

### Auxiliary Info Surface (辅助信息区域)

卡片底部承载补充说明、状态行或附属数据的小型信息面板（如天气建议、待办附属项、专注状态行、排名摘要等）统一使用 **辅助信息区域** 组件规范。

#### 样式与布局

| 属性 | 值 | 说明 |
|---|---|---|
| 背板颜色 | `var(--comp-background-tertiary)` | 浅色 `#0000000C`（黑 5% 半透明）/ 深色 `#FFFFFF19`（白 10% 半透明），随主题翻转 |
| 文字颜色 | `var(--comp-foreground-primary)` | 浅色 `#000000FF` / 深色 `#E5E5E5FF` |
| 圆角 | `corner_radius_level6` = 12vp | |
| 宽度 | 100%（填充 content-area 剩余宽度） | |
| 内边距 | `padding: 4vp 8vp`（上下最少 4vp，左右 8vp） | |
| 内容对齐 | 左对齐（`text-align: left; align-items: flex-start`） | |
| dot / 图标与文字 | 垂直居中对齐（`align-items: center`） | 同行内 dot/icon 与文字基线居中 |

辅助区域位于 content-area 底部，与上方主内容之间保持至少 8vp 间距。同一 content-area 内最多放置 3 个辅助信息区域；每个区域仍各自填充 content-area 剩余宽度（保持上表宽度规则，不写死固定宽度）。当存在两个或以上辅助信息区域时，相邻区域之间的垂直间距为 4vp。

#### 空间受限时的降级策略

当辅助区域内容超出可用空间时，按以下顺序逐级降级：

1. **间距压缩**：文字行间距从默认调整为 2vp
2. **正文降级**：辅助正文（第二行）字号降级或省略
3. **标题降级**：标题（第一行）字号降级
4. **标题替换**：标题替换为更短的辅助文字
5. **仅保留正文**：删除标题，仅保留单行正文

#### 不支持的元素（全卡适用）

**卡片任意区域**（不止辅助信息区域）内不得使用以下无注册组件的自定义图形或手绘 SVG：
- 手绘 ECG / 心电折线 SVG（无 `data-resource-icon` 的自定义 `<path>`）
- 自定义分段进度条（非 `linear-progress` 组件的 `<i>` / `<div>` 序列）
- 自定义柱状图、散点图或其他手绘数据可视化
- 自定义折线图、趋势线、轨迹线（`<polyline>` 或 `<path d="M... L...">` 承载数据）

`data-dataviz` 的取值必须是 `allowedDatavizValues`（`display-ring` / `paired-data-ring` / `linear-progress`）三者之一；任何其它取值视为手绘数据可视化，机器按 `unregistered_dataviz` 拒收。所有资源图标必须内联自 `resource/icons/catalog.json` 的 normalized SVG，禁止自绘图标 path。

这些应替换为纯文字、`linear-progress` 组件、`display-ring` 组件或已注册的 `status-dot`。多值趋势（如 7 天天气、耗电趋势、信号格）的合规降级路径：用多段 `linear-progress` 并列表达各值占比 + 每段旁的数值文字，或用 `display-ring` 表达当前/汇总值，不得画柱或线。

### Gradient Card Button Colors

遮罩渐变卡片上的所有按钮（主按钮、次按钮和图标按钮）必须由卡片所选注册预设的 `buttonColorContext` 决定颜色，不得继续沿用组件的默认蓝底、灰底或自行选择无关颜色。`backgroundClass` 与 `primaryHue` 必须直接读取该预设，不能由 Agent 另行声明或改写。

- **浅色遮罩场景 (`light-overlay-gradient`)**：按钮背景使用场景 `buttonColorContext.primaryHue` 的 10% 透明度，按钮文字或图标使用其 100% 不透明色。不得对整个按钮设置 `opacity: 10%`。
- **不透明场景渐变 (`colored-gradient`)**：按钮背景使用白色，按钮文字或图标使用 `buttonColorContext.primaryHue`；卡片普通文字与图标使用反色文本阶。

以上渐变按钮规则是组件默认色的强制覆盖规则，不是可选建议；按钮的背景分类、背景色和前景色必须成组解析，不得只应用其中一项。若渐变卡片缺少 `buttonColorContext`，不得通过猜测或退回默认按钮颜色完成渲染。

### 状态 token

全局状态 token 统一为 `warning` / `alert` / `confirm`,不得另起其它同义 token。需要兼容历史命名时,应在解析层把旧语义映射到这三个标准 token,但设计文档和组件定义只书写标准 token。

### Hex 与透明度规则

颜色统一书写为 8 位 hex,格式为 `#RRGGBBAA`,其中后两位 `AA` 描述透明度。仅使用以下透明度档位(对应 13 档 alpha):`FF`(100%) / `E5`(90%) / `CC`(80%) / `B2`(70%) / `99`(60%) / `7F`(50%) / `66`(40%) / `4D`(30%) / `33`(20%) / `26`(15%) / `19`(10%) / `0C`(5%) / `00`(0%)。其他透明度档位一律不允许。遮罩渐变使用 `19` → `00`；按钮使用 `19` 背景与 `FF` 前景组成同色相配对；不得通过 CSS `opacity` 降低整个按钮及其文字的透明度。

### 对比度

普通阅读文本与背景的对比度**强制不低于 3:1**。暗色模式下,文字阶自动从黑翻成白,以保持同样对比比。正文级文本（body 层级的长文本阅读）**建议不低于 4.5:1**（与 WCAG AA 对齐，建议级非强制）；对比度判定必须按「前景 × 有效背景栈」逐层 alpha 合成后计算（卡片基底 → 渐变位置色 → 祖先底板），不得只对单点背景色估算。

## Typography

字体系统建立在单一字体族 **HarmonyOS Sans SC** 上,通过字号与字重两个维度表达层级。除 5 类基础文字角色外，`metric-primary-with-support`(32vp) 与 `metric-primary`(40vp) 是主数值的专用语义 token——2×4 主数值常规使用 20-32vp，40vp 仅用于全卡唯一的绝对主数值；每级各司其职。刻意避免混用字重与装饰性变体。

### 5 类语义角色

每类承担一个明确的内容语境:

| 类别 | 用途 |
|------|------|
| **display** | 视觉锚点:卡片主数据(电量 78%、距离 32km)。每张卡片最多一个 |
| **title** | 区段标题、卡片内强调标题 |
| **subtitle** | 行标题、强调文案、按钮文字 |
| **body** | 默认阅读文案、列表正文 |
| **caption** | 元数据、单位、提示文字、时间戳 |

### 3 档字重

每个 (类别, 尺寸) 组合都登记 **Regular / Medium / Bold** 三档,对应 HarmonyOS Sans SC 原生提供的字重:

| 字重 | 值 | 适用语境 |
|------|-----|---------|
| **regular** | 400 | 默认阅读、低层级辅助文字 |
| **medium** | 500 | 行标题、按钮、强调文案 |
| **bold** | 700 | 标题、关键数字、视觉锚点 |

### 3 档尺寸

每类按尺寸分为 L / M / S:

| 类别 | **L** | **M** | **S** |
|------|-------|-------|-------|
| display | 56vp | 48vp | 38vp |
| title | 30vp | 24vp | 20vp |
| subtitle | 18vp | 16vp | 14vp |
| body | 16vp | 14vp | 12vp |
| caption | 12vp | 10vp | 8vp |

### 完整 45 角色矩阵

每一格表示 `{tier}-{size}-{weight}`,形如 `display-l-regular`:

| | **regular (400)** | **medium (500)** | **bold (700)** |
|--|-------------------|------------------|----------------|
| display-l | `display-l-regular` | `display-l-medium` | `display-l-bold` |
| display-m | `display-m-regular` | `display-m-medium` | `display-m-bold` |
| display-s | `display-s-regular` | `display-s-medium` | `display-s-bold` |
| title-l | `title-l-regular` | `title-l-medium` | `title-l-bold` |
| title-m | `title-m-regular` | `title-m-medium` | `title-m-bold` |
| title-s | `title-s-regular` | `title-s-medium` | `title-s-bold` |
| subtitle-l | `subtitle-l-regular` | `subtitle-l-medium` | `subtitle-l-bold` |
| subtitle-m | `subtitle-m-regular` | `subtitle-m-medium` | `subtitle-m-bold` |
| subtitle-s | `subtitle-s-regular` | `subtitle-s-medium` | `subtitle-s-bold` |
| body-l | `body-l-regular` | `body-l-medium` | `body-l-bold` |
| body-m | `body-m-regular` | `body-m-medium` | `body-m-bold` |
| body-s | `body-s-regular` | `body-s-medium` | `body-s-bold` |
| caption-l | `caption-l-regular` | `caption-l-medium` | `caption-l-bold` |
| caption-m | `caption-m-regular` | `caption-m-medium` | `caption-m-bold` |
| caption-s | `caption-s-regular` | `caption-s-medium` | `caption-s-bold` |

### 选用规则

- **单一数据点**:2×4 主数值默认 20-32vp（`title-s`–`metric-primary-with-support`）；仅当它是全卡唯一绝对主数值且无下方辅助信息时才可用 `metric-primary`(40vp / 700)。单位与辅助信息拆分为独立 Text，使用 12-16vp；schema 只提供带单位字符串（如 `durationText:"25分钟"`）时不得用 30vp 以上大字展示
- **常规卡片主标题**:`subtitle-s-medium`(14 / 500)或 `subtitle-l-medium`(18 / 500)
- **副标题 / 辅助**:`body-s-regular`(12 / 400)或 `caption-l-regular`(12 / 400)
- **正文**:`body-s-regular`(12 / 400)是默认阅读字号
- **按钮文字**:默认用 `body-m-regular`(14 / 400);当按钮文案多于 6 个字时降级到 `body-s-regular`(12 / 400),且不得继续低于 `body-s-regular`
- **最小字号**:按 font token 定义,最小为 `caption-s-regular`(8 / 400);任何内容不得小于 8vp
- **同尺寸不同语境的层级差异**用字重区分(例如 14vp 既可以 `subtitle-s-medium` 表达强调,也可以 `body-m-regular` 表达正文)

### 缩放与行高

系统字号缩放支持 0.8x – 1.3x。20vp 及以上的字号不放大,以维持布局完整性。

## Layout & Spacing

本系统采用**固定画布 + 闭合数值预算 + 标准 Layout 组合**，而非流式栅格。`2×4` 逻辑画布恒为 `320×160vp`，由宿主运行时提供；卡片永不硬编码自身的外部尺寸，也不得假设可滚动、可分页或可扩展高度。桌面 widget 由宿主桌面承载和裁切；浏览器预览壳只用于模拟宿主环境。

### 画布与根容器

- `root` 必须是 `Stack`：`width: 320`、`height: 160`、`borderRadius: 20`、`clip: true`，且必须提供 `linearGradient`（`angle` 默认 180，自上而下）。不要写 `constraintSize`，转换器会自动补。
- `root` 的唯一子节点是 `content_root`（`Column` 或 `Row`，`matchParent` 撑满画布）。
- `content_root` 的 `padding` 固定为 `12`（Pixso 布局抽象全量采用）；禁止 `14`、`16`、`18`、`20`。
- 唯一安全内容区：`296×136vp`。一切内容、背板与按钮都必须完整落在安全内容区和 160vp 卡面内，不能依赖 `root.clip` 把溢出内容裁掉。

### 数值闭合预算

安全区唯一：`296×136vp`（padding 12）。**2×4 不是加宽的 2×2**；分栏宽度由等分公式唯一确定，不做非对称分栏。

横向闭合式（全部合法组合，安全宽 296）：

```text
bare 二分：142 + 12 + 142 = 296
titled / 内容级二分：144 + 8 + 144 = 296
整行三分：90.67 × 3 + 12 × 2 = 296
整行四分：65 × 4 + 12 × 3 = 296
次级三分：93.33 × 3 + 8 × 2 = 296
次级四分：68 × 4 + 8 × 3 = 296
144 栏内二分：68 + 8 + 68 = 144
```

纵向闭合式（全部合法组合，安全高 136）：

```text
bare：content 136
titled-compact：17 + 4 + 115 = 136；115 内 53.5 + 8 + 53.5（两行）或 33 × 3 + 8 × 2（三行）
titled-regular：20 + 8 + 108 = 136；108 内 50 + 8 + 50
titled-action：20 + 4 + 72 + 4 + 36 = 136
```

闭合公式对**每一层**容器都适用，不只检查 `content_root`；父容器的 padding 必须计入：

```text
Column 实占高度 = top padding + bottom padding + 子项高度之和 + itemMargin × (子项数 - 1)
Row 实占高度 = top padding + bottom padding + 最高子项高度
任何 Row：左右 padding + 子项宽度之和 + itemMargin 之和 <= 父宽度
```

例如 `height:48, padding:8` 的小卡只有 32vp 内部高度，不能再竖放 `16 + 22 + 16` 三行文字；`height:32` 的 Row 也包不住实际 36vp 的两行 Column。声明较小的父高度不会自动缩小子项，只会重叠或裁切。高级组件展开后的真实高度同样计入父容器：`ProgressUnit plain` 36vp、`numeric-single` 48vp、`numeric-single-caption` 74vp。

标题行（title bar，高 17/20）左置图标 `12×12`、右置图标 `16×16`，至少保留 8vp 隔离空间；标题文字不得延伸到图标下方。内容指标列的子 Text 宽度不得大于父列宽度（父列 54vp 时子 Text 至多 54vp）。

浏览器 HTML 预览遵循 `browser_preview_shell` 的 `design-card-html-v1` 契约：`preview-slot[data-size="2x4"]` 绝对定位在 stage 的 `(256px, 48px)`，`widget` 固定 `320×160px`，卡片相对整个文档的左上角坐标恒为 `(256px, 104px)`。主题切换、内容长度不得改变 slot 坐标；窄 viewport 允许滚动，不得通过 `transform: scale(...)`、`zoom` 或响应式重排移动、缩放卡片。

**预览壳 caption 禁令**：产物中不得输出任何 shell-level caption 节点（如 `.caption`）。尺寸、尺寸别名和点击行为的说明只能保留在 toolbar 区域（`.toolbar` 内），不得作为独立节点输出到 stage 或 slot 中。

统一的间距刻度（`xxs 2 / xs 4 / sm 6 / md 8 / lg 12 / xl 16 / xxl 24`）统御纵横向节奏；布局中的 gap/itemMargin 优先使用 `4、8、12、16`，组间距必须大于或等于组内距，不无理由交替使用多个相近间距。

### 标准 Layout 组合规则

布局几何的唯一权威是 Pixso「布局抽象」（`item-id 60:280`，18 张标准布局卡；本地快照 `Design-guide/docs/pixso-layout-abstraction.md`）。布局**仅指示槽位**——只约束区域尺寸、分栏数、gap 与嵌套关系，不登记圆角等视觉属性（由组件契约与 `rounded` token 决定）。每张卡必须且只能选择一个标准变体（standard variant）；变体由「根结构 × 分栏组合」构成，分栏只做等分，不做非对称分栏。允许在声明范围内微调子组件对齐、字号、颜色和栏内排布，不得跨变体拼接区域，不得为了使用候选而新增一级区域，也不得自由发明布局。

路由顺序：是否需要标题行 → 信息组数决定分栏数（1 一分 / 2 二分 / 3 三分 / 4 四分）→ 主信息形态决定左右（H 系）还是上下（V 系）→ 是否需要按钮（ta 系）→ 检查 `mustKeep` 字段能否全部映射到变体槽位 → 选择结构最简单的可用变体；承载不下时先删除 `shouldKeep`，不自由发明页面。

#### 根结构（4 型）

| 根结构 | 构成 | 垂直闭合 |
|---|---|---|
| `bare` 无标题 | content 296×136，仅横向分栏 | 136 |
| `titled-compact` | title bar 296×17 + gap 4 + content 296×115 | 17+4+115=136 |
| `titled-regular` | title bar 296×20 + gap 8 + content 296×108 | 20+8+108=136 |
| `titled-action` | title bar 296×20 + gap 4 + content 296×72 + gap 4 + capsule 140×36，从顶排布 | 20+4+72+4+36=136 |

#### 分栏原子

布局仅指示槽位：只约束尺寸、分栏数、gap 与嵌套关系，**不登记内容区域圆角**；槽位内组件的圆角由组件契约与 `rounded` token 决定。

- **整行分栏**（bare 全量、整行三分/四分）：gap 12，栏宽 `(296−12×(n−1))/n` → 二分 142、三分 90.67、四分 65。
- **内容级二分与次级分栏**（titled 二分、任何区域内再分）：gap 8，栏宽 `(W−8×(n−1))/n` → 296 内二分 144、次级三分 93.33、次级四分 68；144 栏内二分 68。
- **纵向分栏**（content 内上下分）：gap 8 → 115 内两行 53.5、三行 33；108 内两行 50。
- **2×2 网格**（G4）：仅限 content 108，行列 gap 8、格 144×50。
- 嵌套上限：最小分栏块 68×50，其内不再分栏；任何嵌套不得引入新的非等分宽度。

#### 18 个标准变体

| 变体 | 根结构 | 结构 |
|---|---|---|
| `bare-H2` 左右二分 | bare | H gap12 → 2×(142×136) |
| `bare-H3` 三分 | bare | H gap12 → 3×(90.67×136) |
| `bare-H4` 四分 | bare | H gap12 → 4×(65×136) |
| `tc-S1` 一分 | titled-compact | 1×(296×115) |
| `tc-S1-list3` 一分·三行列表 | titled-compact | V gap8 → 3×(296×33) |
| `tc-H2` 左右二分 | titled-compact | H gap8 → 2×(144×115) |
| `tc-H2-V2` 左右二分·右上下二分 | titled-compact | 左 144×115 + 右 V gap8 → 2×(144×53.5) |
| `tc-H2-H2` 左右二分·右二分 | titled-compact | 左 144×115 + 右 H gap8 → 2×(68×115) |
| `tc-H2-V2H2` 左右二分·右上块下二分 | titled-compact | 左 144 + 右 V → 144×53.5 + H → 2×(68×53.5) |
| `tc-H2-G4` 左右二分·右 2×2 网格 | titled-compact | 左 144 + 右 V → 2 行(144×53.5) 各 H → 2×(68×53.5) |
| `tr-H3` 三分 | titled-regular | H gap12 → 3×(90.67×108) |
| `tr-H4` 四分 | titled-regular | H gap12 → 4×(65×108) |
| `tr-G4` 四分·2×2 网格 | titled-regular | V gap8 → 2 行 H gap8 → 2×(144×50) |
| `tr-V2` 上下二分 | titled-regular | V gap8 → 2×(296×50) |
| `tr-V2-H2` 上下二分·下二分 | titled-regular | 上 296×50 + 下 H gap8 → 2×(144×50) |
| `tr-V2-H3` 上下二分·下三分 | titled-regular | 上 296×50 + 下 H gap8 → 3×(93.33×50) |
| `tr-V2-H4` 上下二分·下四分 | titled-regular | 上 296×50 + 下 H gap8 → 4×(68×50) |
| `ta-S1` 一分·带按钮 | titled-action | content 296×72 + capsule 140×36 |

### 业务骨架映射

业务骨架名保留用于路由与密度约束，几何一律取所属标准变体，不再有独立闭合式：

| 骨架 | 变体 | 槽位要点 |
|---|---|---|
| `meeting-timeline` / `single-event` | `tc-S1` | title bar + 全宽时间线区（TimelineUnit 宽 16 + 事件文字列 itemMargin 10；单条 64-72 高、两条每条 46；事件标题 ≤ 20fp，时间/地点 14-16fp；最多 2 条；没有操作时不生成按钮） |
| `todo-list` | `tc-S1-list3` | 3 行 296×33（r8、浅灰背板、圆形 check 占位、单行 14fp） |
| `event-with-action` | `ta-S1` | content 296×72（三行以内）+ capsule 140×36；按钮固定底部安全区，不拉满 320vp 宽 |
| `large-ring` | `tc-H2` | 左栏 144 环区（RingUnit ≤92 居中、环下至多一行说明）+ 右栏 144 信息列；环内读数不在右栏重复，睡眠卡环内评分与时长二选一 |
| `strong-focus` | `tc-H2` | 左栏 144 焦点区 + 右栏 144 面板（深色卡 15%-20% 白透明背板、文字白色；浅色卡主题色 panel，真实比例加 8vp ProgressUnit，不退化为四行无背板文字） |
| `split-two-column` | `tc-H2-V2` | 左栏 144 主信息 + 右栏 2×(144×53.5) 同色同构小卡；动态值与单位同一 Row；天气 + 日程用 `tc-H2` 两个 144×115 并列面板，不纵向堆窄条 |
| `primary-action-pair` | `tc-H2-H2` | 左栏 144 主状态/主读数 + 右栏 2×(68×115) ActionUnit tile；两操作须同一服务对象、均有真实事件与匹配图标，不足时降级 `tc-H2-V2` 或 `ta-S1`，禁止伪造 |
| `linear-progress` | `tc-S1` | title bar + content 296×115 内 ProgressUnit 与详情；两个对比值用两个同色背板行，只有一个补充事实用单行 detail_area，不把两项信息散落卡片两端 |
| `metric-series` | `tc-H2`（2 项）/ `tr-H3`（3 项） | 严格同构、同一种主题色 panel；每项最多图标 + 主值 + 短标签三层；耳机左右电量用 2 项模式，设备名放标题区 |
| `quad-rings` | `tr-G4` | 4×(144×50) 网格，每格 RingUnit size 40 + 文字列；至多 4 个 |
| `four-action-hub` | `bare-H4` / `tr-H4` / `tr-V2-H4` | 3-4 个 ActionUnit tile（65/68 宽）；须用户逐项明确要求同一服务对象同层级操作，禁止数据展示、混合服务对象、伪造按钮、超过四个 |
| `info-device-card` | `tc-S1` / `ta-S1` | 小标题 + 1-2 个浅色信息面板 + capsule；禁止把「点击查看」「当前设置项」「调整设置」「选项」作为 30 号以上主标题 |

### 变体选择规则

- 有 3 个待办：选 `todo-list`（`tc-S1-list3`）。
- 单个日程无按钮：选 `meeting-timeline / single-event`（`tc-S1`）。
- 单个日程有按钮：选 `event-with-action`（`ta-S1`）。
- 有百分比主指标：优先 `large-ring`（`tc-H2`）。
- 四个同类百分比：选 `quad-rings`（`tr-G4`）。
- 有线性进度语义：选 `linear-progress`（`tc-S1`）。
- 两个并列操作且有两个真实事件：选 `primary-action-pair`（`tc-H2-H2`）。
- 左主右双事项：选 `split-two-column`（`tc-H2-V2`）。
- 强提醒、倒计时、状态突出：选 `strong-focus`（`tc-H2`）。
- 2-3 个同构天气/设备指标：选 `metric-series`（`tc-H2` / `tr-H3`）。
- 3-4 个用户逐项明确要求的同层级操作：选 `four-action-hub`（`bare-H4` / `tr-H4` / `tr-V2-H4`）。
- 无真实数值主指标的设置/设备入口：选信息卡/设备卡变体（`tc-S1` / `ta-S1`）。
- 纯并列同构、无标题语义（如四设备电量）：直接用 bare 系（`bare-H2/H3/H4`）。

### 全宽与左右分区

`tc-S1`、`tc-S1-list3`、`ta-S1` 允许使用全宽单列，但主内容或背板必须使用完整 296vp 安全宽度，不能把所有信息挤在左半边后让右半边空白。`tc-H2` 系优先左右分区，右栏放真实的辅助指标、状态、时间地点、二级列表、`RingUnit`、`ProgressUnit` 或 `ActionUnit`；没有真实信息时不编造右栏。

主辅关系通过栏内内容密度与字号表达；标准变体的栏宽一律等分，不再使用非对称比例。只有真实比较、同级时间序列、双事实或操作集合才允许等宽等高。所有主要文字、数值、图标和动作至少形成一条共同对齐线；辅助信息围绕主焦点聚合，不散落四角。

### 底部与侧栏 CTA

- 需要底部按钮时使用 `titled-action` 根结构（`ta-S1`）：title bar 20 + gap 4 + content 296×72 + gap 4 + capsule 140×36，从顶排布；按钮由 `ActionUnit` 生成，不自写 36 以上高度。
- content 296×72 容纳三行以内内容；内容超过三行时先删减信息，不压缩胶囊。
- 底部 action 固定在卡片底部安全区内，不贴圆角边缘，也不被裁切。
- 侧栏中的胶囊按钮固定宽 140vp；所在栏安全宽度不足 140vp 时（如 68vp 次级栏、65vp 整行四分栏），改用 `tc-H2`（144 栏）承载胶囊，禁止把胶囊塞进窄栏小卡。

### 尺寸密度

`2×4`：

- 一个主信息组和一个辅助信息组；一张卡至多 4 个事实。
- 待办/普通列表最多 3 行；日程/会议最多 2 条；同构序列 2-5 项（`metric-series` 2-3 项）；对比环最多 4 个。
- 默认最多 2 个显式操作；仅四操作 hub 允许 3-4 个由用户逐项明确要求的同层级操作。
- 无按钮时整卡一个热区；有一个或两个按钮时，内容区与每个按钮分别构成独立热区。
- 可以展示短时间线、相关双列或横向媒体结构；不得演变为仪表盘或快捷入口矩阵。

### 尺寸选择与布局适配

选择 `2×4`：

- 主信息需要一个相关辅助信息组。
- 需要短时间线、媒体详情或明确操作。
- 热区都具有真实价值且容易区分。

按钮的存在不会自动要求使用 `2×4`；当主信息和一个按钮能够在安全边距内清晰呈现时，可以使用 `2×2`（以 `DESIGN.md` 为准）。

### `2×4` 收缩为 `2×2`

按以下顺序保留：

1. 主状态或主数值。
2. 理解主信息所必需的标签。
3. 如果操作属于主意图，则保留主操作。
4. 最多两条辅助信息行。

优先删除：长说明、重复的应用或服务名称、第三层元数据、额外操作、密集列表和装饰信息。

### `2×2` 扩展为 `2×4`

- 不放大原布局。
- 保持原主信息的视觉主导地位。
- 只增加相关的时间、趋势、上下文、预览或一个更清晰的操作。
- 没有有价值的辅助信息时，保留留白，不制造填充内容。

### Content Density

服务卡片不是缩小版应用页面。每张卡片只能有一个主信息对象;辅助信息必须帮助用户理解主信息或决定下一步。

卡片采用 **necessary-actionable-only** 删减策略:只呈现与用户下一步操作直接相关的必要信息,非必要不呈现。生成器必须在布局前先判断信息优先级,再决定放入卡片的内容,不得先堆满再依赖缩小字号、裁切或换行补救。

信息取舍以**主操作**为根。先确定用户此刻唯一应做的事，再从候选信息中保留能帮助其做出这个动作的最小集合。每条候选信息都必须通过这个测试：**删除它以后，用户的下一步会改变吗？不会就不呈现。**信息优先级从高到低为:主操作及其决策信号 > 操作上下文 > 会改变操作的辅助信息 > 有独立即时目标的次操作 > 解释性背景。低优先级内容只有在不挤压高优先级内容时才可出现;若同一含义已由主数值、状态色或按钮文案表达,其他位置不得重复表达。

文案必须短到可扫读:标题建议 2-6 字（12fp 单行）,主句不超过 12 字,状态标签不超过 4 字,按钮文案优先 2-4 字、不超过 6 字（确需更长且不能等义缩短时使用更宽按钮或降低到批准字号，不能裁切）。主数值默认最多 1 个——这是上限而非应凑满的配额；同构序列（2-5 项）与四对比环每项可各自携带一个数值，全卡事实总数不超过 4 个。不影响操作的精确数字、差值、示例数值、更新时间、说明性统计默认不呈现。能用"已超时""偏高""待处理"表达时,不要再同时呈现额外精确差值。

`2×4` 可使用一个主信息组和一个辅助信息组。若一侧使用图表,另一侧最多显示 1-2 条摘要列表;若需要显示 3 条以上列表,图表必须降级为单一数值或极简趋势线。

当 `action_area` 出现时,内容必须在按钮区之前结束，并保持 4vp 间距（titled-action 根结构固定 gap）。按钮不得覆盖图表、列表或内容预览。

### Overflow Resolution

当内容无法在安全区内完整呈现时,必须按优先级删减,不得继续压缩、裁切或叠放。

删减顺序:

1. 缩短操作文案,如"查看报告"改为"报告","设目标"改为"目标"。
2. 删除不影响操作判断的精确数字、差值、更新时间和说明性统计。
3. 删除解释性文案;必要说明改为短标签或并入主信息组。
4. 图表降级为 sparkline,移除坐标轴、网格线、日期标签和数据点说明。
5. 日历或列表降级为 1 条摘要,如"2 个日程影响睡眠"。
6. 删除次操作,保留一个主操作。
7. 删除重复信息。若一处已经呈现主数值,其他区域不再重复表达同一指标。
8. 状态胶囊可降级为图标或短标签,但不得遮挡标题或主信息。
## Elevation & Depth

深度通过**调性分层**表达,而非投影。卡片本身坐在宿主表面之上;卡片内部,`comp_background_primary` / `comp_background_secondary` / `comp_background_tertiary` 叠出一组安静的层次。分割线仅在间距不足以表达分组时使用——采用 `comp_divider` token,20% 透明度的前景色(明暗主题各自覆盖)。

## Icons & Resource Assets

功能图标、状态图标和天气主视觉符号都是可选元素，不为填充留白而添加。所有这类视觉元素仅能使用本地 SVG 资源，必须从 `resource/icons/catalog.json` 中选择 `eligibility: approved` 且语义完全匹配的 canonical icon；快速片段生成时模型只输出 `<span data-resource-icon-ref="canonical-id"></span>` 占位，由确定性组装器读取 catalog 对应的 normalized SVG 并内联。不得让模型复制或改写资源几何，不得手绘替代 SVG、使用任何 emoji（包括系统或 Apple Emoji）、字符图标、外部图标库或网络图标。catalog 没有准确语义时，省略图标并使用短文本表达，不得选择只有视觉相似但语义不准确的资源。唯一的 56×56vp 天气 Hero 图标固定为 `icon_weather1`；它是专用的多色插画资源，不属于普通线性图标集合。

浏览器 HTML 使用 catalog 对应的 `resource/icons/normalized/` 标准化版本，并将 SVG 内联到单文件产物。每个资源图标根节点必须保留 `viewBox` 并标记 `data-resource-icon="<canonical-id>"`，不得修改 path、rect、circle、mask、clipPath 等几何。单色图标通过 `currentColor` 继承 `icon_*` / `icon_on_*` token；`multicolor` 或 `legacy` 资源只有在 catalog 明确标记为 `approved` 后才允许使用，且多色资源不得被自动改色。

资源 SVG 的 24×24 等原始尺寸是坐标系，不是统一的最终显示尺寸。最终尺寸按场景选择：左上标题前置 `leading-icon` 12vp、2×4 标题行右侧图标 16×16vp、`RingUnit` 中心图标（`centerIcon`）24vp。图标类型的 `hero-visual` 在 56×56vp 下只能使用 `icon_weather1`，并必须同时标记 `data-resource-icon="icon_weather1"` 与 `data-hero-visual="weather-icon"`；普通单色或线性 catalog 图标一律不得放大到 56vp 充当 Hero。`data-dataviz` 仍可按自身组件契约使用 Hero 空间，但不属于图标。其他场景必须由对应组件契约明确尺寸，不得由原文件 width / height 决定。

图表、进度和其他数据可视化 SVG 不属于资源图标，根节点必须标记 `data-dataviz`。所有内联 SVG 必须二选一标记 `data-resource-icon` 或 `data-dataviz`，不得同时标记，也不得存在未分类 SVG。机器只校验来源、几何、路径、分类和记录完整性；图标是否适合当前设计仍由人类设计师评审。

默认禁用装饰性投影。宿主表面始终优先:卡片绝不发明与桌面摆放位置相悖的高度。

## Shapes

形态语言是**柔和几何**。圆角统一采用 HarmonyOS 官方 `corner_radius_level*` 命名,共 **14 个 token**(`none` + `level1`–`level12` + `level16`,跳过 `level13/14/15`);`level1`–`level12` 每档间隔 2vp,`level16` 是 32vp 的保留超大圆角。

### 圆角刻度

| Token | 值 | 典型用途 |
|-------|-----|---------|
| `corner_radius_none` | 0 | 直角元素 |
| `corner_radius_level1` | 2vp | 极小标签 |
| `corner_radius_level2` | 4vp | 标签、徽标 |
| `corner_radius_level3` | 6vp | 小型控件 |
| `corner_radius_level4` | 8vp | 图片、中型控件 |
| `corner_radius_level5` | 10vp | — |
| `corner_radius_level6` | 12vp | 多维度信息底板 |
| `corner_radius_level7` | 14vp | — |
| `corner_radius_level8` | 16vp | — |
| `corner_radius_level9` | 18vp | — |
| `corner_radius_level10` | 20vp | **卡片本体与按钮 (card-root / button 默认值)** |
| `corner_radius_level11` | 22vp | — |
| `corner_radius_level12` | 24vp | 大型容器 |
| `corner_radius_level16` | 32vp | 圆角卡片 |

### 主圆角与同族规则

- **卡片本体主圆角**为 `corner_radius_level10`(20vp)，即 root 固定 `borderRadius: 20`
- **胶囊按钮为全圆角胶囊**：固定 `140×36vp`、圆角 70（`capsule_full_action`，高于高度一半即为全圆角），由 ActionUnit 转换器生成
- **小元素**(`corner_radius_level2`–`level4`)用于图片、徽标、标签；信息背板 8-12vp，主要支撑背板 12-16vp
- 同一功能用同一圆角——不做逐实例的圆角微调

### 胶囊与圆形控件

胶囊按钮为全圆角胶囊：固定 `140×36vp`、圆角 70（`capsule_full_action`），由 ActionUnit 转换器落地，无需用 `9999vp` 兜底。

预览壳在卡片外额外应用稍大的外圆角(`2×4` 上 22vp),便于宿主干净裁切;该圆角不属于卡片内容。

不使用装饰性嵌套圆矩形。

## Components

一套小巧、强约束的组件词汇。每个组件定义为扁平 token 条目；组件结构与行为同时受 YAML `component_contracts` 约束。

### 卡片根容器 Card Root

- 2×4 画布恒为 `320×160vp`；root 为 `Stack`，固定 `borderRadius: 20`、`clip: true`，必须提供 `linearGradient`（angle 默认 180，自上而下）。
- 必须先使用 `comp_background_primary` 基底；场景精确命中 `background_gradients` 中已登记的遮罩预设时叠加对应渐变，未命中时叠加 `general-fallback`，不得只保留裸基底。
- 卡片本体使用 `corner_radius_level10`(20vp)圆角；安全边距由 `content_root` 的 12vp 固定 padding 承载（Pixso 布局抽象全量采用 12vp 档）。
- 约束安全边距、宿主裁切和整体点击行为；不得依赖 `root.clip` 裁掉溢出内容。

### 标题与身份 Title & Identity

- `title-area` 与 `title-text` 必选；标题不得因核心内容自明而省略。
- 标题用于解释卡片服务或当前内容上下文，默认单行。
- 必要时在左上显示服务名称或服务身份文字。
- 右上角可放应用图标或营销 Logo，但必须来自本地 `resource` SVG（`data-resource-icon` 标注并通过 catalog 校验），不得使用 emoji 或外链。
- 应用名称不得在标题与身份区重复出现。
- `leading-icon` 可选：左上 12×12vp，或 2×4 标题行右侧 16×16vp（title bar 高 17/20，至少保留 8vp 隔离）；一卡至多两个 `leading-icon`（左上 12vp 一个 + 右上 16vp 一个）

### 主信息 Hero

主信息只允许一个，可为：

- 数值。
- 当前状态。
- 下一事件。
- 日期或倒计时。
- 图片或媒体预览。
- 单一进度。

`value-group.value` 无下方辅助信息时使用 `metric-primary`(40vp / 700)，有下方 `12vp` 辅助信息时使用 `metric-primary-with-support`(32vp / 700)，其余信息不得与主信息争夺层级。

Hero 可选用 `hero-visual-text` 横向变体增强数据表达：左侧是固定 `56×56vp` 的 `hero-visual`，右侧是 `hero-text-block`。左侧若使用天气图标，只能使用本地 `icon_weather1`，并同时标记 `data-resource-icon="icon_weather1"` 与 `data-hero-visual="weather-icon"`；若使用数据可视化，图表 SVG 必须标记 `data-dataviz`。右侧允许三种组合：仅大字号主文本、仅一行辅助文本、或大字号主文本加一行辅助文本。视觉与文本必须表达同一数据对象并共同计为一个 Hero，不得把视觉槽当作第二个主信息。

`hero-visual` 不是通用大图标槽，也不是装饰插图槽。`icon_weather1` 仅用于直接表达当前天气状态，固定为 `56×56vp`，不得使用 emoji，也不得复用于标题、按钮、状态或留白装饰。其他普通线性图标即使语义与天气相关，也只能遵循各自的小尺寸组件契约，不能放大后替代 `icon_weather1`。数据可视化必须编码主数值、进度或状态，不得为填充留白而添加。

### 辅助内容 Supporting Content

- 必须帮助用户理解主信息或决定下一步。
- 不得加入与主意图无关的推荐、广告或快捷入口。
- `2×4` 可将多行松散信息放入独立子表面进行分组（如 `split-two-column` 右栏小卡、`linear-progress` 详情背板）；普通列表最多 3 行，带图表时最多 2 行，日程/会议最多 2 条。
- 辅助信息落在右区或底部辅助面板时，必须围绕主焦点聚合，不散落四角。

### 操作 Action

- 卡片操作统一使用 `ActionUnit`，禁止基础 `Button`；`taskspec.eventCandidates` 为空时不得生成 `ActionUnit`，也不得生成任何 `onClick`。
- 2×4 只使用 `state:"capsule"` 或 `state:"tile"`，不使用 `icon-round`。
- `capsule` 用于底部或侧栏短按钮：固定 `140×36vp`、圆角 70 全圆角（产物不得手写 `width/height/padding/borderRadius/backgroundColor/fontColor`）；必须有 `label` 与来自候选事件的 `onClick`。
- `tile` 只用于并列的竖向操作卡：宽 64-80vp、高 80-112vp，必须有来自 `assetCandidates` 的匹配 icon 与 2-4 字标签。
- 浅色卡必须显式写与主题色包一致的 `actionInk`；需要固定浅底时可把同色 `panel` 写入 `actionSurface`。强背景使用 `actionInk:"#FFFFFFFF"`、`actionSurface:"#33FFFFFF"`，避免纯白大胶囊。
- `onClick` 的 call 与静态 args 逐字段复用 eventCandidates；动态参数改写成 `{"path":"/..."}` 并补同路径数据样例行；禁止 `{{ }}`、`${...}` 或字符串内 path，禁止样例里的 `demo://`。
- 默认至多 2 个显式操作，且次操作必须具备独立、即时目标且不与主操作竞争；仅当用户逐项明确要求同一服务对象下 3-4 个同层级快捷操作时，才允许 four-action-hub 的 3-4 个 tile。
- 有底部胶囊时使用 `titled-action` 根结构：title bar 20 + gap 4 + content 296×72 + gap 4 + capsule 140×36，从顶排布；胶囊固定在底部安全区内，不拉满 320vp 宽卡，不贴圆角边缘、不被裁切。
- 按钮文案优先 2-4 字，不超过 6 字；超过 6 字时降级到 `body-s-regular`，不得继续降低；不截断用户明确要求的 CTA，按钮宽度需覆盖文字宽度和左右至少 8vp 内边距。
- 可点击视觉尺寸至少 24vp，热区至少 40vp。
- 无按钮时，整张卡片为一个热区。
- 有一个或两个按钮时，卡片内容区与每个按钮分别构成不重叠热区，并提供独立点击反馈；点击按钮只触发按钮操作，不得同时触发内容区或整卡操作。
### 列表 List

- `list-row`（如 `todo_item`）高 `33vp`，列表项文字使用 `body-m-regular`(14vp)，内边距约 `10/12vp`，行圆角 8vp、浅灰背板；左侧圆形 check 占位 + 右侧单行文字；三行闭合 `33×3 + 8×2 = 115`。
- `2×4` 普通列表最多 3 行；带图表时最多 2 行；日程/会议类最多 2 条（每条 `TimelineUnit` + 文字列）。
- 仅当前决策项可将一段主文案升至 subtitle 层级。
### 进度 Progress

可选类型：

- 环形（`RingUnit`）：单一连续比例，一个焦点。
- 线性（`ProgressUnit`）：连续进度或多行详情组合。

禁止手写基础 `Progress` 表达环或线性进度。`RingUnit` 的 `size` 只能取 40/44/52/80/92/98；`state` 只能是 `center-text`、`center-icon`、`center-icon-below-text`；语义色只用 green/blue/orange/red，禁止紫色；`centerIcon` 必须来自 `assetCandidates`。`ProgressUnit` 的 `state` 只能是 `bar`、`numeric-single`、`numeric-single-caption`、`plain`，必须有 `value` 与 `total`，`caption` 至多一行。

高级组件展开后的真实高度必须计入父容器：`plain` 36vp、`numeric-single` 48vp、`numeric-single-caption` 74vp。若在 `plain` 外再放一个 16vp caption，外层 `progress_area` 至少 `36 + gap 4 + 16 = 56vp`，禁止只声明 40vp。

- 没有目标、总量、范围或阶段参照时，直接使用文字或数值，不为装饰而添加进度。
- 一个连续数值相对单一目标是唯一主焦点时使用大环（`large-ring` 骨架，环 92vp）；四个同类对比占比使用 `quad-rings`（4 个 40vp 环，至多 4 个）。
- 环内读数不能再在右侧重复；同一数据对象只保留一个环心读数（评分或时长二选一）。
- 环形进度必须保持正圆并使用系统或运行时进度组件；进度弧线两端必须使用圆形端帽（SVG 对应 `stroke-linecap="round"`），底轨统一使用中性 `progress_ring_track`（浅色 `#00000019` / 深色 `#FFFFFF19`，随主题翻转）。
- 环心同时展示数值与单位时，数值和单位必须保持同一行，不得上下换行；空间不足时先降单位字号（最低 8vp），再降数值一个文字层级；仍不能清晰展示时将整组移至圆环旁边，不继续缩小或强行塞入圆心。
系统不鼓励密集按钮网格、多步表单、隐藏手势交互。卡片操作默认保持单一主操作;2×4 显式操作上限 2 个（第二个必须具备独立即时目标），仅四操作 hub 允许 3-4 个由用户逐项明确要求的同层级操作。

## Do's and Don'ts

**Do**

- 默认颜色用 token 名引用;让主题层解析明暗。`card-root` 先铺 `comp_background_primary`，再在精确命中 6 个已登记场景之一时叠加对应遮罩渐变。
- 用 `value-group.value` 与 `metric-primary` 确立一个主数据点;其他一切退让。
- 所有内容保持在安全内容区内（`content_root` padding 固定 12 → 296×136vp）。
- 按等分公式选择标准变体；每张卡只选一个标准变体，不做非对称分栏，不自由发明布局。
- 提供当前已登记的反馈状态——默认按钮组件与 `button-primary-pressed`。
- 卡片本体用 `corner_radius_level10`(20vp，root 固定值);胶囊按钮为全圆角胶囊(固定 140×36vp、圆角 70);标签用 `corner_radius_level2`(4vp)。
- 所有 `background_gradients` 预设必须原样使用其 stops；不得在产物中自行配对、手调或新建渐变。

**Dont**

- 不要在普通组件或正文中硬编码 hex;仅 `card-root` 场景化渐变背景可直接指定渐变色。
- 不要把已废弃的旧场景渐变、扩展色板或自定义渐变用作 `card-root` 背景。
- 不要给装饰性元素加投影;用调性分层表达深度。
- 不要让 2×4 超过 2 个显式操作(四操作 hub 除外，且必须由用户逐项明确要求)。
- 不要在同一组件族内混用圆角。
- 不要引入第四种字重、新字体族,或低于 8vp 的字号。
- 不要把 `warning` 红色用作品牌色;它专用于风险与紧急。
- 不要混用透明度档位——只能用规定的 13 档 alpha。
- 不要在 `themes.dark` 之外另起一个主题层。
- 不要为内容拉大画布;按画布裁剪内容。
- 不要通过缩小字号、压缩安全边距、负间距、绝对定位或裁切来掩盖内容过载。
- 不要让按钮覆盖图表、列表或内容预览。
