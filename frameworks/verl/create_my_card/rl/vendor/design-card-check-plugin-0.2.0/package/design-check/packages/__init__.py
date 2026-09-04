"""检测包（check packages）——1+5 拆包（docs/idea-check-package-split.md §2）。

本目录是逻辑分包的物理载体：每包一个目录 + manifest.yaml + 规则模块；
装载器 ``validators/packages_loader.py`` 扫描 manifest 产出包清单与规则归属。
规则注册仍走 ``validators.rules.register``（注册表机制不变，模块来源改为五包）。
"""
