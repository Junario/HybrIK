# HybrIK 완전 설치 가이드 (PyTorch3D 포함) - 2024년 검증된 방법

## 🎯 최신 검증된 설치 방법 (권장)

### 1단계: 환경 생성 및 기본 설정
```bash
# 새로운 conda 환경 생성
conda create -n hybrik_186_prac python=3.9
conda activate hybrik_186_prac
```

### 2단계: PyTorch 및 CUDA 설치
```bash
# PyTorch 1.13.0 + CUDA 11.6 설치 (conda 방식)
conda install pytorch=1.13.0 torchvision pytorch-cuda=11.6 -c pytorch -c nvidia
```

### 3단계: PyTorch3D 의존성 설치
```bash
# PyTorch3D 필수 의존성
conda install -c fvcore -c iopath -c conda-forge fvcore iopath
conda install -c bottler nvidiacub
```

### 4단계: PyTorch3D 설치
```bash
# Anaconda Cloud에서 PyTorch3D 설치
conda install pytorch3d -c pytorch3d
```

### 5단계: 기타 의존성 설치
```bash
# OpenCV 설치
pip install opencv-python

# HybrIK 설치 (개발 모드)
pip install -e .

# NumPy 버전 호환성 (chumpy 호환을 위해)
pip install "numpy<1.24"

# 최종 개발 모드 설치
python setup.py develop
```

### 6단계: 실행 테스트
```bash
# 비디오 데모 실행
python scripts/demo_video.py --video-name examples/taiji.mp4 --out-dir results --save-img

# 2D,3D 키포인트 & SMPL 파라미터 추출
python scripts/demo_video_x.py --video-name examples/taiji.mp4 --out-dir result --save-img --save-pt
```
---
## 📝 사용법

### 비디오 처리
```bash
# 기본 실행
python scripts/demo_video.py --video-name examples/비디오이름.mp4 --out-dir 결과폴더 --save-img

# 예시
python scripts/demo_video.py --video-name examples/taiji.mp4 --out-dir results --save-img
```

### 이미지 처리
```bash
# 이미지 처리
python scripts/demo_image.py --image-name examples/이미지이름.jpg --out-dir 결과폴더
```

---

## 📋 검증된 의존성 버전 조합

### 핵심 환경
- **Python**: 3.9
- **PyTorch**: 1.13.0
- **CUDA**: 11.6
- **PyTorch3D**: 최신 버전 (conda)

### 주요 라이브러리
```
PyTorch: 1.13.0
torchvision: 1.13.0
PyTorch3D: conda 최신 버전
NumPy: <1.24 (chumpy 호환)
OpenCV: 최신 버전
CUDA: 11.6
```

---

## 🔧 문제 해결

### 일반적인 문제들

1. **CUDA 버전 불일치**
   ```bash
   # 현재 CUDA 버전 확인
   nvidia-smi
   
   # PyTorch CUDA 버전 확인
   python -c "import torch; print(torch.version.cuda)"
   ```

2. **NumPy 버전 충돌**
   ```bash
   # chumpy 호환을 위해 NumPy 다운그레이드
   pip install "numpy<1.24"
   ```

3. **PyTorch3D import 오류**
   ```bash
   # conda로 재설치
   conda install pytorch3d -c pytorch3d
   ```

### 설치 검증
```bash
# PyTorch GPU 확인
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# PyTorch3D 확인
python -c "import pytorch3d; print('PyTorch3D import 성공')"

# HybrIK 확인
python -c "import hybrik; print('HybrIK import 성공')"
```

---

## ⚠️ 중요 사항

1. **PyTorch3D는 반드시 설치되어야 함** - 이 설치 없이 문제를 해결하려고 하지 마세요
2. **CUDA 버전 일치** - PyTorch와 시스템 CUDA 버전이 호환되어야 함
3. **NumPy 버전 제한** - chumpy 호환을 위해 NumPy < 1.24 사용
4. **GPU 사용 필수** - CPU 모드는 지원하지 않음

---

## 🔗 참고 자료
- [HybrIK GitHub 저장소](https://github.com/jeffffffli/HybrIK)
- [PyTorch3D GitHub 저장소](https://github.com/facebookresearch/pytorch3d)
- [PyTorch 공식 설치 가이드](https://pytorch.org/get-started/locally/)

**이 방법은 2024년에 검증된 가장 안정적인 설치 방법입니다.**