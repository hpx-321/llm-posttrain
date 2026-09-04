---
version: alpha
name: HarmonyOS A2UI Service Card
description: HarmonyOS 桌面 widget 服务卡片(`2×2` / `2×4`)的设计系统——一眼扫读、建议单一主操作、浅层任务入口。
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

  # Metric tier — 40 / 32; reserved for the single hero metric in 2×2 cards
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
    title-leading-icon-trailing: 20vp
    button-icon-2x2-content: 16vp
    button-with-icon-content: 20vp
    display-ring-center: 24vp
    paired-data-ring-center: 16vp
    hero-visual: 56vp
  svgClassification:
    resourceIconAttribute: data-resource-icon
    datavizAttribute: data-dataviz
    unclassifiedInlineSvgAllowed: false
    # `data-dataviz` 的值必须是下列已注册组件 id 之一；任何其它取值视为手绘数据可视化，机器按 unregistered_dataviz 拒收。
    allowedDatavizValues: [display-ring, paired-data-ring, linear-progress]
layout_slots:
  canvas:
    "2x2":
      width: 160vp
      height: 160vp
      safeMargin: "{spacing.safe-margin}"
      layoutMode: vertical-stack
    "2x4":
      width: 320vp
      height: 160vp
      safeMargin: "{spacing.safe-margin}"
      layoutMode: horizontal-or-vertical-composition
  regions:
    title-area:
      required: true
      placement: top
      heightMode: content
      maxLines: 1
      gapAfter: 8vp
      children:
        leading-icon:
          required: false
          variants:
            leading:
              size: 12vp
              placement: leading
              color: "{colors.icon_primary}"
            trailing:
              size: 20vp
              placement: top-right
              color: "{colors.icon_secondary}"
          maxPerCard: 2
        title-text:
          required: true
          typography:
            regular-card-primary: "{typography.subtitle-s-medium}"
            regular-card-prominent: "{typography.subtitle-l-medium}"
            numeric-card: "{typography.body-s-regular}"
          color: "{colors.font_primary}"
          maxLines: 1
        subtitle-text:
          required: false
          typography: "{typography.caption-l-regular}"
          color: "{colors.font_secondary}"
          maxLines: 1
      layoutVariants:
        "2x2.withButton":
          titleMaxLines: 1
          subtitleAllowed: false
    content-area:
      required: true
      placement: middle
      gapBeforeAfterTitle: 8vp
      heightMode: fill-remaining-budget
      fillBehavior:
        mainAxis: consume-all-space-between-title-and-button-or-safe-edge
        crossAxis: stretch
        minHeight: 0
        parentRequirement: direct-slot-container-is-full-height-vertical-layout
        contentAlignmentDoesNotChangeAreaHeight: true
      contentAlignment:
        scope: content-group-within-content-area
        preserveComponentInternalLayout: true
        fullAreaContentRemainsFill: true
        byContentType:
          plain-text:
            appliesWhen: content-area-has-no-content-preview-dataviz-or-icon-children
            detection: 区域内只有纯文字（正文、状态文案、辅助说明、value-group 数值组/大数字），无 SVG/图片/图表/进度环/图标等可见视觉装饰节点
            vertical: bottom
            horizontal: left
            rationale: 纯文字与数值主视觉不争夺纵向注意力，居底居左让标题与按钮区的间距节奏稳定；value-group 大数字作为主决策信号仍属文本语义，归入此类
          hero-icon:
            appliesWhen: content-area-contains-hero-icon-or-scene-illustration-but-no-dataviz
            detection: 区域内有一个承载场景语义的装饰型大图标（天气图标、心率图标、场景插画等 hero-icon / data-hero-visual 节点，或图标+温度文字的 hero-visual-text 横向组合），但不含图表/进度环等数据可视化
            vertical: center
            horizontal: flex-start
            rationale: 装饰型 hero 图标垂直居中让其与卡片整体重心对齐，居左保留与标题的阅读起点一致；图标尺寸 48–56vp，不撑满 content-area
            precedence: below-visual-content
          visual-content:
            appliesWhen: content-area-contains-content-preview-dataviz-or-display-ring
            detection: 区域内有 content-preview（图表/图片/媒体）、data-dataviz SVG、display-ring 或 paired-data-ring 等数据可视化节点；value-group 数值组不属于此类
            vertical: center
            horizontal: center
            rationale: 表现型主视觉（图表、环形进度）是卡片视觉焦点，须在 content-area 内上下左右居中对齐；具体 fill/fixed 占用规则由各组件 fillContract 决定，contentAlignment 仅约束内容组的居中锚点
            precedence: highest
      defaultTypography: "{typography.body-s-regular}"
      typographyRule: ordinary-content-uses-12vp-by-default; promote-only-primary-decision-signal
      heightBudget:
        "2x2":
          withTitleAndButton: 58vp
          withTitleAndTextButton: 58vp
          withTitleAndIconButton: 64vp
          withTitleOnly: 102vp
        "2x4":
          withTitleAndButton: flexible-after-slot-budget
          withTitleOnly: flexible-after-slot-budget
      componentBackground: optional
      gapAfterWhenButton: 8vp
      overflowPolicy: remove-secondary-content-before-render
      children:
        content-preview:
          required: false
          role: image | chart | list | map | media | placeholder
          fillMode:
            hero-or-chart: fill
            sparkline-or-progress: fixed
          fillContract:
            fill: container-and-dataviz-svg-use-full-width-and-height-with-min-height-0
            fixed: component-declares-explicit-height-and-must-not-stretch
          backgroundColor: "{colors.comp_background_tertiary}"
          rounded: "{rounded.corner_radius_level4}"
        value-group:
          required: false
          role: numeric
          direction: horizontal-baseline
          children:
            value:
              typography: "{typography.metric-primary}"
              color: "{colors.font_primary}"
              maxLines: 1
            unit:
              typography: "{typography.body-s-regular}"
              color: "{colors.font_secondary}"
              maxLines: 1
            assistive-text:
              required: false
              typography: "{typography.body-s-regular}"
              color: "{colors.font_secondary}"
              maxLines: 1
        bottom-information-surface:
          required: false
          role: paired-text-summary
          placement: bottom-of-content-area
          allowedWhen: "2x2.withTitleOnly"
          buttonAreaAllowed: false
          padding: "{spacing.md}"
          rounded: "{rounded.corner_radius_level6}"
          children:
            title-text:
              typography: "{typography.body-s-bold}"
              maxLines: 1
            assistive-text:
              typography: "{typography.body-s-regular}"
              maxLines: 1
      allowedContentCombinations:
        "2x2.withTitleAndButton":
          - one-decision-state-plus-primary-action
          - one-decision-value-plus-primary-action
          - one-line-decision-sentence-plus-primary-action
        "2x2.withTitleAndIconButton":
          - one-decision-state-plus-one-essential-assistive-line-plus-icon-action
          - one-decision-value-plus-one-essential-assistive-line-plus-icon-action
          - one-compact-fixed-dataviz-plus-icon-action
        "2x2.withTitleOnly":
          - one-decision-state-plus-up-to-two-assistive-lines
          - one-decision-value-plus-up-to-two-assistive-lines
          - content-preview-only
          - paired-ring-progress
          - one-paired-text-summary-surface
          - one-line-decision-sentence-only
        "2x4":
          - one-decision-signal-plus-primary-action
          - content-preview-plus-summary
          - one-decision-value-plus-action-context
      forbiddenContentCombinations:
        "2x2.withTitleAndButton":
          - sentence-plus-large-number-plus-status-chip-plus-button
          - multi-line-text-plus-status-chip-plus-button
          - duplicated-metric-plus-button
        all-actionable-cards:
          - status-plus-value-when-they-express-the-same-decision
          - status-plus-exact-delta-when-the-delta-does-not-change-action
          - explanatory-copy-plus-repeated-status
          - secondary-action-without-a-distinct-immediate-user-goal
    button-area:
      required: false
      requiredWhen:
        - query-specifies-concrete-action
        - query-specifies-click-or-navigation-action
      wholeCardClickMaySubstitute: false
      placement: bottom
      marginTop: "{spacing.md}"
      children:
        action-button:
          componentBySize:
            "2x2": button-primary | button-secondary | button-icon-2x2
            "2x4": button-primary | button-secondary
          maxCount:
            "2x2": 1
            "2x4": 2
          arrangement:
            "2x2": single
            "2x4": single | vertical-stack
        icon-button:
          component: button-icon-2x2
          allowedSizes: "2x2"
          placement: bottom-right
          alignment: end
          selectionPriority: preferred-under-essential-content-pressure
          preferredWhen:
            all:
              - explicitActionCount: 1
              - essentialContentPressure: true
              - approvedExactActionIconAvailable: true
              - actionUnderstandableWithoutVisibleLabel: true
          essentialContentPressure:
            any:
              - primaryDecisionSignalPlusOneEssentialAssistiveLine
              - compactFixedDatavizRequiredForDecision
            excludes:
              - decorativeContent
              - duplicatedInformation
              - nonActionableContext
          forbiddenWhen:
            - approvedExactActionIconAvailable: false
            - actionUnderstandableWithoutVisibleLabel: false
            - actionRisk: destructive-or-irreversible
            - actionRequires: confirmation-or-consent
            - size: "2x4"
          fallback: use-size-appropriate-text-button
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
  "2x2":
    primaryObjectsMax: 1
    supportingLinesMax: 2
    actionableStatusMax: 1
    explicitActionsMax: 1
    numbersMax: 1
    pairedRingProgress:
      allowed: true
      ringMax: 2
      numbersMax: 2
      buttonAreaAllowed: false
  "2x4":
    primaryGroupsMax: 1
    supportingGroupsMax: 1
    explicitActionsMax: 2
    numbersMax: 1
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
    maxVisibleNumbers: 1
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
    "2x2": { x: 48px, y: 48px, width: 160px, height: 160px }
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
      "2x2": 2
      "2x4": 3
    maxRowsWithChart:
      "2x4": 2
  action:
    explicitActionsBySize:
      "2x2": 1
      "2x4": 2
    actionGroupBySize:
      "2x2":
        arrangement: single
      "2x4":
        arrangement:
          - single
          - vertical-stack
        verticalStackMax: 2
        interButtonGap:
          min: 8
          max: 12
          unit: vp
    requiresClearLabelOrSymbol: true
    geometry:
      minimumVisualSize: 24
      minimumHotZone: 40
      circularButton2x2:
        width: 30
        height: 30
      iconButton2x2:
        width: 30
        height: 30
        iconSize: 16
        placement: bottom-right
        alignment: end
      capsuleHeight: 36
      minimumEdgeDistance: 12
      unit: vp
      radiusRule: fixed-20vp
    visualStyle:
      allowed:
        - ordinary-filled
      emphasizedAllowed: false
      textOnlyAllowed: false
      useDirectTokenColorAssembly: true
      allowedShapes:
        - circular
        - capsule
  progress:
    allowedKinds:
      - ring
      - linear
      - segmented
    linearPlacement:
      appliesTo: 2x2
      placement: bottom-of-content-area
      fixedHeightRequired: true
      height: 8vp
      supportingTextPlacement: immediately-above-progress
      precedence: overrides-content-group-center-alignment
    singleRingMaxPerCard: 1
    pairedRingMaxPerCard:
      "2x2": 2
      "2x4": 0
    ringVariants:
      display-ring:
        allowedSizes: "2x2 | 2x4"
        size: 52vp
        strokeWidth: 6vp
        strokeAlignment: inside
        trackColor: "{colors.progress_ring_track}"
        progressStrokeLinecap: round
        placement: content-area | bottom-left-of-content-area
        centerContent:
          exclusive: true
          textTypography: "{typography.subtitle-m-regular}"
          iconSize: 24vp
      paired-data-ring:
        allowedSizes: "2x2"
        ringCount: 2
        arrangement: horizontal
        outerSize: 44vp
        strokeWidth: 6vp
        strokeAlignment: inside
        trackColor: "{colors.progress_ring_track}"
        progressStrokeLinecap: round
        centerIconSize: 16vp
        labelPlacement: below-ring
        labelTypography: "{typography.caption-m-regular}"
        ringGap: "{spacing.xxl}"
        labelGap: "{spacing.xs}"
        buttonAreaAllowed: false
    ringCenterLabel:
      appliesTo: display-ring
      numberAndUnitSameLine: true
      wrappingAllowed: false
      horizontalAlignment: center
      verticalAlignment: center
      minimumUnitSize: 8
      fitOrder:
        - keepDefaultNumberSizeWhenContentFits
        - reduceUnitToMinimumSize
        - reduceNumberByOneTypographyLevel
        - moveLabelOutsideRingIfStillUnreadable
    radius:
      heightAbove10vp: 4
      heightAtOrBelow10vp: 2
  snapshot:
    mustMatchRealLayout: true
    rectangularWithoutBakedCorner: true
    lightAndDarkRequired: true
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.font_on_primary}"
    gradientBackgroundOverride: "{button_color_rules}"
    typography: "{typography.body-m-regular}"
    typographyFallback: "{typography.body-s-regular}"
    fallbackWhen: text-length > 6
    rounded: "{rounded.corner_radius_level10}"
    padding: 10vp 8vp
    gap: 8vp
    contentAlign: center
    height: 36vp
  button-primary-pressed:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.font_on_primary}"
    gradientBackgroundOverride: "{button_color_rules}"
    typography: "{typography.body-m-regular}"
    typographyFallback: "{typography.body-s-regular}"
    fallbackWhen: text-length > 6
    rounded: "{rounded.corner_radius_level10}"
    padding: 10vp 8vp
    gap: 8vp
    contentAlign: center
    height: 36vp
  button-secondary:
    backgroundColor: "{colors.comp_background_tertiary}"
    textColor: "{colors.font_primary}"
    gradientBackgroundOverride: "{button_color_rules}"
    typography: "{typography.body-m-regular}"
    typographyFallback: "{typography.body-s-regular}"
    fallbackWhen: text-length > 6
    rounded: "{rounded.corner_radius_level10}"
    padding: 10vp 8vp
    gap: 8vp
    contentAlign: center
    height: 36vp
  button-icon-2x2:
    size: 30vp
    iconSize: 16vp
    placement: bottom-right
    contentAlign: center
    rounded: "{rounded.corner_radius_level10}"
    minimumHotZone: 40vp
    backgroundColor: "{colors.comp_background_tertiary}"
    iconColor: "{colors.icon_primary}"
    gradientBackgroundOverride: "{button_color_rules}"
    requiredAttribute: { data-component: button-icon-2x2 }
    iconSource: approved-exact-semantic-match-from-resource-icon-catalog
    visibleText: false
    accessibleName:
      required: true
      source: explicit-action-label
    hotZoneExtension:
      allowedInto: button-area-gap-and-card-safe-padding-only
      contentOverlapAllowed: false
      cardOverflowAllowed: false
  button-with-icon:
    structure: Row + Image + Text（onClick 仅挂外层 Row；内部 Image/Text 不绑定事件，不嵌套 Button）
    height: 36vp
    rounded: "{rounded.corner_radius_level10}"
    padding: 左右至少 8vp
    gap: 8vp
    contentAlign: center
    iconSize: 20vp
    typography: "{typography.body-m-regular}"
    typographyFallback: "{typography.body-s-regular}"
    fallbackWhen: text-length > 6
    minWidth: 左右 padding + iconSize + gap + 标签压力宽度 × 1.2
    gradientBackgroundOverride: "{button_color_rules}"
    note: Button 组件仅支持 label（纯文字按钮），不支持图标与 children；需要图文按钮时必须使用本形态
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
    padding: "{spacing.safe-margin}"
  list-row:
    typography: "{typography.body-s-regular}"
    height: 32vp
    padding: 0 8vp
  progress-ring-label:
    typography: "{typography.title-s-bold}"
    textColor: "{colors.font_primary}"
