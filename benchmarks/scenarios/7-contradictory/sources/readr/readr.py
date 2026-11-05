# Readr: reading lists and 1-5 star ratings.
import sqlite3
DB = sqlite3.connect("readr.db")
DB.execute("create table if not exists books (id integer primary key, title text not null)")
DB.execute("create table if not exists lists (id integer primary key, name text not null)")
DB.execute("create table if not exists list_books (list_id integer references lists(id), "
           "book_id integer references books(id))")
DB.execute("create table if not exists ratings (book_id integer references books(id), stars integer)")

def rate(book_id, stars):
    if stars not in (1, 2, 3, 4, 5):
        raise ValueError("1 to 5 stars")
    DB.execute("insert into ratings values (?, ?)", (book_id, stars))

def add_to_list(list_id, book_id):
    DB.execute("insert into list_books values (?, ?)", (list_id, book_id))
