@echo off
title Coletor de Dados - Voto Aberto
color 0A

:menu
cls
echo ========================================================
echo            COLETOR DE DADOS - VOTO ABERTO
echo ========================================================
echo.
echo Escolha qual modulo deseja atualizar:
echo.
echo [1] Cotas (Gastos Parlamentares)
echo [2] Votacoes
echo [3] Proposicoes
echo [4] Rodar TODOS os 3 modulos em sequencia
echo [0] Sair
echo.
set /p opcao="Digite o numero desejado e aperte ENTER: "

if "%opcao%"=="1" goto cotas
if "%opcao%"=="2" goto votacoes
if "%opcao%"=="3" goto proposicoes
if "%opcao%"=="4" goto todos
if "%opcao%"=="0" exit

echo.
echo Opcao invalida! Tente novamente.
pause
goto menu

:cotas
cls
echo Rodando Coletor de Cotas...
python coletores\coletor_cotas.py
pause
goto menu

:votacoes
cls
echo Rodando Coletor de Votacoes...
python coletores\coletor_votacoes.py
pause
goto menu

:proposicoes
cls
echo Rodando Coletor de Proposicoes...
python coletores\coletor_proposicoes.py
pause
goto menu

:todos
cls
echo Rodando TODOS os coletores em sequencia...
echo.
echo [1/3] Cotas...
python coletores\coletor_cotas.py
echo.
echo [2/3] Votacoes...
python coletores\coletor_votacoes.py
echo.
echo [3/3] Proposicoes...
python coletores\coletor_proposicoes.py
pause
goto menu