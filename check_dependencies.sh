#!/bin/bash

echo "=== HybrIK 환경 의존성 점검 ==="
echo ""

# 1. 현재 활성화된 환경 확인
echo "1. 현재 활성화된 환경:"
conda info --envs | grep "*"
echo ""

# 2. Python 버전 확인
echo "2. Python 버전:"
python --version
echo ""

# 3. CUDA 버전 확인
echo "3. CUDA 버전:"
nvidia-smi | grep "CUDA Version" || echo "CUDA 정보를 가져올 수 없습니다"
echo ""

# 4. PyTorch 관련 패키지 버전 확인
echo "4. PyTorch 관련 패키지:"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'CUDA version: {torch.version.cuda}')"
python -c "import torchvision; print(f'TorchVision: {torchvision.__version__}')"
echo ""

# 5. PyTorch3D 확인
echo "5. PyTorch3D:"
python -c "import pytorch3d; print(f'PyTorch3D: {pytorch3d.__version__}')" 2>/dev/null || echo "PyTorch3D import 실패"
echo ""

# 6. 핵심 의존성 패키지들 확인
echo "6. 핵심 의존성 패키지들:"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "import opencv; print(f'OpenCV: {opencv.__version__}')" 2>/dev/null || python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python -c "import scipy; print(f'SciPy: {scipy.__version__}')"
python -c "import matplotlib; print(f'Matplotlib: {matplotlib.__version__}')"
python -c "import yaml; print(f'PyYAML: {yaml.__version__}')" 2>/dev/null || echo "PyYAML: 설치되지 않음"
echo ""

# 7. SMPL 관련 패키지 확인
echo "7. SMPL 관련 패키지:"
python -c "import smplx; print(f'SMPL-X: {smplx.__version__}')" 2>/dev/null || echo "SMPL-X: 설치되지 않음"
python -c "import chumpy; print('Chumpy: 설치됨')" 2>/dev/null || echo "Chumpy: 설치되지 않음"
echo ""

# 8. GPU 메모리 확인
echo "8. GPU 메모리 상태:"
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader,nounits 2>/dev/null || echo "GPU 정보를 가져올 수 없습니다"
echo ""

# 9. PyTorch CUDA 테스트
echo "9. PyTorch CUDA 테스트:"
python -c "
import torch
if torch.cuda.is_available():
    device = torch.device('cuda')
    x = torch.randn(3, 3).to(device)
    print(f'CUDA 테스트 성공: {x.device}')
    print(f'사용 가능한 GPU 개수: {torch.cuda.device_count()}')
    print(f'현재 GPU: {torch.cuda.current_device()}')
    print(f'GPU 이름: {torch.cuda.get_device_name()}')
else:
    print('CUDA를 사용할 수 없습니다')
"
echo ""

# 10. 환경 경로 확인
echo "10. Python 경로:"
python -c "import sys; print('\\n'.join(sys.path))"
echo ""

echo "=== 점검 완료 ===" 