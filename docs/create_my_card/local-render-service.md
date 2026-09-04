# CreateMyCard 本地渲染服务操作手册

目标链路：

```text
远程训练容器
  -> 远程服务器 127.0.0.1:18080
  -> SSH 反向隧道
  -> Windows 127.0.0.1:8000
  -> DevEco/HDC 渲染
  -> 返回截图和 dumpLayout
  -> L2 质检
```

固定应用信息：

```text
bundle  = com.example.myapplication
ability = EntryAbility
module  = entry
```

## 1. Windows 首次安装依赖

渲染工程已经包含在仓库根目录 `A2UI_Render_0716` 中。首次拉取后执行一次：

```powershell
Set-Location '<Windows 上的仓库根目录>\A2UI_Render_0716'
& 'D:\DevEco Studio\tools\ohpm\bin\ohpm.bat' install
```

`oh_modules` 已存在时不需要重复安装。

## 2. Windows 启动渲染服务

在 PowerShell 中进入仓库根目录：

```powershell
Set-Location '<Windows 上的仓库根目录>'

$env:A2UI_RENDER_PROJECT_ROOT=(Resolve-Path '.\A2UI_Render_0716').Path
$env:A2UI_RENDER_DEVECO_HOME='D:\DevEco Studio'
$env:A2UI_RENDER_HVIGOR='D:\DevEco Studio\tools\hvigor\bin\hvigorw.js'
$env:A2UI_RENDER_NODE='D:\DevEco Studio\tools\node\node.exe'
$env:A2UI_RENDER_HDC='D:\toolchains\hdc.exe'
$env:A2UI_RENDER_DEVICE_SN='127.0.0.1:5555'
$env:A2UI_RENDER_ARTIFACT_ROOT=(Join-Path (Get-Location) 'outputs\local-render-service')
$env:A2UI_RENDER_BIND='127.0.0.1'
$env:A2UI_RENDER_PORT='8000'
$env:A2UI_RENDER_TIMEOUT_SECONDS='300'
$env:A2UI_RENDER_START_WAIT_SECONDS='8'
```

当前使用本机 TCP 模拟器。启动服务前确认其状态为 `Connected`：

```powershell
& 'D:\toolchains\hdc.exe' tconn '127.0.0.1:5555'
& 'D:\toolchains\hdc.exe' -t '127.0.0.1:5555' shell 'echo connected'
```

确认输出 `connected` 后启动服务，并保持当前窗口运行：

```powershell
python -m frameworks.verl.create_my_card.render_service.server
```

每次渲染的请求、截图、布局和日志保存在：

```text
outputs\local-render-service\<任务目录>\
```

## 3. Windows 建立 SSH 反向隧道

另开一个 PowerShell 窗口并保持运行：

```powershell
ssh -NT `
  -R 127.0.0.1:18080:127.0.0.1:8000 `
  -o ExitOnForwardFailure=yes `
  -o ServerAliveInterval=30 `
  root@7.242.106.189
```

SSH 成功后没有输出且不返回提示符，属于正常状态。

服务不做 HTTP 鉴权，因此 Windows 和远程转发地址都必须保持绑定在
`127.0.0.1`，不要改成 `0.0.0.0`。

## 4. 训练容器配置

进入远程训练容器，设置服务地址和请求超时：

```bash
export A2UI_RENDER_SERVICE_URL=http://127.0.0.1:18080
export A2UI_RENDER_REQUEST_TIMEOUT_SECONDS=320
```

确认服务可访问：

```bash
curl --fail-with-body --max-time 10 http://127.0.0.1:18080/health
```

预期返回 `status=ok` 和 `deviceReady=true`。

## 5. 渲染一条样本

在训练容器的仓库根目录执行：

```bash
python frameworks/verl/create_my_card/rl/evaluation/render_l2_sample.py \
  --input frameworks/verl/create_my_card/sft/data/source/design_compact_dsl.jsonl \
  --taskspec-file frameworks/verl/create_my_card/sft/data/source/taskspec.json \
  --output-dir outputs/l2-render-smoke \
  --limit 1 \
  --execute
```

成功后生成：

```text
outputs/l2-render-smoke/render-sample-manifest.json
outputs/l2-render-smoke/layouts/<id>.layout.json
outputs/l2-render-smoke/screenshots/<id>.jpeg
```

`--output-dir` 必须使用一个尚不存在的新目录。

## 6. 执行 L2 质检

```bash
python frameworks/verl/create_my_card/rl/evaluation/audit_rewards.py \
  --input frameworks/verl/create_my_card/sft/data/source/design_compact_dsl.jsonl \
  --taskspec-file frameworks/verl/create_my_card/sft/data/source/taskspec.json \
  --layout-dir outputs/l2-render-smoke/layouts \
  --default-finish-reason stop \
  --limit 1 \
  --output outputs/l2-reward-audit.jsonl
```

质检结果位于：

```text
outputs/l2-reward-audit.jsonl
```

## 7. 日常使用顺序

以后每次使用只需：

1. Windows 启动渲染服务。
2. Windows 建立 SSH 反向隧道。
3. 训练容器设置服务地址和请求超时。
4. 执行渲染命令和 L2 质检命令。

结束时，在渲染服务和 SSH 隧道对应的 PowerShell 窗口分别按 `Ctrl+C`。

当前 HTTP 链路用于离线 L2 渲染和奖励审计；在线训练入口尚未逐样本接入设备渲染。
