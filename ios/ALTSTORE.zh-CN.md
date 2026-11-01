# GitHub 打包与 AltStore 安装

## Swift 原生版

当前重写分支为 `codex/swift-native`，工作流名称是 **Native Swift IPA for AltStore**。
界面为 SwiftUI，计算为 Swift，IPA 内不再包含网页、Python 或 WebAssembly。
更新旧版 App 前，请先在旧版导出飞机档案 JSON；原生版不会自动读取旧 WebView 的存储。
安装后在“飞机档案”导入备份并核对本机数据。参见 [原生版说明](NATIVE.md)。

以下为旧 WebView 分支的操作说明，安装产物仍通过 AltStore Classic 签名。

适用分支：`codex/ios-iphone-support`。离线版要求 iOS 26 及以上，面向普通 iPhone、Pro／Pro Max，以及可变窗口尺寸和展开布局；不再要求兼容 SE 或老款 iPhone 5。
折叠／展开按实际窗口尺寸变化处理，不写死未经确认的机型尺寸。目前没有折叠屏真机验收，不能视为某个具体型号的兼容认证。

## 你需要准备

- GitHub 仓库开启 Actions。
- 已配置好的 AltStore Classic、AltServer 和你自己的 Apple 账号。
- 不需要服务器、域名或 HTTPS 配置。

不用自己购买 Mac，也不用向 GitHub 提交 Apple 密码、证书或付费开发者账号。
GitHub 的 Mac 环境负责编译；AltStore Classic 在安装时负责签名。
不要把 Apple 密码写到代码、仓库或此构建流程的 Secrets 中。

## 打包

1. 将此分支的完整代码提交并推送到 GitHub，包括 `ios/`、`.github/` 和网页/计算模块。
2. 进入仓库的 **Actions**，打开 **iOS IPA for AltStore** 构建记录。
3. 等待计算测试、离线冷启动检查、设备版编译和原生 WebKit 测试全部通过。
4. 在该记录的 **Artifacts** 下载 **PPL-AltStore**。
5. 解压下载的 ZIP，找到 **PPL-AltStore.ipa**。

此分支的 iOS 改动推送后会自动构建。GitHub 的 **Run workflow** 手动按钮需要工作流先存在于默认分支；没有按钮时请查看此次推送触发的记录。
Actions 可能消耗仓库的构建额度。产物保留 30 天；当前没有自动创建 Release 或上传到公开下载站。

附带的 `.sha256` 是下载校验码，`package-info.json` 记录版本、包标识和最低系统版本。
只有测试成功后才会发布安装产物。失败时先看红色步骤的日志，不要安装不完整的包。

## 安装

1. 将解压出的 `PPL-AltStore.ipa` 放进 iPhone 的“文件”。
2. 打开 **AltStore Classic → My Apps → +**，选择这个 IPA。
3. 按你现有的 AltServer / Apple 账号流程完成签名和安装。
4. 打开 PPL，等待本地计算引擎启动，然后直接使用；无需填写服务器。

这里用的是 **AltStore Classic**，不是 AltStore PAL。不要选择 GitHub 下载的外层 ZIP，也不要期待在“文件”中直接点 IPA 就完成安装。
普通 Apple 账号侧载的应用通常需要每七天刷新。保持同一 Apple 账号和应用标识更新，重装前先导出飞机档案备份。

## 离线计算与数据

起飞、降落、巡航、爬升、W&B、飞机档案、手工 POH 数据表及详细计算步骤，均在手机内运行。
代码、数据表、Python 和 NumPy 运行组件在打包时一并装入 IPA，不需要外部服务器，也不会在手机上启动监听端口。
首次启动也无需联网。运行组件约增加 25 MB 未压缩资源，启动时需要一点本地初始化时间。

网页版继续保留原有服务器运行方式，不影响这个独立离线 App。
网页里的飞机档案不会自动出现在 App 中。先在网页导出 JSON，再在 App 中导入；之后保存在手机本地。
重装、删除 App 或更换签名账号前应导出备份。计算仍需核对本机实际 POH 和称重记录。
点击外部 POH 来源链接会打开系统浏览器，那些网页仍需联网，但不影响离线计算。

## 验证状态

Windows 上已禁用浏览器网络，验证首次启动、全部五类计算、与网页版的结果一致性、保存档案和重开后的持久化，且无外部资源请求。
GitHub 工作流验证 Mac 编译、App 内资源加载和 WebKit 离线运算。请查看对应提交的 Actions 记录再下载 IPA；旧构建的最低系统要求可能不同。AltStore 安装和具体折叠机型仍需真机验收。

官方说明：[AltStore Classic](https://faq.altstore.io/altstore-classic/your-altstore)、[Classic 与 PAL 的区别](https://github.com/altstoreio/FAQ/blob/main/altstore-pal-v.-altstore-classic.md)。
