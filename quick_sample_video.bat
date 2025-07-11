@echo off
chcp 65001 > nul
echo ==========================================
echo    Quick Sample Video Creator
echo ==========================================
echo.

echo 🚀 빠른 샘플 영상 생성 (30개 프레임, 15 FPS)
echo    - 약 2초 길이의 Combined 영상이 생성됩니다.
echo.

python visualize_dance_keypoints.py --start 0 --end 30 --video-combined --video-fps 15

echo.
echo ✨ 샘플 영상 생성 완료!
pause 