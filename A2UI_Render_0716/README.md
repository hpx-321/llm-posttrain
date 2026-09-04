# A2UI Render 0716

本目录是 CreateMyCard L2 截图与 `dumpLayout` 使用的 HarmonyOS 渲染工程源快照。工程来自经过验证的 `A2UI_Render_0716`，提交时不包含 `.hvigor`、`.idea`、`oh_modules`、`build`、`.preview` 和 `local.properties` 等机器生成内容。

固定运行契约：

```text
bundle:  com.example.myapplication
ability: EntryAbility
module:  entry
rawfile: entry/src/main/resources/rawfile/test.json
```

本地渲染服务会在单设备互斥锁内临时替换 `test.json`，完成构建、安装、启动、截图和布局采集后恢复原文件。不要在服务运行期间手工修改或构建本工程。

首次在新的 Windows 渲染主机上检出仓库后，需要在本目录完成 DevEco 工程同步或执行对应版本的 `ohpm install`，生成未纳入版本控制的 `oh_modules`，再启动本地渲染服务。渲染工程随本仓库通过 Git 拉取。