---

## Overview

本系统描述 **HarmonyOS 桌面 widget 服务卡片** 的视觉身份——`2×2` 与 `2×4` 两种小尺寸、可一眼扫读的桌面表面,各自承载**一条核心信息**,并**默认单一主操作；仅当次操作有独立且即时的用户目标时才附带**。品牌基调是**冷静、技术感、确定**:受控的场景渐变托起一个高对比的数据点,再用唯一一抹饱和强调色告诉用户"该做什么"。

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

遮罩渐变卡片上的所有按钮（主按钮、次按钮和图标按钮）必须由卡片所选注册预设的 `buttonColorContext` 决定颜色，不得继续沿用组件的默认蓝底、灰底或自行选择无关颜色。`backgroundClass` 与 `primaryHue` 必须直接读取该预设，不能由 Agent 另行声明或改写。按钮颜色按卡片背景类分流，合法形态为正向枚举——不匹配任何登记形态即不合规；按钮仅使用普通填充样式，任何合法形态都不携带描边（`borderWidth` / `borderColor`）。

- **浅色遮罩场景 (`light-overlay-gradient`)**：以下三种背景形态合法，前景按形态配对：
  - **10% 直写（正典）**：按钮背景使用 `buttonColorContext.primaryHue` 的 10% 透明度（alpha 档 `19`，进位孪生 `1A` 同效），按钮文字或图标使用其 100% 不透明色；
  - **预合成浅底**：按钮背景使用 10% 主色在纯白宿主上的不透明预合成等效色（opaqueEquivalent flatten 写法，仅适用浅色宿主），前景仍为 primaryHue 100%；
  - **实心主色**：按钮背景使用 `primaryHue` 的 100% 不透明色，前景使用白色（`font_on_primary`）。
  - 不得对整个按钮设置 `opacity: 10%`。
