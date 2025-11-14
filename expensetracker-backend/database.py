from sqlalchemy import text, create_engine
from pymysql.constants import CLIENT
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import sys

load_dotenv()


db_url = f'mysql+pymysql://{os.getenv("dbuser")}:{os.getenv("dbpassword")}@{os.getenv("dbhost")}:{os.getenv("dbport")}/{os.getenv("dbname")}'

engine = create_engine (
    db_url,
    connect_args={"client_flag": CLIENT.MULTI_STATEMENTS}
)

session = sessionmaker(bind=engine)

db = session()

user_query = text("""
    CREATE TABLE IF NOT EXISTS users (
        id int auto_increment primary key not null,
        name varchar(50) not null,
        email varchar(50) unique not null,
        password varchar(100) not null
    );
    
    CREATE TABLE IF NOT EXISTS expensetracker (
        id int auto_increment primary key not null,
        title varchar(50) not null,
        amount int not null,
        dateinput date not null,
        category varchar(50) not null,
        budget int not null,
        user_id int not null,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );              
""")

db.execute(user_query)


# db.commit()