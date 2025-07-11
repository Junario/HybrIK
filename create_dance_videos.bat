@echo off
chcp 65001 > nul
echo ==========================================
echo    Dance Keypoints Video Creator
echo ==========================================
echo.

set /p "start_frame=시작 프레임 번호 (기본값: 0): "
if "%start_frame%"=="" set start_frame=0

set /p "end_frame=종료 프레임 번호 (기본값: 100): "
if "%end_frame%"=="" set end_frame=100

set /p "fps=영상 FPS (기본값: 15): "
if "%fps%"=="" set fps=15

echo.
echo 🎬 Combined 영상 생성 시작...
echo    - 프레임 범위: %start_frame% ~ %end_frame%
echo    - FPS: %fps%
echo.

python visualize_dance_keypoints.py --start %start_frame% --end %end_frame% --video-combined --video-fps %fps%

echo.
echo ✨ 작업 완료! 생성된 영상을 확인해보세요.
pause 