- **不透明场景渐变 (`colored-gradient`)**：按钮背景使用白色，按钮文字或图标使用 `buttonColorContext.primaryHue`；卡片普通文字与图标使用反色文本阶。

以上渐变按钮规则是组件默认色的强制覆盖规则，不是可选建议；按钮的背景分类、背景色和前景色必须成组解析，不得只应用其中一项。若渐变卡片缺少 `buttonColorContext`，不得通过猜测或退回默认按钮颜色完成渲染。

### 状态 token

全局状态 token 统一为 `warning` / `alert` / `confirm`,不得另起其它同义 token。需要兼容历史命名时,应在解析层把旧语义映射到这三个标准 token,但设计文档和组件定义只书写标准 token。

### Hex 与透明度规则

颜色统一书写为 8 位 hex,格式为 `#RRGGBBAA`,其中后两位 `AA` 描述透明度。仅使用以下透明度档位(对应 13 档 alpha):`FF`(100%) / `E5`(90%) / `CC`(80%) / `B2`(70%) / `99`(60%) / `7F`(50%) / `66`(40%) / `4D`(30%) / `33`(20%) / `26`(15%) / `19`(10%) / `0C`(5%) / `00`(0%)。其他透明度档位一律不允许。遮罩渐变使用 `19` → `00`；按钮按《Gradient Card Button Colors》的登记形态配对（10% 直写为 `19` 背景 + `FF` 前景；实心主色为 `FF` 背景 + `FF` 白前景）；不得通过 CSS `opacity` 降低整个按钮及其文字的透明度。

