@echo off
setlocal

echo =============================================
echo   COMITE DE IAs - Evaluador de CV
echo =============================================
echo.

:: --- Buscar Python compatible (3.13 o 3.12) via Python Launcher ---
set PYTHON_CMD=

py -3.13 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.13
    goto :python_found
)

py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.12
    goto :python_found
)

py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3.11
    goto :python_found
)

echo [ERROR] No se encontro Python 3.11, 3.12 ni 3.13 en este sistema.
echo.
echo  crewai requiere Python 3.10-3.13. Tu Python por defecto es 3.14,
echo  que aun no es compatible con crewai.
echo.
echo  Instala Python 3.13 desde: https://www.python.org/downloads/
echo  (marca la opcion "Add to PATH" e "Install launcher for all users")
echo.
pause
exit /b 1

:python_found
for /f "tokens=*" %%v in ('%PYTHON_CMD% --version 2^>^&1') do echo [INFO] Usando %%v
echo.

:: Actualizar pip silenciosamente
%PYTHON_CMD% -m pip install --upgrade pip --quiet

:: --- Verificar dependencias ---
echo [1/2] Verificando dependencias...
set FALTAN=0

for /f "tokens=*" %%p in (requirements.txt) do (
    if not "%%p"=="" (
        %PYTHON_CMD% -c "import pkg_resources; pkg_resources.require('%%p')" >nul 2>&1
        if errorlevel 1 (
            echo   [!] Falta: %%p
            set FALTAN=1
        )
    )
)

if "%FALTAN%"=="1" (
    echo.
    echo [2/2] Instalando dependencias faltantes...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion. Revisa tu conexion o permisos.
        pause
        exit /b 1
    )
    echo [OK] Dependencias instaladas correctamente.
) else (
    echo [OK] Todas las dependencias estan instaladas.
)

echo.
echo [2/2] Iniciando evaluador...
echo.

:: --- Seleccion de backend de IA ---
echo =============================================
echo   Selecciona el proveedor de IA:
echo.
echo   [1] Groq  (nube, requiere internet)
echo   [2] LM Studio  (local, sin internet)
echo =============================================
echo.

:elegir_backend
set /p OPCION="Tu eleccion (1 o 2): "

if "%OPCION%"=="1" (
    set EVALUADOR_BACKEND=groq
    echo.
    echo [OK] Usando Groq ^(Llama 3.3 70B^)
    echo.
    goto :lanzar
)

if "%OPCION%"=="2" (
    set EVALUADOR_BACKEND=lmstudio
    echo.
    set LMSTUDIO_URL=http://localhost:1234/v1
    echo [INFO] Se usara LM Studio en: http://localhost:1234/v1
    echo [INFO] Asegurate de tener LM Studio abierto con un modelo cargado.
    echo.
    goto :lanzar
)

echo [!] Opcion invalida. Introduce 1 o 2.
goto :elegir_backend

:lanzar
%PYTHON_CMD% evaluador_cv.py

echo.
echo =============================================
echo   Evaluacion completada.
echo =============================================
pause
endlocal
