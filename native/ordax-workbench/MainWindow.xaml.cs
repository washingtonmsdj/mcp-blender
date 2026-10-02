using System.ComponentModel;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Threading;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;

namespace Ordax.Workbench;

public partial class MainWindow : Window
{
    private sealed record ProviderDefinition(string Id, string Label, string Url);

    private readonly DispatcherTimer _runtimeTimer = new() { Interval = TimeSpan.FromSeconds(5) };
    private readonly List<ProviderDefinition> _providers = new();
    private StudioBridgeClient? _bridge;
    private bool _ready;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += MainWindow_Loaded;
        Closing += MainWindow_Closing;
        _runtimeTimer.Tick += async (_, _) => await RefreshRuntimeStateAsync();
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        try
        {
            LoadProviders();
            _bridge = new StudioBridgeClient(LogActivity);
            await _bridge.StartAsync();

            await InitializeViewAsync(ProviderView, "provider");
            await InitializeViewAsync(StudioView, "studio");
            await InitializeViewAsync(PreviewView, "preview-visible");
            await InitializeViewAsync(WorkbenchBrowserView, "user-browser");

            ConfigureProviderView();
            ConfigureStudioView();
            ConfigureWorkbenchBrowser();

            _ready = true;
            ProviderSelector.SelectedIndex = 0;
            await RefreshRuntimeStateAsync();
            _runtimeTimer.Start();
            StatusText.Text = "Workbench pronta";
        }
        catch (Exception error)
        {
            StatusText.Text = $"Falha ao iniciar: {error.Message}";
            LogActivity(error.ToString());
        }
    }

    private async Task InitializeViewAsync(WebView2CompositionControl view, string profile)
    {
        var profileRoot = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "OrdaX", "Workbench", "WebView2", profile
        );
        Directory.CreateDirectory(profileRoot);
        view.CreationProperties = new CoreWebView2CreationProperties
        {
            UserDataFolder = profileRoot,
        };
        await view.EnsureCoreWebView2Async();
        view.CoreWebView2.Settings.AreDevToolsEnabled = true;
        view.CoreWebView2.Settings.AreDefaultContextMenusEnabled = true;
    }

    private void ConfigureProviderView()
    {
        ProviderView.CoreWebView2.SourceChanged += (_, _) =>
        {
            ProviderAddress.Text = ProviderView.Source?.ToString() ?? "";
        };
        ProviderView.CoreWebView2.NewWindowRequested += (_, args) =>
        {
            args.Handled = true;
            Navigate(ProviderView, args.Uri);
        };
    }

    private void ConfigureStudioView()
    {
        var assets = LocateStudioAssets();
        StudioView.CoreWebView2.SetVirtualHostNameToFolderMapping(
            "ordax.local",
            assets,
            CoreWebView2HostResourceAccessKind.Allow
        );
        StudioView.CoreWebView2.WebMessageReceived += StudioWebMessageReceived;
        StudioView.Source = new Uri("https://ordax.local/studio_product.html");
    }

    private void ConfigureWorkbenchBrowser()
    {
        WorkbenchBrowserView.CoreWebView2.NewWindowRequested += (_, args) =>
        {
            args.Handled = true;
            Navigate(WorkbenchBrowserView, args.Uri);
        };
        WorkbenchBrowserView.CoreWebView2.SourceChanged += (_, _) =>
        {
            WorkbenchBrowserAddress.Text = WorkbenchBrowserView.Source?.ToString() ?? "";
        };
        WorkbenchBrowserAddress.Text = "http://127.0.0.1:5173/";
    }

    private async void StudioWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
    {
        if (_bridge is null)
            return;

        string? requestId = null;
        try
        {
            using var document = JsonDocument.Parse(e.WebMessageAsJson);
            var root = document.RootElement;
            if (!root.TryGetProperty("type", out var type) || type.GetString() != "ordax-rpc")
                return;
            requestId = root.GetProperty("id").GetString();
            var method = root.GetProperty("method").GetString() ?? "";
            var args = root.TryGetProperty("args", out var argsElement)
                ? argsElement.Clone()
                : JsonSerializer.SerializeToElement(Array.Empty<object>());

            var raw = await _bridge.CallRawAsync(method, args, requestId);
            StudioView.CoreWebView2.PostWebMessageAsJson(raw);
        }
        catch (Exception error)
        {
            var response = JsonSerializer.Serialize(new
            {
                id = requestId,
                error = $"{error.GetType().Name}: {error.Message}",
            });
            StudioView.CoreWebView2.PostWebMessageAsJson(response);
            LogActivity($"RPC Studio falhou: {error.Message}");
        }
    }

    private void LoadProviders()
    {
        _providers.Clear();
        _providers.AddRange(new[]
        {
            new ProviderDefinition("chatgpt", "ChatGPT", "https://chatgpt.com/"),
            new ProviderDefinition("grok", "Grok", "https://grok.com/"),
            new ProviderDefinition("claude", "Claude", "https://claude.ai/new"),
            new ProviderDefinition("gemini", "Gemini", "https://gemini.google.com/app"),
            new ProviderDefinition("custom", "Local / Custom", "http://127.0.0.1:3000/"),
        });
        ProviderSelector.ItemsSource = _providers;
        ProviderSelector.DisplayMemberPath = nameof(ProviderDefinition.Label);
    }

    private void ProviderSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_ready || ProviderSelector.SelectedItem is not ProviderDefinition provider)
            return;
        ProviderAddress.Text = provider.Url;
        Navigate(ProviderView, provider.Url);
        LogActivity($"Provider visível: {provider.Label}. O ORDAX não automatiza este WebView.");
    }

    private void ProviderBack_Click(object sender, RoutedEventArgs e)
    {
        if (ProviderView.CoreWebView2?.CanGoBack == true)
            ProviderView.CoreWebView2.GoBack();
    }

    private void ProviderForward_Click(object sender, RoutedEventArgs e)
    {
        if (ProviderView.CoreWebView2?.CanGoForward == true)
            ProviderView.CoreWebView2.GoForward();
    }

    private void ProviderRefresh_Click(object sender, RoutedEventArgs e) => ProviderView.CoreWebView2?.Reload();

    private void ProviderAddress_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
            Navigate(ProviderView, ProviderAddress.Text);
    }

    private void WorkbenchBrowserAddress_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
            Navigate(WorkbenchBrowserView, WorkbenchBrowserAddress.Text);
    }

    private void WorkbenchBrowserGo_Click(object sender, RoutedEventArgs e) =>
        Navigate(WorkbenchBrowserView, WorkbenchBrowserAddress.Text);

    private async void WorkTabs_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_ready || WorkTabs.SelectedItem is not TabItem tab)
            return;
        if (Equals(tab.Header, "Preview"))
            await RefreshPreviewAsync();
    }

    private async void RefreshPreview_Click(object sender, RoutedEventArgs e) => await RefreshPreviewAsync();

    private async Task RefreshPreviewAsync()
    {
        if (_bridge is null || PreviewView.CoreWebView2 is null)
            return;

        try
        {
            var status = await _bridge.CallResultAsync("preview_status");
            if (TryData(status, out var data) &&
                data.TryGetProperty("url", out var urlElement) &&
                Uri.TryCreate(urlElement.GetString(), UriKind.Absolute, out var url) &&
                IsWebUri(url))
            {
                PreviewAddress.Text = url.ToString();
                PreviewView.Source = url;
                return;
            }

            var image = await _bridge.CallResultAsync("preview_image");
            if (TryData(image, out var imageData) &&
                imageData.TryGetProperty("src", out var srcElement))
            {
                var src = srcElement.GetString() ?? "";
                var encoded = JavaScriptEncoder.Default.Encode(src);
                PreviewAddress.Text = "Captura visual do projeto";
                PreviewView.CoreWebView2.NavigateToString(
                    $"<!doctype html><html><body style='margin:0;background:#040a11;display:grid;place-items:center;height:100vh'>" +
                    $"<img src=\"{encoded}\" style='max-width:100%;max-height:100%;object-fit:contain'></body></html>"
                );
                return;
            }

            PreviewAddress.Text = "Nenhum preview disponível";
            PreviewView.CoreWebView2.NavigateToString(
                "<!doctype html><html><body style='margin:0;background:#040a11;color:#8e9db4;font-family:Segoe UI;display:grid;place-items:center;height:100vh'>Nenhum preview disponível.</body></html>"
            );
        }
        catch (Exception error)
        {
            PreviewAddress.Text = $"Preview indisponível: {error.Message}";
            LogActivity($"Preview: {error.Message}");
        }
    }

    private async Task RefreshRuntimeStateAsync()
    {
        if (_bridge is null)
            return;
        try
        {
            var result = await _bridge.CallResultAsync("product_status");
            if (!TryData(result, out var data))
                return;

            var device = data.TryGetProperty("device_agent", out var deviceElement) ? deviceElement : default;
            var remote = data.TryGetProperty("remote_mcp", out var remoteElement) ? remoteElement : default;
            var deviceOk = device.ValueKind == JsonValueKind.Object &&
                           device.TryGetProperty("ok", out var deviceOkElement) &&
                           deviceOkElement.ValueKind == JsonValueKind.True;
            var remoteOk = remote.ValueKind == JsonValueKind.Object &&
                           remote.TryGetProperty("ok", out var remoteOkElement) &&
                           remoteOkElement.ValueKind == JsonValueKind.True;

            RuntimeState.Text = $"Runtime: {(deviceOk ? "online" : "local")} · MCP: {(remoteOk ? "online" : "verificando")}";
        }
        catch (Exception error)
        {
            RuntimeState.Text = "Runtime: bridge indisponível";
            LogActivity($"Status: {error.Message}");
        }
    }

    private static bool TryData(JsonElement result, out JsonElement data)
    {
        data = default;
        return result.ValueKind == JsonValueKind.Object &&
               result.TryGetProperty("ok", out var ok) &&
               ok.ValueKind == JsonValueKind.True &&
               result.TryGetProperty("data", out data);
    }

    private static bool IsWebUri(Uri uri) =>
        uri.Scheme.Equals(Uri.UriSchemeHttp, StringComparison.OrdinalIgnoreCase) ||
        uri.Scheme.Equals(Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase);

    private void Navigate(WebView2CompositionControl view, string? raw)
    {
        if (!Uri.TryCreate(raw?.Trim(), UriKind.Absolute, out var uri) || !IsWebUri(uri))
        {
            StatusText.Text = "Use uma URL http:// ou https:// válida.";
            return;
        }
        view.Source = uri;
        StatusText.Text = uri.Host;
    }

    private static string LocateStudioAssets()
    {
        var configured = Environment.GetEnvironmentVariable("ORDAX_STUDIO_ASSETS_DIR");
        if (!string.IsNullOrWhiteSpace(configured) && Directory.Exists(configured))
            return Path.GetFullPath(configured);

        var candidates = new[]
        {
            Path.Combine(AppContext.BaseDirectory, "runtime", "Lib", "site-packages", "ordax_studio"),
            Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "runtime", "Lib", "site-packages", "ordax_studio")),
            Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "ordax_studio")),
        };
        foreach (var candidate in candidates)
            if (File.Exists(Path.Combine(candidate, "studio_product.html")))
                return candidate;

        throw new DirectoryNotFoundException("Could not locate ORDAX Studio web assets.");
    }

    private void LogActivity(string text)
    {
        Dispatcher.Invoke(() =>
        {
            ActivityLog.AppendText($"[{DateTime.Now:HH:mm:ss}] {text}{Environment.NewLine}");
            ActivityLog.ScrollToEnd();
        });
    }

    private async void MainWindow_Closing(object? sender, CancelEventArgs e)
    {
        _runtimeTimer.Stop();
        if (_bridge is not null)
            await _bridge.DisposeAsync();
    }
}