### 对比度

普通阅读文本与背景的对比度**强制不低于 3:1**。暗色模式下,文字阶自动从黑翻成白,以保持同样对比比。正文级文本（body 层级的长文本阅读）**建议不低于 4.5:1**（与 WCAG AA 对齐，建议级非强制）；对比度判定必须按「前景 × 有效背景栈」逐层 alpha 合成后计算（卡片基底 → 渐变位置色 → 祖先底板），不得只对单点背景色估算。按钮子树内的文字与图标旁标签不按 3:1 强制档判定，降为建议级提示——按钮配色已由 `button_color_rules` 的登记形态全权管辖；其余文本仍按强制档执行。

## Typography

字体系统建立在单一字体族 **HarmonyOS Sans SC** 上,通过字号与字重两个维度表达层级。除 5 类基础文字角色外，`metric-primary` 与 `metric-primary-with-support` 是 `2×2` 主数值的专用语义 token；每级各司其职。刻意避免混用字重与装饰性变体。

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

- **单一数据点**:无下方辅助信息时，数字呈现卡主数字用 `metric-primary`(40vp / 700)；下方存在 `12vp` 辅助信息时改用 `metric-primary-with-support`(32vp / 700)，以确保组内垂直预算。单位与辅助信息使用 `body-s-regular`(12vp / 400)
- **常规卡片主标题**:`subtitle-s-medium`(14 / 500)或 `subtitle-l-medium`(18 / 500)
- **副标题 / 辅助**:`body-s-regular`(12 / 400)或 `caption-l-regular`(12 / 400)
- **正文**:`body-s-regular`(12 / 400)是默认阅读字号
- **按钮文字**:默认用 `body-m-regular`(14 / 400);当按钮文案多于 6 个字时降级到 `body-s-regular`(12 / 400),且不得继续低于 `body-s-regular`
- **最小字号**:按 font token 定义,最小为 `caption-s-regular`(8 / 400);任何内容不得小于 8vp
- **同尺寸不同语境的层级差异**用字重区分(例如 14vp 既可以 `subtitle-s-medium` 表达强调,也可以 `body-m-regular` 表达正文)

### 缩放与行高

系统字号缩放支持 0.8x – 1.3x。20vp 及以上的字号不放大,以维持布局完整性。

## Layout & Spacing

又名 "Layout & Spacing"。

本系统采用**固定比例画布 + 安全区构图**,而非流式栅格。每个卡片尺寸都有由宿主运行时提供的固定画布(`2×2 = 160×160vp`,`2×4 = 320×160vp`);卡片永不硬编码自身的外部尺寸。

桌面 widget 由宿主桌面承载和裁切,卡片内部不得假设可滚动、可分页或可扩展高度。浏览器预览壳只用于模拟宿主环境;真正的卡片内容必须始终落在 `widget` / `card-root` 的固定画布和 12vp 安全区内。

浏览器 HTML 必须遵循 `browser_preview_shell` 的 `design-card-html-v1` 契约，以便审查台按稳定坐标加载。`html, body` 必须清除默认 margin 和 padding。`preview-app` 是 `1440×1100px` 的相对定位画布；`toolbar` 绝对定位在 `(0, 0)`，尺寸为 `1440×56px`；`preview-stage` 绝对定位在 `(0, 56px)`，尺寸为 `1440×1044px`。`preview-slot[data-size="2x2"]` 必须绝对定位在 stage 的 `(48px, 48px)`，内部 `widget[data-size="2x2"]` 固定为 `160×160px`；因此 `2×2` 卡片相对整个文档的左上角坐标恒为 `(48px, 104px)`。`2×4` slot 固定在 stage 的 `(256px, 48px)`，widget 为 `320×160px`。主题切换、内容长度和是否缺少另一尺寸都不得改变 slot 坐标；窄 viewport 允许滚动，不得通过 `transform: scale(...)`、`zoom` 或响应式重排移动、缩放卡片。

标准 DOM 顺序为 `preview-app > toolbar + preview-stage > preview-slot > widget.card-root`。`html` 必须标记 `data-artifact-contract="design-card-html-v1"`，slot 与 widget 必须分别标记规范化的 `data-size="2x2"` 或 `data-size="2x4"`。工具栏属于预览外壳，不得插入 slot 内；业务内容只允许进入 `widget.card-root`。审查台可以读取这些稳定 class、属性和坐标进行 iframe 预览或定点裁切，但不得据此自动评价设计质量。

**预览壳 caption 禁令**：产物中不得输出任何 shell-level caption 节点（如 `.caption`）。预览壳曾用此类节点标注尺寸、尺寸别名、点击行为和主题切换提示（例如 `160×160vp · 2×2 · 整卡点击打开日历 · L/D 切换主题`），这些是开发调试元数据，不是卡片业务内容；审查台按 slot 坐标做定点裁切时，caption 若落在 slot 边界内或紧贴其下方会被裁进卡片画面，造成内部元数据泄露。尺寸与点击行为的说明只能保留在 toolbar 区域（`.toolbar` 内），不得作为独立节点输出到 stage 或 slot 中。

统一的 **12vp 安全边距**把所有内容从每条边内缩。安全区之内,七档间距刻度(`xxs 2 / xs 4 / sm 6 / md 8 / lg 12 / xl 16 / xxl 24`)统御纵横向节奏。特定元素对之间使用语义间距:

- 标题 → 副标题:2–4vp
- 标签 → 数值:4–6vp
- 图标 → 文字:6–8vp
- 组 → 组:8–12vp
- 内容 → 操作:8–12vp

### 尺寸密度

`2×2`：

- 一个主信息对象。
- 最多两个辅助信息行。
- 最多一个明确按钮。
- 不承载长段落或密集列表。

`2×4`：

- 一个主信息组和一个辅助信息组。
- 无按钮时整卡一个热区；有一个或两个按钮时，内容区与每个按钮分别构成独立热区。
- 可以展示短时间线、相关双列或横向媒体结构。
- 不得演变为仪表盘或快捷入口矩阵。
- 普通列表最多 3 行；带图表时最多 2 行，超过后必须先降级图表或删减列表。

### 尺寸选择与布局适配

选择 `2×2`：

- 一个状态、数值、日期、图片或操作即可完成意图。
- 辅助信息不超过两项。
- 整卡点击足够。

选择 `2×4`：

