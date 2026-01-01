# 🚀 Quick Push to GitHub Script
# Run this after creating the repository on GitHub

Write-Host "🌌 Advanced Modular RAG - GitHub Push Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to project directory
$projectDir = "C:\Users\aryan\OneDrive\Desktop\Simple_ChatBot"
Set-Location $projectDir

Write-Host "📍 Current Directory: $projectDir" -ForegroundColor Yellow
Write-Host ""

# Step 1: Clean test files
Write-Host "🧹 Step 1: Cleaning test output files..." -ForegroundColor Green
$testFiles = @(
    "Backend\test_output.txt",
    "Backend\test_results.txt",
    "Backend\test_results_utf8.txt",
    "test_logs.txt",
    "test_logs_clean.txt",
    "logs.txt"
)

foreach ($file in $testFiles) {
    if (Test-Path $file) {
        Remove-Item $file -Force
        Write-Host "  ✅ Removed: $file" -ForegroundColor DarkGreen
    }
}

Write-Host ""

# Step 2: Check if .gitkeep exists in uploads
Write-Host "📁 Step 2: Ensuring .gitkeep in uploads..." -ForegroundColor Green
$gitkeepPath = "Backend\uploads\.gitkeep"
if (-not (Test-Path $gitkeepPath)) {
    New-Item -Path $gitkeepPath -ItemType File -Force | Out-Null
    Write-Host "  ✅ Created .gitkeep in Backend/uploads/" -ForegroundColor DarkGreen
} else {
    Write-Host "  ✅ .gitkeep already exists" -ForegroundColor DarkGreen
}

Write-Host ""

# Step 3: Verify .env is not tracked
Write-Host "🔒 Step 3: Checking .env files..." -ForegroundColor Green
$envFile = "Backend\.env"
if (Test-Path $envFile) {
    Write-Host "  ✅ Backend/.env exists (will be ignored by .gitignore)" -ForegroundColor DarkGreen
} else {
    Write-Host "  ⚠️  Backend/.env not found - create from .env.example" -ForegroundColor Yellow
}

Write-Host""

# Step 4: Initialize Git if needed
Write-Host "📂 Step 4: Initializing Git repository..." -ForegroundColor Green
if (-not (Test-Path ".git")) {
    git init
    Write-Host "  ✅ Git repository initialized" -ForegroundColor DarkGreen
} else {
    Write-Host "  ✅ Git repository already exists" -ForegroundColor DarkGreen
}

Write-Host ""

# Step 5: Stage files
Write-Host "📦 Step 5: Staging files..." -ForegroundColor Green
git add .
Write-Host "  ✅ All files staged" -ForegroundColor DarkGreen

Write-Host ""

# Step 6: Check status
Write-Host "📊 Step 6: Git status..." -ForegroundColor Green
git status --short
Write-Host ""

# Step 7: Verify .env is not staged
Write-Host "🔍 Step 7: Verifying .env is ignored..." -ForegroundColor Green
$stagedFiles = git diff --cached --name-only
if ($stagedFiles -match "\.env$") {
    Write-Host "  ❌ ERROR: .env file is staged! This should not happen." -ForegroundColor Red
    Write-Host "  Run: git rm --cached Backend/.env" -ForegroundColor Red
    exit 1
} else {
    Write-Host "  ✅ .env files are properly ignored" -ForegroundColor DarkGreen
}

Write-Host ""

# Step 8: Commit
Write-Host "💾 Step 8: Creating initial commit..." -ForegroundColor Green
git commit -m "Initial commit: Advanced Modular RAG Chatbot with Agentic Chunking"
Write-Host "  ✅ Commit created" -ForegroundColor DarkGreen

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "✅ Repository prepared successfully!" -ForegroundColor Green
Write-Host ""

# Step 9: Instructions for GitHub
Write-Host "📝 Next Steps:" -ForegroundColor Magenta
Write-Host ""
Write-Host "1. Create a new repository on GitHub:" -ForegroundColor White
Write-Host "   https://github.com/new" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Repository name: advanced-modular-rag-chatbot" -ForegroundColor Yellow
Write-Host "3. Description: 🌌 Advanced Modular RAG chatbot with Agentic Chunking, FAISS HNSW, and Azure OpenAI GPT-5" -ForegroundColor Yellow
Write-Host "4. Choose Public or Private" -ForegroundColor Yellow
Write-Host "5. DO NOT initialize with README (you already have one)" -ForegroundColor Red
Write-Host ""

Write-Host "6. After creating the repo, run these commands:" -ForegroundColor White
Write-Host ""
Write-Host "   git remote add origin https://github.com/AryanKadar/advanced-modular-rag-chatbot.git" -ForegroundColor Cyan
Write-Host "   git branch -M main" -ForegroundColor Cyan
Write-Host "   git push -u origin main" -ForegroundColor Cyan
Write-Host ""

Write-Host "7. Add topics on GitHub:" -ForegroundColor White
Write-Host "   rag, chatbot, azure-openai, faiss, hnsw, agentic-ai, llm, machine-learning" -ForegroundColor Cyan
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🎉 Happy coding! 🚀" -ForegroundColor Magenta
Write-Host ""

# Optional: Open GitHub in browser
Write-Host "🌐 Press Enter to open GitHub in browser, or Ctrl+C to skip..." -ForegroundColor Yellow
Read-Host
Start-Process "https://github.com/new"
