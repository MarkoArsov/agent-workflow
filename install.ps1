# Install Agent Flow on Windows.
#
#   irm https://agentic.markoarsov.com/install.ps1 | iex
#
# Options:
#   & ([scriptblock]::Create((irm https://agentic.markoarsov.com/install.ps1))) --project .
#   --project PATH       install into one project instead of for your user account
#   --agents claude ...  choose agent CLIs instead of detecting them
# Other:
#   $env:AGENTFLOW_REF = "v0.1.0"   pin a release tag or branch (default: latest release, else main)
#   $env:AGENTFLOW_NO_MODIFY_PATH = 1  leave your user PATH unchanged
#   --local-source PATH             install from a checkout without downloading (first argument)
& {
  $ErrorActionPreference = "Stop"
  $ProgressPreference = "SilentlyContinue"
  $repo = "MarkoArsov/agent-workflow"

  function Find-Python {
    # py is the python.org launcher; python may be the Microsoft Store stub, which fails this check.
    foreach ($candidate in @(@("py", "-3"), @("python"), @("python3"))) {
      if (-not (Get-Command $candidate[0] -ErrorAction SilentlyContinue)) { continue }
      $rest = @($candidate | Select-Object -Skip 1)
      try {
        $found = & $candidate[0] @rest -c "import sys; print(sys.executable if sys.version_info >= (3, 11) else '')" 2>$null
      } catch { continue }
      if ($LASTEXITCODE -eq 0 -and $found) { return "$found".Trim() }
    }
    throw "agentflow: Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ and run this again."
  }

  $python = Find-Python
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "agentflow: Git is required. Install it from https://git-scm.com/downloads and run this again."
  }
  $options = @($args)
  $binDir = Join-Path $HOME ".local\bin"

  function Add-ToPath {
    # Before installing, so the summary sees the command on PATH; say so after.
    if ($options -contains "--project" -or $env:AGENTFLOW_NO_MODIFY_PATH) { return $false }
    if (@($env:Path -split ";") -notcontains $binDir) { $env:Path = "$binDir;$env:Path" }
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $entries = @($userPath -split ";" | Where-Object { $_ })
    if ($entries -contains $binDir) { return $false }
    [Environment]::SetEnvironmentVariable("Path", (@($binDir) + $entries) -join ";", "User")
    return $true
  }

  function Install-From([string]$source, [string[]]$extra) {
    $pathAdded = Add-ToPath
    & $python -X utf8 (Join-Path $source "install.py") --local-source $source @extra
    if ($LASTEXITCODE -ne 0) { throw "agentflow: installation failed." }
    if ($pathAdded -and $options -notcontains "--json") {
      Write-Host "Added $binDir to your user PATH. New terminals will find the agentflow command."
    }
  }

  if ($options.Count -ge 2 -and $options[0] -eq "--local-source") {
    Install-From $options[1] @($options | Select-Object -Skip 2)
    return
  }

  [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
  $ref = $env:AGENTFLOW_REF
  if (-not $ref) {
    # /releases/latest redirects to /releases/tag/<tag> once a release exists.
    $ref = "main"
    try {
      $request = [System.Net.WebRequest]::Create("https://github.com/$repo/releases/latest")
      $request.Method = "HEAD"
      $request.AllowAutoRedirect = $false
      $response = $request.GetResponse()
      $location = $response.Headers["Location"]
      $response.Close()
      if ($location -match "/releases/tag/([^/]+)$") { $ref = $Matches[1] }
    } catch { }
  }

  $temp = Join-Path ([IO.Path]::GetTempPath()) ("agentflow-" + [guid]::NewGuid())
  New-Item -ItemType Directory -Path $temp | Out-Null
  try {
    Write-Host "Downloading Agent Flow ($ref)..."
    $archive = Join-Path $temp "package.tar.gz"
    try {
      Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/$repo/archive/$ref.tar.gz" -OutFile $archive
    } catch {
      throw "agentflow: Could not download $ref from github.com/$repo."
    }
    $extract = Join-Path $temp "extract.py"
    Set-Content -Path $extract -Encoding ASCII -Value @'
import pathlib
import sys
import tarfile
root = pathlib.Path(sys.argv[1])
with tarfile.open(root / "package.tar.gz", "r:gz") as archive:
    members = archive.getmembers()
    for member in members:
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
            raise SystemExit("Unsafe archive member")
    if hasattr(tarfile, "data_filter"):
        archive.extractall(root / "source", members=members, filter="data")
    else:
        archive.extractall(root / "source", members=members)
packages = list((root / "source").glob("*/workflow-package.json"))
if len(packages) != 1:
    raise SystemExit("Archive does not contain exactly one workflow package")
print(packages[0].parent)
'@
    $source = & $python $extract $temp
    if ($LASTEXITCODE -ne 0) { throw "agentflow: the downloaded archive failed its safety check." }
    Install-From "$source".Trim() $options
  } finally {
    Remove-Item -Recurse -Force $temp -ErrorAction SilentlyContinue
  }
} @args
