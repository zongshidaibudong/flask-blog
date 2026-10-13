title: 用 Python 驱动 NX：二次开发入门
date: 2026-08-28
tags: NX, Python, 二次开发
summary: NX 自带 Python API（NXOpen），可以用脚本自动完成建模、装配和出图，让重复劳动交给程序。

## 为什么要给 NX 写脚本

大一做 CAD/NX 作业时发现：同样的垫圈、螺母、销轴，每个装配体都要画一遍。
手动重复创建标准件效率太低，而 NX 的 NXOpen API 恰好可以用 Python 自动化。

## 环境与第一个脚本

NX 安装后自带 Python 解释器，菜单里可以直接运行：

```python
import NXOpen

session = NXOpen.Session.GetSession()
work_part = session.Parts.Work

# 新建一个立方体块
block_feat, body = work_part.Features.CreateBlockBuilder(None)
```

## 实际能自动化的事情

1. **参数化标准件**：输入规格 M10 / M12，自动生成对应尺寸的螺母
2. **批量出图**：遍历装配体所有零件，自动导出工程图 PDF
3. **装配检查**：脚本遍历约束，报告缺配对的零件

## 学习路线建议

- 先读 `NXOpen` 的帮助文档（NX 安装目录里有 CHM）
- 用「录制」功能把手动操作转成代码，再改参数
- 从简单特征（块、圆柱、孔）开始，逐步过渡到草图和约束

把课程作业当成 API 练习场，建模速度和理解都会上一个台阶。
