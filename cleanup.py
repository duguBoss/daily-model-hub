import shutil
from datetime import datetime, timedelta
from pathlib import Path

from config import DATA_DIR, DAILY_DIR, WEEK_DIR, IMAGE_ROOT_DIR, RUN_DATE


def cleanup_old_files(keep_days: int = 0) -> None:
    """清理历史数据文件，只保留当天的数据.

    Args:
        keep_days: 保留最近多少天的数据，默认0表示只保留当天
    """
    # 当 keep_days=0 时，只保留当天数据（删除所有早于今天的内容）
    cutoff_date = RUN_DATE - timedelta(days=keep_days)
    deleted_count = 0

    # 清理 daily 目录下的旧 JSON 文件
    if DAILY_DIR.exists():
        for json_file in DAILY_DIR.glob("*.json"):
            try:
                file_date = datetime.strptime(json_file.stem, "%Y-%m-%d").date()
                if file_date < cutoff_date:
                    json_file.unlink()
                    deleted_count += 1
                    print(f"Deleted old daily record: {json_file.name}")
            except ValueError:
                continue
            except Exception as e:
                print(f"Failed to delete {json_file}: {e}")

    # 清理 week 目录下的旧 JSON 文件
    if WEEK_DIR.exists():
        for json_file in WEEK_DIR.glob("*.json"):
            try:
                file_date = datetime.strptime(json_file.stem, "%Y-%m-%d").date()
                if file_date < cutoff_date:
                    json_file.unlink()
                    deleted_count += 1
                    print(f"Deleted old weekly record: {json_file.name}")
            except ValueError:
                continue
            except Exception as e:
                print(f"Failed to delete {json_file}: {e}")

    # 清理 assets 目录下的旧图片文件夹
    if IMAGE_ROOT_DIR.exists():
        for folder in IMAGE_ROOT_DIR.iterdir():
            if not folder.is_dir():
                continue
            try:
                folder_date = datetime.strptime(folder.name, "%Y-%m-%d").date()
                if folder_date < cutoff_date:
                    shutil.rmtree(folder, ignore_errors=True)
                    deleted_count += 1
                    print(f"Deleted old image folder: {folder.name}")
            except ValueError:
                continue
            except Exception as e:
                print(f"Failed to delete folder {folder}: {e}")

    # 清理根目录下的 Daily_HF_Models_*.json 文件
    root_dir = Path(__file__).resolve().parent
    for json_file in root_dir.glob("Daily_HF_Models_*.json"):
        try:
            file_date = datetime.strptime(json_file.stem.replace("Daily_HF_Models_", ""), "%Y-%m-%d").date()
            if file_date < cutoff_date:
                json_file.unlink()
                deleted_count += 1
                print(f"Deleted old WeChat JSON: {json_file.name}")
        except ValueError:
            continue
        except Exception as e:
            print(f"Failed to delete {json_file}: {e}")

    if deleted_count == 0:
        print("No old files to clean up")
    else:
        print(f"Cleanup complete: removed {deleted_count} old items")
