@echo off
echo Instalando dependencias...
python -m pip install -r backend\requirements.txt -q

echo.
echo Subindo Swift NPS Analytics em http://localhost:5050
echo Para encerrar: feche esta janela ou pressione Ctrl+C
echo ---

python backend\api.py
pause