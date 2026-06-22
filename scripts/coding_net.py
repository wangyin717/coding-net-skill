"""Coding.net Open API helper — used by the coding-net Claude Code skill."""
import os, json, urllib.request, urllib.error

TOKEN = os.environ.get("CODING_TOKEN", "")
DEFAULT_PROJECT = os.environ.get("CODING_DEFAULT_PROJECT_NAME", "")
DEFAULT_ITERATION = os.environ.get("CODING_DEFAULT_ITERATION_CODE", "")


def _req(action_or_path, data=None):
    """POST to open-api with an Action payload, or GET a v1 REST path."""
    if data is not None:
        url = "https://e.coding.net/open-api"
        body = json.dumps(data).encode()
        method = "POST"
    else:
        url = f"https://e.coding.net/open-api{action_or_path}"
        body = None
        method = "GET"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "msg": e.read().decode()}


# ── Iterations ────────────────────────────────────────────────────────────────

def get_iteration_list(project_name=None):
    """返回 [{"code": int, "name": str}, ...]"""
    project = project_name or DEFAULT_PROJECT
    resp = _req(None, {"Action": "DescribeIterationList", "ProjectName": project})
    items = resp.get("Response", {}).get("Data", {}).get("List", [])
    return [{"code": it["Code"], "name": it["Name"]} for it in items]


def find_iteration_code(name_keyword, project_name=None):
    """按名称关键字查找迭代 code，不区分大小写。"""
    for it in get_iteration_list(project_name):
        if name_keyword.lower() in it["name"].lower():
            return it["code"], it["name"]
    return None, None


# ── Issues ────────────────────────────────────────────────────────────────────

def describe_issue_list(project_name=None, issue_type="ALL", limit=500,
                        assignee_ids=None, iteration=None, status_types=None):
    """
    查询事项列表。

    注意：
    - API 侧的 IterationCodes / AssigneeIds 过滤有时不可靠，
      建议用 filter_issues() 在客户端二次过滤。
    - 返回原始 Response dict，事项列表在 Response["IssueList"]。
    """
    project = project_name or DEFAULT_PROJECT
    payload = {
        "Action": "DescribeIssueList",
        "ProjectName": project,
        "IssueType": issue_type,
        "Limit": limit,
    }
    if assignee_ids:
        payload["AssigneeIds"] = assignee_ids
    if iteration is not None:
        payload["IterationCodes"] = [iteration]
    if status_types is not None:
        payload["IssueStatusTypes"] = status_types
    else:
        payload["IssueStatusTypes"] = ["TODO", "PROCESSING"]
    return _req(None, payload)


def get_issue_list(project_name=None, issue_type="ALL", limit=500,
                   iteration=None, status_types=None):
    """
    便捷方法：直接返回事项列表 []。
    结果已按迭代 code 在客户端二次过滤（避免 API 侧过滤失效）。
    """
    resp = describe_issue_list(
        project_name=project_name,
        issue_type=issue_type,
        limit=limit,
        iteration=iteration,
        status_types=status_types,
    )
    items = resp.get("Response", {}).get("IssueList", [])
    # 客户端二次过滤迭代（API 侧过滤有时失效）
    if iteration is not None:
        items = [it for it in items
                 if (it.get("Iteration") or {}).get("Code") == iteration]
    return items


def filter_issues(items, assignee_name=None, assignee_id=None, iteration_code=None):
    """
    客户端过滤：支持按处理人姓名/ID、迭代 code 筛选。
    Assignees 是数组，任意一个匹配即算。
    """
    result = []
    for it in items:
        if iteration_code is not None:
            if (it.get("Iteration") or {}).get("Code") != iteration_code:
                continue
        if assignee_id is not None or assignee_name is not None:
            assignees = it.get("Assignees") or []
            matched = False
            for a in assignees:
                if assignee_id and a.get("Id") == assignee_id:
                    matched = True; break
                if assignee_name and assignee_name.lower() in (a.get("Name") or "").lower():
                    matched = True; break
            if not matched:
                continue
        result.append(it)
    return result


