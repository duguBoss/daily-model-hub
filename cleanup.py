import shutil
from datetime import datetime, timedelta
from pathlib import Path

from config import DATA_DIR, DAILY_DIR, WEEK_DIR, IMAGE_ROOT_DIR, RUN_DATE, RUN_IMAGE_DIR


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
                # 处理两种格式: YYYY-MM-DD.json 和 Daily_HF_Models_YYYY-MM-DD.json
                stem = json_file.stem
                if stem.startswith("Daily_HF_Models_"):
                    file_date = datetime.strptime(stem.replace("Daily_HF_Models_", ""), "%Y-%m-%d").date()
                else:
                    file_date = datetime.strptime(stem, "%Y-%m-%d").date()
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



    if deleted_count == 0:
        print("No old files to clean up")
    else:
        print(f"Cleanup complete: removed {deleted_count} old items")


def cleanup_current_assets() -> None:
    """清空当天的 assets 文件夹，确保每次执行前都是干净的."""
    if RUN_IMAGE_DIR.exists():
        shutil.rmtree(RUN_IMAGE_DIR, ignore_errors=True)
        print(f"Cleaned up current assets directory: {RUN_IMAGE_DIR}")
    RUN_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
