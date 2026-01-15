# LoraMint - Combined Blazor + Python for Hugging Face Spaces
# Runs both the Blazor frontend and Python AI backend in one container

# ============================================
# Stage 1: Build Blazor Application
# ============================================
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS blazor-build
WORKDIR /src

# Copy Blazor project files
COPY src/LoraMint.Web/LoraMint.Web.csproj ./LoraMint.Web/
WORKDIR /src/LoraMint.Web
RUN dotnet restore

# Copy all Blazor source and build
COPY src/LoraMint.Web/ ./
RUN dotnet publish -c Release -o /app/blazor

# ============================================
# Stage 2: Runtime with .NET + Python + CUDA
# ============================================
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # .NET dependencies
    wget \
    apt-transport-https \
    # Python dependencies
    python3.10 \
    python3-pip \
    python3.10-venv \
    # Process manager
    supervisor \
    # Utilities
    git \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install .NET 8 Runtime
RUN wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y aspnetcore-runtime-8.0 \
    && rm -rf /var/lib/apt/lists/*

# Create user with ID 1000 (required by HF Spaces)
RUN useradd -m -u 1000 user

# Set up directories
WORKDIR /app
RUN mkdir -p /app/blazor /app/python-backend /app/data/models /app/data/loras /app/data/outputs /app/data/temp \
    && chown -R user:user /app

# Copy Python backend
COPY --chown=user:user src/python-backend/ /app/python-backend/

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r /app/python-backend/requirements.txt

# Copy built Blazor app
COPY --from=blazor-build --chown=user:user /app/blazor /app/blazor

# Copy HF-specific configuration
COPY --chown=user:user hf-space/appsettings.HuggingFace.json /app/blazor/appsettings.Production.json
COPY --chown=user:user hf-space/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set environment variables
ENV ASPNETCORE_ENVIRONMENT=Production
ENV ASPNETCORE_URLS=http://+:7860
ENV DOTNET_RUNNING_IN_CONTAINER=true
ENV HF_HOME=/app/data/hf_cache
ENV TRANSFORMERS_CACHE=/app/data/hf_cache
ENV TORCH_HOME=/app/data/torch_cache
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER user

# Expose port 7860 (HF Spaces requirement)
EXPOSE 7860

# Start both services via supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
