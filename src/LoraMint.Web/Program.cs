using LoraMint.Web.Models;
using LoraMint.Web.Services;
using LoraMint.Web.BackgroundServices;
using Microsoft.Extensions.FileProviders;
using System.Text;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

builder.Services.AddHttpClient<PythonBackendService>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["PythonBackend:BaseUrl"] ?? "http://localhost:8000");
    client.Timeout = TimeSpan.FromMinutes(10); // Image generation can take a while, especially on first run
});

// Add HttpClient for Blazor components to call local Minimal APIs
builder.Services.AddScoped(sp =>
{
    var navigationManager = sp.GetRequiredService<Microsoft.AspNetCore.Components.NavigationManager>();
    return new HttpClient
    {
        BaseAddress = new Uri(navigationManager.BaseUri),
        Timeout = TimeSpan.FromMinutes(60) // Allow long operations like model downloads
    };
});

builder.Services.AddSingleton<FileStorageService>();

// Add Model Configuration Service
builder.Services.AddSingleton<IModelConfigurationService>(sp =>
{
    var config = sp.GetRequiredService<IConfiguration>();
    var httpClient = new HttpClient
    {
        BaseAddress = new Uri(config["PythonBackend:BaseUrl"] ?? "http://localhost:8000"),
        Timeout = TimeSpan.FromMinutes(5)
    };
    var logger = sp.GetRequiredService<ILogger<ModelConfigurationService>>();
    return new ModelConfigurationService(config, httpClient, logger);
});

// Add Python backend hosted service
builder.Services.AddHostedService<PythonBackendHostedService>();

var app = builder.Build();

// Configure the HTTP request pipeline
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();

// Serve generated images and LoRA files from the data directory
var dataPath = Path.GetFullPath(Path.Combine(app.Environment.ContentRootPath, "..", "..", "data"));
if (!Directory.Exists(dataPath))
{
    Directory.CreateDirectory(dataPath);
}

// Serve /outputs from data/outputs
var outputsPath = Path.Combine(dataPath, "outputs");
if (!Directory.Exists(outputsPath))
{
    Directory.CreateDirectory(outputsPath);
}
app.UseStaticFiles(new StaticFileOptions
{
    FileProvider = new PhysicalFileProvider(outputsPath),
    RequestPath = "/outputs"
});

// Serve /loras from data/loras
var lorasPath = Path.Combine(dataPath, "loras");
if (!Directory.Exists(lorasPath))
{
    Directory.CreateDirectory(lorasPath);
}
app.UseStaticFiles(new StaticFileOptions
{
    FileProvider = new PhysicalFileProvider(lorasPath),
    RequestPath = "/loras"
});

app.UseAntiforgery();

// Setup redirect middleware - redirect to /setup if setup is not complete
app.Use(async (context, next) =>
{
    var path = context.Request.Path.Value?.ToLowerInvariant() ?? "";

    // Skip middleware for setup page, API endpoints, static files
    if (path.StartsWith("/setup") ||
        path.StartsWith("/api/") ||
        path.StartsWith("/_") ||
        path.StartsWith("/outputs") ||
        path.StartsWith("/loras") ||
        path.Contains("."))
    {
        await next();
        return;
    }

    var modelService = context.RequestServices.GetRequiredService<IModelConfigurationService>();
    var settings = await modelService.GetSettingsAsync();

    if (!settings.SetupComplete)
    {
        context.Response.Redirect("/setup");
        return;
    }

    await next();
});

