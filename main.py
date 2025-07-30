from fasthtml.common import *
from svgs import svgs
import random
import sqlite3
from datetime import date
from dataclasses import dataclass
from locations import *
from typing import List, Dict, Optional, Any

@dataclass
class DiegoLocation:
    location: str
    date_visited: date
    proof: str
    latval: float
    lonval: float

headers=[
    Meta(charset='UTF-8'),
    Meta(name='viewport', content='width=device-width, initial-scale=1.0, maximum-scale=1.0'),
    
    ## htmx
    # Script(src="https://unpkg.com/htmx.org@next/dist/htmx.min.js"),
    
    Script(src="/static/js/htmx.min.js"),
    Script(src="/static/js/surreal.js"),
    
    ### here for testing... ###
    # Link(href='https://cdn.jsdelivr.net/npm/daisyui@5', rel='stylesheet', type='text/css'),
    # Script(src='https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4'),
    ###########################
    
    ## theme-change
    # Script(src='https://cdn.jsdelivr.net/npm/theme-change@2.0.2/index.js'), # testing
    Script(src='/static/js/theme-change.js'),
    
    ## leaflet
    # Link(href='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css', rel='stylesheet'), # testing
    Link(href='/static/css/leaflet.min.css', rel='stylesheet'),
    
    Link(rel='icon', href='/static/assets/state.svg', type='image/svg+xml'),    
    
    ## css
    ## pathing was messed up. static file server was not working correctly
    ## still unsure if the tailwind exe file will build this correctly while nested in the static/css/... 
    Link(rel="stylesheet", href="/static/css/output.css", type="text/css"), 
    Link(rel="stylesheet", href="/static/css/custom.css", type="text/css"), 
    
    ## I don't think this will work anymore because it is not served in the static/ folder ... but not sure everything will build correctly while nested
    # Link(rel="stylesheet", href="output.css", type="text/css"), 
    # Link(rel="stylesheet", href="custom.css", type="text/css"),
    # what a fucking mess
    
    Style(
    """
        .text-wrap-2 {
            display: -webkit-box;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 2;
            overflow: hidden;
            white-space: normal;
            text-overflow: clip;
        }
        
        .custom-popup {
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 5px;
            box-shadow: 0 3px 14px rgba(0,0,0,0.4);
        }  
        
        .group-touch-active .touch-absolute {
            position: absolute;
        }

        .group-touch-active .touch-opacity-0 {
            opacity: 0;
        }
    """
    ) 
    
]


def log_session(req, sess):
    ip = req.client.host
    ua = req.headers.get("user-agent", "")
    path = str(req.url.path)
    
    con = sqlite3.connect('data.db')
    try:
        con.execute(
            "INSERT INTO sessions (ip, user_agent, path) VALUES (?, ?, ?)",
            (ip, ua, path)
        )
        con.commit()   
    except sqlite3.IntegrityError as e:
        print(e)
        pass
    finally:
        con.close()
        

app = FastHTML(title='Hoosier News', before=log_session, hdrs=headers, default_hdrs=False)
rt = app.route      

@rt("/static/{full_path:path}")
def static(full_path: str):
    return FileResponse(f"static/{full_path}")


@rt('/where-is-diego')
def get():
    return(
        Body()(
            Div(cls='px-5 bg-base-100 min-h-screen w-full bg-[radial-gradient(#979797_1px,transparent_1px)] [background-size:24px_24px]')(
                title_bar(diego=True),
                H1('Where in the world is Diego Morales?', cls='text-5xl py-2 '),
                Div(id='map', cls='w-full h-[500px]'),
                diego_form()
  
            )    
        ),
        Script(src='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'),
        Script(src='/static/js/leaf.js'),
    )
    
def create_sessions_table(db_path):
    # Connect to (or create) the SQLite database
    conn = sqlite3.connect(db_path)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT,
        user_agent TEXT,
        path TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()

@rt('/diego-location')
def post(d:DiegoLocation):
    create_locations_table("data.db")
    location_id = insert_location("data.db", d)
    print(f"Inserted location with ID: {location_id}") 
    
    return H1('Thank you for spotting Diego!', cls='text-5xl')


def get_posts(
    page: int = 0,
    per_site: int = 2,
    sites: Optional[List[str]] = None,
    db_path: str = "data.db",
) -> List[Dict[str, Any]]:
    """
    Fetches up to `per_site` posts per site, optionally filtering to a given list of sites,
    and returns them in random order.

    Args:
        page: zero-based page index (so page=0 returns rn=1…per_site, page=1 returns rn=per_site+1…2*per_site).
        per_site: number of posts per site per page.
        sites: if provided, only posts whose `site` is in this list will be considered.
        db_path: path to your SQLite database file.

    Returns:
        A list of dicts, each representing one post, shuffled randomly.
    """
    # Build optional WHERE … IN (?,?,…) clause
    params: List[Any] = []
    where_clause = ""
    if sites:
        placeholders = ",".join("?" for _ in sites)
        where_clause = f"WHERE site IN ({placeholders})"
        params.extend(sites)

    sql = f"""
    WITH recents AS (
        SELECT
            id, title, summary, url, site, email,
            ROW_NUMBER() OVER (
                PARTITION BY site
                ORDER BY created_at DESC
            ) AS rn
        FROM posts
        {where_clause}
    )
    SELECT id, title, summary, url, site, email
    FROM recents
    WHERE rn > ? AND rn <= ?
    ORDER BY site, rn
    """

    # calculate the rn bounds
    start_rn = page * per_site
    end_rn = (page + 1) * per_site
    params.extend([start_rn, end_rn])

    # execute
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()

    posts = [dict(r) for r in rows]
    random.shuffle(posts)
    return posts

