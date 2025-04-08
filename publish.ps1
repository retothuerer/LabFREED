param(
    [string]$target
)

if (-not $target) {
    Write-Host "Usage: ./publish.ps1 [test|prod]"
    exit 1
}

python update_readme.py

if ($target -eq "prod") {
    flit publish --repository pypi
}
else {
    flit publish --repository testpypi
}
