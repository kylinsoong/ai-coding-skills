#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行成本打分脚本。

读取运行成本 CSV,按固定 8 维权重打分,输出评分 CSV(总分降序)。
仅使用标准库,无第三方依赖。

CLI:
    python3 score_runtime_cost.py <input.csv> [output.csv]

输入列(默认):
    模型,时间（分钟）,对话次数,会话次数,模型调用次数,Token 消耗（万）,金额消耗（元）,一次执行完成,执行集成测试

输出列:
    模型,时间得分,对话得分,会话得分,调用得分,Token得分,金额得分,一次执行完成得分,执行集成测试得分,总分
"""

import csv
import sys

# 定量列: (输入列名, 权重, 输出列名) —— 越低越好
QUANTITATIVE = [
    ("时间（分钟）", 1.0, "时间得分"),
    ("对话次数", 1.0, "对话得分"),
    ("会话次数", 1.0, "会话得分"),
    ("模型调用次数", 1.0, "调用得分"),
    ("Token 消耗（万）", 1.0, "Token得分"),
    ("金额消耗（元）", 2.0, "金额得分"),
]

# 定性列: (输入列名, 输出列名, 是->分, 否->分)
QUALITATIVE = [
    ("一次执行完成", "一次执行完成得分", 2.0, 0.5),
    ("执行集成测试", "执行集成测试得分", 1.0, 0.0),
]

MODEL_COL = "模型"
EPSILON = 0.01


def parse_float(value):
    """解析数值,兼容空串/千分位(去掉字符串数字中的逗号)。"""
    if value is None:
        raise ValueError("数值列为空")
    text = str(value).strip().replace(",", "")
    if text == "":
        raise ValueError("数值列为空")
    return float(text)


def read_rows(input_path):
    """读取 CSV,返回 (表头列表, 记录列表)。跳过模型为空的空行。"""
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV 无表头")
        fieldnames = list(reader.fieldnames)
        for col in [MODEL_COL] + [c[0] for c in QUANTITATIVE] + [c[0] for c in QUALITATIVE]:
            if col not in fieldnames:
                raise ValueError(f"缺少必要列: {col!r}(实际列: {fieldnames})")
        rows = []
        for row in reader:
            if row.get(MODEL_COL, "").strip() == "":
                continue  # 跳过空行
            rows.append(row)
        return rows


def normalize_scores(rows):
    """对六个定量列做 min-max 归一化,返回 {列名: {row_index: 归一化值}}。"""
    result = {}
    for col, weight, out_col in QUANTITATIVE:
        values = [parse_float(row[col]) for row in rows]
        min_v = min(values)
        max_v = max(values)
        norm = {}
        for i, v in enumerate(values):
            if max_v == min_v:
                norm[i] = 1.0  # 列内所有值相同 -> 全列满权重分
            else:
                norm[i] = 0.1 + 0.9 * (max_v - v) / (max_v - min_v)
        result[col] = norm
    return result


def build_scores(rows, normalized):
    """计算每行各维度得分与总分。"""
    scored = []
    for i, row in enumerate(rows):
        model = row[MODEL_COL].strip()
        item = {"模型": model}
        total = 0.0
        # 定量列
        for col, weight, out_col in QUANTITATIVE:
            score = weight * normalized[col][i]
            item[out_col] = score
            total += score
        # 定性列
        for col, out_col, yes_pt, no_pt in QUALITATIVE:
            raw = row.get(col, "").strip()
            if raw == "是":
                score = yes_pt
            elif raw == "否":
                score = no_pt
            else:
                raise ValueError(f"模型 {model!r} 的定性列 {col!r} 取值非法: {raw!r}(应为 是/否)")
            item[out_col] = score
            total += score
        item["总分"] = total
        scored.append(item)
    return scored


def validate(scored, rows):
    """写前校验: 定量得分范围 + 行内求和 = 总分。"""
    for i, (item, row) in enumerate(zip(scored, rows)):
        expected_sum = 0.0
        for col, weight, out_col in QUANTITATIVE:
            score = item[out_col]
            low = weight * 0.1
            high = weight * 1.0
            if not (low - EPSILON <= score <= high + EPSILON):
                raise ValueError(
                    f"模型 {item['模型']!r} 列 {col!r} 得分 {score} 越界(应为 [{low}, {high}])"
                )
            expected_sum += score
        for col, out_col, yes_pt, no_pt in QUALITATIVE:
            expected_sum += item[out_col]
        if abs(item["总分"] - expected_sum) > EPSILON:
            raise ValueError(
                f"模型 {item['模型']!r} 行内求和 {expected_sum} != 总分 {item['总分']}"
            )


def write_output(scored, output_path):
    """按总分降序写出 CSV。"""
    ordered = sorted(scored, key=lambda x: x["总分"], reverse=True)
    header = ["模型"] + [out for _, _, out in QUANTITATIVE] + [
        out for _, out, _, _ in QUALITATIVE
    ] + ["总分"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for item in ordered:
            row = {}
            for k in header:
                val = item[k]
                row[k] = val if k == MODEL_COL else f"{val:.2f}"
            writer.writerow(row)


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(argv) >= 2 and argv[1] in ("-h", "--help") else 1

    input_path = argv[1]
    if len(argv) >= 3:
        output_path = argv[2]
    else:
        import os
        output_path = os.path.join(os.path.dirname(os.path.abspath(input_path)),
                                   "runtime-cost-score.csv")

    rows = read_rows(input_path)
    normalized = normalize_scores(rows)
    scored = build_scores(rows, normalized)
    validate(scored, rows)
    write_output(scored, output_path)
    print(f"已写出 {len(scored)} 行到 {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))