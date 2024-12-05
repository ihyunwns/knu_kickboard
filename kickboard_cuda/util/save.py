import time
import cv2
import os
import mariadb


def save_violation_image(kickboard_id, frame, frame_idx, violation_time):
    year = violation_time.tm_year
    month = violation_time.tm_mon
    day = violation_time.tm_mday

    base_folder = r"D:\violation"

    year_month_folder = f"{year}-{month:02d}"
    day_folder = f"day {day}"

    hour = violation_time.tm_hour
    min = violation_time.tm_min
    sec = violation_time.tm_sec

    kickboard_folder = os.path.join(base_folder, year_month_folder, day_folder, str(kickboard_id))
    os.makedirs(kickboard_folder, exist_ok=True)

    time_str = f"{hour:02d}-{min:02d}-{sec:02d}"
    filename = f"frame_{frame_idx}_{time_str}.jpg"
    filepath = os.path.join(kickboard_folder, filename)

    cv2.imwrite(filepath, frame)
    print(f"Saved frame {frame_idx} for kickboard {kickboard_id} at {filepath}")

    # 파일이 저장되는 이미지 폴더 리턴
    return kickboard_folder


def save_violation_db(
        kickboard_id,
        violation_type,
        violation_date,
        violation_duration,
        image_url
):
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': 'kickboard',
        'database': 'kickboard_violation'
    }

    conn = None
    cursor = None

    try:

        conn = mariadb.connect(**db_config)
        cursor = conn.cursor()

        violation_type_mapping = {
            'HELMET': 1,
            '2-PERSON': 2,
            'BOTH': 3
        }


        violation_type_id = violation_type_mapping.get(violation_type.upper())
        date_str = time.strftime('%Y%m%d', time.localtime(violation_date))

        cursor.execute('''
            SELECT MAX(CAST(SUBSTRING(violation_id, LENGTH(%s) + 2) AS UNSIGNED)) 
            FROM VIOLATION 
            WHERE violation_id LIKE %s
        ''', (date_str, date_str + '%'))
        max_id = cursor.fetchone()[0]

        if max_id is None:
            violation_id = f'{date_str}-0001'  # 첫 번째 ID 생성 (숫자 부분 0001로 시작)
        else:
            violation_id = f'{date_str}-{max_id + 1:04}'  # 최대값에 1을 더하고 4자리 형식으로 생성

        insert_sql = '''INSERT INTO VIOLATION
                    (violation_id,
                    tracking_id,
                    violation_type_id,
                    violation_date,
                    violation_duration,
                    image_url) VALUES (%s, %s, %s, %s, %s, %s)'''

        insert_values = (violation_id,
                         kickboard_id,
                         violation_type_id,
                         time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(violation_date)),
                         violation_duration,
                         image_url)

        cursor.execute(insert_sql, insert_values)
        conn.commit()

        print(f"Violation info saved to DB with violation_id: {violation_id}")


    except mariadb.Error as err:
        print(f"Database error: {err}")
        return None

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
