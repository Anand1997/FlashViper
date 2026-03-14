# 1. Find MSBuild
$msBuildPaths = @(
    "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe",
    "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
    "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
    "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe"
)

$msBuildPath = $null
foreach ($path in $msBuildPaths) {
    if (Test-Path $path) {
        $msBuildPath = $path
        break
    }
}

if (-not $msBuildPath) {
    # Try using vswhere as a fallback
    $vswherePath = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswherePath) {
        $msBuildPath = & $vswherePath -latest -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe
    }
}

if (-not $msBuildPath) {
    Write-Error "MSBuild not found. Please ensure Visual Studio or Build Tools are installed."
    exit 1
}

# 2. Build the project
Write-Host "--- Building MQSim ---" -ForegroundColor Cyan
& $msBuildPath MQSim.sln /p:Configuration=Release /p:Platform=x64 /t:Rebuild

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed!"
    exit $LASTEXITCODE
}

# 3. Run the simulation
$ssdConfig = "ssdconfig.xml"
$workloadConfig = "workload.xml"

if (-Not (Test-Path $ssdConfig)) {
    Write-Error "SSD config file not found: $ssdConfig"
    exit 1
}

if (-Not (Test-Path $workloadConfig)) {
    Write-Error "Workload config file not found: $workloadConfig"
    exit 1
}

Write-Host "`n--- Running MQSim ---" -ForegroundColor Green
& .\MQSim.exe -i $ssdConfig -w $workloadConfig

if ($LASTEXITCODE -ne 0) {
    Write-Error "Simulation failed!"
    exit $LASTEXITCODE
}

Write-Host "`nSimulation completed successfully." -ForegroundColor Green
