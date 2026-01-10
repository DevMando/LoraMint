using System.Text.Json.Serialization;

namespace LoraMint.Web.Models;

/// <summary>
/// Represents a progress event from the SSE stream during image generation
/// </summary>
public class SseProgressEvent
{
    [JsonPropertyName("event")]
    public string Event { get; set; } = string.Empty;

    [JsonPropertyName("step")]
    public int? Step { get; set; }

    [JsonPropertyName("total_steps")]
    public int? TotalSteps { get; set; }

    [JsonPropertyName("percentage")]
    public double? Percentage { get; set; }

    [JsonPropertyName("message")]
    public string? Message { get; set; }

    [JsonPropertyName("image_path")]
    public string? ImagePath { get; set; }

    [JsonPropertyName("error")]
    public string? Error { get; set; }

    [JsonPropertyName("success")]
    public bool Success { get; set; }
}
