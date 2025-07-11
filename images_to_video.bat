@echo off
chcp 65001 > nul
echo ==========================================
echo    Images to Video Converter
echo ==========================================
echo.

set /p "folder_path=이미지 폴더 경로를 입력하세요: "
if "%folder_path%"=="" (
    echo 폴더 경로를 입력해주세요.
    pause
    exit /b
)

if not exist "%folder_path%" (
    echo 폴더가 존재하지 않습니다: %folder_path%
    pause
    exit /b
)

set /p "fps=영상 FPS (기본값: 15): "
if "%fps%"=="" set fps=15

echo.
echo 📁 폴더: %folder_path%
echo 🎬 FPS: %fps%
echo.

cd /d "%folder_path%"

:: 2D 영상 생성
if exist "2d_frame_*.png" (
    echo 🎨 2D 영상 생성 중...
    ffmpeg -y -framerate %fps% -i 2d_frame_%%04d.png -c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -movflags +faststart dance_2d.mp4
    echo ✅ dance_2d.mp4 생성 완료
    echo.
)

:: 3D 영상 생성
if exist "3d_frame_*.png" (
    echo 🎨 3D 영상 생성 중...
    ffmpeg -y -framerate %fps% -i 3d_frame_%%04d.png -c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -movflags +faststart dance_3d.mp4
    echo ✅ dance_3d.mp4 생성 완료
    echo.
)

:: Combined 영상 생성
if exist "combined_frame_*.png" (
    echo 🎨 Combined 영상 생성 중...
    ffmpeg -y -framerate %fps% -i combined_frame_%%04d.png -c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -movflags +faststart dance_combined.mp4
    echo ✅ dance_combined.mp4 생성 완료
    echo.
)

echo ✨ 모든 영상 생성 완료!
echo 📂 결과물 위치: %folder_path%
pause 