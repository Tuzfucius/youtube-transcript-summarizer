# tests/ 测试目录

本目录包含 Video Summarizer 的测试脚本。

## 运行测试

```bash
# 从项目根目录运行
python tests/test_stability.py
```

## 测试文件

| 文件 | 说明 |
|------|------|
| `test_stability.py` | 基础稳定性测试（无需 API Key），覆盖日志、计时器、重试、平台检测、Prompt 模板、工具定义 |
