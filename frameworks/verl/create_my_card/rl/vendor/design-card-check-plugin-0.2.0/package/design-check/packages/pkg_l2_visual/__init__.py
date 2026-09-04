"""pkg-l2-visual —— L2 视觉对账包（真值 = dump 实测，依赖外层渲染管线/设备）。

模块：layout（DumpLayout 解析）/ slot_map（三区归位）/ geometry（L2a GEOMETRY.*）/
reconcile_lib（L2b RECONCILE.*）。规则不进 L1 注册表（_RULES），由
run_geometry / reconcile 独立驱动。
兼容：validators/{layout,slot_map,geometry,reconcile_lib} 旧路径经
validators/__init__.py 的 sys.modules 别名继续可用（存量脚本/测试零改动）。
"""
