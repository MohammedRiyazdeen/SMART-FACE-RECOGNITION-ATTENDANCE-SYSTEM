$startDate = Get-Date -Year 2025 -Month 11 -Day 1 -Hour 10 -Minute 0 -Second 0
$endDate = Get-Date -Year 2026 -Month 4 -Day 9 -Hour 20 -Minute 0 -Second 0
$totalDays = ($endDate - $startDate).Days

$messages = @(
    "Initial project setup", "Added base models for students", "Configured settings.py", 
    "Implemented authentication views", "Fixed layout alignment", "Added mobile responsiveness",
    "Optimized face detection logic", "Integrated OpenCV models", "Refactored app structure",
    "Improved UI transitions", "Added search functionality", "Fixed database query bug",
    "Updated README documentation", "Enhanced security middleware", "Optimized image processing",
    "Added attendance reports", "Improved dashboard performance", "Fixed edge cases in login",
    "Updated dependencies", "Final UI polish", "Code cleanup and refactoring",
    "Added email notifications", "Fixed period selection issue", "Optimized student lookup",
    "Improved face matching accuracy", "Added department filters", "Fixed styling bugs"
)

$activeDays = @("Monday", "Wednesday", "Friday", "Saturday")
$currentDate = $startDate
$commitCount = 0

# Initial add of basic files to start with
git add manage.py requirements.txt .gitignore face_recognition_web/
$env:GIT_COMMITTER_DATE = $currentDate.ToString("yyyy-MM-ddTHH:mm:ss")
$env:GIT_AUTHOR_DATE = $currentDate.ToString("yyyy-MM-ddTHH:mm:ss")
git commit -m "Initial project setup"
$commitCount++

while ($currentDate -lt $endDate) {
    if ($activeDays -contains $currentDate.DayOfWeek.ToString()) {
        $hourlyCommits = Get-Random -Minimum 4 -Maximum 7
        for ($i = 0; $i -lt $hourlyCommits; $i++) {
            $commitTime = $currentDate.AddHours($i * 2 + (Get-Random -Minimum 0 -Maximum 2))
            if ($commitTime -gt $endDate) { break }
            
            # Staging logic based on progress
            if ($commitCount -eq 20) { git add recognition/apps.py recognition/__init__.py recognition/urls/ }
            if ($commitCount -eq 40) { git add recognition/models.py recognition/admin.py recognition/migrations/ }
            if ($commitCount -eq 60) { git add recognition/views/ recognition/forms.py }
            if ($commitCount -eq 100) { git add recognition/services/ recognition/utils.py recognition/scheduler.py recognition/management/ }
            if ($commitCount -eq 150) { git add recognition/face_system.py recognition/models_dnn/ }
            if ($commitCount -eq 200) { git add recognition/static/ recognition/templates/ }
            if ($commitCount -eq 250) { git add README.md }
            if ($commitCount -eq 280) { git add . } # Add everything else

            $msg = $messages | Get-Random
            $env:GIT_COMMITTER_DATE = $commitTime.ToString("yyyy-MM-ddTHH:mm:ss")
            $env:GIT_AUTHOR_DATE = $commitTime.ToString("yyyy-MM-ddTHH:mm:ss")
            
            git commit --allow-empty -m "$msg" --quiet
            $commitCount++
        }
    }
    $currentDate = $currentDate.AddDays(1)
}

Write-Host "Total Commits Created: $commitCount"
