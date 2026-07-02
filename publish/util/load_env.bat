@echo off
REM ================================================================
REM Environment Variable Loader - Load config from .env
REM ================================================================

set "SCRIPT_DIR=%~dp0..\"

REM ================================================================
REM Read .env and set variables directly (no setlocal/endlocal)
REM ================================================================
for /f "usebackq eol=# delims=" %%a in ("%SCRIPT_DIR%.env") do (
    set "line=%%a"
    set "line=!line:#=!"
    for /f "tokens=1,* delims==" %%k in ("!line!") do (
        set "key=%%k"
        set "val=%%l"
        set "key=!key: =!"
        if not "!key!"=="" (
            set "!key!=!val!"
        )
    )
)

REM ================================================================
REM Fix SSH_KEY path - convert to absolute Unix path for ssh/scp
REM Git Bash uses /c/ prefix, not /mnt/c/
REM ================================================================
if defined SSH_KEY (
    if "!SSH_KEY:~1,1!"==":" (
        REM Convert Windows absolute path to Unix path for Git Bash
        set "SSH_KEY_UNIX=!SSH_KEY:C:=/c!"
        set "SSH_KEY_UNIX=!SSH_KEY_UNIX:\=/!"
        set "SSH_KEY=!SSH_KEY_UNIX!"
    ) else (
        REM Relative path - make absolute then convert
        set "SSH_KEY=!SCRIPT_DIR!..\..\deploy\!SSH_KEY!"
        set "SSH_KEY_UNIX=!SSH_KEY:C:=/c!"
        set "SSH_KEY_UNIX=!SSH_KEY_UNIX:\=/!"
        set "SSH_KEY=!SSH_KEY_UNIX!"
    )
)

REM ================================================================
REM Verify JAVA_HOME loaded
REM ================================================================
if not defined JAVA_HOME (
    echo [ERROR] JAVA_HOME not set - check .env file
    exit /b 1
)
if not exist "!JAVA_HOME!\bin\java.exe" (
    echo [ERROR] JDK not found: !JAVA_HOME!\bin\java.exe
    exit /b 1
)

exit /b 0