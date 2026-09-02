# WinUI3 可编译骨架

## 快速使用

1. 安装 Visual Studio 2022（含 WinUI3 工作负载）或 .NET 8 SDK
2. 将 LLM 生成的 XAML 内容粘贴到 `SettingsPage.xaml` 的 `<!-- {{XAML_CONTENT}} -->` 位置
3. 命令行编译：
   ```bash
   dotnet build E2EApp.csproj -c Debug -p:Platform=x64
   ```
4. 运行：
   ```bash
   dotnet run --project E2EApp.csproj -c Debug -p:Platform=x64
   ```
   或在 VS 中打开 `E2EApp.sln` 按 F5

## 环境要求

- Windows 10 1809+ (17763+) 或 Windows 11
- .NET 8 SDK
- Windows App SDK 1.5
- Visual Studio 2022（推荐，含 WinUI 工作负载）或仅 .NET SDK + dotnet CLI

## 无 dotnet 时降级

当环境中无 .NET SDK 时，使用近似 HTML 渲染：
- `backend/e2e_deep_verify.py` 中的 `winui3_xaml_to_html()` 函数
- XAML 控件映射为 HTML 元素（StackPanel→flex-column, ToggleSwitch→checkbox 等）
- Edge headless 截图验证布局结构

## 文件结构

```
winui3/
├── E2EApp.sln              # Visual Studio 解决方案
├── E2EApp.csproj            # .NET 项目文件
├── app.manifest             # 应用清单（DPI 兼容性等）
├── App.xaml                 # 应用根（XAML Controls 资源注册）
├── App.xaml.cs              # 应用入口（创建 Window + SettingsPage）
├── SettingsPage.xaml         # 页面骨架（含占位符）
├── SettingsPage.xaml.cs      # 页面 code-behind
└── README.md
```