- 主信息需要一个相关辅助信息组。
- 需要短时间线、媒体详情或明确操作。
- 热区都具有真实价值且容易区分。

按钮的存在不会自动要求使用 `2×4`；当主信息和一个按钮能够在安全边距内清晰呈现时，可以使用 `2×2`。

### `2×4` 收缩为 `2×2`

按以下顺序保留：

1. 主状态或主数值。
2. 理解主信息所必需的标签。
3. 如果操作属于主意图，则保留主操作。
4. 最多两条辅助信息行。

优先删除：

- 长说明。
- 重复的应用或服务名称。
- 第三层元数据。
- 额外操作。
- 密集列表和装饰信息。

### `2×2` 扩展为 `2×4`

- 不放大原布局。
- 保持原主信息的视觉主导地位。
- 只增加相关的时间、趋势、上下文、预览或一个更清晰的操作。
- 没有有价值的辅助信息时，保留留白，不制造填充内容。

### Slot Model

卡片生成以 `layout_slots` 为第一层布局契约。HTML、A2UI 与 ArkUI 输出都应先选择卡片尺寸,再把内容映射到 `title-area`、`content-area`、`button-area` 三个区域;不得从示意图反推绝对坐标。

**title-area** 是必选槽,位于安全区顶部,用于承载卡片的上下文。标题区域由可选 `leading-icon` 与必选 `title-text` 组成;`leading-icon` 有两种合法形态:**左上前置 12×12vp**(与标题文字水平对齐)或**右上 20×20vp**(贴标题区右上角,可承载应用图标、营销 Logo 或装饰/状态图标)。**桌面服务卡片的 `title-text` 统一使用 `body-s-regular`(12vp / 400)**,不再使用 14vp 或 18vp 的 subtitle 层级——12vp 标题为 content-area 的主数值和主视觉释放最大纵向空间,且与卡片"一眼扫读"的定位一致;副标题与辅助信息同样使用 `caption-l-regular`(12vp / 400)。`leading-icon` 一卡至多两个(左上 12vp 一个 + 右上 20vp 一个);右上角图标必须来自本地 `resource` SVG(`data-resource-icon` 标注并通过 catalog 校验),不得使用 emoji 或外链。

**content-area** 是必选槽,承载卡片的主信息或主视觉。内容区的普通正文、列表行、时间与说明文字默认优先使用 `body-s-regular`(**12vp / 400**),不得因内容较多默认升至 14vp；只有承载当前决策的主数值、主状态或需强调的一行主文案，才可按语义升至对应的 display / subtitle 层级。常规信息呈现卡可以放置 `content-preview`,包括图片、图表、列表、地图、媒体封面或占位底板。数字呈现卡使用 `value-group`:无下方辅助信息时核心数字使用 `metric-primary`(40vp / 700)，有下方 `12vp` 辅助信息时使用 `metric-primary-with-support`(32vp / 700)；同一组内的单位与辅助信息使用 `body-s-regular`(12vp / 400)。

`content-area` 与前方 `title-area` 必须保持 **8vp** 间距。该间距属于槽位栅格,优先于内容区内部的左下对齐或自适应规则,不得因使用 `flex: 1`、`justify-content` 或紧凑内容而折叠、吞并或省略。

`content-area` 的 `fill-remaining-budget` 表示区域本身必须占满 `title-area` 下方至 `button-area` 上方的全部剩余高度；没有 `button-area` 时,占满至安全区底部。浏览器 HTML 中三个槽位的直接父容器固定为全高纵向布局的 `.card-content`；A2UI 与 ArkUI 使用等价的全高纵向槽位容器。

`content-area` 的对齐规则按内容类型区分，不得一刀切：

- **纯文本/数值内容**（区域内只有正文、状态文案、辅助说明、`value-group` 数值组/大数字，无 SVG、图片、图表、进度环或图标等可见视觉装饰节点）：内容组整体锚定到 `content-area` **左下角**（纵向 `bottom`、横向 `left`）。这是默认对齐，适用于常规信息呈现卡、决策状态文案卡、数值卡等。`value-group` 大数字作为主决策信号也归入此类——它仍是文本语义而非视觉装饰，左下对齐让标题与按钮区的间距节奏稳定。存在多个纯文本/数值元素时，应先组成一个内容组，再将该内容组整体锚定到左下角。
- **装饰型 hero 图标**（区域内有一个承载场景语义的大图标，如天气图标、心率图标、场景插画等 `hero-icon` / `data-hero-visual` 节点，或由图标+温度文字组成的 `hero-visual-text` 横向组合，但不含图表/进度环等数据可视化）：内容组在 `content-area` 内**纵向垂直居中、横向居左对齐**（纵向 `center`、横向 `flex-start`，即 `justify-content:center; align-items:flex-start`）。这类图标是装饰性主视觉，垂直居中让其与卡片整体重心对齐，居左保留与标题的阅读起点一致；图标尺寸通常为 48–56vp，不得撑满整个 content-area。判定：当 content-area 内最大的可见节点是一个语义图标（而非 ring/chart）时，套用本类。
- **表现型内容**（区域内有 `content-preview` 图表/图片/媒体、`data-dataviz` SVG、`display-ring` 或 `paired-data-ring` 等数据可视化节点）：内容组在 `content-area` 内**上下左右垂直居中对齐**（纵向 `center`、横向 `center`）。表现型主视觉是卡片视觉焦点，居中能保证环形图、图表在可用空间内对称呈现。`value-group` 数值组**不属于**此类——它归纯文本/数值内容。具体 fill（占满）或 fixed（固定高度）占用规则由各组件 `fillContract` 决定，本对齐规则只约束内容组的居中锚点。

判定口径（三类的优先级）：先检测是否含 `data-dataviz`/`display-ring`/`paired-data-ring`/`content-preview` 等表现型数据可视化节点——有则套用居中对齐（center/center）；否则检测是否含 `hero-icon`/`data-hero-visual` 等装饰型图标——有则套用 hero 图标对齐（center/flex-start，垂直居中居左）；两者皆无才套用纯文本/数值左下对齐（flex-end/flex-start）。`value-group`/大数字不参与表现型判定，始终归入纯文本/数值类。不允许把表现型数据可视化强行贴到左下角，也不允许把纯文本/数值内容居中悬浮。

内容对齐不得改变 `content-area` 的高度；内部内容较少时,区域本身仍不得按内容高度收缩。所有尺寸都必须保留显式 `content-area` 容器,不得用 `body`、左右面板或其他自定义容器替代该槽位。由此,存在 `button-area` 时,内容区会消化中间剩余空间并将按钮区稳定推至安全区底部。

