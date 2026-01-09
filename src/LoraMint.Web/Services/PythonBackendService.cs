using LoraMint.Web.Models;
using System.Text;
using System.Text.Json;

namespace LoraMint.Web.Services;

public class PythonBackendService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<PythonBackendService> _logger;

    public PythonBackendService(HttpClient httpClient, ILogger<PythonBackendService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<string> GenerateImageAsync(GenerateRequest request)
    {
        try
        {
            var json = JsonSerializer.Serialize(request);
            _logger.LogInformation("Sending generate request: {Json}", json);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            var response = await _httpClient.PostAsync("/generate", content);

            var result = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError("Python backend error: {StatusCode} - {Response}", response.StatusCode, result);
                throw new Exception($"Python backend error: {result}");
            }

            var jsonResult = JsonSerializer.Deserialize<JsonElement>(result);

            return jsonResult.GetProperty("image_path").GetString() ?? string.Empty;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error generating image");
            throw;
        }
    }

    public async Task<string> TrainLoraAsync(string loraName, string userId, IFormFileCollection files)
    {
        try
        {
            using var formData = new MultipartFormDataContent();
            formData.Add(new StringContent(loraName), "lora_name");
            formData.Add(new StringContent(userId), "user_id");

            foreach (var file in files)
            {
                var fileContent = new StreamContent(file.OpenReadStream());
                fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(file.ContentType);
                formData.Add(fileContent, "images", file.FileName);
            }

            var response = await _httpClient.PostAsync("/train-lora", formData);
            response.EnsureSuccessStatusCode();

            var result = await response.Content.ReadAsStringAsync();
            var jsonResult = JsonSerializer.Deserialize<JsonElement>(result);

            return jsonResult.GetProperty("lora_path").GetString() ?? string.Empty;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error training LoRA");
            throw;
        }
    }
}
