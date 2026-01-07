# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copy csproj and restore dependencies
COPY LoraMint.Web.csproj .
RUN dotnet restore

# Copy everything else and build
COPY . .
RUN dotnet build -c Release -o /app/build

# Publish stage
FROM build AS publish
RUN dotnet publish -c Release -o /app/publish

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

# Copy published app
COPY --from=publish /app/publish .

# Create data directories
RUN mkdir -p /app/data/loras /app/data/outputs

# Expose port
EXPOSE 80

# Set entry point
ENTRYPOINT ["dotnet", "LoraMint.Web.dll"]
