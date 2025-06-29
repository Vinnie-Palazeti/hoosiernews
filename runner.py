# import sqlite3

# with sqlite3.connect('data.db') as con:
#     con.row_factory = sqlite3.Row
#     cursor = con.cursor()
#     # q = """select date, title, created_at from posts where site = 'Jesse Brown' order by created_at desc"""
#     q = """select site, count(*) as cnt from posts group by site"""
#     data = [dict(row) for row in cursor.execute(q).fetchall()]
#     breakpoint()
    
    # q = """
    # DELETE FROM posts
    # WHERE site = 'Indianapolis Local News';
    # """
    
    # q = "delete from posts where url LIKE '%courier%'"
    # cursor.execute(q)
    # con.commit()
    

# ### there should be the most recent data in here...
# ## I just pulled it..

# ## but getdata is not pulling it..
# q = """
# select date, title, created_at from posts where site = 'Jesse Brown' order by created_at desc
# """
# data = cursor.execute(q).fetchall()
# re = [dict(row) for row in data]
 

# breakpoint()