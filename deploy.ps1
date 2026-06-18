# deploy.ps1 — 빌드 → 커밋·푸시 → Cloudflare 라이브 배포
# 사용법: .\deploy.ps1 "커밋 메시지"
# 주의: .gitignore가 essays/*.xml·.env·백업·작업CSV를 막으므로 git add -A 안전.

param([string]$msg = "rebuild site")

Write-Host "1. build.py 실행..." -ForegroundColor Cyan
py build.py
if (-not $?) { Write-Host "[오류] build.py 실패" -ForegroundColor Red; exit 1 }

Write-Host "2. 변경 파일 스테이징 (gitignore가 원문·크레덴셜 차단)..." -ForegroundColor Cyan
git add -A

Write-Host "3. 커밋..." -ForegroundColor Cyan
git commit -m $msg
if (-not $?) { Write-Host "변경사항 없음 (커밋 건너뜀) — 그래도 배포는 진행" -ForegroundColor Yellow }

Write-Host "4. 푸시..." -ForegroundColor Cyan
git push origin main

Write-Host "5. Cloudflare 배포 (wrangler deploy)..." -ForegroundColor Cyan
npx wrangler deploy
if (-not $?) { Write-Host "[오류] wrangler deploy 실패" -ForegroundColor Red; exit 1 }

Write-Host "완료 — 라이브 반영됨." -ForegroundColor Green
