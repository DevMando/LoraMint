using LoraMint.Web.Models;
using LoraMint.Web.Services;
using LoraMint.Web.BackgroundServices;
using Microsoft.Extensions.FileProviders;

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
    return new HttpClient { BaseAddress = new Uri(navigationManager.BaseUri) };
});

builder.Services.AddSingleton<FileStorageService>();

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

// Blazor Components
app.MapRazorComponents<LoraMint.Web.Components.App>()
    .AddInteractiveServerRenderMode();

app.Run();
