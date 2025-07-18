"""Image demo script."""
import argparse
import os

import cv2
import numpy as np
import torch
from easydict import EasyDict as edict
from hybrik.models import builder
from hybrik.utils.config import update_config
from hybrik.utils.presets import SimpleTransform3DSMPLX
from hybrik.utils.render_pytorch3d import render_mesh
from hybrik.utils.vis import get_max_iou_box, get_one_box, vis_2d
from torchvision import transforms as T
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from tqdm import tqdm


det_transform = T.Compose([T.ToTensor()])

halpe_wrist_ids = [94, 115]
halpe_left_hand_ids = [
    5, 6, 7,
    9, 10, 11,
    17, 18, 19,
    13, 14, 15,
    1, 2, 3,
]
halpe_right_hand_ids = [
    5, 6, 7,
    9, 10, 11,
    17, 18, 19,
    13, 14, 15,
    1, 2, 3,
]

halpe_lhand_leaves = [
    8, 12, 20, 16, 4
]
halpe_rhand_leaves = [
    8, 12, 20, 16, 4
]


halpe_hand_ids = [i + 94 for i in halpe_left_hand_ids] + [i + 115 for i in halpe_right_hand_ids]
halpe_hand_leaves_ids = [i + 94 for i in halpe_lhand_leaves] + [i + 115 for i in halpe_rhand_leaves]


def xyxy2xywh(bbox):
    x1, y1, x2, y2 = bbox

    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    w = x2 - x1
    h = y2 - y1
    return [cx, cy, w, h]