def extract_members_from_issues(items):
    """从事项列表中提取所有出现过的处理人（去重）。"""
    seen, out = set(), []
    for it in items:
        for a in (it.get("Assignees") or []):
            if a["Id"] not in seen:
                seen.add(a["Id"])
                out.append({"id": a["Id"], "name": a.get("Name", "")})
    return sorted(out, key=lambda x: x["name"])


def describe_issue(issue_code, project_name=None):
    project = project_name or DEFAULT_PROJECT
    return _req(None, {
        "Action": "DescribeIssue",
        "ProjectName": project,
        "IssueCode": issue_code,
    })


def create_issue(name, issue_type="REQUIREMENT", description="", priority=2,
                 assignee_id=None, iteration=None, start_date=None,
                 due_date=None, label_ids=None, working_hours=None,
                 issue_type_id=None, defect_type_id=None, project_name=None,
                 custom_field_values=None):
    # API requires Priority/AssigneeId/IterationCode as strings
    project = project_name or DEFAULT_PROJECT
    payload = {
        "Action": "CreateIssue",
        "ProjectName": project,
        "Name": name,
        "Type": issue_type,
        "Description": description,
        "Priority": str(priority),
    }
    if assignee_id:         payload["AssigneeId"] = str(assignee_id)
    if iteration:           payload["IterationCode"] = str(iteration)
    if start_date:          payload["StartDate"] = start_date
    if due_date:            payload["DueDate"] = due_date
    if label_ids:           payload["LabelIds"] = label_ids
    if working_hours:       payload["WorkingHours"] = working_hours
    if issue_type_id:       payload["IssueTypeId"] = issue_type_id
    if defect_type_id:      payload["DefectTypeId"] = defect_type_id
    # custom_field_values: [{"Id": <IssueFieldId>, "Content": "<value>"}, ...]
    if custom_field_values: payload["CustomFieldValues"] = custom_field_values
    return _req(None, payload)


def get_custom_fields_from_issues(issue_type="REQUIREMENT", project_name=None, sample=10):
    """
    通过采样现有事项推断项目中使用的自定义字段（无需高权限 token）。
    由于 DescribeIssueCustomFieldsBoundToProject 需要额外 scope，改用此法。
    返回 [{"id": int, "name": str}, ...]
    创建事项前应先调用此函数，以便传入 custom_field_values。
    """
    items = get_issue_list(project_name=project_name, issue_type=issue_type,
                           status_types=[], limit=sample)
    seen, result = set(), []
    for it in items:
        for cf in (it.get("CustomFields") or []):
            fid = cf.get("Id")
            if fid and fid not in seen:
                seen.add(fid)
                result.append({"id": fid, "name": cf.get("Name", "")})
    return result


def describe_defect_types(project_name=None):
    project = project_name or DEFAULT_PROJECT
    resp = _req(None, {"Action": "DescribeDefectTypes", "ProjectName": project})
    items = resp.get("Response", {}).get("Data", [])
    return [{"id": it["Id"], "name": it["Name"]} for it in items]


# ── Members ───────────────────────────────────────────────────────────────────

def get_team_members(project_name=None):
    """
    尝试通过 DescribeProjectMembers 获取成员列表。
    若 token scope 不足（返回空或无权限），回退提示从事项列表中提取。
    """
    project = project_name or DEFAULT_PROJECT
    result, page = [], 1
    while True:
        resp = _req(None, {
            "Action": "DescribeProjectMembers",
            "ProjectName": project,
            "PageNumber": page,
            "PageSize": 100,
        })
        if resp.get("Response", {}).get("Error"):
            break
        items = resp.get("Response", {}).get("Data", {}).get("List", [])
        if not items:
            break
        result.extend(items)
        page += 1
    return [{"id": m["Id"], "name": m.get("Name", "")} for m in result]


# ── Team ─────────────────────────────────────────────────────────────────────

def get_team_info():
    """返回团队基本信息，包含 TeamHost，可帮助确认团队域名。"""
    resp = _req(None, {"Action": "DescribeTeam"})
    return resp.get("Response", {}).get("Data", {})


