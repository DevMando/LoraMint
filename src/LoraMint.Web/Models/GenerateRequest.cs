using System.Text.Json.Serialization;

namespace LoraMint.Web.Models;

public class GenerateRequest
{
    [JsonPropertyName("prompt")]
    public string Prompt { get; set; } = string.Empty;

    [JsonPropertyName("userId")]
    public string UserId { get; set; } = string.Empty;

    [JsonPropertyName("loras")]
    public List<LoraReference>? Loras { get; set; }
}

public class LoraReference
{
    [JsonPropertyName("file")]
    public string File { get; set; } = string.Empty;

    [JsonPropertyName("strength")]
    public double Strength { get; set; } = 1.0;
}
