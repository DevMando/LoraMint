using LoraMint.Web.Models;

namespace LoraMint.Web.Services;

public class FileStorageService
{
    private readonly IConfiguration _configuration;
    private readonly string _lorasBasePath;
    private readonly string _outputsBasePath;

    public FileStorageService(IConfiguration configuration)
    {
        _configuration = configuration;
        _lorasBasePath = _configuration["Storage:LorasPath"] ?? "../../../data/loras";
        _outputsBasePath = _configuration["Storage:OutputsPath"] ?? "../../../data/outputs";

        // Ensure directories exist
        Directory.CreateDirectory(_lorasBasePath);
        Directory.CreateDirectory(_outputsBasePath);
    }

    public List<LoraInfo> GetUserLoras(string userId)
    {
        var userLoraPath = Path.Combine(_lorasBasePath, userId);

        if (!Directory.Exists(userLoraPath))
            return new List<LoraInfo>();

        var loraFiles = Directory.GetFiles(userLoraPath, "*.safetensors");

        return loraFiles.Select(filePath => new LoraInfo
        {
            Name = Path.GetFileNameWithoutExtension(filePath),
            FileName = Path.GetFileName(filePath),
            FilePath = filePath,
            FileSize = new FileInfo(filePath).Length,
            CreatedAt = File.GetCreationTime(filePath)
        }).OrderByDescending(l => l.CreatedAt).ToList();
    }

    public List<ImageInfo> GetUserImages(string userId)
    {
        var userOutputPath = Path.Combine(_outputsBasePath, userId);

        if (!Directory.Exists(userOutputPath))
            return new List<ImageInfo>();

        var imageExtensions = new[] { ".png", ".jpg", ".jpeg" };
        var imageFiles = Directory.GetFiles(userOutputPath)
            .Where(f => imageExtensions.Contains(Path.GetExtension(f).ToLower()))
            .ToArray();

        return imageFiles.Select(filePath => new ImageInfo
        {
            FileName = Path.GetFileName(filePath),
            FilePath = filePath,
            Url = $"/outputs/{userId}/{Path.GetFileName(filePath)}",
            CreatedAt = File.GetCreationTime(filePath)
        }).OrderByDescending(i => i.CreatedAt).ToList();
    }

    public string GetLoraPath(string userId, string loraFileName)
    {
        return Path.Combine(_lorasBasePath, userId, loraFileName);
    }

    public string GetOutputPath(string userId, string fileName)
    {
        return Path.Combine(_outputsBasePath, userId, fileName);
    }
}
