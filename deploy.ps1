# deploy.ps1 — 빌드 후 변경된 사이트 파일 전체 커밋·푸시
# 사용법: .\deploy.ps1 "커밋 메시지"

param([string]$msg = "rebuild site")

Write-Host "1. build.py 실행..." -ForegroundColor Cyan
py build.py
if (-not $?) { Write-Host "[오류] build.py 실패" -ForegroundColor Red; exit 1 }

Write-Host "2. 변경 파일 스테이징..." -ForegroundColor Cyan
git add site/data/ site/essays/ site/critics/ site/writers/ persons.json
git add index.html critics.html writers.html concepts.html research.html criticism.html ask.html contribute.html style.css

Write-Host "3. 커밋..." -ForegroundColor Cyan
git commit -m $msg
if (-not $?) { Write-Host "변경사항 없음 또는 커밋 실패" -ForegroundColor Yellow; exit 0 }

Write-Host "4. 푸시..." -ForegroundColor Cyan
git push origin main

Write-Host "완료." -ForegroundColor Green
