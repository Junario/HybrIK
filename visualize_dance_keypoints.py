#!/usr/bin/env python3
"""
춤 키포인트 시각화 프로그램
3D 키포인트 데이터를 2D 및 3D 이미지로 변환하여 저장합니다.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import argparse
from tqdm import tqdm
from mpl_toolkits.mplot3d import Axes3D
from datetime import datetime
import subprocess
import os
import glob
from PIL import Image

class DanceKeypointVisualizer:
    def __init__(self, json_path, output_dir="output_frames"):
        """
        춤 키포인트 시각화 클래스
        
        Args:
            json_path: JSON 파일 경로
            output_dir: 출력 이미지 디렉토리
        """
        self.json_path = json_path
        
        # 현재 시간 기반 폴더명 생성 (월일24시간분)
        timestamp = datetime.now().strftime("%m%d%H%M")
        timestamped_dir = f"{output_dir}/{timestamp}"
        
        self.output_dir = Path(timestamped_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 관절 연결 정보 (인체 스켈레톤 구조)
        self.joint_connections = [
            # 척추 라인
            ('pelv', 'spi1'), ('spi1', 'spi2'), ('spi2', 'spi3'), ('spi3', 'neck'),
            # 머리
            ('neck', 'head'),
            # 왼쪽 다리
            ('pelv', 'lhip'), ('lhip', 'lkne'), ('lkne', 'lank'), ('lank', 'ltoe'),
            # 오른쪽 다리
            ('pelv', 'rhip'), ('rhip', 'rkne'), ('rkne', 'rank'), ('rank', 'rtoe'),
            # 어깨
            ('neck', 'lcla'), ('neck', 'rcla'),
            # 왼쪽 팔
            ('lcla', 'lsho'), ('lsho', 'lelb'), ('lelb', 'lwri'), ('lwri', 'lhan'),
            # 오른쪽 팔
            ('rcla', 'rsho'), ('rsho', 'relb'), ('relb', 'rwri'), ('rwri', 'rhan'),
        ]
        
        # 관절별 색상 정의
        self.joint_colors = {
            'pelv': '#FF6B6B', 'spi1': '#4ECDC4', 'spi2': '#45B7D1', 'spi3': '#96CEB4',
            'neck': '#FFEAA7', 'head': '#DDA0DD',
            'lhip': '#FF8A80', 'lkne': '#FF8A80', 'lank': '#FF8A80', 'ltoe': '#FF8A80',
            'rhip': '#81C784', 'rkne': '#81C784', 'rank': '#81C784', 'rtoe': '#81C784',
            'lcla': '#FFB74D', 'lsho': '#FFB74D', 'lelb': '#FFB74D', 'lwri': '#FFB74D', 'lhan': '#FFB74D',
            'rcla': '#9575CD', 'rsho': '#9575CD', 'relb': '#9575CD', 'rwri': '#9575CD', 'rhan': '#9575CD'
        }
        
        self.load_data()
    
    def load_data(self):
        """JSON 데이터 로드"""
        with open(self.json_path, 'r') as f:
            self.data = json.load(f)
        
        self.joint_names = self.data['joint_names']
        self.frames = self.data['frames']
        self.fps = self.data['fps']
        
        print(f"✅ 데이터 로드 완료: {len(self.frames)}개 프레임, {len(self.joint_names)}개 관절")
        print(f"📂 출력 폴더: {self.output_dir}")
    
    def extract_2d_coordinates(self, keypoints_3d):
        """
        3D 키포인트에서 X, Y 좌표만 추출 (2D 버전)
        """
        coords_2d = []
        for point in keypoints_3d:
            x, y, z = point
            coords_2d.append([x, y])
        return np.array(coords_2d)
    
    def project_3d_to_2d(self, keypoints_3d):
        """
        3D 키포인트를 2D로 투영 (3D 버전)
        간단한 원근 투영 사용
        """
        projected_2d = []
        
        for point in keypoints_3d:
            x, y, z = point
            # Z축을 기준으로 원근 투영 (Z가 클수록 작게)
            scale = 1000 / (z + 1000)  # 원근 효과
            proj_x = x * scale
            proj_y = y * scale
            projected_2d.append([proj_x, proj_y])
        
        return np.array(projected_2d)
    
    def normalize_coordinates(self, coords_2d):
        """
        2D 좌표를 이미지 크기에 맞게 정규화
        """
        if len(coords_2d) == 0:
            return coords_2d
        
        # 좌표 범위 계산
        min_x, max_x = coords_2d[:, 0].min(), coords_2d[:, 0].max()
        min_y, max_y = coords_2d[:, 1].min(), coords_2d[:, 1].max()
        
        # 범위가 0이면 기본값 사용
        if max_x - min_x == 0:
            max_x = min_x + 1
        if max_y - min_y == 0:
            max_y = min_y + 1
        
        # 정규화 (0~1 범위로)
        norm_x = (coords_2d[:, 0] - min_x) / (max_x - min_x)
        norm_y = (coords_2d[:, 1] - min_y) / (max_y - min_y)
        
        # 이미지 크기로 스케일링 (패딩 추가)
        img_width, img_height = 800, 600
        padding = 50
        
        scaled_x = norm_x * (img_width - 2 * padding) + padding
        scaled_y = norm_y * (img_height - 2 * padding) + padding
        
        return np.column_stack([scaled_x, scaled_y])
    
    def normalize_3d_coordinates(self, coords_3d):
        """
        3D 좌표를 3D 공간에 맞게 정규화
        """
        if len(coords_3d) == 0:
            return coords_3d
        
        # 각 축별로 좌표 범위 계산
        min_x, max_x = coords_3d[:, 0].min(), coords_3d[:, 0].max()
        min_y, max_y = coords_3d[:, 1].min(), coords_3d[:, 1].max()
        min_z, max_z = coords_3d[:, 2].min(), coords_3d[:, 2].max()
        
        # 범위가 0이면 기본값 사용
        if max_x - min_x == 0:
            max_x = min_x + 1
        if max_y - min_y == 0:
            max_y = min_y + 1
        if max_z - min_z == 0:
            max_z = min_z + 1
        
        # 정규화 (-1~1 범위로, 중심을 0으로)
        norm_x = 2 * (coords_3d[:, 0] - min_x) / (max_x - min_x) - 1
        norm_y = 2 * (coords_3d[:, 1] - min_y) / (max_y - min_y) - 1
        norm_z = 2 * (coords_3d[:, 2] - min_z) / (max_z - min_z) - 1
        
        # 스케일링 (적절한 크기로)
        scale = 100
        
        scaled_x = norm_x * scale
        scaled_y = norm_y * scale
        scaled_z = norm_z * scale
        
        return np.column_stack([scaled_x, scaled_y, scaled_z])
    
    def draw_skeleton_2d(self, ax, coords_2d, frame_info):
        """
        2D 스켈레톤 그리기 (평면적)
        """
        # 관절 점들 그리기
        for i, joint_name in enumerate(self.joint_names):
            x, y = coords_2d[i]
            color = self.joint_colors.get(joint_name, '#CCCCCC')
            ax.scatter(x, y, c=color, s=60, alpha=0.9, edgecolors='black', linewidth=1.5)
        
        # 관절 연결선 그리기
        for joint1, joint2 in self.joint_connections:
            if joint1 in self.joint_names and joint2 in self.joint_names:
                idx1 = self.joint_names.index(joint1)
                idx2 = self.joint_names.index(joint2)
                
                x1, y1 = coords_2d[idx1]
                x2, y2 = coords_2d[idx2]
                
                ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2.5, alpha=0.8)
    
    def draw_skeleton_3d(self, ax, coords_3d, frame_info):
        """
        진짜 3D 스켈레톤 그리기 (3D 축 사용)
        """
        # 관절 점들 그리기
        for i, joint_name in enumerate(self.joint_names):
            x, y, z = coords_3d[i]
            color = self.joint_colors.get(joint_name, '#CCCCCC')
            ax.scatter(x, y, z, c=color, s=60, alpha=0.8, edgecolors='black', linewidth=1)
        
        # 관절 연결선 그리기
        for joint1, joint2 in self.joint_connections:
            if joint1 in self.joint_names and joint2 in self.joint_names:
                idx1 = self.joint_names.index(joint1)
                idx2 = self.joint_names.index(joint2)
                
                x1, y1, z1 = coords_3d[idx1]
                x2, y2, z2 = coords_3d[idx2]
                
                ax.plot([x1, x2], [y1, y2], [z1, z2], 'k-', linewidth=2.5, alpha=0.8)
    
    def create_2d_frame_image(self, frame_data, frame_idx):
        """
        2D 프레임 이미지 생성 (X, Y 좌표만 사용)
        """
        fig, ax = plt.subplots(figsize=(12, 9))
        
        # 3D 키포인트에서 X, Y만 추출
        keypoints_3d = np.array(frame_data['keypoints_3d'])
        coords_2d = self.extract_2d_coordinates(keypoints_3d)
        
        # 좌표 정규화
        coords_2d = self.normalize_coordinates(coords_2d)
        
        # 2D 스켈레톤 그리기
        self.draw_skeleton_2d(ax, coords_2d, frame_data)
        
        # 축 설정
        ax.set_xlim(0, 800)
        ax.set_ylim(0, 600)
        ax.set_aspect('equal')
        ax.invert_yaxis()  # Y축 반전 (이미지 좌표계)
        
        # 그래프 꾸미기
        ax.set_title(f'2D Dance Keypoints - Frame {frame_data["frame_id"]} '
                    f'(Time: {frame_data["timestamp"]:.2f}s)', fontsize=14)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.grid(True, alpha=0.3)
        
        # 배경색 설정
        fig.patch.set_facecolor('white')
        ax.set_facecolor('#F0F8FF')  # 2D는 연한 파란색 배경
        
        return fig, ax
    
    def create_3d_frame_image(self, frame_data, frame_idx):
        """
        3D 프레임 이미지 생성 (실제 3D 축 사용, Z축이 위쪽)
        """
        fig = plt.figure(figsize=(12, 9))
        ax = fig.add_subplot(111, projection='3d')
        
        # 3D 좌표 직접 사용
        keypoints_3d = np.array(frame_data['keypoints_3d'])
        coords_3d = self.normalize_3d_coordinates(keypoints_3d)
        
        # 3D 스켈레톤 그리기
        self.draw_skeleton_3d(ax, coords_3d, frame_data)
        
        # 3D 축 설정
        ax.set_xlim(-150, 150)
        ax.set_ylim(-150, 150)
        ax.set_zlim(-150, 150)
        
        # 축 레이블 설정
        ax.set_xlabel('X', fontsize=12)
        ax.set_ylabel('Y', fontsize=12)
        ax.set_zlabel('Z (Height)', fontsize=12)
        
        # 쿼터뷰 각도 설정 (비스듬한 각도에서 보기)
        ax.view_init(elev=20, azim=45)  # 높이 20도, 방위각 45도
        
        # 그래프 꾸미기
        ax.set_title(f'3D Dance Keypoints - Frame {frame_data["frame_id"]} '
                    f'(Time: {frame_data["timestamp"]:.2f}s)', fontsize=14, pad=20)
        
        # 격자와 배경 설정
        ax.grid(True, alpha=0.3)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        
        # 패널 색상 설정 (투명하게)
        ax.xaxis.pane.set_edgecolor('gray')
        ax.yaxis.pane.set_edgecolor('gray')
        ax.zaxis.pane.set_edgecolor('gray')
        ax.xaxis.pane.set_alpha(0.1)
        ax.yaxis.pane.set_alpha(0.1)
        ax.zaxis.pane.set_alpha(0.1)
        
        # 배경색 설정
        fig.patch.set_facecolor('white')
        
        return fig, ax
    
    def save_frame(self, frame_data, frame_idx, mode='both', format='png'):
        """
        프레임을 이미지 파일로 저장
        
        Args:
            frame_data: 프레임 데이터
            frame_idx: 프레임 인덱스
            mode: 'both', '2d', '3d' 중 하나
            format: 이미지 포맷
        """
        saved_files = []
        
        if mode in ['both', '2d']:
            # 2D 버전 저장
            fig, ax = self.create_2d_frame_image(frame_data, frame_idx)
            filename = f"2d_frame_{frame_idx:04d}.{format}"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close(fig)
            saved_files.append(filepath)
        
        if mode in ['both', '3d']:
            # 3D 버전 저장
            fig, ax = self.create_3d_frame_image(frame_data, frame_idx)
            filename = f"3d_frame_{frame_idx:04d}.{format}"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close(fig)
            saved_files.append(filepath)
        
        return saved_files
    
    def visualize_all_frames(self, mode='both', format='png', start_frame=0, end_frame=None):
        """
        모든 프레임을 이미지로 변환
        
        Args:
            mode: 'both', '2d', '3d' 중 하나
            format: 이미지 포맷
            start_frame: 시작 프레임
            end_frame: 종료 프레임
        """
        if end_frame is None:
            end_frame = len(self.frames)
        
        mode_text = {'both': '2D + 3D', '2d': '2D', '3d': '3D'}[mode]
        print(f"🎬 {end_frame - start_frame}개 프레임을 {mode_text} {format} 형식으로 변환 중...")
        
        success_count = 0
        
        for i in tqdm(range(start_frame, end_frame), desc="프레임 변환"):
            try:
                frame_data = self.frames[i]
                saved_files = self.save_frame(frame_data, i, mode, format)
                success_count += len(saved_files)
                
                # 진행상황 출력 (100프레임마다)
                if (i + 1) % 100 == 0:
                    print(f"  ✅ {i + 1}개 프레임 완료")
                    
            except Exception as e:
                print(f"  ❌ 프레임 {i} 처리 실패: {e}")
        
        print(f"\n🎉 변환 완료!")
        print(f"   성공: {success_count}개 이미지 파일")
        print(f"   모드: {mode_text}")
        print(f"   출력 폴더: {self.output_dir}")
    
    def create_sample_frames(self, num_samples=10, mode='both', format='png'):
        """
        샘플 프레임 몇 개만 생성 (테스트용)
        
        Args:
            num_samples: 샘플 개수
            mode: 'both', '2d', '3d' 중 하나
            format: 이미지 포맷
        """
        total_frames = len(self.frames)
        step = max(1, total_frames // num_samples)
        
        sample_indices = range(0, total_frames, step)[:num_samples]
        
        mode_text = {'both': '2D + 3D', '2d': '2D', '3d': '3D'}[mode]
        print(f"📸 {num_samples}개 샘플 프레임을 {mode_text} 모드로 생성 중...")
        
        for i, frame_idx in enumerate(sample_indices):
            frame_data = self.frames[frame_idx]
            saved_files = self.save_frame(frame_data, frame_idx, mode, format)
            for filepath in saved_files:
                print(f"  ✅ 샘플 {i+1}: {filepath.name}")
        
        print(f"\n🎉 샘플 생성 완료! 출력 폴더: {self.output_dir}")
    
    def create_video_ffmpeg(self, mode='both', format='mp4', fps=30):
        """
        ffmpeg를 사용하여 생성된 이미지들을 영상으로 변환
        
        Args:
            mode: 'both', '2d', '3d' 중 하나
            format: 'mp4', 'avi' 등 영상 포맷
            fps: 초당 프레임 수
        """
        videos_created = []
        
        if mode in ['both', '2d']:
            # 2D 영상 생성
            video_path = self._create_video_ffmpeg_helper("2d_frame_*.png", f"dance_2d.{format}", fps)
            if video_path:
                videos_created.append(video_path)
        
        if mode in ['both', '3d']:
            # 3D 영상 생성
            video_path = self._create_video_ffmpeg_helper("3d_frame_*.png", f"dance_3d.{format}", fps)
            if video_path:
                videos_created.append(video_path)
        
        return videos_created
    
    def _create_video_ffmpeg_helper(self, pattern, output_name, fps):
        """ffmpeg 비디오 생성 헬퍼 함수 (파일 리스트 방식)"""
        # 이미지 파일 목록 가져오기
        image_files = sorted(glob.glob(str(self.output_dir / pattern)))
        
        if not image_files:
            print(f"❌ {pattern} 패턴의 이미지 파일이 없습니다.")
            return None
        
        # 임시 파일 리스트 생성
        file_list_path = str(self.output_dir / "temp_file_list.txt")
        with open(file_list_path, 'w') as f:
            for img_file in image_files:
                f.write(f"file '{os.path.basename(img_file)}'\n")
        
        output_path = str(self.output_dir / output_name)
        
        # 더 호환성 있는 ffmpeg 명령어
        cmd = [
            'ffmpeg', '-y',  # 덮어쓰기 허용
            '-f', 'concat',  # 파일 리스트 사용
            '-safe', '0',  # 안전 모드 해제
            '-i', file_list_path,  # 입력 파일 리스트
            '-vf', f'fps={fps}',  # 프레임 레이트 설정
            '-c:v', 'libx264',  # H.264 코덱
            '-preset', 'medium',  # 인코딩 속도/품질 균형
            '-crf', '23',  # 품질 (23은 일반적으로 좋은 품질)
            '-pix_fmt', 'yuv420p',  # 호환성 픽셀 포맷
            '-movflags', '+faststart',  # 웹 스트리밍 최적화
            output_path
        ]
        
        try:
            print(f"🎬 {len(image_files)}개 이미지로 {output_name} 생성 중...")
            
            # 작업 디렉토리를 이미지 폴더로 변경
            result = subprocess.run(cmd, cwd=str(self.output_dir), check=True, 
                                  capture_output=True, text=True)
            
            # 임시 파일 삭제
            os.remove(file_list_path)
            
            print(f"✅ ffmpeg 영상 생성 완료: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            print(f"❌ ffmpeg 영상 생성 실패: {e.stderr}")
            # 임시 파일 정리
            if os.path.exists(file_list_path):
                os.remove(file_list_path)
            return None
    
    def create_video_opencv(self, mode='both', format='mp4', fps=30):
        """
        OpenCV를 사용하여 생성된 이미지들을 영상으로 변환
        
        Args:
            mode: 'both', '2d', '3d' 중 하나
            format: 'mp4', 'avi' 등 영상 포맷
            fps: 초당 프레임 수
        """
        try:
            import cv2
        except ImportError:
            print("❌ OpenCV가 설치되어 있지 않습니다. 'pip install opencv-python'으로 설치해주세요.")
            return []
        
        videos_created = []
        
        if mode in ['both', '2d']:
            video_path = self._create_video_opencv_helper("2d_frame_*.png", f"dance_2d.{format}", fps)
            if video_path:
                videos_created.append(video_path)
        
        if mode in ['both', '3d']:
            video_path = self._create_video_opencv_helper("3d_frame_*.png", f"dance_3d.{format}", fps)
            if video_path:
                videos_created.append(video_path)
        
        return videos_created
    
    def _create_video_opencv_helper(self, pattern, output_name, fps):
        """OpenCV 비디오 생성 헬퍼 함수"""
        try:
            import cv2
        except ImportError:
            return None
        
        # 이미지 파일 목록 가져오기
        image_files = sorted(glob.glob(str(self.output_dir / pattern)))
        
        if not image_files:
            print(f"❌ {pattern} 패턴의 이미지 파일이 없습니다.")
            return None
        
        # 첫 번째 이미지로 크기 확인
        first_image = cv2.imread(image_files[0])
        if first_image is None:
            print(f"❌ 첫 번째 이미지를 읽을 수 없습니다: {image_files[0]}")
            return None
        
        height, width, layers = first_image.shape
        
        # 비디오 라이터 설정
        output_path = str(self.output_dir / output_name)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') if output_name.endswith('.mp4') else cv2.VideoWriter_fourcc(*'XVID')
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        print(f"🎬 {len(image_files)}개 이미지로 영상 생성 중...")
        
        for i, image_file in enumerate(tqdm(image_files, desc="영상 생성")):
            frame = cv2.imread(image_file)
            if frame is not None:
                video_writer.write(frame)
            
            if (i + 1) % 100 == 0:
                print(f"  ✅ {i + 1}개 프레임 처리 완료")
        
        video_writer.release()
        print(f"✅ OpenCV 영상 생성 완료: {output_path}")
        
        return output_path
    
    def _check_images_exist(self, pattern):
        """이미지 파일이 존재하는지 확인"""
        image_files = glob.glob(str(self.output_dir / pattern))
        return len(image_files) > 0
    
    def combine_2d_3d_images(self):
        """
        2D와 3D 이미지를 좌우로 합성하여 새로운 combined 이미지 생성
        """
        # 2D와 3D 이미지 파일 목록 가져오기
        image_2d_files = sorted(glob.glob(str(self.output_dir / "2d_frame_*.png")))
        image_3d_files = sorted(glob.glob(str(self.output_dir / "3d_frame_*.png")))
        
        if not image_2d_files or not image_3d_files:
            print("❌ 2D 또는 3D 이미지 파일이 없습니다.")
            return False
        
        if len(image_2d_files) != len(image_3d_files):
            print("❌ 2D와 3D 이미지 개수가 일치하지 않습니다.")
            return False
        
        print(f"🎨 {len(image_2d_files)}개의 2D+3D 합성 이미지 생성 중...")
        
        combined_count = 0
        
        for i, (img_2d_path, img_3d_path) in enumerate(tqdm(zip(image_2d_files, image_3d_files), 
                                                           desc="이미지 합성", 
                                                           total=len(image_2d_files))):
            try:
                # 2D와 3D 이미지 열기
                img_2d = Image.open(img_2d_path)
                img_3d = Image.open(img_3d_path)
                
                # 이미지 크기 맞추기 (높이 기준)
                height = min(img_2d.height, img_3d.height)
                
                # 비율 유지하면서 크기 조정
                img_2d_resized = img_2d.resize((int(img_2d.width * height / img_2d.height), height), 
                                              Image.Resampling.LANCZOS)
                img_3d_resized = img_3d.resize((int(img_3d.width * height / img_3d.height), height), 
                                              Image.Resampling.LANCZOS)
                
                # 합성된 이미지 크기 계산
                total_width = img_2d_resized.width + img_3d_resized.width
                
                # 새로운 합성 이미지 생성
                combined_img = Image.new('RGB', (total_width, height), (255, 255, 255))
                
                # 2D 이미지를 왼쪽에 붙이기
                combined_img.paste(img_2d_resized, (0, 0))
                
                # 3D 이미지를 오른쪽에 붙이기
                combined_img.paste(img_3d_resized, (img_2d_resized.width, 0))
                
                # 구분선 그리기 (선택사항)
                from PIL import ImageDraw
                draw = ImageDraw.Draw(combined_img)
                line_x = img_2d_resized.width
                draw.line([(line_x, 0), (line_x, height)], fill=(128, 128, 128), width=2)
                
                # 라벨 추가
                from PIL import ImageFont
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    font = ImageFont.load_default()
                
                draw.text((20, 20), "2D View", fill=(0, 0, 0), font=font)
                draw.text((img_2d_resized.width + 20, 20), "3D View", fill=(0, 0, 0), font=font)
                
                # 합성된 이미지 저장
                frame_num = int(os.path.basename(img_2d_path).split('_')[2].split('.')[0])
                combined_filename = f"combined_frame_{frame_num:04d}.png"
                combined_path = self.output_dir / combined_filename
                
                combined_img.save(combined_path, 'PNG')
                combined_count += 1
                
                # 메모리 정리
                img_2d.close()
                img_3d.close()
                combined_img.close()
                
            except Exception as e:
                print(f"❌ 프레임 {i} 합성 실패: {e}")
                continue
        
        print(f"✅ 합성 완료: {combined_count}개 combined 이미지 생성")
        return combined_count > 0
    
    def create_combined_video(self, format='mp4', fps=30):
        """
        합성된 이미지들을 영상으로 변환
        """
        # 합성된 이미지 파일 목록 가져오기
        combined_files = sorted(glob.glob(str(self.output_dir / "combined_frame_*.png")))
        
        if not combined_files:
            print("❌ 합성된 이미지 파일이 없습니다.")
            return None
        
        output_filename = f"dance_combined.{format}"
        
        # ffmpeg 명령어 (직접 프레임 시퀀스 사용 방식)
        cmd = [
            'ffmpeg', '-y',  # 덮어쓰기 허용
            '-framerate', str(fps),  # 입력 프레임 레이트
            '-i', 'combined_frame_%04d.png',  # 입력 패턴
            '-c:v', 'libx264',  # H.264 코덱
            '-preset', 'medium',  # 인코딩 속도/품질 균형
            '-crf', '23',  # 품질
            '-pix_fmt', 'yuv420p',  # 호환성 픽셀 포맷
            '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',  # 크기를 짝수로 조정
            '-movflags', '+faststart',  # 웹 스트리밍 최적화
            output_filename  # 출력 파일명만 (경로 없이)
        ]
        
        try:
            print(f"🎬 {len(combined_files)}개 합성 이미지로 Combined 영상 생성 중...")
            
            subprocess.run(cmd, cwd=str(self.output_dir), check=True, 
                          capture_output=True, text=True)
            
            output_path = str(self.output_dir / output_filename)
            print(f"✅ Combined 영상 생성 완료: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Combined 영상 생성 실패: {e.stderr}")
            return None


def main():
    parser = argparse.ArgumentParser(description='춤 키포인트 데이터 시각화')
    parser.add_argument('--json', default='data/dance_keypoints_final.json',
                       help='JSON 파일 경로')
    parser.add_argument('--output', default='output_frames',
                       help='출력 디렉토리')
    parser.add_argument('--format', choices=['png', 'jpg'], default='png',
                       help='이미지 포맷')
    parser.add_argument('--mode', choices=['both', '2d', '3d'], default='both',
                       help='시각화 모드: both(2D+3D), 2d(X,Y만), 3d(X,Y,Z 원근투영)')
    parser.add_argument('--sample', type=int, default=0,
                       help='샘플 프레임 개수 (0=모든 프레임)')
    parser.add_argument('--start', type=int, default=0,
                       help='시작 프레임 번호')
    parser.add_argument('--end', type=int, default=None,
                       help='종료 프레임 번호')
    parser.add_argument('--video', action='store_true',
                       help='이미지 생성 후 영상으로 변환')
    parser.add_argument('--video-fps', type=int, default=30,
                       help='영상 프레임 레이트 (기본값: 30)')
    parser.add_argument('--video-format', choices=['mp4', 'avi'], default='mp4',
                       help='영상 포맷 (기본값: mp4)')
    parser.add_argument('--video-method', choices=['ffmpeg', 'opencv'], default='ffmpeg',
                       help='영상 생성 방법 (기본값: ffmpeg)')
    parser.add_argument('--video-combined', action='store_true',
                       help='2D와 3D를 좌우로 합성한 영상 생성 (자동으로 both 모드 적용)')
    
    args = parser.parse_args()
    
    # Combined 영상 생성 시 자동으로 both 모드 적용
    if args.video_combined:
        args.mode = 'both'
        args.video = True
        print("🎨 Combined 영상 모드: 2D와 3D 이미지를 모두 생성하고 합성된 영상을 만듭니다.")
    
    # 시각화 실행
    visualizer = DanceKeypointVisualizer(args.json, args.output)
    
    if args.sample > 0:
        visualizer.create_sample_frames(args.sample, args.mode, args.format)
    else:
        visualizer.visualize_all_frames(args.mode, args.format, args.start, args.end)
    
    # 영상 생성 (옵션)
    if args.video:
        print(f"\n🎬 영상 생성 시작...")
        
        # Combined 영상 생성
        if args.video_combined:
            # 2D와 3D 이미지 합성
            if visualizer.combine_2d_3d_images():
                combined_video = visualizer.create_combined_video(args.video_format, args.video_fps)
                if combined_video:
                    print(f"\n🎉 Combined 영상 생성 완료!")
                    print(f"   📹 {combined_video}")
                else:
                    print(f"\n❌ Combined 영상 생성 실패")
            else:
                print(f"\n❌ 이미지 합성 실패")
        else:
            # 기존 방식의 개별 영상 생성
            if args.video_method == 'ffmpeg':
                videos = visualizer.create_video_ffmpeg(args.mode, args.video_format, args.video_fps)
            else:
                videos = visualizer.create_video_opencv(args.mode, args.video_format, args.video_fps)
            
            if videos:
                print(f"\n🎉 영상 생성 완료!")
                for video in videos:
                    print(f"   📹 {video}")
            else:
                print(f"\n❌ 영상 생성 실패")
    
    print(f"\n✨ 모든 작업 완료! 출력 폴더: {visualizer.output_dir}")


if __name__ == "__main__":
    main() 