def get_post_by_id(id):
    with sqlite3.connect('data.db') as con:
        con.row_factory = sqlite3.Row
        cursor = con.cursor()
        post = cursor.execute('select title, site, content from posts where id = ?', (id, )).fetchone()
    return dict(post)    
    
def card(title, summary=None, site=None, url=None, email=None, id=None, target='_blank', **kwargs):
    if email:
        url = f'/post/{id}'
        target=None
    return (
        A(href=url, target=target, cls="group relative block h-52 sm:h-60 lg:h-72")(
            # background
            Span(cls=f"absolute inset-0 border-4 border-dashed"),

            ## background white here is for the card bg-white 
            Div(cls="bg-base-100 min-w-[300px] relative flex h-full transform items-end border-4 transition-transform group-hover:-translate-x-2 group-hover:-translate-y-2 group-[.touch-active]:-translate-x-2 group-[.touch-active]:-translate-y-2")(
                
                Div(cls='sm:h-4/5 p-4 !pt-0 transition-opacity group-hover:absolute group-hover:opacity-0 group-[.touch-active]:absolute group-[.touch-active]:opacity-0 sm:p-6 lg:p-8')(
                    Div(cls='flex flex-row items-center gap-4')(svgs.get(site), H1(site, cls='font-medium text-3xl text-wrap-2')),
                    Div(cls='mt-4')(H2(cls="font-medium text-xl sm:text-2xl sm:line-clamp-3 lg:line-clamp-4 ")(title))
                ),
                
                Div(cls="absolute p-4 opacity-0 transition-opacity group-hover:relative group-hover:opacity-100 group-[.touch-active]:relative group-[.touch-active]:opacity-100 sm:p-8 lg:p-8")(
                    H2(cls="font-medium text-xl sm:text-2xl")(site),
                    P(cls="mt-2 text-md sm:text-lg line-clamp-4")(summary),
                    P(cls='mt-4 font-bold')('Read more')
                )
            )
        )                
    )

def grid():
    return Div(id='content', cls='pb-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4')

def toggle():
    ## tried to get a post call to swap the svgs.. couldn't get it to work
    return Div(cls='mt-10 flex flex-row gap-2 backdrop-blur-sm')(
        Span()(svgs['sun']),
        Div(cls='inline-block w-10')(
            Span(data_toggle_theme='dark', data_act_class='pl-4', 
                 cls='border rounded-full border-base-700 flex items-center cursor-pointer w-10 transition-all duration-300 ease-in-out pl-0')(
                Span(cls='rounded-full w-3 h-3 m-1 bg-gray-700')
            )
        ),
        Span()(svgs['moon'])
    )
    
def title_bar(diego=None):
    return (
        Div(cls='flex flex-col sm:flex-row items-center justify-between pt-6 pb-2 gap-2')(
            Div(cls='flex items-center')(
                A(href='/')(P('Hoosier News', cls='pl-2 sm:pl-0 text-7xl text-base-content leading-none m-0 backdrop-blur-sm')),
                Div(cls='pl-2')(svgs['indiana']),
                toggle()
            ), 
            
            (A(href='/where-is-diego', cls='btn px-8 backdrop-blur-sm mt-10 text-xl self-start sm:self-center mt-2 sm:mt-0')(
                "Where is Diego?"
            )) if not diego else None
        )
    ) 

@rt('/post/{id}')
def get(id:int):
    post = get_post_by_id(id)
    
    return Body()(
        Div(cls='px-5 bg-base-100 min-h-screen w-full bg-[radial-gradient(#979797_1px,transparent_1px)] [background-size:24px_24px]')(
            title_bar(), 
            NotStr(post.get('content'))
            
        ),
    )    

@rt('/')
def get():
    return Body()(
        Div(cls='px-5 bg-base-100 min-h-screen w-full bg-[radial-gradient(#979797_1px,transparent_1px)] [background-size:24px_24px]')(
            title_bar(),
            Form()(
            Div(cls='mx-auto font-sans antialiased h-full w-full')(
                grid()(*[Div(cls=f'fade-in-{random.choice(["one","two","three","four","five","six"])}')(card(**i)) for i in get_posts()]),
                Input(id='p', name='p', value=1, type='hidden'),
                Div(cls='h-10', hx_target='#content', hx_trigger='revealed', hx_swap='beforeend', hx_post='/scroll', hx_on__before_request="this.remove();")
                )
            )                 
        ),
        Script(src='/static/js/touch.js'),      
    )
    
@rt('/scroll')
def post(p:list[int]):
    # this is a workaround because I can't figure out how to send just a single number
    # or even delete the input after request?
    p=max(p)
    return (
        ([Div(cls=f'fade-in-{random.choice(["one","two","three","four","five","six"])}')(card(**i)) for i in get_posts(page=p+1)]),
        Input(name='p', value=p+1, type='hidden'),
        Div(hx_target='#content', hx_trigger='revealed', hx_swap='beforeend', hx_post='/scroll', hx_on__before_request="this.remove();")      
    )

@rt('/test')
def post():
    print('hi')


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
    



