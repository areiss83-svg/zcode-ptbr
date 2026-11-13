@echo off
rem Troca o app.asar do ZCode pelo arquivo patcheado em estagio, assim que o ZCode fechar.
rem Gerado pelo projeto zcode-ptbr (harness/zcode-ptbr).
setlocal
set "STAGED=C:\Users\ander\AppData\Local\Programs\ZCode\resources\app.asar.novo-ptbr"
set "ASAR=C:\Users\ander\AppData\Local\Programs\ZCode\resources\app.asar"

if not exist "%STAGED%" (
  echo Arquivo em estagio nao encontrado: %STAGED%
  pause
  exit /b 1
)

echo Feche o ZCode agora. Esperando ele sair...
:espera
tasklist /FI "IMAGENAME eq ZCode.exe" 2>NUL | find /I "ZCode.exe" >NUL
if not errorlevel 1 (
  timeout /t 2 /nobreak >NUL
  goto espera
)

move /Y "%STAGED%" "%ASAR%" >NUL
if errorlevel 1 (
  echo FALHA ao trocar o arquivo. O original esta intacto.
  pause
  exit /b 1
)

echo Trocado com sucesso.
echo Abra o ZCode: Configuracoes ^> Geral ^> Idioma ^> Portugues (Brasil).
echo Para reverter, restaure o backup app.asar.bak-* na pasta resources.
pause
