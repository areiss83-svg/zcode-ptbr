@echo off
rem ============================================================
rem  Instalador pt-BR do ZCode Desktop (Windows)
rem  Um clique: extrai o app.asar, injeta o idioma, verifica tudo,
rem  faz backup timestamped e orienta o último passo.
rem  Requisitos: Python 3.8+ e Node.js (npx) no PATH.
rem ============================================================
cd /d "%~dp0"

where python >NUL 2>NUL
if errorlevel 1 (
  echo [X] Python nao encontrado no PATH. Instale em https://python.org e rode de novo.
  pause
  exit /b 1
)
where npx >NUL 2>NUL
if errorlevel 1 (
  echo [X] Node.js/npx nao encontrado no PATH. Instale em https://nodejs.org e rode de novo.
  pause
  exit /b 1
)

python tool\aplica_patch.py %*
set RC=%errorlevel%

if "%RC%"=="2" (
  echo.
  echo ============================================================
  echo  O ZCode esta aberto, entao o arquivo patcheado ficou em
  echo  estagio. Para concluir:
  echo    1. Feche o ZCode.
  echo    2. Rode tool\trocar_apos_fechar.cmd  (espera o app sair
  echo       e troca sozinho, com backup).
  echo    3. Abra o ZCode: Configuracoes - Geral - Idioma -
  echo       Portugues (Brasil).
  echo ============================================================
  pause
  exit /b 0
)
if not "%RC%"=="0" (
  echo.
  echo [X] O instalador retornou codigo %RC%. O app original esta intacto.
  pause
  exit /b %RC%
)

echo.
echo ============================================================
echo  Concluido. Abra o ZCode:
echo    Configuracoes - Geral - Idioma - Portugues (Brasil)
echo  Para reverter: restaure app.asar.bak-* da pasta resources.
echo  Apos atualizar o ZCode, rode este instalador novamente.
echo ============================================================
pause