// Minimal API Endpoints
app.MapPost("/api/generate", async (GenerateRequest request, PythonBackendService pythonService) =>
{
    try
    {
        var imageData = await pythonService.GenerateImageAsync(request);
        return Results.Ok(new { success = true, imageData });
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

// SSE Streaming endpoint for image generation with progress
app.MapPost("/api/generate/stream", async (GenerateRequest request, HttpContext context, IConfiguration config) =>
{
    var pythonBaseUrl = config["PythonBackend:BaseUrl"] ?? "http://localhost:8000";

    context.Response.ContentType = "text/event-stream";
    context.Response.Headers.Append("Cache-Control", "no-cache");
    context.Response.Headers.Append("Connection", "keep-alive");

    using var httpClient = new HttpClient();
    httpClient.Timeout = TimeSpan.FromMinutes(10);

    var json = JsonSerializer.Serialize(request);
    var content = new StringContent(json, Encoding.UTF8, "application/json");

    try
    {
        var request2 = new HttpRequestMessage(HttpMethod.Post, $"{pythonBaseUrl}/generate/stream")
        {
            Content = content
        };

        using var response = await httpClient.SendAsync(
            request2,
            HttpCompletionOption.ResponseHeadersRead,
            context.RequestAborted
        );

        if (!response.IsSuccessStatusCode)
        {
            var errorData = JsonSerializer.Serialize(new
            {
                @event = "error",
                success = false,
                error = $"Python backend returned status {response.StatusCode}",
                message = "Failed to connect to generation service"
            });
            await context.Response.WriteAsync($"data: {errorData}\n\n");
            return;
        }

        using var stream = await response.Content.ReadAsStreamAsync(context.RequestAborted);
        using var reader = new StreamReader(stream);

        while (!reader.EndOfStream && !context.RequestAborted.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(context.RequestAborted);
            if (line != null)
            {
                await context.Response.WriteAsync(line + "\n");
                await context.Response.Body.FlushAsync(context.RequestAborted);
            }
        }
    }
    catch (OperationCanceledException)
    {
        // Request was cancelled, that's fine
    }
    catch (Exception ex)
    {
        var errorData = JsonSerializer.Serialize(new
        {
            @event = "error",
            success = false,
            error = ex.Message,
            message = "Failed to connect to generation service"
        });
        await context.Response.WriteAsync($"data: {errorData}\n\n");
    }
});

app.MapPost("/api/train-lora", async (HttpRequest req, PythonBackendService pythonService) =>
{
    try
    {
        if (!req.HasFormContentType)
            return Results.BadRequest(new { success = false, error = "Invalid form data" });

        var form = await req.ReadFormAsync();
        var loraName = form["loraName"].ToString();
        var userId = form["userId"].ToString();
        var files = form.Files;

        if (string.IsNullOrEmpty(loraName) || files.Count == 0)
            return Results.BadRequest(new { success = false, error = "LoRA name and images are required" });

        var result = await pythonService.TrainLoraAsync(loraName, userId, files);
        return Results.Ok(new { success = true, result });
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

// SSE Streaming endpoint for LoRA training with progress
app.MapPost("/api/train-lora/stream", async (HttpRequest req, HttpContext context, IConfiguration config) =>
{
    var pythonBaseUrl = config["PythonBackend:BaseUrl"] ?? "http://localhost:8000";

    if (!req.HasFormContentType)
    {
        context.Response.ContentType = "text/event-stream";
        var errorData = JsonSerializer.Serialize(new
        {
            @event = "error",
            success = false,
            error = "Invalid form data"
        });
        await context.Response.WriteAsync($"data: {errorData}\n\n");
        return;
    }

    context.Response.ContentType = "text/event-stream";
    context.Response.Headers.Append("Cache-Control", "no-cache");
    context.Response.Headers.Append("Connection", "keep-alive");

    using var httpClient = new HttpClient();
    httpClient.Timeout = TimeSpan.FromMinutes(60); // Training can take a long time

    try
    {
        // Read form and forward to Python backend
        var form = await req.ReadFormAsync();
        var formData = new MultipartFormDataContent();

        // Add form fields
        var loraName = form["lora_name"].ToString();
        var userId = form["user_id"].ToString();

        if (string.IsNullOrEmpty(loraName))
        {
            var errorData = JsonSerializer.Serialize(new
            {
                @event = "error",
                success = false,
                error = "LoRA name is required"
            });
            await context.Response.WriteAsync($"data: {errorData}\n\n");
            return;
        }

        formData.Add(new StringContent(loraName), "lora_name");
        formData.Add(new StringContent(userId), "user_id");

        // Add optional training settings
        if (form.ContainsKey("fast_mode"))
            formData.Add(new StringContent(form["fast_mode"].ToString()), "fast_mode");
        if (form.ContainsKey("num_train_epochs") && !string.IsNullOrEmpty(form["num_train_epochs"].ToString()))
            formData.Add(new StringContent(form["num_train_epochs"].ToString()), "num_train_epochs");
        if (form.ContainsKey("learning_rate"))
            formData.Add(new StringContent(form["learning_rate"].ToString()), "learning_rate");
        if (form.ContainsKey("lora_rank"))
            formData.Add(new StringContent(form["lora_rank"].ToString()), "lora_rank");
        if (form.ContainsKey("with_prior_preservation"))
            formData.Add(new StringContent(form["with_prior_preservation"].ToString()), "with_prior_preservation");

        // Add files
        foreach (var file in form.Files)
        {
            var streamContent = new StreamContent(file.OpenReadStream());
            streamContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(
                file.ContentType ?? "image/jpeg"
            );
            formData.Add(streamContent, "images", file.FileName);
        }

        var request2 = new HttpRequestMessage(HttpMethod.Post, $"{pythonBaseUrl}/train-lora/stream")
        {
            Content = formData
        };

        using var response = await httpClient.SendAsync(
            request2,
            HttpCompletionOption.ResponseHeadersRead,
            context.RequestAborted
        );

        if (!response.IsSuccessStatusCode)
        {
            var errorData = JsonSerializer.Serialize(new
            {
                @event = "error",
                success = false,
                error = $"Python backend returned status {response.StatusCode}",
                message = "Failed to connect to training service"
            });
            await context.Response.WriteAsync($"data: {errorData}\n\n");
            return;
        }

        using var stream = await response.Content.ReadAsStreamAsync(context.RequestAborted);
        using var reader = new StreamReader(stream);

        while (!reader.EndOfStream && !context.RequestAborted.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(context.RequestAborted);
            if (line != null)
            {
                await context.Response.WriteAsync(line + "\n");
                await context.Response.Body.FlushAsync(context.RequestAborted);
            }
        }
    }
    catch (OperationCanceledException)
    {
        // Request was cancelled, that's fine
    }
    catch (Exception ex)
    {
        var errorData = JsonSerializer.Serialize(new
        {
            @event = "error",
            success = false,
            error = ex.Message,
            message = "Failed to connect to training service"
        });
        await context.Response.WriteAsync($"data: {errorData}\n\n");
    }
});

app.MapGet("/api/loras/{userId}", (string userId, FileStorageService storageService) =>
{
    try
    {
        var loras = storageService.GetUserLoras(userId);
        return Results.Ok(new { success = true, loras });
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

app.MapGet("/api/images/{userId}", (string userId, FileStorageService storageService) =>
{
    try
    {
        var images = storageService.GetUserImages(userId);
        return Results.Ok(new { success = true, images });
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

// Model Management API Endpoints
app.MapGet("/api/models", async (IConfiguration config) =>
{
    var pythonBaseUrl = config["PythonBackend:BaseUrl"] ?? "http://localhost:8000";
    using var httpClient = new HttpClient();
    try
    {
        var response = await httpClient.GetAsync($"{pythonBaseUrl}/models");
        var content = await response.Content.ReadAsStringAsync();
        return Results.Content(content, "application/json");
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

app.MapGet("/api/models/current", async (IConfiguration config) =>
{
    var pythonBaseUrl = config["PythonBackend:BaseUrl"] ?? "http://localhost:8000";
    using var httpClient = new HttpClient();
    try
    {
        var response = await httpClient.GetAsync($"{pythonBaseUrl}/models/current");
        var content = await response.Content.ReadAsStringAsync();
        return Results.Content(content, "application/json");
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

app.MapGet("/api/models/{modelId}/status", async (string modelId, IConfiguration config) =>
{
    var pythonBaseUrl = config["PythonBackend:BaseUrl"] ?? "http://localhost:8000";
    using var httpClient = new HttpClient();
    try
    {
        var response = await httpClient.GetAsync($"{pythonBaseUrl}/models/{modelId}/status");
        var content = await response.Content.ReadAsStringAsync();
        return Results.Content(content, "application/json");
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

app.MapPost("/api/models/{modelId}/download", async (string modelId, HttpContext context, IConfiguration config) =>
{
    var pythonBaseUrl = config["PythonBackend:BaseUrl"] ?? "http://localhost:8000";

    context.Response.ContentType = "text/event-stream";
    context.Response.Headers.Append("Cache-Control", "no-cache");
    context.Response.Headers.Append("Connection", "keep-alive");

    using var httpClient = new HttpClient();
    httpClient.Timeout = TimeSpan.FromMinutes(30); // Model download can take a while

    try
    {
        var request = new HttpRequestMessage(HttpMethod.Post, $"{pythonBaseUrl}/models/{modelId}/download");
        using var response = await httpClient.SendAsync(
            request,
            HttpCompletionOption.ResponseHeadersRead,
            context.RequestAborted
        );

        if (!response.IsSuccessStatusCode)
        {
            var errorData = JsonSerializer.Serialize(new
            {
                @event = "error",
                modelId,
                error = $"Python backend returned status {response.StatusCode}"
            });
            await context.Response.WriteAsync($"data: {errorData}\n\n");
            return;
        }

        using var stream = await response.Content.ReadAsStreamAsync(context.RequestAborted);
        using var reader = new StreamReader(stream);

        while (!reader.EndOfStream && !context.RequestAborted.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(context.RequestAborted);
            if (line != null)
            {
                await context.Response.WriteAsync(line + "\n");
                await context.Response.Body.FlushAsync(context.RequestAborted);
            }
        }
    }
    catch (OperationCanceledException)
    {
        // Request was cancelled
    }
    catch (Exception ex)
    {
        var errorData = JsonSerializer.Serialize(new
        {
            @event = "error",
            modelId,
            error = ex.Message
        });
        await context.Response.WriteAsync($"data: {errorData}\n\n");
    }
});

app.MapPost("/api/models/{modelId}/load", async (string modelId, IConfiguration config) =>
{
    var pythonBaseUrl = config["PythonBackend:BaseUrl"] ?? "http://localhost:8000";
    using var httpClient = new HttpClient();
    httpClient.Timeout = TimeSpan.FromMinutes(10); // Model loading can take a while
    try
    {
        var response = await httpClient.PostAsync($"{pythonBaseUrl}/models/{modelId}/load", null);
        var content = await response.Content.ReadAsStringAsync();
        return Results.Content(content, "application/json");
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

app.MapPost("/api/models/unload", async (IConfiguration config) =>
{
    var pythonBaseUrl = config["PythonBackend:BaseUrl"] ?? "http://localhost:8000";
    using var httpClient = new HttpClient();
    try
    {
        var response = await httpClient.PostAsync($"{pythonBaseUrl}/models/unload", null);
        var content = await response.Content.ReadAsStringAsync();
        return Results.Content(content, "application/json");
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

app.MapGet("/api/system/gpu", async (IConfiguration config) =>
{
    var pythonBaseUrl = config["PythonBackend:BaseUrl"] ?? "http://localhost:8000";
    using var httpClient = new HttpClient();
    try
    {
        var response = await httpClient.GetAsync($"{pythonBaseUrl}/system/gpu");
        var content = await response.Content.ReadAsStringAsync();
        return Results.Content(content, "application/json");
    }
    catch (Exception ex)
    {
        return Results.BadRequest(new { success = false, error = ex.Message });
    }
});

// Blazor Components
app.MapRazorComponents<LoraMint.Web.Components.App>()
    .AddInteractiveServerRenderMode();

app.Run();
