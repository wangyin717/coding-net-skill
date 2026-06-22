---
name: coding-net
description: 查询和操作 Coding 开放平台（e.coding.net）数据，包括迭代、需求/缺陷/任务、团队成员，以及创建需求和缺陷。当用户提到"查看迭代"、"查看需求"、"创建缺陷"、"Coding 任务"时触发。
---

# Coding Net

通过 Coding 开放平台 API 查询和操作项目数据。

## 启动引导（每次对话开始时必须执行）

**第一步：收集 token**

检查用户是否已在消息中提供 token。若未提供，检查环境变量：

```bash
python3 -c "import os; t=os.environ.get('CODING_TOKEN',''); print('已设置' if t else '未设置')"
```

若均未提供，向用户询问：「请提供您的 Coding 个人访问令牌（Bearer Token）」

**第二步：验证 token，获取团队信息**

拿到 token 后立即执行 bootstrap 验证（无需项目名）：

```bash
CODING_TOKEN=<token> python3 $HOME/.claude/skills/coding-net/scripts/coding_net.py bootstrap
```

输出示例：`✓ Token 有效  团队: 数势科技  (https://digit-force.coding.net)`

若 token 无效，告知用户并停止。

**第三步：确认项目**

告知用户已验证团队，然后询问：
「请提供项目 URL 或项目标识。项目 URL 格式为 `https://<团队>.coding.net/p/<项目标识>/`，项目标识是 URL 中 `/p/` 后面的部分（如 `biaopin-swiftagent`）。」

> ⚠️ **不要猜项目名**。Coding.net 区分"显示名"和"项目标识"，API 只认项目标识。用户说"项目叫 swiftagent"不等于标识就是 `swiftagent`。

**第四步：验证项目 + 展示迭代列表，让用户选择**

```bash
CODING_TOKEN=<token> CODING_DEFAULT_PROJECT_NAME=<project> \
  python3 $HOME/.claude/skills/coding-net/scripts/coding_net.py bootstrap <project>
```

输出示例：
```
✓ Token 有效  团队: 数势科技
项目 'biaopin-swiftagent' 下的迭代列表:
  [23078] 标品4.1.0
  [22904] Clawteams
  [22599] SA迭代
  ...
```

将迭代列表展示给用户，询问：「请问您要查看哪个迭代？」

完成以上四步后，再执行用户的实际查询请求。

---

## 脚本路径

```bash
SCRIPT="$HOME/.claude/skills/coding-net/scripts/coding_net.py"
```

## 常用操作

### 查询迭代列表

```bash
CODING_TOKEN=xxx CODING_DEFAULT_PROJECT_NAME=xxx python3 $SCRIPT iterations
```

返回 `[{"code": 123, "name": "迭代名称"}, ...]`。

按关键字查找迭代 code（不区分大小写）：

```bash
python3 $SCRIPT find-iteration clawteams
```

### 查询需求/缺陷/任务列表

**重要**：
1. API 响应的事项列表字段是 `Response["IssueList"]`，**不是** `Response["Data"]["List"]`
2. API 侧的 `IterationCodes` 过滤有时失效，**必须在 Python 侧二次过滤**
3. 处理人信息在 `Assignees`（数组），**不是** `AssigneeName` 字段

推荐用 `get_issue_list()` + `filter_issues()` 组合，已内置客户端二次过滤：

```python
import sys, os
sys.path.insert(0, f"{os.environ['HOME']}/.claude/skills/coding-net/scripts")
from coding_net import get_issue_list, filter_issues, format_issue

# 拉取指定迭代下所有需求（客户端已二次过滤迭代）
items = get_issue_list(
    issue_type="REQUIREMENT",   # ALL / REQUIREMENT / DEFECT / MISSION
    iteration=22904,             # 迭代 code（整数）
    status_types=None,           # None=TODO+PROCESSING; []=全部状态
)

# 再按处理人筛选（支持姓名模糊匹配或 ID 精确匹配）
items = filter_issues(items, assignee_name="wangyin")
# 或：filter_issues(items, assignee_id=9403993)

for it in items:
    print(format_issue(it))
```

如需原始 API 响应：

