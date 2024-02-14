
import pymysql.cursors

def connect_to_database():
    connection = pymysql.connect(
        host="",
        user="",
        password="",
        database="",
        cursorclass=pymysql.cursors.DictCursor,
    )
    return connection