def get_video_info(in_file):
    stream = cv2.VideoCapture(in_file)
    assert stream.isOpened(), 'Cannot capture source'
    # self.path = input_source
    datalen = int(stream.get(cv2.CAP_PROP_FRAME_COUNT))
    fourcc = int(stream.get(cv2.CAP_PROP_FOURCC))
    fps = stream.get(cv2.CAP_PROP_FPS)
    frameSize = (int(stream.get(cv2.CAP_PROP_FRAME_WIDTH)),
                 int(stream.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    # bitrate = int(stream.get(cv2.CAP_PROP_BITRATE))
    videoinfo = {'fourcc': fourcc, 'fps': fps, 'frameSize': frameSize}
    stream.release()

    return stream, videoinfo, datalen


def recognize_video_ext(ext=''):
    if ext == 'mp4':
        return cv2.VideoWriter_fourcc(*'mp4v'), '.' + ext
    elif ext == 'avi':
        return cv2.VideoWriter_fourcc(*'XVID'), '.' + ext
    elif ext == 'mov':
        return cv2.VideoWriter_fourcc(*'XVID'), '.' + ext
    else:
        print("Unknow video format {}, will use .mp4 instead of it".format(ext))
        return cv2.VideoWriter_fourcc(*'mp4v'), '.mp4'


def integral_hm(hms):
    # hms: [B, K, H, W]
    B, K, H, W = hms.shape
    hms = hms.sigmoid()
    hms = hms.reshape(B, K, -1)
    hms = hms / hms.sum(dim=2, keepdim=True)
    hms = hms.reshape(B, K, H, W)

    hm_x = hms.sum((2,))
    hm_y = hms.sum((3,))

    w_x = torch.arange(hms.shape[3]).to(hms.device).float()
    w_y = torch.arange(hms.shape[2]).to(hms.device).float()

    hm_x = hm_x * w_x
    hm_y = hm_y * w_y

    coord_x = hm_x.sum(dim=2, keepdim=True)
    coord_y = hm_y.sum(dim=2, keepdim=True)

    coord_x = coord_x / float(hms.shape[3]) - 0.5
    coord_y = coord_y / float(hms.shape[2]) - 0.5

    coord_uv = torch.cat((coord_x, coord_y), dim=2)
    return coord_uv


parser = argparse.ArgumentParser(description='HybrIK Demo')

parser.add_argument('--gpu',
                    help='gpu',
                    default=0,
                    type=int)
# parser.add_argument('--img-path',
#                     help='image name',
#                     default='',
#                     type=str)
parser.add_argument('--video-name',
                    help='video name',
                    default='',
                    type=str)
parser.add_argument('--out-dir',
                    help='output folder',
                    default='',
                    type=str)
parser.add_argument('--save-pt', default=False, dest='save_pt',
                    help='save prediction', action='store_true')
parser.add_argument('--save-img', default=False, dest='save_img',
                    help='save prediction', action='store_true')
parser.add_argument('--save-npz', default=False, dest='save_npz',
                    help='save prediction in NPZ format for SmoothNet', action='store_true')


opt = parser.parse_args()


cfg_file = './configs/smplx/256x192_hrnet_rle_smplx_kid.yaml'
CKPT = './pretrained_models/hybrikx_rle_hrnet.pth'

cfg = update_config(cfg_file)

cfg['MODEL']['EXTRA']['USE_KID'] = cfg['DATASET'].get('USE_KID', False)
cfg['LOSS']['ELEMENTS']['USE_KID'] = cfg['DATASET'].get('USE_KID', False)


bbox_3d_shape = getattr(cfg.MODEL, 'BBOX_3D_SHAPE', (2000, 2000, 2000))
bbox_3d_shape = [item * 1e-3 for item in bbox_3d_shape]
dummpy_set = edict({
    'joint_pairs_17': None,
    'joint_pairs_24': None,
    'joint_pairs_29': None,
    'bbox_3d_shape': bbox_3d_shape
})

res_keys = [
    'pred_uvd',
    'pred_xyz_17',
    'pred_xyz_29',
    'pred_xyz_24_struct',
    'pred_scores',
    'pred_camera',
    'f',
    'pred_betas',
    'pred_theta_quat',
    'pred_theta_mat',
    'pred_phi',
    'pred_cam_root',
    'pred_lh_uvd',
    'pred_rh_uvd',
    'transl',
    'bbox',
    'height',
    'width',
    'img_path'
]
res_db = {k: [] for k in res_keys}

transformation = SimpleTransform3DSMPLX(
    dummpy_set, scale_factor=cfg.DATASET.SCALE_FACTOR,
    color_factor=cfg.DATASET.COLOR_FACTOR,
    occlusion=cfg.DATASET.OCCLUSION,
    input_size=cfg.MODEL.IMAGE_SIZE,
    output_size=cfg.MODEL.HEATMAP_SIZE,
    depth_dim=cfg.MODEL.EXTRA.DEPTH_DIM,
    bbox_3d_shape=bbox_3d_shape,
    rot=cfg.DATASET.ROT_FACTOR, sigma=cfg.MODEL.EXTRA.SIGMA,
    train=False, add_dpg=False,
    loss_type=cfg.LOSS['TYPE'])

det_model = fasterrcnn_resnet50_fpn(pretrained=True)

hybrik_model = builder.build_sppe(cfg.MODEL)

print(f'Loading model from {CKPT}...')
save_dict = torch.load(CKPT, map_location='cpu')
if type(save_dict) == dict:
    model_dict = save_dict['model']
    hybrik_model.load_state_dict(model_dict)
else:
    hybrik_model.load_state_dict(save_dict)

det_model.cuda(opt.gpu)
hybrik_model.cuda(opt.gpu)
det_model.eval()
hybrik_model.eval()

print('### Extract Image...')
video_basename = os.path.basename(opt.video_name).split('.')[0]

if not os.path.exists(opt.out_dir):
    os.makedirs(opt.out_dir)
if not os.path.exists(os.path.join(opt.out_dir, 'raw_images')):
    os.makedirs(os.path.join(opt.out_dir, 'raw_images'))
if not os.path.exists(os.path.join(opt.out_dir, 'res_images')) and opt.save_img:
    os.makedirs(os.path.join(opt.out_dir, 'res_images'))
if not os.path.exists(os.path.join(opt.out_dir, 'res_2d_images')) and opt.save_img:
    os.makedirs(os.path.join(opt.out_dir, 'res_2d_images'))

_, info, _ = get_video_info(opt.video_name)
video_basename = os.path.basename(opt.video_name).split('.')[0]

savepath = f'./{opt.out_dir}/res_{video_basename}.mp4'
savepath2d = f'./{opt.out_dir}/res_2d_{video_basename}.mp4'
info['savepath'] = savepath
info['savepath2d'] = savepath2d

write_stream = cv2.VideoWriter(
    *[info[k] for k in ['savepath', 'fourcc', 'fps', 'frameSize']])
write2d_stream = cv2.VideoWriter(
    *[info[k] for k in ['savepath2d', 'fourcc', 'fps', 'frameSize']])
if not write_stream.isOpened():
    print("Try to use other video encoders...")
    ext = info['savepath'].split('.')[-1]
    fourcc, _ext = recognize_video_ext(ext)
    info['fourcc'] = fourcc
    info['savepath'] = info['savepath'][:-4] + _ext
    info['savepath2d'] = info['savepath2d'][:-4] + _ext
    write_stream = cv2.VideoWriter(
        *[info[k] for k in ['savepath', 'fourcc', 'fps', 'frameSize']])
    write2d_stream = cv2.VideoWriter(
        *[info[k] for k in ['savepath2d', 'fourcc', 'fps', 'frameSize']])

assert write_stream.isOpened(), 'Cannot open video for writing'
assert write2d_stream.isOpened(), 'Cannot open video for writing'

os.system(f'ffmpeg -i {opt.video_name} {opt.out_dir}/raw_images/{video_basename}-%06d.png')


files = os.listdir(f'{opt.out_dir}/raw_images')
files.sort()

img_path_list = []

for file in tqdm(files):
    if not os.path.isdir(file) and file[-4:] in ['.jpg', '.png']:

        img_path = os.path.join(opt.out_dir, 'raw_images', file)
        img_path_list.append(img_path)

prev_box = None
renderer = None
smplx_faces = torch.from_numpy(hybrik_model.smplx_layer.faces.astype(np.int32))

print('### Run Model...')
idx = 0
for img_path in tqdm(img_path_list):
    dirname = os.path.dirname(img_path)
    basename = os.path.basename(img_path)

    with torch.no_grad():
        # Run Detection
        input_image = cv2.cvtColor(cv2.imread(img_path), cv2.COLOR_BGR2RGB)
        det_input = det_transform(input_image).to(opt.gpu)
        det_output = det_model([det_input])[0]

        if prev_box is None:
            tight_bbox = get_one_box(det_output)  # xyxy
            if tight_bbox is None:
                continue
        else:
            tight_bbox = get_one_box(det_output)  # xyxy
            # tight_bbox = get_max_iou_box(det_output, prev_box)  # xyxy

        if tight_bbox is None:
            tight_bbox = prev_box

        prev_box = tight_bbox

        # Run HybrIK
        # bbox: [x1, y1, x2, y2]
        pose_input, bbox, img_center = transformation.test_transform(
            input_image.copy(), tight_bbox)
        pose_input = pose_input.to(opt.gpu)[None, :, :, :]

        '''
        pose_input_192 = pose_input[:, :, :, 32:-32].clone()

        # pose_input_192, bbox192 = al_transformation.test_transform(
        #     input_image.copy(), tight_bbox)
        # pose_input_192 = pose_input_192.to(opt.gpu)[None, :, :, :]
        pose_input_192[:, 0] = pose_input_192[:, 0] * 0.225
        pose_input_192[:, 1] = pose_input_192[:, 1] * 0.224
        pose_input_192[:, 2] = pose_input_192[:, 2] * 0.229
        al_output = alphapose_model(pose_input_192)
        al_uv_jts = integral_hm(al_output).squeeze(0)
        # hand_uv_jts = al_uv_jts[halpe_hand_ids, :]
        al_uv_jts[:, 0] = al_uv_jts[:, 0] * 192 / 256
        wrist_uv_jts = al_uv_jts[halpe_wrist_ids, :]
        hand_uv_jts = al_uv_jts[halpe_hand_ids, :]
        hand_leaf_uv_jts = al_uv_jts[halpe_hand_leaves_ids, :]
        '''
        # vis 2d
        bbox_xywh = xyxy2xywh(bbox)
        '''
        al_fb_pts = al_uv_jts.clone() * bbox_xywh[2]
        al_fb_pts[:, 0] = al_fb_pts[:, 0] + bbox_xywh[0]
        al_fb_pts[:, 1] = al_fb_pts[:, 1] + bbox_xywh[1]
        '''

        pose_output = hybrik_model(
            pose_input, flip_test=True,
            bboxes=torch.from_numpy(np.array(bbox)).to(pose_input.device).unsqueeze(0).float(),
            img_center=torch.from_numpy(img_center).to(pose_input.device).unsqueeze(0).float(),
            # al_hands=hand_uv_jts.to(pose_input.device).unsqueeze(0).float(),
            # al_hands_leaf=hand_leaf_uv_jts.to(pose_input.device).unsqueeze(0).float(),
        )

        uv_jts = pose_output.pred_uvd_jts.reshape(-1, 3)[:, :2]
        # uv_jts[25:55, :2] = hand_uv_jts
        # uv_jts[-10:, :2] = hand_leaf_uv_jts
        transl = pose_output.transl.detach()

        # Visualization
        image = input_image.copy()
        focal = 1000.0
        bbox_xywh = xyxy2xywh(bbox)

        focal = focal / 256 * bbox_xywh[2]

        vertices = pose_output.pred_vertices.detach()

        verts_batch = vertices
        transl_batch = transl

        color_batch = render_mesh(
            vertices=verts_batch, faces=smplx_faces,
            translation=transl_batch,
            focal_length=focal, height=image.shape[0], width=image.shape[1])

        valid_mask_batch = (color_batch[:, :, :, [-1]] > 0)
        image_vis_batch = color_batch[:, :, :, :3] * valid_mask_batch
        image_vis_batch = (image_vis_batch * 255).cpu().numpy()

        color = image_vis_batch[0]
        valid_mask = valid_mask_batch[0].cpu().numpy()
        input_img = image
        alpha = 0.9
        image_vis = alpha * color[:, :, :3] * valid_mask + (
            1 - alpha) * input_img * valid_mask + (1 - valid_mask) * input_img

        image_vis = image_vis.astype(np.uint8)
        image_vis = cv2.cvtColor(image_vis, cv2.COLOR_RGB2BGR)

        if opt.save_img:
            idx += 1
            res_path = os.path.join(opt.out_dir, 'res_images', f'image-{idx:06d}.jpg')
            cv2.imwrite(res_path, image_vis)
        write_stream.write(image_vis)
        
        # vis 2d
        pts = uv_jts * bbox_xywh[2]
        pts[:, 0] = pts[:, 0] + bbox_xywh[0]
        pts[:, 1] = pts[:, 1] + bbox_xywh[1]
        image = input_image.copy()
        bbox_img = vis_2d(image, tight_bbox, pts)
        # bbox_img = vis_2d(image, tight_bbox, al_fb_pts)
        bbox_img = cv2.cvtColor(bbox_img, cv2.COLOR_RGB2BGR)
        write2d_stream.write(bbox_img)

        if opt.save_img:
            res_path = os.path.join(
                opt.out_dir, 'res_2d_images', f'image-{idx:06d}.jpg')
            cv2.imwrite(res_path, bbox_img)

        if opt.save_pt:
            assert pose_input.shape[0] == 1, 'Only support single batch inference for now'

            # Debug: Print available attributes (force on first iteration)
            if len(res_db['pred_xyz_17']) == 0:
                print("Available pose_output attributes:")
                for attr in dir(pose_output):
                    if not attr.startswith('_'):
                        print(f"  {attr}")
                print(f"pose_output type: {type(pose_output)}")
                print(f"pose_output keys (if dict): {pose_output.keys() if hasattr(pose_output, 'keys') else 'Not a dict'}")
                print(f"pose_output items (if dict): {list(pose_output.items())[:5] if hasattr(pose_output, 'items') else 'Not a dict'}")
                print("="*50)
            
            # Extract 2D keypoints (UVD coordinates)
            pred_uvd_jts = pose_output.pred_uvd_jts.reshape(-1, 3).cpu().data.numpy()
            
            # Extract 3D keypoints using available attributes
            if hasattr(pose_output, 'pred_xyz_hybrik'):
                pred_xyz_jts_17 = pose_output.pred_xyz_hybrik.reshape(-1, 3).cpu().data.numpy()
            else:
                pred_xyz_jts_17 = np.zeros((17, 3))
                
            if hasattr(pose_output, 'pred_xyz_hybrik_struct'):
                pred_xyz_jts_24_struct = pose_output.pred_xyz_hybrik_struct.reshape(-1, 3).cpu().data.numpy()
            else:
                pred_xyz_jts_24_struct = np.zeros((24, 3))
                
            if hasattr(pose_output, 'pred_xyz_full'):
                pred_xyz_jts_29 = pose_output.pred_xyz_full.reshape(-1, 3).cpu().data.numpy()
            else:
                pred_xyz_jts_29 = np.zeros((29, 3))
                
            # Extract scores
            if hasattr(pose_output, 'scores'):
                pred_scores = pose_output.scores.cpu().data.numpy()
            elif hasattr(pose_output, 'maxvals'):
                pred_scores = pose_output.maxvals.cpu().data[:, :29].reshape(29).numpy()
            else:
                pred_scores = np.ones(29)
                
            # Extract camera parameters
            if hasattr(pose_output, 'pred_camera'):
                pred_camera = pose_output.pred_camera.squeeze(dim=0).cpu().data.numpy()
            else:
                pred_camera = np.array([1.0, 0.0, 0.0])
                
            # Extract SMPL shape parameters
            if hasattr(pose_output, 'pred_beta'):
                pred_betas = pose_output.pred_beta.squeeze(dim=0).cpu().data.numpy()
            elif hasattr(pose_output, 'pred_shape_full'):
                pred_betas = pose_output.pred_shape_full.squeeze(dim=0).cpu().data.numpy()[:10]  # First 10 shape params
            else:
                pred_betas = np.zeros(10)
                
            # Extract SMPL pose parameters (quaternion format)
            if hasattr(pose_output, 'pred_theta_quat'):
                pred_theta_quat = pose_output.pred_theta_quat.squeeze(dim=0).cpu().data.numpy()
            else:
                pred_theta_quat = np.zeros((24, 4))  # 24 joints, 4 quaternion values
                
            # Extract SMPL pose parameters (matrix format)
            if hasattr(pose_output, 'pred_theta_mat'):
                pred_theta_mat = pose_output.pred_theta_mat.squeeze(dim=0).cpu().data.numpy()
            else:
                pred_theta_mat = np.zeros((24, 3, 3))  # 24 joints, 3x3 rotation matrices
                
            # Extract additional parameters
            if hasattr(pose_output, 'pred_phi'):
                pred_phi = pose_output.pred_phi.squeeze(dim=0).cpu().data.numpy()
            else:
                pred_phi = np.zeros(3)
                
            if hasattr(pose_output, 'cam_root'):
                pred_cam_root = pose_output.cam_root.squeeze(dim=0).cpu().numpy()
            else:
                pred_cam_root = np.zeros(3)
                
            # Extract hand keypoints if available
            if hasattr(pose_output, 'pred_lh_uvd'):
                pred_lh_uvd = pose_output.pred_lh_uvd.squeeze(dim=0).cpu().data.numpy()
            else:
                pred_lh_uvd = np.zeros((21, 3))  # 21 hand keypoints
                
            if hasattr(pose_output, 'pred_rh_uvd'):
                pred_rh_uvd = pose_output.pred_rh_uvd.squeeze(dim=0).cpu().data.numpy()
            else:
                pred_rh_uvd = np.zeros((21, 3))  # 21 hand keypoints
            img_size = np.array((input_image.shape[0], input_image.shape[1]))

            res_db['pred_xyz_17'].append(pred_xyz_jts_17)
            res_db['pred_uvd'].append(pred_uvd_jts)
            res_db['pred_xyz_29'].append(pred_xyz_jts_29)
            res_db['pred_xyz_24_struct'].append(pred_xyz_jts_24_struct)
            res_db['pred_scores'].append(pred_scores)
            res_db['pred_camera'].append(pred_camera)
            res_db['f'].append(1000.0)
            res_db['pred_betas'].append(pred_betas)
            res_db['pred_theta_quat'].append(pred_theta_quat)
            res_db['pred_theta_mat'].append(pred_theta_mat)
            res_db['pred_phi'].append(pred_phi)
            res_db['pred_cam_root'].append(pred_cam_root)
            res_db['pred_lh_uvd'].append(pred_lh_uvd)
            res_db['pred_rh_uvd'].append(pred_rh_uvd)
            res_db['transl'].append(transl[0].cpu().data.numpy())
            res_db['bbox'].append(np.array(bbox))
            res_db['height'].append(img_size[0])
            res_db['width'].append(img_size[1])
            res_db['img_path'].append(img_path)

write_stream.release()
write2d_stream.release()

# Save keypoints and SMPL parameters to JSON and pickle files
if opt.save_pt and len(res_db['pred_xyz_17']) > 0:
    import json
    import pickle
    
    # Convert numpy arrays to lists for JSON serialization
    def convert_to_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_to_serializable(value) for key, value in obj.items()}
        else:
            return obj
    
    # Prepare data for JSON
    json_data = {}
    for key, value_list in res_db.items():
        if len(value_list) > 0:
            json_data[key] = convert_to_serializable(value_list)
    
    # Add metadata
    metadata = {
        'video_name': opt.video_name,
        'total_frames': len(json_data.get('pred_xyz_17', [])),
        'model_config': cfg_file,
        'model_checkpoint': CKPT
    }
    json_data['metadata'] = metadata
    
    # Save to JSON file
    json_path = os.path.join(opt.out_dir, f'{video_basename}_keypoints.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # Save to pickle file (preserves numpy arrays and original data types)
    pickle_data = res_db.copy()
    pickle_data['metadata'] = metadata
    
    pickle_path = os.path.join(opt.out_dir, f'{video_basename}_keypoints.pkl')
    with open(pickle_path, 'wb') as f:
        pickle.dump(pickle_data, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    print(f'Saved keypoints and SMPL parameters to:')
    print(f'  JSON: {json_path}')
    print(f'  Pickle: {pickle_path}')
    print(f'Total frames processed: {len(json_data.get("pred_xyz_17", []))}')
    
    # Print file sizes for comparison
    json_size = os.path.getsize(json_path) / (1024 * 1024)  # MB
    pickle_size = os.path.getsize(pickle_path) / (1024 * 1024)  # MB
    print(f'File sizes: JSON={json_size:.1f}MB, Pickle={pickle_size:.1f}MB')

# Save keypoints in NPZ format for SmoothNet (dance_hybrik_3D_test.npz와 동일한 구조)
if opt.save_npz and len(res_db['pred_xyz_17']) > 0:
    print(f'\nSaving NPZ files for SmoothNet...')
    
    # Get video name for imgname (dance_hybrik_3D_test.npz와 동일한 형식)
    video_name = opt.video_name  # 전체 경로 사용 (예: examples/ohyeah.mp4)
    total_frames = len(res_db['pred_xyz_17'])
    
    # Create imgname array for SmoothNet format (dance_hybrik_3D_test.npz와 동일)
    imgname = [f"{video_name}/frame_{i:06d}" for i in range(total_frames)]
    
    # Convert keypoints to numpy arrays
    keypoints_3d_17 = np.array(res_db['pred_xyz_17'])  # (frames, 17, 3)
    keypoints_3d_24 = np.array(res_db['pred_xyz_24_struct'])  # (frames, 24, 3)
    keypoints_3d_29 = np.array(res_db['pred_xyz_29'])  # (frames, 29, 3)
    
    # Extract SMPL parameters
    pose_params = np.array(res_db['pred_theta_quat'])  # (frames, 24, 4)
    shape_params = np.array(res_db['pred_betas'])  # (frames, 10)
    
    # Convert pose from quaternion to rotation matrix format (simplified)
    # For SmoothNet, we need (frames, 72) pose parameters
    if len(pose_params.shape) == 3:  # (frames, 24, 4) quaternion format
        pose_flat = pose_params[:, :, :3].reshape(total_frames, -1)  # Take first 3 values from quaternion
    elif len(pose_params.shape) == 2:  # (frames, 96) already flattened
        pose_flat = pose_params[:, :72]  # Take first 72 values
    else:
        pose_flat = np.zeros((total_frames, 72))
    
    # Save 17 keypoints NPZ file
    if keypoints_3d_17.shape[1] == 17:
        keypoints_17_flat = keypoints_3d_17.reshape(total_frames, -1)  # (frames, 51)
        npz_data_17 = {
            'imgname': np.array(imgname),
            'keypoints_3d': keypoints_17_flat
        }
        npz_path_17 = os.path.join(opt.out_dir, f'{video_basename}_17_3D_test.npz')
        np.savez(npz_path_17, **npz_data_17)
        print(f'  17 keypoints NPZ: {npz_path_17} (shape: {keypoints_17_flat.shape})')
    
    # Save 24 keypoints NPZ file
    if keypoints_3d_24.shape[1] == 24:
        keypoints_24_flat = keypoints_3d_24.reshape(total_frames, -1)  # (frames, 72)
        npz_data_24 = {
            'imgname': np.array(imgname),
            'keypoints_3d': keypoints_24_flat
        }
        npz_path_24 = os.path.join(opt.out_dir, f'{video_basename}_24_3D_test.npz')
        np.savez(npz_path_24, **npz_data_24)
        print(f'  24 keypoints NPZ: {npz_path_24} (shape: {keypoints_24_flat.shape})')
    
    # Save 29 keypoints NPZ file
    if keypoints_3d_29.shape[1] == 29:
        keypoints_29_flat = keypoints_3d_29.reshape(total_frames, -1)  # (frames, 87)
        npz_data_29 = {
            'imgname': np.array(imgname),
            'keypoints_3d': keypoints_29_flat
        }
        npz_path_29 = os.path.join(opt.out_dir, f'{video_basename}_29_3D_test.npz')
        np.savez(npz_path_29, **npz_data_29)
        print(f'  29 keypoints NPZ: {npz_path_29} (shape: {keypoints_29_flat.shape})')
    
    # Save SMPL parameters NPZ file
    if pose_flat.shape[1] == 72 and shape_params.shape[1] == 10:
        npz_data_smpl = {
            'imgname': np.array(imgname),
            'pose': pose_flat,
            'shape': shape_params
        }
        npz_path_smpl = os.path.join(opt.out_dir, f'{video_basename}_smpl_test.npz')
        np.savez(npz_path_smpl, **npz_data_smpl)
        print(f'  SMPL parameters NPZ: {npz_path_smpl} (pose: {pose_flat.shape}, shape: {shape_params.shape})')
    
    # Save 71 keypoints NPZ file (dance_hybrik_3D_test.npz와 동일한 구조)
    # pred_xyz_24_struct가 이미 71개 키포인트를 가지고 있음
    if keypoints_3d_24.shape[1] == 71:
        # 71개 키포인트를 그대로 사용
        keypoints_71_flat = keypoints_3d_24.reshape(total_frames, -1)  # (frames, 213)
        npz_data_71 = {
            'imgname': np.array(imgname),
            'keypoints_3d': keypoints_71_flat
        }
        npz_path_71 = os.path.join(opt.out_dir, f'{video_basename}_hybrik_3D_test.npz')
        np.savez(npz_path_71, **npz_data_71)
        print(f'  71 keypoints NPZ (dance_hybrik_3D_test.npz 형식): {npz_path_71} (shape: {keypoints_71_flat.shape})')
    else:
        print(f'  Warning: Expected 71 keypoints, but got {keypoints_3d_24.shape[1]} keypoints')
    
    print(f'NPZ files saved successfully!')
    print(f'Total frames: {total_frames}')
    print(f'Video name: {video_name}')