```python
from coding_net import describe_issue_list
resp = describe_issue_list(issue_type="REQUIREMENT", iteration=22904)
items = resp["Response"]["IssueList"]   # 注意：是 IssueList，不是 Data.List
```

### 查看单个事项详情

```bash
python3 $SCRIPT issue <事项编号>
```

### 查询成员 ID

`DescribeProjectMembers` 在部分 token scope 下无权限。推荐从事项列表中提取：

```python
from coding_net import get_issue_list, extract_members_from_issues

items = get_issue_list(issue_type="ALL", status_types=[])  # 全状态
members = extract_members_from_issues(items)
for m in members:
    print(m["id"], m["name"])
```

### 创建需求

> ⚠️ **创建前必须先检测项目的自定义字段**，否则若存在必填自定义字段（如"提测日期"），API 会返回 `issue_custom_field_required` 错误。

```python
from coding_net import create_issue, get_iteration_list, get_issue_list, \
    extract_members_from_issues, get_custom_fields_from_issues

# 第一步：获取自定义字段列表（通过采样现有需求推断）
custom_fields = get_custom_fields_from_issues(issue_type="REQUIREMENT")
# 返回示例：[{"id": 38589683, "name": "提测日期"}, ...]
# 向用户确认各字段的值，必填字段必须传入

# 第二步：获取迭代 code
iterations = get_iteration_list()   # [{"code": 123, "name": "..."}, ...]

# 第三步：获取成员 ID（从事项列表提取）
items = get_issue_list(issue_type="ALL", status_types=[])
members = extract_members_from_issues(items)

# 第四步：创建需求，将自定义字段值一并传入
result = create_issue(
    name="新需求标题",
    issue_type="REQUIREMENT",
    description="需求描述",
    priority=2,            # 0=低 1=中 2=高 3=紧急（API 文档定义）
    assignee_id=456,
    iteration=123,
    start_date="2026-06-22",
    due_date="2026-06-30",
    working_hours=8,
    custom_field_values=[
        {"Id": 38589683, "Content": "2026-06-30"},  # 提测日期
        # 其他必填自定义字段...
    ],
)
print(result)
```

### 创建缺陷

```python
from coding_net import create_issue, describe_defect_types

defect_types = describe_defect_types()  # [{"id": 1, "name": "功能缺陷"}, ...]

result = create_issue(
    name="缺陷标题",
    issue_type="DEFECT",
    description="缺陷描述",
    defect_type_id=1,
    priority=1,
    assignee_id=456,
    iteration=123,
)
print(result)
```

## 工作流示例

**查询指定迭代下，指定处理人的需求，按状态分组：**

```python
import sys, os
sys.path.insert(0, f"{os.environ['HOME']}/.claude/skills/coding-net/scripts")
from coding_net import get_issue_list, filter_issues, format_issue
from collections import defaultdict

items = get_issue_list(issue_type="REQUIREMENT", iteration=22904, status_types=[])
items = filter_issues(items, assignee_name="wangyin")

by_status = defaultdict(list)
for it in items:
    by_status[it.get("IssueStatusName", "未知")].append(it)

for status, group in by_status.items():
    print(f"\n【{status}】({len(group)}条)")
    for it in group:
        print(f"  #{it['Code']} {it['Name']}")
```

## 注意事项

- `iteration` 参数传的是迭代的 `code`（整数），不是名称
- 事项列表响应字段是 `Response["IssueList"]`，**不是** `Response["Data"]["List"]`
- `IterationCodes` API 过滤不可靠，务必配合 `filter_issues()` 或 `get_issue_list()` 做客户端二次过滤
- 处理人是 `Assignees` 数组，不是单个 `AssigneeName` 字段
- 项目名必须是 URL 里的项目标识，不是显示名；如用户未提供，先追问
- 创建事项时 `start_date`/`due_date` 格式为 `YYYY-MM-DD`
- **优先级值**（API 文档定义，创建和读取均一致）：`"0"=低 "1"=中 "2"=高 "3"=紧急`
- **创建事项前必须调用 `get_custom_fields_from_issues()` 检测项目自定义字段**，若存在必填字段未传入，API 返回 `issue_custom_field_required` 错误。`DescribeIssueCustomFieldsBoundToProject` 需要更高 token scope，改用采样现有事项的方式推断
