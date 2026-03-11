import os
import json

folder = "/mnt/petrelfs/zhengzihao/workspace/mos/experiments/pico_experiment"
for fname in ["task_defination.json", "metric_defination.json"]:
    fpath = os.path.join(folder, fname)
    print(f"\nChecking {fpath}:")
    try:
        with open(fpath, encoding='utf-8') as f:
            print(f.read())  # 查看内容
            f.seek(0)
            json.load(f)     # 格式校验
        print("OK!")
    except Exception as e:
        print(f"Error: {e}")