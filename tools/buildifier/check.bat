@echo off
setlocal enabledelayedexpansion

set STATUS=0

for /R %%F in (BUILD BUILD.bazel *.bzl MODULE.bazel) do (
  echo %%F | findstr /I "\\third_party\\bazel\\" >nul
  if errorlevel 1 (
    buildifier --mode=check --lint=warn "%%F"
    if errorlevel 1 set STATUS=1
  )
)

exit /b %STATUS%
