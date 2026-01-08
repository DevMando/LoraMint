using System.Diagnostics;
using System.Runtime.InteropServices;

namespace LoraMint.Web.BackgroundServices;

public class PythonBackendHostedService : IHostedService, IDisposable
{
    private readonly ILogger<PythonBackendHostedService> _logger;
    private readonly IConfiguration _configuration;
    private Process? _pythonProcess;
    private readonly string _pythonBackendPath;
    private readonly string _venvPath;
    private readonly bool _autoStart;
    private readonly bool _autoInstallDependencies;
    private bool _startedByThisService = false;

    public PythonBackendHostedService(
        ILogger<PythonBackendHostedService> logger,
        IConfiguration configuration)
    {
        _logger = logger;
        _configuration = configuration;

        _pythonBackendPath = Path.GetFullPath(
            _configuration["PythonBackend:Path"] ?? "../python-backend");

        _venvPath = Path.Combine(_pythonBackendPath, "venv");
        _autoStart = _configuration.GetValue<bool>("PythonBackend:AutoStart", true);
        _autoInstallDependencies = _configuration.GetValue<bool>("PythonBackend:AutoInstallDependencies", true);
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        if (!_autoStart)
        {
            _logger.LogInformation("Python backend auto-start is disabled");
            return;
        }

        _logger.LogInformation("========================================");
        _logger.LogInformation("Starting Python Backend Setup...");
        _logger.LogInformation("========================================");

        try
        {
            // Check if Python backend is already running
            if (await IsPythonBackendRunningAsync(cancellationToken))
            {
                _logger.LogInformation("[DETECTED] Python backend is already running on port 8000");
                _logger.LogInformation("[SUCCESS] Skipping startup - using existing Python backend instance");
                _logger.LogInformation("========================================");
                return;
            }

            // Check if Python backend directory exists
            if (!Directory.Exists(_pythonBackendPath))
            {
                _logger.LogError("[FAILED] Python backend directory not found: {Path}", _pythonBackendPath);
                return;
            }

            // Setup virtual environment
            await EnsureVirtualEnvironmentAsync(cancellationToken);

            // Install dependencies if needed
            if (_autoInstallDependencies)
            {
                await InstallDependenciesAsync(cancellationToken);
            }

            // Start Python backend
            await StartPythonBackendAsync(cancellationToken);

            _logger.LogInformation("========================================");
            _logger.LogInformation("[SUCCESS] Python backend started successfully!");
            _logger.LogInformation("========================================");
        }
        catch (Exception ex)
        {
            _logger.LogError("========================================");
            _logger.LogError(ex, "[FAILED] Could not start Python backend");
            _logger.LogError("========================================");
        }
    }

    public async Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Stopping Python backend service...");

