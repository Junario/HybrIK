# HybrIK JSON 키포인트 출력 가이드

## 개요
HybrIK의 `demo_video.py` 스크립트에 JSON 출력 기능이 추가되었습니다. 이 기능을 사용하면 비디오에서 추출한 2D, 3D 키포인트를 JSON 형식으로 저장할 수 있습니다.

## 사용법

### 기본 명령어
```bash
python scripts/demo_video.py --video-name <비디오파일> --out-dir <출력폴더> --save-json
```

### 예시
```bash
# taiji.mp4 비디오에서 키포인트 추출
python scripts/demo_video.py --video-name examples/taiji.mp4 --out-dir res_taiji_json --save-json

# 이미지도 함께 저장하려면
python scripts/demo_video.py --video-name examples/taiji.mp4 --out-dir res_taiji_json --save-json --save-img

# pickle 파일도 함께 저장하려면
python scripts/demo_video.py --video-name examples/taiji.mp4 --out-dir res_taiji_json --save-json --save-pk
```

## 출력 파일 구조

### JSON 파일: `keypoints.json`

```json
{
  "video_info": {
    "video_name": "examples/taiji.mp4",
    "fps": 23.976023976023978,
    "frame_size": [1280, 720],
    "total_frames": 412
  },
  "frames": [
    {
      "frame_idx": 0,
      "img_path": "res_taiji_json/raw_images/taiji-000001.png",
      "bbox": [258.0, -25.7, 1059.8, 776.1],
      "keypoints_2d": {
        "uv_29": [[x1, y1], [x2, y2], ...],  // 29개 2D 키포인트
        "scores": [score1, score2, ...]       // 각 키포인트의 신뢰도 점수
      },
      "keypoints_3d": {
        "xyz_17": [[x1, y1, z1], [x2, y2, z2], ...],      // 17개 3D 키포인트
        "xyz_29": [[x1, y1, z1], [x2, y2, z2], ...],      // 29개 3D 키포인트
        "xyz_24_struct": [[x1, y1, z1], [x2, y2, z2], ...] // 24개 구조적 3D 키포인트
      },
      "smpl_params": {
        "betas": [...],    // SMPL 모양 파라미터
        "thetas": [...],   // SMPL 관절 회전 파라미터
        "phi": [...]       // SMPL 추가 파라미터
      },
      "camera_params": {
        "camera": [...],           // 카메라 파라미터
        "cam_root": [...],         // 카메라 루트 위치
        "transl": [...],           // 전역 변환
        "transl_camsys": [...]     // 카메라 좌표계 변환
      }
    }
  ]
}
```

## 키포인트 설명

### 2D 키포인트 (uv_29)
- 29개의 2D 키포인트 좌표
- 정규화된 좌표 (0~1 범위)
- `scores` 배열은 각 키포인트의 신뢰도 점수

### 3D 키포인트
- **xyz_17**: 17개 주요 관절의 3D 좌표
- **xyz_29**: 29개 키포인트의 3D 좌표
- **xyz_24_struct**: 24개 구조적 키포인트의 3D 좌표

### SMPL 파라미터
- **betas**: 몸체 모양 파라미터 (10개)
- **thetas**: 관절 회전 파라미터 (24개 관절 × 3축)
- **phi**: 추가 모델 파라미터

## JSON 파일 읽기 예시

```python
import json

# JSON 파일 로드
with open('res_taiji_json/keypoints.json', 'r') as f:
    data = json.load(f)

# 비디오 정보
print(f"비디오: {data['video_info']['video_name']}")
print(f"FPS: {data['video_info']['fps']}")
print(f"총 프레임: {data['video_info']['total_frames']}")

# 첫 번째 프레임의 2D 키포인트
first_frame = data['frames'][0]
keypoints_2d = first_frame['keypoints_2d']['uv_29']
scores = first_frame['keypoints_2d']['scores']

print(f"첫 번째 프레임의 2D 키포인트 개수: {len(keypoints_2d)}")
print(f"첫 번째 키포인트: {keypoints_2d[0]}, 신뢰도: {scores[0]}")

# 첫 번째 프레임의 3D 키포인트
keypoints_3d = first_frame['keypoints_3d']['xyz_17']
print(f"첫 번째 프레임의 3D 키포인트 개수: {len(keypoints_3d)}")
print(f"첫 번째 3D 키포인트: {keypoints_3d[0]}")
```

## 주의사항

1. **메모리 사용량**: 긴 비디오의 경우 JSON 파일이 매우 클 수 있습니다.
2. **처리 시간**: JSON 출력은 추가 처리 시간이 필요합니다.
3. **좌표계**: 2D 키포인트는 정규화된 좌표이며, 실제 픽셀 좌표로 변환하려면 bbox 정보를 사용해야 합니다.

## 기존 기능과의 호환성

- `--save-json` 옵션은 기존의 `--save-img`, `--save-pk` 옵션과 함께 사용할 수 있습니다.
- JSON 출력은 비디오 렌더링이나 이미지 저장에 영향을 주지 않습니다. 