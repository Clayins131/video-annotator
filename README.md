# 视频标注工具

这是一个使用 Python 和 Tkinter 构建的视频标注工具，采用 OpenCV 进行视频处理。该工具允许用户为视频帧添加自定义矩形标注，附加元数据，如击杀时刻、游戏类型和角色信息。

## 特性

- 打开并播放视频文件（支持 MP4、AVI、MOV 格式）。
- 在视频帧上进行矩形标注。
- 显示标注信息，如角色、游戏类型和击杀时刻。
- 保存和加载 JSON 格式的标注文件。
- 编辑和删除标注。

## 安装要求

- Python 3.x
- OpenCV (`opencv-python`)
- Pillow (`Pillow`)

## 安装依赖

要安装所需的依赖库，请运行：

```bash
pip install -r requirements.txt
