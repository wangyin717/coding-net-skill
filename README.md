# coding-net — Claude Code Skill

在 Claude Code 中查询和操作 [Coding 开放平台](https://e.coding.net)，支持迭代、需求、缺陷、任务和团队成员。

## 安装

```bash
npx skills@latest add wangyin717/coding-net-skill
```

或手动克隆：

```bash
git clone https://github.com/wangyin717/coding-net-skill ~/.claude/skills/coding-net
```

## 使用

在 Claude Code 中输入 `/coding-net`，或直接用自然语言描述需求。

首次使用时 Claude 会引导你完成以下步骤：
1. 提供 Coding 个人访问令牌（Bearer Token）
2. 验证 token 并确认团队
3. 提供项目 URL（格式：`https://<团队>.coding.net/p/<项目标识>/`）
4. 选择目标迭代

之后即可直接查询，例如：

- "查看 Clawteams 迭代下 wangyin 的需求"
- "帮我创建一个缺陷，标题是 xxx"
- "列出所有团队成员"
- "查看 #123 的详情"

## 环境变量（可选）

配置后免去每次输入：

```bash
export CODING_TOKEN=your_token
export CODING_DEFAULT_PROJECT_NAME=biaopin-swiftagent   # 项目标识（URL 中 /p/ 后的部分）
export CODING_DEFAULT_ITERATION_CODE=22904              # 迭代 Code（整数）
```

## 支持的操作

| 操作 | 说明 |
|------|------|
| 查询迭代列表 | 获取所有迭代及其编号 |
| 查询事项列表 | 支持按类型、处理人、迭代、状态筛选 |
| 查看事项详情 | 获取单个需求/缺陷的完整信息 |
| 创建需求 | 支持设置优先级、处理人、迭代、工时等 |
| 创建缺陷 | 支持设置缺陷类型 |
| 查询团队成员 | 从事项列表中提取成员 ID 和姓名 |