当图表或主视觉承担 `content-area` 的主要信息表达时,其 `content-preview` 使用 `data-content-role="chart" data-fill-mode="fill"`,容器及内部 `svg[data-dataviz]` 都必须沿横向和纵向占满可用区域,并设置 `min-height:0` 防止 flex 溢出。sparkline、进度条和阶段条属于紧凑数据组件,使用 `data-fill-mode="fixed"` 并声明明确高度,不得为了填满留白而纵向拉伸。`fill` 与 `fixed` 必须按可视化语义二选一。

`2×2` 的两块文字必须收敛为 `bottom-information-surface`：标题为 `body-s-bold`(12vp / 700)，辅助文本为 `body-s-regular`(12vp / 400)，底板内边距固定为 `8vp`。该底板贴靠 `content-area` 底部，用于在内容区内收敛相关信息；使用它时不得出现 `button-area`，也不得作为额外层级或独立操作入口。

**button-area** 默认是非必选槽。只有当用户意图需要显式操作时才出现；但当 query 提到具体操作，或包含点击、打开、进入、查看详情等跳转动作时，`button-area` 与承载该动作的显式按钮必须存在，不得用点击整张卡片跳转代替。按钮区固定贴近安全区底部,与 `content-area` 保持 8vp 间距。卡片默认只有一个主操作;`2×2` 最多 1 个按钮。当 `2×2` 中保留了一个主决策信号与一条不可删除的辅助信息，或保留了必要的紧凑数据可视化，且唯一操作有 approved 且语义精确的动作图标时，底部优先使用 `button-icon-2x2`。`2×4` 的容量上限是 2 个按钮，但次操作只有在具有独立、即时目标且不与主操作竞争时才可出现。按钮区直接位于卡片根背景上,不叠放到内容预览底板内部。

### Slot Budget

`2×2` 的安全区是 `126×126vp`。当卡片使用 36vp 文字按钮时,推荐栅格为 `16vp title / 8vp gap / 58vp content / 8vp gap / 36vp text button`；当命中紧凑内容规则并使用 30vp 图标按钮时，栅格为 `16vp title / 8vp gap / 64vp content / 8vp gap / 30vp icon button`。图标按钮的 40vp 热区只能向 8vp 间距与卡片安全边距内扩展，不得覆盖 `content-area` 或溢出 `card-root`。生成器不得借图标按钮保留装饰、重复信息或不影响下一步的上下文。

`2×2` 内容预算:

| 状态 | 安全区预算 | content-area 上限 | 可见内容组合 |
|------|------------|------------------|--------------|
| title + text button | 126vp | 58vp | 一条决策状态 / 一个主数值 / 一句短决策文案，三选一，再加文字主操作 |
| title + icon button | 126vp | 64vp | 一个主决策信号 + 最多一条必要辅助信息，或一个必要的紧凑定高数据可视化，再加唯一图标操作 |
| title only | 126vp | 102vp | 一条决策状态、一个主数值、双数据并列圆环或一块两文字信息底板，四选一；主数值必要时加最多两条直接影响操作的辅助信息 |

`2×2 + title + button` 禁止组合:一句话 + 大数字 + 状态胶囊 + 按钮;多行正文 + 状态胶囊 + 按钮;重复指标 + 按钮。若用户同时要求"中间一句话带数字""按钮""危险提示",危险提示应优先折叠为标题旁图标、短标签或和主数值同组的 1 个短状态词,不得额外占一整行。

横向比例带把 `2×4` 画布划分为两个区域:`62/38`、`55/45`、`50/50`、`30/70`、`15/85`。推荐搭配:数字强调用 `55/45`,时间线用 `30/70`,密集对比用 `15/85`,媒体预览用 `62/38`,状态用 `55/45` 或 `50/50`。

`2×2` 画布不做机械正方形切分;改为垂直堆叠或单一均衡块。`2×2` 与 `2×4` 之间的互转是**内容优先级重排**,不是重新排版。

### Content Density

服务卡片不是缩小版应用页面。每张卡片只能有一个主信息对象;辅助信息必须帮助用户理解主信息或决定下一步。

图物卡片采用 **necessary-actionable-only** 删减策略:只呈现与用户下一步操作直接相关的必要信息,非必要不呈现。生成器必须在布局前先判断信息优先级,再决定放入卡片的内容,不得先堆满再依赖缩小字号、裁切或换行补救。

### 三层信息预算：先决定动作，再挑选内容

信息取舍以**主操作**为根，而不是以“业务给了哪些字段”为根。先确定用户此刻唯一应做的事，再从候选信息中保留能帮助其做出这个动作的最小集合。每条候选信息都必须通过这个测试：**删除它以后，用户的下一步会改变吗？不会就不呈现。**

信息优先级从高到低为:主操作及其决策信号 > 操作上下文 > 会改变操作的辅助信息 > 有独立即时目标的次操作 > 解释性背景。低优先级内容只有在不挤压高优先级内容时才可出现。若同一含义已由主数值、状态色或按钮文案表达,其他位置不得重复表达。

文案必须短到可扫读:标题建议 2–6 字,主句不超过 12 字,状态标签不超过 4 字,按钮文案不超过 4 字。辅助句应优先改写为短标签或并入主信息组;无法并入时删除。数字默认最多出现 1 个——这是上限而非应凑满的配额——且必须影响用户判断或操作；仅 `2×2` 的双数据并列圆环可展示 2 个直接可比较的数据标签。不影响操作的精确数字、差值、示例数值、更新时间、说明性统计默认不呈现。能用"已超时""偏高""待处理"表达时,不要再同时呈现额外精确差值。

例如防沉迷卡片中,用户需要的是"现在是否危险"和"下一步去哪里处理"。推荐呈现为:标题"防沉迷"、主状态"已超时"、一个主按钮"设置"。若任务是让用户判断使用时长而非处理超时，则改为“已用 1.5 小时”，并删除“已超时”。红色危险只需作为第 2 层状态色/短标签进入同一信息组。不要同时放置"已超时"胶囊、"1.5 小时"大数字、"今日已用"辅助、"已超每日上限 30 分钟"完整警告句、"去设置"和"查看报告"两个按钮；这些内容都没有改变“去设置”这一下一步。

内容过多时优先删减低优先级内容,不得通过缩小字号到 token 下限以下、压缩安全边距、负间距、绝对定位或裁切来隐藏布局问题。所有可见内容必须保持在 `card-root` 的安全区内,不同区域之间不得重叠,也不得溢出卡片画布。