def bootstrap(project_name=None):
    """
    引导检查：验证 token 有效性并返回团队信息 + 迭代列表。
    project_name 为空时只验证 token，不查迭代。
    返回 {"team": {...}, "iterations": [...], "error": str or None}
    """
    result = {"team": None, "iterations": [], "error": None}
    if not TOKEN:
        result["error"] = "CODING_TOKEN 未设置"
        return result
    team = get_team_info()
    if not team or "Name" not in team:
        result["error"] = "Token 无效或无法访问团队信息"
        return result
    result["team"] = {
        "name": team.get("Name"),
        "host": team.get("TeamHost"),
    }
    if project_name:
        resp = _req(None, {"Action": "DescribeIterationList", "ProjectName": project_name})
        err = resp.get("Response", {}).get("Error")
        if err:
            result["error"] = f"项目 '{project_name}' 不存在或无权限: {err.get('Message')}"
        else:
            items = resp.get("Response", {}).get("Data", {}).get("List", [])
            result["iterations"] = [{"code": it["Code"], "name": it["Name"]} for it in items]
    return result


# ── Formatting helpers ────────────────────────────────────────────────────────

# 优先级映射（API 读写均使用：0=低 1=中 2=高 3=紧急）
PRIORITY_MAP = {"0": "低", "1": "中", "2": "高", "3": "紧急"}


def format_issue(it):
    priority = PRIORITY_MAP.get(str(it.get("Priority", "")), "")
    assignees = ", ".join(a.get("Name", "") for a in (it.get("Assignees") or []))
    custom = it.get("CustomFields") or []
    test_date = next((c.get("RealValue", "") for c in custom if c.get("Name") == "提测日期"), "")
    iter_name = (it.get("Iteration") or {}).get("Name", "")
    return (
        f"#{it['Code']} [{it.get('IssueStatusName', '')}] {it['Name']}\n"
        f"   迭代:{iter_name}  处理人:{assignees}  优先级:{priority}  提测日期:{test_date}"
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "iterations":
        print(json.dumps(get_iteration_list(), ensure_ascii=False, indent=2))

    elif cmd == "members":
        members = get_team_members()
        if members:
            print(json.dumps(members, ensure_ascii=False, indent=2))
        else:
            print("⚠ DescribeProjectMembers 无权限，请改为从事项列表提取成员。")
            print("示例: python3 coding_net.py issues | 然后用 extract_members_from_issues()")

    elif cmd == "issues":
        iteration = int(DEFAULT_ITERATION) if DEFAULT_ITERATION else None
        items = get_issue_list(iteration=iteration, issue_type="ALL")
        print(f"共 {len(items)} 条事项")
        for it in items:
            print(format_issue(it))

    elif cmd == "issue" and len(sys.argv) > 2:
        print(json.dumps(describe_issue(int(sys.argv[2])), ensure_ascii=False, indent=2))

    elif cmd == "defect-types":
        print(json.dumps(describe_defect_types(), ensure_ascii=False, indent=2))

    elif cmd == "team":
        print(json.dumps(get_team_info(), ensure_ascii=False, indent=2))

    elif cmd == "find-iteration" and len(sys.argv) > 2:
        code, name = find_iteration_code(sys.argv[2])
        if code:
            print(f"找到迭代: {name} (code={code})")
        else:
            print(f"未找到包含 '{sys.argv[2]}' 的迭代")

    elif cmd == "bootstrap":
        project = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PROJECT or None
        info = bootstrap(project)
        if info["error"]:
            print(f"✗ {info['error']}")
        else:
            t = info["team"]
            print(f"✓ Token 有效  团队: {t['name']}  ({t['host']})")
            if info["iterations"]:
                print(f"\n项目 '{project}' 下的迭代列表:")
                for it in info["iterations"]:
                    print(f"  [{it['code']}] {it['name']}")
            elif project:
                print(f"⚠ 项目 '{project}' 下暂无迭代")

    else:
        print("Usage: python coding_net.py [iterations|members|issues|issue <code>|defect-types|team|find-iteration <keyword>]")
