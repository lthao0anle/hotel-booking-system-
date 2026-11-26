@echo off
chcp 65001 >nul
title Tangerine Grand Hotel — Web System
cd /d "%~dp0web_app"
call Chay_Web.bat
