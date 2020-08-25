@echo off

python -m robot -d output --logtitle "Task log" tasks || goto :error

echo Success
goto :EOF

:error
echo Failed with error %errorlevel%.
exit /b %errorlevel%