`2×4` 可使用一个主信息组和一个辅助信息组。若一侧使用图表,另一侧最多显示 1–2 条摘要列表;若需要显示 3 条以上列表,图表必须降级为单一数值或极简趋势线。

当 `button-area` 出现时,`content-area` 必须在按钮区之前结束,并保持 8–12vp 间距。按钮不得覆盖图表、列表或内容预览。

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

资源 SVG 的 24×24 等原始尺寸是坐标系，不是统一的最终显示尺寸。最终尺寸按场景选择：左上标题前置 `leading-icon` 12vp、右上 `leading-icon` 20vp、`button-icon-2x2` 内部图标 16vp、图文按钮（`button-with-icon`）内部图标 20vp、`display-ring` 中心图标 24vp、`paired-data-ring` 中心图标 16vp。图标类型的 `hero-visual` 在 56×56vp 下只能使用 `icon_weather1`，并必须同时标记 `data-resource-icon="icon_weather1"` 与 `data-hero-visual="weather-icon"`；普通单色或线性 catalog 图标一律不得放大到 56vp 充当 Hero。`data-dataviz` 仍可按自身组件契约使用 Hero 空间，但不属于图标。其他场景必须由对应组件契约明确尺寸，不得由原文件 width / height 决定。

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
| `corner_radius_level9` | 18vp | 按钮全圆角下限（胶囊 ≥18vp） |
| `corner_radius_level10` | 20vp | **卡片本体 (card-root 默认值)** |
| `corner_radius_level11` | 22vp | — |
| `corner_radius_level12` | 24vp | 大型容器 |
| `corner_radius_level16` | 32vp | 圆角卡片 |

### 主圆角与同族规则

- **容器与表面的主圆角**为 `corner_radius_level10`(20vp),与卡片本体一致
- **按钮主圆角**为 `corner_radius_level10`(20vp),36vp 高按钮的胶囊视觉量感
- **小元素**(`corner_radius_level2`–`level4`)用于图片、徽标、标签
- 同一功能用同一圆角——不做逐实例的圆角微调

### 胶囊与圆形控件

胶囊与圆形按钮在 HarmonyOS 体系下通过 `corner_radius_level10`(20vp)表达,适配 36vp 标准按钮高度,无需用 `9999vp` 兜底。

预览壳在卡片外额外应用稍大的外圆角(`2×2` 上 18vp,`2×4` 上 22vp),便于宿主干净裁切;该圆角不属于卡片内容。

不使用装饰性嵌套圆矩形。

## Components

一套小巧、强约束的组件词汇。每个组件定义为扁平 token 条目；组件结构与行为同时受 YAML `component_contracts` 约束。

### 卡片根容器 Card Root

- 接受宿主提供的运行时画布，不在组件代码中写死卡片外层宽高。
- 必须先使用 `comp_background_primary` 基底；场景精确命中 `background_gradients` 中已登记的遮罩预设时叠加对应渐变，未命中时叠加 `general-fallback`，不得只保留裸基底。
- 卡片本体使用 `corner_radius_level10`(20vp)圆角和 12vp 安全边距内边距。
- 约束安全边距、宿主裁切和整体点击行为。

### 标题与身份 Title & Identity

- `title-area` 与 `title-text` 必选；标题不得因核心内容自明而省略。
- 标题用于解释卡片服务或当前内容上下文，默认单行。
- 必要时在左上显示服务名称或服务身份文字。
- 右上角可放应用图标或营销 Logo，但必须来自本地 `resource` SVG（`data-resource-icon` 标注并通过 catalog 校验），不得使用 emoji 或外链。
- 应用名称不得在标题与身份区重复出现。
- `leading-icon` 可选，左上 12×12vp 或右上 20×20vp；一卡至多两个 `leading-icon`（左上 12vp 一个 + 右上 20vp 一个）。

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
- `2×2` 最多两个辅助信息行;
- `2×4` 可将多行松散信息放入独立子表面进行分组；普通列表最多 3 行，带图表时最多 2 行。
- `2×2` 的两块文字使用一块 `bottom-information-surface` 收敛：标题 `12vp / 700`，辅助文本 `12vp / 400`，内边距 `8vp`；该变体不允许 `button-area`。

### 操作 Action

- 当 query 明确提出具体操作或点击跳转动作时，必须在底部 `button-area` 中提供对应按钮；整卡点击不得替代该按钮。
- 遮罩渐变卡片上的按钮必须执行 `button_color_rules`：按卡片背景类选用登记形态——浅色遮罩卡可用 10% 直写、预合成浅底或实心主色三种背景形态，前景按形态配对（见《Gradient Card Button Colors》）。
- 图文按钮使用 `button-with-icon`（`Row + Image + Text`，onClick 仅挂外层 Row）：高度 36vp、内部图标 20×20vp、文字 `body-m-regular`（超过 6 个字降级 `body-s-regular`）；`Button` 组件仅支持 `label` 纯文字，不得为其添加协议外图标字段。
- `2×2` 最多一个明确按钮。
- `2×4` 可使用一个按钮，或上下排列两个按钮；不得超过两个。
- 两个按钮必须对应两个清楚、直接且与主意图相关的操作，不得形成快捷入口列表。
- 两个按钮保持等宽、等高并上下对齐，按钮间距为 `8–12vp`。
- 按钮仅使用普通填充样式，不携带描边（`borderWidth` / `borderColor`）；背景色、文字色和状态色直接引用本文件中的组件 Token。
- 按钮文案默认使用 `body-m-regular`；超过 6 个字时降级到 `body-s-regular`，不得继续降低。
- 可点击视觉尺寸至少为 `24vp`，热区至少为 `40vp`。
- `2×2` 圆形按钮参考尺寸为 `30×30vp`；胶囊按钮参考高度为 `36vp`。
- `2×2` 图标按钮使用 `button-icon-2x2`：视觉尺寸固定为 `30×30vp`，内部图标固定为 `16×16vp`，在 `button-area` 内右下角对齐；视觉尺寸之外保留至少 `40×40vp` 的热区，并必须输出 `data-component="button-icon-2x2"`。
- 底部图标按钮的优先触发条件必须同时满足：卡片是 `2×2`；只有一个显式操作；删除某条辅助信息或紧凑数据可视化会改变用户的下一步判断；本地图标 catalog 存在 `eligibility: approved` 且与该操作语义精确匹配的图标；不看按钮文字也能准确理解操作。
- 以上任一条不满足时使用文字按钮。危险或不可逆操作、需要确认/同意的操作、以及没有精确 approved 图标的“查看详情”不得为节省空间强行图标化。
- 图标按钮无可见文字，但必须提供来自完整操作文案的可访问名称（HTML 使用 `aria-label`，A2UI / ArkUI 使用等价语义属性），不得只写图标资源名。
- 按钮使用胶囊全圆角：`borderRadius ≥ 18vp`（36vp 高按钮即半高 18 全圆角）；card-root 仍固定 `corner_radius_level10`（20vp）。
- 按钮距离卡片边缘至少 `12vp`。
- 无按钮时，整张卡片为一个热区。
- 有一个或两个按钮时，卡片内容区与每个按钮分别构成不重叠热区，并提供独立点击反馈。
- 点击按钮只能触发按钮操作，不得同时触发内容区或整卡操作。
- `2×4` 中存在按钮时，辅助信息面板必须在按钮组之前结束，并与按钮组保持 `8–12vp` 间距；按钮直接位于卡片根背景上，不得叠放在辅助面板之上。

