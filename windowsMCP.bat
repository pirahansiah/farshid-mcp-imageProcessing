@echo off
setlocal

set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "MCP_EXE=%VENV_DIR%\Scripts\farshid-mcp-imageprocessing.exe"
set "PYTHON314=%LocalAppData%\Programs\Python\Python314\python.exe"
set "PYTHON314_SCRIPTS=%LocalAppData%\Programs\Python\Python314\Scripts"
set "PYTHON_INSTALL_ID=Python.Python.3.14"
set "PYTHON_INSTALL_FALLBACK_ID=Python.PythonInstallManager"
set "USE_CONDA=0"

where conda >nul 2>nul
if not errorlevel 1 (
	call conda env list | findstr /r /c:"^[ ]*py314[ ]" >nul 2>nul
	if not errorlevel 1 (
		set "USE_CONDA=1"
	)
)

if "%USE_CONDA%"=="1" goto :setup_conda

call :ensure_python_installed
if errorlevel 1 exit /b %ERRORLEVEL%

if not exist "%VENV_PY%" (
	if exist "%PYTHON314%" (
		echo Creating virtual environment with Python 3.14...
		"%PYTHON314%" -m venv "%VENV_DIR%"
		if errorlevel 1 goto :venv_failed
	) else (
		where py >nul 2>nul
		if not errorlevel 1 (
			echo Creating virtual environment with py -3.14...
			py -3.14 -m venv "%VENV_DIR%"
			if errorlevel 1 goto :venv_failed
		) else (
			where python >nul 2>nul
			if errorlevel 1 (
				echo Python was not found on PATH.
				echo Install Python or open a shell where python is available, then run this file again.
				exit /b 1
			)

			echo Creating virtual environment with python...
			python -m venv "%VENV_DIR%"
			if errorlevel 1 goto :venv_failed
		)
	)
)

echo Upgrading pip in %VENV_DIR%...
"%VENV_PY%" -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo Installing farshid_mcp_imageprocessing in %VENV_DIR%...
"%VENV_PY%" -m pip install farshid_mcp_imageprocessing
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

if not exist "%MCP_EXE%" (
	echo Expected MCP executable was not created:
	echo %MCP_EXE%
	exit /b 1
)

if not exist ".vscode" mkdir ".vscode"
(
	echo {
	echo   "servers": {
	echo     "imageProcessing": {
	echo       "command": ".venv\\Scripts\\farshid-mcp-imageprocessing.exe",
	echo       "type": "stdio"
	echo     }
	echo   }
	echo }
) > ".vscode\mcp.json"

echo Starting MCP server...
"%MCP_EXE%"
exit /b %ERRORLEVEL%

:setup_conda
echo Using conda environment py314...
call conda run -n py314 python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo Installing farshid_mcp_imageprocessing in conda env py314...
call conda run -n py314 python -m pip install farshid_mcp_imageprocessing
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

if not exist ".vscode" mkdir ".vscode"
(
	echo {
	echo   "servers": {
	echo     "imageProcessing": {
	echo       "command": "conda",
	echo       "args": ["run", "--no-capture-output", "-n", "py314", "farshid-mcp-imageprocessing"],
	echo       "type": "stdio"
	echo     }
	echo   }
	echo }
) > ".vscode\mcp.json"

echo Starting MCP server...
call conda run --no-capture-output -n py314 farshid-mcp-imageprocessing
exit /b %ERRORLEVEL%

:ensure_python_installed
if exist "%PYTHON314%" goto :python_ready

where py >nul 2>nul
if not errorlevel 1 goto :python_ready

where python >nul 2>nul
if not errorlevel 1 goto :python_ready

where winget >nul 2>nul
if errorlevel 1 (
	echo Python was not found and winget is not available.
	echo Install Python 3.14 or later, then run this file again.
	exit /b 1
)

echo Python was not found. Installing Python 3.14 with winget...
winget install --id %PYTHON_INSTALL_ID% -e --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
	echo Python 3.14 package was not installed. Trying Python Install Manager for the latest Python 3...
	winget install --id %PYTHON_INSTALL_FALLBACK_ID% -e --accept-package-agreements --accept-source-agreements
	if errorlevel 1 (
		echo Automatic Python installation failed.
		exit /b 1
	)

	py install 3
	if errorlevel 1 (
		echo Automatic Python installation failed.
		exit /b 1
	)
)

:python_ready
if exist "%PYTHON314%" (
	set "PATH=%LocalAppData%\Programs\Python\Python314;%PYTHON314_SCRIPTS%;%PATH%"
)
exit /b 0

:venv_failed
echo Failed to create virtual environment.
exit /b 1