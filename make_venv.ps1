$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($False)

Write-Host "Running Wabbajack Cleaner environment setup."

Write-Host "Removing existing virtual environment directory."

Remove-Item -LiteralPath "venv" -Force -Recurse -ErrorAction SilentlyContinue

Write-Host "Initializing new virtual environment."

python -m venv venv

Write-Host "Activating new virtual environment."

.\venv\Scripts\activate

Write-Host "Updating pip."

python -m pip install --upgrade pip

Write-Host "Installing dependencies from .\packages.txt file."

pip install -r .\packages.txt

Write-Host "New virtual environment is ready."

Write-Host "Freezing installed packages in .\requirements.txt file."

pip freeze > .\requirements.txt

$requirements = get-content ".\requirements.txt"

[System.IO.File]::WriteAllLines(".\requirements.txt", $requirements, $OutputEncoding)

Write-Host "Installed dependencies written to .\requirements.txt file."
