# 当前实验运行说明 / Running the current experiment

## 已保存结果回放 / Saved-generation replay

使用[首页安装命令](../README.zh-CN.md#查看与运行)创建独立环境，然后运行：

```bash
python scripts/verify_grounding.py
streamlit run dashboard.py --server.address 127.0.0.1
```

默认显示「视觉贡献干预 v3」。这是从已有模型输出重算指标，不是新的推理。CI 还回放历史规则流程并检查软件契约；CI 通过不代表重新运行了神经模型。

The default viewer and verification command use the current saved image-intervention experiment. CI also checks the historical rule workflow; it does not rerun neural inference.

## 真实模型执行 / Actual model inference

需要独立 Python 3.12 环境与[冻结协议](GROUNDING_V3_PROTOCOL.md)对应的 SmolVLM 快照。依赖安装方式：

```bash
uv venv --python 3.12 .venv-vlm
uv pip install --python .venv-vlm/bin/python -r requirements-vlm-lock.txt
```

模型 revision 为 `7e3e67edbbed1bf9888184d9df282b700a323964`。协议中的 `/path/to/fixed/snapshot` 须替换为实际下载并核验的本地目录；程序核验每个模型文件和执行源文件。不得用浮动 latest 权重替换。

已发布生成不可覆盖；直接运行会核验并复用既有观测。确需从零执行时，在独立 checkout 中归档原结果目录，保留原协议，按协议执行 `python -m flywheel.grounding run --snapshot ...`。不要重新 freeze、删除失败或把缓存回放记作新模型运行。当前文档整理没有执行这一步。

Use the exact frozen snapshot and preserve reference generations in a separate checkout before a fresh run. Existing observations are verified and reused, not silently overwritten.

## 历史入口 / Historical workflows

- 第一轮 72 题提示比较：[复现说明](REAL_VLM_REPRODUCE.md)。历史脚本会重写结果，实际重推必须先建立独立 checkout；只看结果无需运行它。与当前 90 题图像干预分开。
- `flywheel demo`：读取 metadata 的规则原型；只用于历史流程复现，不加载 SmolVLM，不训练模型。
- Dashboard 可切换三条历史/当前实验记录，不能将它们的分数串成模型学习曲线。
