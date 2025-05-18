import json
import logging
import os
import sqlite3
from datetime import datetime

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="data_processing.log",
)


def clean_data(data):
    """
    对投诉数据进行清洗，包括时间格式转换和空值处理
    """
    cleaned_data = []
    for item in data:
        try:
            # 时间格式转换
            complaint_time = item.get("complaint_time")
            if complaint_time:
                complaint_time = datetime.strptime(
                    complaint_time, "%Y-%m-%d %H:%M:%S"
                ).strftime("%Y-%m-%d %H:%M:%S")
            else:
                complaint_time = None

            # 空值处理
            content = item.get("content", "").strip()
            user_id = item.get("user_id", "").strip()
            product_category = item.get("product_category", "").strip()

            cleaned_data.append(
                {
                    "complaint_time": complaint_time,
                    "content": content,
                    "user_id": user_id,
                    "product_category": product_category,
                }
            )
        except Exception as e:
            logging.error(f"清洗数据项时发生错误: {str(e)}")
            continue

    return cleaned_data


def import_data_to_db():
    """
    从JSON文件读取投诉数据，进行清洗后导入到数据库
    """
    try:
        # 读取JSON文件
        json_file = "./data/complaints.json"
        if not os.path.exists(json_file):
            logging.error(f"JSON文件不存在: {json_file}")
            return False

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 数据清洗
        cleaned_data = clean_data(data)
        logging.info(f"清洗后的数据条数: {len(cleaned_data)}")

        # 连接到数据库
        conn = sqlite3.connect("complaints.db")
        cursor = conn.cursor()

        # 创建表（如果不存在）
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_time DATETIME,
                content TEXT,
                user_id TEXT,
                product_category TEXT
            )
        """
        )

        # 插入数据
        for item in cleaned_data:
            cursor.execute(
                """
                INSERT INTO complaints (complaint_time, content, user_id, product_category)
                VALUES (?, ?, ?, ?)
            """,
                (
                    item["complaint_time"],
                    item["content"],
                    item["user_id"],
                    item["product_category"],
                ),
            )

        conn.commit()
        logging.info(f"成功导入 {len(cleaned_data)} 条数据到数据库")
        return True

    except Exception as e:
        logging.error(f"导入数据到数据库时发生错误: {str(e)}")
        return False
    finally:
        if "conn" in locals():
            conn.close()


def create_complaint(complaint_time, content, user_id, product_category):
    """
    创建新的投诉记录
    """
    try:
        conn = sqlite3.connect("complaints.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO complaints (complaint_time, content, user_id, product_category)
            VALUES (?, ?, ?, ?)
        """,
            (complaint_time, content, user_id, product_category),
        )
        conn.commit()
        logging.info(f"成功创建投诉记录，用户ID: {user_id}")
        return True
    except Exception as e:
        logging.error(f"创建投诉记录时发生错误: {str(e)}")
        return False
    finally:
        conn.close()


def read_complaints():
    """
    读取所有投诉记录
    """
    try:
        conn = sqlite3.connect("complaints.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints")
        complaints = cursor.fetchall()
        logging.info(f"成功读取 {len(complaints)} 条投诉记录")
        return complaints
    except Exception as e:
        logging.error(f"读取投诉记录时发生错误: {str(e)}")
        return []
    finally:
        conn.close()


def update_complaint(
    complaint_id, complaint_time=None, content=None, user_id=None, product_category=None
):
    """
    更新投诉记录
    """
    try:
        conn = sqlite3.connect("complaints.db")
        cursor = conn.cursor()
        update_fields = []
        values = []
        if complaint_time:
            update_fields.append("complaint_time = ?")
            values.append(complaint_time)
        if content:
            update_fields.append("content = ?")
            values.append(content)
        if user_id:
            update_fields.append("user_id = ?")
            values.append(user_id)
        if product_category:
            update_fields.append("product_category = ?")
            values.append(product_category)

        if update_fields:
            values.append(complaint_id)
            query = f"UPDATE complaints SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            logging.info(f"成功更新投诉记录，ID: {complaint_id}")
            return True
        return False
    except Exception as e:
        logging.error(f"更新投诉记录时发生错误: {str(e)}")
        return False
    finally:
        conn.close()


def delete_complaint(complaint_id):
    """
    删除投诉记录
    """
    try:
        conn = sqlite3.connect("complaints.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
        conn.commit()
        logging.info(f"成功删除投诉记录，ID: {complaint_id}")
        return True
    except Exception as e:
        logging.error(f"删除投诉记录时发生错误: {str(e)}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    logging.info("开始处理投诉数据...")
    success = import_data_to_db()
    if success:
        logging.info("投诉数据处理完成。")
    else:
        logging.error("投诉数据处理失败。")