        // Only stop the process if we started it ourselves
        if (_startedByThisService && _pythonProcess != null && !_pythonProcess.HasExited)
        {
            try
            {
                _pythonProcess.Kill(entireProcessTree: true);
                await _pythonProcess.WaitForExitAsync(cancellationToken);
                _logger.LogInformation("Python backend stopped successfully");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error stopping Python backend");
            }
        }
        else if (!_startedByThisService)
        {
            _logger.LogInformation("Python backend was already running - leaving it running");
        }
    }

    private async Task EnsureVirtualEnvironmentAsync(CancellationToken cancellationToken)
    {
        if (Directory.Exists(_venvPath))
        {
            _logger.LogInformation("[STEP 1/3] Virtual environment found - skipping creation");
            return;
        }

        _logger.LogInformation("[STEP 1/3] Creating Python virtual environment...");
        _logger.LogInformation("            This may take 30-60 seconds...");

        var pythonCmd = GetPythonCommand();
        var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = pythonCmd,
                Arguments = $"-m venv \"{_venvPath}\"",
                WorkingDirectory = _pythonBackendPath,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            }
        };

        process.Start();
        var output = await process.StandardOutput.ReadToEndAsync(cancellationToken);
        var error = await process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken);

        if (process.ExitCode != 0)
        {
            _logger.LogError("[FAILED] Could not create virtual environment: {Error}", error);
            throw new Exception($"Failed to create virtual environment: {error}");
        }

        _logger.LogInformation("[SUCCESS] Virtual environment created successfully!");
    }

    private async Task InstallDependenciesAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("[STEP 2/3] Installing Python dependencies...");
        _logger.LogInformation("            This may take 2-5 minutes on first run");
        _logger.LogInformation("            Installing: PyTorch, diffusers, transformers, and more");

        var pipCmd = GetPipCommand();
        var requirementsPath = Path.Combine(_pythonBackendPath, "requirements.txt");

        if (!File.Exists(requirementsPath))
        {
            _logger.LogWarning("[WARNING] requirements.txt not found, skipping dependency installation");
            return;
        }

        var packagesInstalled = new HashSet<string>();

        var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = pipCmd,
                Arguments = $"install -r \"{requirementsPath}\"",
                WorkingDirectory = _pythonBackendPath,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            }
        };

        process.OutputDataReceived += (sender, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
            {
                // Highlight major packages being downloaded
                if (e.Data.Contains("Downloading torch-"))
                {
                    _logger.LogInformation("            > Downloading PyTorch (this is the largest package ~200MB)");
                }
                else if (e.Data.Contains("Downloading diffusers-"))
                {
                    _logger.LogInformation("            > Downloading diffusers (for Stable Diffusion)");
                }
                else if (e.Data.Contains("Downloading transformers-"))
                {
                    _logger.LogInformation("            > Downloading transformers (for AI models)");
                }
                else if (e.Data.Contains("Successfully installed"))
                {
                    _logger.LogInformation("            > {Output}", e.Data);
                }
                else
                {
                    _logger.LogInformation("            {Output}", e.Data);
                }
            }
        };

        process.ErrorDataReceived += (sender, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                _logger.LogWarning("            [pip] {Error}", e.Data);
        };

        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        await process.WaitForExitAsync(cancellationToken);

        if (process.ExitCode != 0)
        {
            _logger.LogError("[FAILED] Could not install dependencies");
            throw new Exception("Failed to install Python dependencies");
        }

        _logger.LogInformation("[SUCCESS] All Python dependencies installed successfully!");
    }

    private async Task StartPythonBackendAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("[STEP 3/3] Starting Python FastAPI backend...");

        var pythonCmd = GetVenvPythonCommand();
        var mainPyPath = Path.Combine(_pythonBackendPath, "main.py");

        if (!File.Exists(mainPyPath))
        {
            _logger.LogError("[FAILED] main.py not found at: {Path}", mainPyPath);
            throw new FileNotFoundException($"main.py not found at: {mainPyPath}");
        }

        _pythonProcess = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = pythonCmd,
                Arguments = $"\"{mainPyPath}\"",
                WorkingDirectory = _pythonBackendPath,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            }
        };

        _pythonProcess.OutputDataReceived += (sender, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                _logger.LogInformation("            [Python] {Output}", e.Data);
        };

        _pythonProcess.ErrorDataReceived += (sender, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                _logger.LogWarning("            [Python Error] {Error}", e.Data);
        };

        _pythonProcess.Start();
        _pythonProcess.BeginOutputReadLine();
        _pythonProcess.BeginErrorReadLine();

        // Wait a bit to ensure Python backend starts
        await Task.Delay(2000, cancellationToken);

        if (_pythonProcess.HasExited)
        {
            _logger.LogError("[FAILED] Python backend exited immediately with code: {ExitCode}",
                _pythonProcess.ExitCode);
            throw new Exception($"Python backend failed to start. Exit code: {_pythonProcess.ExitCode}");
        }

        _startedByThisService = true;
        _logger.LogInformation("[SUCCESS] Python backend is running on port 8000");
    }

    private async Task<bool> IsPythonBackendRunningAsync(CancellationToken cancellationToken)
    {
        var baseUrl = _configuration["PythonBackend:BaseUrl"] ?? "http://localhost:8000";

        try
        {
            using var httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(3) };

            // Try to hit the health endpoint or root endpoint
            var healthEndpoints = new[] { $"{baseUrl}/health", $"{baseUrl}/", $"{baseUrl}/docs" };

            foreach (var endpoint in healthEndpoints)
            {
                try
                {
                    var response = await httpClient.GetAsync(endpoint, cancellationToken);
                    if (response.IsSuccessStatusCode)
                    {
                        return true;
                    }
                }
                catch
                {
                    // Continue to next endpoint
                    continue;
                }
            }

            return false;
        }
        catch
        {
            return false;
        }
    }

    private string GetPythonCommand()
    {
        // Try common Python commands
        var pythonCommands = new[] { "python3", "python" };

        foreach (var cmd in pythonCommands)
        {
            try
            {
                var process = Process.Start(new ProcessStartInfo
                {
                    FileName = cmd,
                    Arguments = "--version",
                    RedirectStandardOutput = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                });

                if (process != null)
                {
                    process.WaitForExit();
                    if (process.ExitCode == 0)
                    {
                        return cmd;
                    }
                }
            }
            catch
            {
                continue;
            }
        }

        return RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "python" : "python3";
    }

    private string GetPipCommand()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            return Path.Combine(_venvPath, "Scripts", "pip.exe");
        }
        else
        {
            return Path.Combine(_venvPath, "bin", "pip");
        }
    }

    private string GetVenvPythonCommand()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            return Path.Combine(_venvPath, "Scripts", "python.exe");
        }
        else
        {
            return Path.Combine(_venvPath, "bin", "python");
        }
    }

    public void Dispose()
    {
        // Only kill the process if we started it
        if (_startedByThisService && _pythonProcess != null && !_pythonProcess.HasExited)
        {
            try
            {
                _pythonProcess.Kill(entireProcessTree: true);
                _pythonProcess.Dispose();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error disposing Python backend process");
            }
        }
    }
}
