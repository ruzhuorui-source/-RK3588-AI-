import cv2
import time
from rknnpool.rknnpool_ld import rknnPoolExecutor
from func.func_yolov8_optimize import myFunc

# ---------- 配置 ----------
modelPath = "./box.rknn"   # 您的 yolov8.rknn
video_source = "/dev/video11"         # 或视频文件路径，如 "test.mp4"
TPEs = 8                              # 根据 CPU 核心数调整
out_win = "YOLOv8 Detection"
save_video = True                     # 若无法显示，是否保存视频
output_video_path = "/home/elf/Videos/output.mp4"
# -------------------------







# 初始化 RKNN 池
pool = rknnPoolExecutor(
    rknnModel=modelPath,
    TPEs=TPEs,
    func=myFunc
)

cap = cv2.VideoCapture(video_source)
if not cap.isOpened():
    print("无法打开视频源")
    pool.release()
    exit(-1)

# 获取视频属性（用于保存视频）
fps = cap.get(cv2.CAP_PROP_FPS) or 30
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
if width == 0: width = 640
if height == 0: height = 640

ret,frame=cap.read()
if ret:
    h,w=frame.shape[:2]
    print(f"fenbianlu:{w}x{h}")

# 尝试创建显示窗口（若 OpenCV 有 GUI 支持）
gui_supported = True
try:
    cv2.namedWindow(out_win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(out_win, 640, 640)
except cv2.error:
    gui_supported = False
    print("OpenCV 无 GUI 支持，将保存视频或图片帧")

# 准备 VideoWriter（备份方案）
writer = None
if save_video and not gui_supported:
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    print(f"结果将保存到 {output_video_path}")

# 预填充队列（确保流水线不空）
for _ in range(TPEs + 1):
    ret, frame = cap.read()
    if not ret:
        break
    pool.put(frame)

frames = 0
loop_time = time.time()
init_time = time.time()
start_time = time.time()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 送入新帧
    pool.put(frame)

    # 获取已处理好的帧（阻塞直到有结果）
    result_frame, flag = pool.get()
    if not flag:
        break

    frames += 1

    # ---- 显示或保存 ----
    if gui_supported:
        # 调整大小以适应屏幕（可省略）
        display = cv2.resize(result_frame, (1280, 800))
        cv2.imshow(out_win, display)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:
        # 无GUI：直接写入视频文件
        if writer:
            writer.write(result_frame)
        passtime = time.time() - start_time

        if passtime >= 10:
            break
          
        # 或者每隔N帧保存一张图片（可选）
        # if frames % 30 == 0:
        #     cv2.imwrite(f"frame_{frames}.jpg", result_frame)

    # 打印帧率
    if frames % 30 == 0:
        print(f"30帧平均帧率: {30/(time.time()-loop_time):.2f} FPS")
        loop_time = time.time()
    
    

print(f"总平均帧率: {frames/(time.time()-init_time):.2f} FPS")

# 释放资源
cap.release()
if writer:
    writer.release()
cv2.destroyAllWindows()
pool.release()
