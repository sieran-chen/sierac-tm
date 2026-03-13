# 3D 模型目录

将设备 **glTF/GLB** 模型文件放入此目录并命名为 **001.glb**，即可在数字孪生中启用 3D 模型查看。

- **路径**：`/models/001.glb`（对应 `src/config/modelConfig.ts` 中的 `path`）
- **格式**：GLB（推荐）或 glTF + bin/images
- **部件命名**：模型内节点名称需与 `src/config/partMapping.ts` 中的 `partName` 一致，才能支持部件高亮、点击参数与数据驱动动画
- 若未放置模型或加载失败，系统会自动回退为多角度图片查看器
- 查看模型节点名：`python scripts/read_glb_nodes.py public/models/001.glb`