### 列表 List

- `list-row` 为 `simple_list` 内的单行，高 `32vp`，使用内容区默认的 `body-s-regular`(12vp / 400)，内边距为 `0/8vp`。
- `2×2` 最多 2 行；`2×4` 最多 3 行；带图表的 `2×4` 最多 2 行。
- 仅当前决策项可将一段主文案升至 subtitle 层级。

### 进度 Progress

可选类型：

- 环形：单一连续比例，一个焦点。
- 线性：连续比例或多个可比较数值。
- 分段：具名阶段或离散步骤。

`2×2` 默认最多一个展示环；仅“双数据展示”变体允许两个并列数据环，且不得与 `button-area` 同时出现。`2×4` 仍最多一个展示环。

进度类型按数据关系选择：

- 没有目标、总量、范围或阶段参照时，直接使用文字或数值，不为装饰而添加进度。
- 一个连续数值相对单一目标、总量或范围，且它是唯一主焦点时使用展示环。
- 两个直接可比较且分别需要独立进度语义的数据，仅在 `2×2` 无按钮状态下使用双数据并列圆环；其他多值场景使用线性进度，不并排堆叠多个环形进度。
- 具名阶段或离散步骤使用分段进度，并同时显示当前阶段文字。
- `2×2` 中出现线性进度或阶段条时，条形图本体必须贴靠 `content-area` 底边；该规则优先于内容组整体居中。与进度直接相关的辅助文字放在条形图正上方并保持紧凑间距，主数值和主状态保留在上方可用区域内。
- 环形进度必须保持正圆并使用系统或运行时进度组件。所有环形进度的背景底轨统一使用 `progress_ring_track`（与 `comp_background_secondary` 同值：浅色 `#00000019` / 深色 `#FFFFFF19`，半透明前景色，随主题翻转，在浅色与深色基底上都可见）；进度弧线两端必须使用圆形端帽，SVG 实现对应 `stroke-linecap="round"`，其他运行时使用等价的 round cap 属性。
- 图文展示环与左下角图表环为同一 `display-ring` 样式：外径 `52×52vp`、描边 `6vp` 且为完整内描边；两者仅布局位置不同。圆心可二选一放置 `16vp` 文本或 `24×24vp` 图标。
- 双数据并列圆环的每个圆环外径为 `44×44vp`，描边 `6vp` 且为完整内描边；圆心仅放置 `16×16vp` 图标，`10vp` 数据文本位于圆环下方，与圆环垂直间距固定 `4vp`（`labelGap = spacing.xs`）。**两个圆环之间的水平间距固定 `24vp`（`ringGap = spacing.xxl`）**，由 paired-data-ring 容器的 `gap` 实现，不得压缩或放大——24vp 间距让两个独立进度环在视觉上各自成立又保持并列对比关系。
- 圆心同时展示数值与单位时，数值和单位必须保持同一行，不得上下换行。
- 数值与单位作为一个整体，必须与圆环水平、垂直居中对齐；空间不足时单位可降至全局允许的最小字号 `8vp`，仍无法保持同一行时，再将数值降低一个文字层级。
- 数值降低一档后仍不能清晰展示时，将整组数值与单位移至圆环旁边，不继续缩小或强行塞入圆心

系统不鼓励密集按钮网格、多步表单、隐藏手势交互。卡片操作默认保持单一主操作;卡片尺寸上限:`2×2` 最多 1 个显式操作,`2×4` 最多 2 个，但第二个操作必须具备独立即时目标。组件几何遵循与其他地方相同的 `safe-margin` 间距 token。

## Do's and Don'ts

**Do**

- 默认颜色用 token 名引用;让主题层解析明暗。`card-root` 先铺 `comp_background_primary`，再在精确命中 6 个已登记场景之一时叠加对应遮罩渐变。
- 用 `value-group.value` 与 `metric-primary` 确立一个主数据点;其他一切退让。
- 所有内容保持在 12vp 安全边距内。
- 提供当前已登记的反馈状态——默认按钮组件与 `button-primary-pressed`。
- 卡片表面用 `corner_radius_level8`(16vp),按钮用 `corner_radius_level10`(20vp),标签用 `corner_radius_level2`(4vp)。
- 所有 `background_gradients` 预设必须原样使用其 stops；不得在产物中自行配对、手调或新建渐变。

**Dont**

- 不要在普通组件或正文中硬编码 hex;仅 `card-root` 场景化渐变背景可直接指定渐变色。
- 不要把已废弃的旧场景渐变、扩展色板或自定义渐变用作 `card-root` 背景。
- 不要给装饰性元素加投影;用调性分层表达深度。
- 不要让 `2×2` 超过 1 个显式操作,或让 `2×4` 超过 1 个主操作 + 1 个次操作。
- 不要在同一组件族内混用圆角。
- 不要引入第四种字重、新字体族,或低于 8vp 的字号。
- 不要把 `warning` 红色用作品牌色;它专用于风险与紧急。
- 不要混用透明度档位——只能用规定的 13 档 alpha。
- 不要在 `themes.dark` 之外另起一个主题层。
- 不要为内容拉大画布;按画布裁剪内容。
- 不要通过缩小字号、压缩安全边距、负间距、绝对定位或裁切来掩盖内容过载。
- 不要让按钮覆盖图表、列表或内容预览。
