$OutputEncoding = [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($False)

Write-Host "Making virtual environment."

Write-Host "Removing existing virtual environment directory."

Remove-Item -LiteralPath "venv" -Force -Recurse -ErrorAction SilentlyContinue

Write-Host "Initializing new virtual environment."

python -m venv venv

Write-Host "Activating new virtual environment."

.\venv\Scripts\activate

Write-Host "Updating pip."

python -m pip install --upgrade pip

Write-Host "Installing package dependencies from .\packages.txt file."

pip install -r .\packages.txt

Write-Host "New virtual environment is ready."

Write-Host "Freezing installed packages."

pip freeze > .\requirements.txt

$requirements = get-content ".\requirements.txt"

[System.IO.File]::WriteAllLines(".\requirements.txt", $requirements, $OutputEncoding)

Write-Host "Installed package dependencies written to .\requirements.txt file."
