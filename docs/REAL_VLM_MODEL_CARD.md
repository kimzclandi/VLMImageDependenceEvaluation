# 真实 VLM 模型卡

本实验使用 HuggingFaceTB/SmolVLM-256M-Instruct，固定 revision `7e3e67edbbed1bf9888184d9df282b700a323964`。官方卡标注 Apache-2.0；模型用于公开免费本地推理，无 API、付费服务或训练。权重不随本仓库分发，下载保留上游许可。

来源：[官方模型卡](https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct/tree/7e3e67edbbed1bf9888184d9df282b700a323964)。这是约 256M 参数的图文生成模型；输出是文本，不是机器人动作。

本地实测配置为 Python 3.12、PyTorch 2.14.0、Transformers 4.57.6、CPU float32、eager attention、4 个计算线程。完整依赖见 `requirements-vlm-lock.txt`，实际权重 SHA-256、处理器文件摘要见 `reports/real_vlm/environment.json`。不启用 `trust_remote_code`，不执行模型仓库脚本。

输入接口严格限定 `VisualInput(image: bytes, question: str)`，不接受 scene、query、答案或样本字典。生成器及评分器可以访问结构化标签；模型适配器不能访问这些字段。此边界是应用接口隔离，不是操作系统级沙箱。图像先解码为 RGB，processor 产生 input_ids 与视觉张量，模型自回归生成最多 16 个 token，解码时移除输入 token。保存所有原始输出和实际延迟。

两种提示都使用自由贪心生成，不使用有限答案 trie 或 gold 候选评分。大小写、末尾句号和空白可以归一化，整段文本必须匹配合法答案域。`There are 2` 不被偷偷抽取为 `2`。错误、空输出和解析失败都计入分母。

限制：小模型、干净二维图形、英语模板、固定四物体、无遮挡；仅 12 个保留场景族。字母 ID 需要视觉识别，近横坐标空间题存在像素级边界。模型误答不能直接诊断为感知、推理或 OCR 根因。结果不外推到道路检测、真实具身操作、安全性、自动标注替代率或训练收益。
