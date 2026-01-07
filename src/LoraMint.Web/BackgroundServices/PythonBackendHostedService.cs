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

        _logger.LogInformation("Starting Python backend service...");

        try
        {
            // Check if Python backend directory exists
            if (!Directory.Exists(_pythonBackendPath))
            {
                _logger.LogError("Python backend directory not found: {Path}", _pythonBackendPath);
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

            _logger.LogInformation("Python backend started successfully");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start Python backend");
        }
    }

    public async Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Stopping Python backend service...");

        if (_pythonProcess != null && !_pythonProcess.HasExited)
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
    }

    private async Task EnsureVirtualEnvironmentAsync(CancellationToken cancellationToken)
    {
        if (Directory.Exists(_venvPath))
        {
            _logger.LogInformation("Virtual environment already exists");
            return;
        }

        _logger.LogInformation("Creating Python virtual environment...");

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
            _logger.LogError("Failed to create virtual environment: {Error}", error);
            throw new Exception($"Failed to create virtual environment: {error}");
        }

        _logger.LogInformation("Virtual environment created successfully");
    }

    private async Task InstallDependenciesAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Installing Python dependencies...");

        var pipCmd = GetPipCommand();
        var requirementsPath = Path.Combine(_pythonBackendPath, "requirements.txt");

        if (!File.Exists(requirementsPath))
        {
            _logger.LogWarning("requirements.txt not found, skipping dependency installation");
            return;
        }

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
                _logger.LogInformation("[pip] {Output}", e.Data);
        };

        process.ErrorDataReceived += (sender, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                _logger.LogWarning("[pip] {Error}", e.Data);
        };

        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        await process.WaitForExitAsync(cancellationToken);

        if (process.ExitCode != 0)
        {
            _logger.LogError("Failed to install dependencies");
            throw new Exception("Failed to install Python dependencies");
        }

        _logger.LogInformation("Dependencies installed successfully");
    }

    private async Task StartPythonBackendAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Starting Python backend process...");

        var pythonCmd = GetVenvPythonCommand();
        var mainPyPath = Path.Combine(_pythonBackendPath, "main.py");

        if (!File.Exists(mainPyPath))
        {
            _logger.LogError("main.py not found at: {Path}", mainPyPath);
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
                _logger.LogInformation("[Python] {Output}", e.Data);
        };

        _pythonProcess.ErrorDataReceived += (sender, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
                _logger.LogWarning("[Python] {Error}", e.Data);
        };

        _pythonProcess.Start();
        _pythonProcess.BeginOutputReadLine();
        _pythonProcess.BeginErrorReadLine();

        // Wait a bit to ensure Python backend starts
        await Task.Delay(2000, cancellationToken);

        if (_pythonProcess.HasExited)
        {
            _logger.LogError("Python backend exited immediately with code: {ExitCode}",
                _pythonProcess.ExitCode);
            throw new Exception($"Python backend failed to start. Exit code: {_pythonProcess.ExitCode}");
        }

        _logger.LogInformation("Python backend is running");
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
        if (_pythonProcess != null && !_pythonProcess.HasExited)
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
