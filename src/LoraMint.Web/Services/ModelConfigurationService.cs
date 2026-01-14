using System.Text.Json;
using LoraMint.Web.Models;

namespace LoraMint.Web.Services;

public interface IModelConfigurationService
{
    Task<List<ModelInfo>> GetAvailableModelsAsync();
    Task<ModelInfo?> GetSelectedModelAsync();
    Task<ModelSettings> GetSettingsAsync();
    Task SaveSettingsAsync(ModelSettings settings);
    Task<bool> IsModelDownloadedAsync(string modelId);
    string GetModelsPath();
}

public class ModelConfigurationService : IModelConfigurationService
{
    private readonly IConfiguration _configuration;
    private readonly HttpClient _httpClient;
    private readonly ILogger<ModelConfigurationService> _logger;
    private readonly string _modelsPath;
    private readonly string _settingsFilePath;
    private readonly List<ModelInfo> _availableModels;
    private ModelSettings? _cachedSettings;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true
    };

    public ModelConfigurationService(
        IConfiguration configuration,
        HttpClient httpClient,
        ILogger<ModelConfigurationService> logger)
    {
        _configuration = configuration;
        _httpClient = httpClient;
        _logger = logger;

        _modelsPath = _configuration["Storage:ModelsPath"] ?? "../../data/models";
        _settingsFilePath = Path.Combine(_modelsPath, "..", "model-settings.json");

        // Ensure models directory exists
        Directory.CreateDirectory(_modelsPath);

        // Load available models from configuration
        _availableModels = _configuration.GetSection("AvailableModels").Get<List<ModelInfo>>() ?? new List<ModelInfo>();

        _logger.LogInformation("ModelConfigurationService initialized with {Count} available models", _availableModels.Count);
    }

    public string GetModelsPath() => Path.GetFullPath(_modelsPath);

    public async Task<List<ModelInfo>> GetAvailableModelsAsync()
    {
        // Update download status for each model
        foreach (var model in _availableModels)
        {
            model.IsDownloaded = await IsModelDownloadedAsync(model.Id);
            if (model.IsDownloaded)
            {
                model.LocalPath = GetModelLocalPath(model.Id);
            }
        }

        return _availableModels;
    }

    public async Task<ModelInfo?> GetSelectedModelAsync()
    {
        var settings = await GetSettingsAsync();
        if (string.IsNullOrEmpty(settings.SelectedModelId))
            return null;

        var model = _availableModels.FirstOrDefault(m => m.Id == settings.SelectedModelId);
        if (model != null)
        {
            model.IsDownloaded = await IsModelDownloadedAsync(model.Id);
            if (model.IsDownloaded)
            {
                model.LocalPath = GetModelLocalPath(model.Id);
            }
        }

        return model;
    }

    public async Task<ModelSettings> GetSettingsAsync()
    {
        if (_cachedSettings != null)
            return _cachedSettings;

        try
        {
            if (File.Exists(_settingsFilePath))
            {
                var json = await File.ReadAllTextAsync(_settingsFilePath);
                _cachedSettings = JsonSerializer.Deserialize<ModelSettings>(json, JsonOptions);
                if (_cachedSettings != null)
                {
                    _logger.LogDebug("Loaded model settings: SelectedModel={ModelId}, SetupComplete={SetupComplete}",
                        _cachedSettings.SelectedModelId, _cachedSettings.SetupComplete);
                    return _cachedSettings;
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to load model settings from {Path}", _settingsFilePath);
        }

        // Return default settings
        _cachedSettings = new ModelSettings
        {
            ModelsPath = _modelsPath,
            SetupComplete = false
        };

        return _cachedSettings;
    }

    public async Task SaveSettingsAsync(ModelSettings settings)
    {
        try
        {
            var directory = Path.GetDirectoryName(_settingsFilePath);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }

            var json = JsonSerializer.Serialize(settings, JsonOptions);
            await File.WriteAllTextAsync(_settingsFilePath, json);

            _cachedSettings = settings;

            _logger.LogInformation("Saved model settings: SelectedModel={ModelId}, SetupComplete={SetupComplete}",
                settings.SelectedModelId, settings.SetupComplete);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to save model settings to {Path}", _settingsFilePath);
            throw;
        }
    }

    public async Task<bool> IsModelDownloadedAsync(string modelId)
    {
        // First check local path
        var localPath = GetModelLocalPath(modelId);
        if (Directory.Exists(localPath))
        {
            // Check if model files exist (at minimum, we need a model_index.json or config.json)
            var hasModelFiles = File.Exists(Path.Combine(localPath, "model_index.json")) ||
                               File.Exists(Path.Combine(localPath, "config.json"));
            if (hasModelFiles)
            {
                return true;
            }
        }

        // Also check with Python backend if it has the model cached
        try
        {
            var response = await _httpClient.GetAsync($"/models/{modelId}/status");
            if (response.IsSuccessStatusCode)
            {
                var result = await response.Content.ReadFromJsonAsync<ModelStatusResponse>();
                return result?.IsDownloaded ?? false;
            }
        }
        catch (Exception ex)
        {
            _logger.LogDebug(ex, "Could not check model status with backend for {ModelId}", modelId);
        }

        return false;
    }

    private string GetModelLocalPath(string modelId)
    {
        return Path.Combine(_modelsPath, modelId);
    }
}
