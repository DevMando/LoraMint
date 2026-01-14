using System.Text.Json.Serialization;

namespace LoraMint.Web.Models;

/// <summary>
/// Information about an available AI model
/// </summary>
public class ModelInfo
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("huggingFaceId")]
    public string HuggingFaceId { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("minVramGb")]
    public int MinVramGb { get; set; }

    [JsonPropertyName("recommendedVramGb")]
    public int RecommendedVramGb { get; set; }

    [JsonPropertyName("inferenceSteps")]
    public int InferenceSteps { get; set; }

    [JsonPropertyName("speedRating")]
    public string SpeedRating { get; set; } = string.Empty; // "Fast", "Medium", "Slow"

    [JsonPropertyName("qualityRating")]
    public string QualityRating { get; set; } = string.Empty; // "Excellent", "High", "Good"

    [JsonPropertyName("estimatedSizeGb")]
    public int EstimatedSizeGb { get; set; }

    [JsonPropertyName("isDownloaded")]
    public bool IsDownloaded { get; set; }

    [JsonPropertyName("localPath")]
    public string? LocalPath { get; set; }

    [JsonPropertyName("supportsLora")]
    public bool SupportsLora { get; set; } = true;
}

/// <summary>
/// User's model selection and configuration settings
/// </summary>
public class ModelSettings
{
    [JsonPropertyName("selectedModelId")]
    public string? SelectedModelId { get; set; }

    [JsonPropertyName("modelsPath")]
    public string ModelsPath { get; set; } = "../../data/models";

    [JsonPropertyName("setupComplete")]
    public bool SetupComplete { get; set; }

    [JsonPropertyName("downloadedModels")]
    public List<string> DownloadedModels { get; set; } = new();
}

/// <summary>
/// GPU information from the system
/// </summary>
public class GpuInfo
{
    [JsonPropertyName("available")]
    public bool Available { get; set; }

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("totalVramGb")]
    public double TotalVramGb { get; set; }

    [JsonPropertyName("freeVramGb")]
    public double FreeVramGb { get; set; }

    [JsonPropertyName("cudaVersion")]
    public string? CudaVersion { get; set; }
}

/// <summary>
/// Response from model status endpoint
/// </summary>
public class ModelStatusResponse
{
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    [JsonPropertyName("isDownloaded")]
    public bool IsDownloaded { get; set; }

    [JsonPropertyName("localPath")]
    public string? LocalPath { get; set; }

    [JsonPropertyName("error")]
    public string? Error { get; set; }
}

/// <summary>
/// Model download progress event
/// </summary>
public class ModelDownloadProgress
{
    [JsonPropertyName("event")]
    public string Event { get; set; } = string.Empty; // "progress", "complete", "error"

    [JsonPropertyName("modelId")]
    public string ModelId { get; set; } = string.Empty;

    [JsonPropertyName("percentage")]
    public double Percentage { get; set; }

    [JsonPropertyName("downloadedMb")]
    public double DownloadedMb { get; set; }

    [JsonPropertyName("totalMb")]
    public double TotalMb { get; set; }

    [JsonPropertyName("message")]
    public string? Message { get; set; }

    [JsonPropertyName("error")]
    public string? Error { get; set; }
}
