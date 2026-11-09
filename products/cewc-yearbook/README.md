# 经济工作年鉴（产品 2）

1994 年以来中央经济工作会议通稿的逐年解读：新提法、重点任务排序、财政货币定调、信息观念。政府工作报告只作对照。

- 页面：`index.html`（单文件，无构建步骤），数据：`data/site.json`、`data/corpus.json`（按句，供检索）、`data/fulltext.json`（按段，供全文阅读）
- 部署：Vercel 项目 `cewc-yearbook`，Root Directory = `products/cewc-yearbook`，推送到 main 后自动发布

## 每年更新（会议结束后）

1. 新一年的通稿 docx 放进原始材料目录 `当前/数据/99_原有数据包/数据/中央经济工作会议/`
2. `python3 scripts/build.py --src <原始材料目录>`；脚本会打印新年份自动切分的重点任务，核对后写入 `scripts/tasks_curated.json`
3. 在 `scripts/terms.json` 补充当年新提法（按判断/定调/方法/战略/抓手分类），必要时在 `scripts/milestones.json` 补充信息观念转折句
4. 再运行一次 build，提交 `data/` 与 `scripts/` 的改动
