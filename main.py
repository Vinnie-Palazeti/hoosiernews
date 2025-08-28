from fasthtml.common import *
from svgs import svgs
import random
import sqlite3
from datetime import date
from dataclasses import dataclass
from locations import *
from typing import List, Dict, Optional, Any
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv
load_dotenv()


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
    # I had to move the market images to the static/css file because I believe the leaflet.min.css went looking for them there...
    Link(href='/static/css/leaflet.min.css', rel='stylesheet'),
    
    Link(rel='icon', href='/static/assets/state.svg', type='image/svg+xml'),    
    
    ## css
    ## pathing was messed up. static file server was not working correctly
    ## still unsure if the tailwind exe file will build this correctly while nested in the static/css/... 
    Link(rel="stylesheet", href="/static/css/output.css", type="text/css"), 
    Link(rel="stylesheet", href="/static/css/custom.css", type="text/css"), 
    
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
    ),
    Script(_async=True, src=f'https://www.googletagmanager.com/gtag/js?id={os.getenv("GOOGLE_ANALYTICS_ID")}'),
    Script(
        f"""
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{os.getenv("GOOGLE_ANALYTICS_ID")}');        
    """)
    
]

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
app.add_middleware(SessionMiddleware, secret_key=os.environ['SESSION_SECRET'])

@rt("/static/{full_path:path}")
def static(full_path: str):
    return FileResponse(f"static/{full_path}")

def get_posts(
    page: int = 0,
    per_site: int = 2,
    sites: list[str] | None = None,
    db_path: str = "data.db",
) -> list[dict[str, Any]]:
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
    
    params: list[Any] = []
    where_clause = ""
    if sites is not None:
        if len(sites) == 0:
            return []
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

def list_sites(db_path: str = "data.db") -> list[str]:
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute("SELECT DISTINCT site FROM posts ORDER BY site")
        return [r[0] for r in cur.fetchall()]
    finally:
        con.close()

def card(title, summary=None, site=None, url=None, email=None, id=None, target='_blank', **kwargs):
    if email:
        url = f'/post/{id}'
        target=None
    return (
        A(href=url, target=target, cls="group relative block h-52 sm:h-52 lg:h-60")(
            # background
            Span(cls=f"absolute inset-0 border-4 border-dashed"),

            ## background white here is for the card bg-white 
            Div(cls="bg-base-100 relative flex h-full transform items-end border-4 transition-transform group-hover:-translate-x-2 group-hover:-translate-y-2 group-[.touch-active]:-translate-x-2 group-[.touch-active]:-translate-y-2")(
                
                ## this is what shows by default:
                Div(cls='h-9/10 p-2 !pt-0 sm:p-6 lg:p-8 transition-opacity group-hover:absolute group-hover:opacity-0 group-[.touch-active]:absolute group-[.touch-active]:opacity-0')(
                    Div(cls='flex flex-row items-center gap-4')(svgs.get(site), H1(site, cls='font-medium text-2xl text-wrap-2')),
                    Div(cls='mt-2')(H2(cls="font-medium text-xl sm:line-clamp-3 lg:line-clamp-4 ")(title))
                ),
                # this is what shows when hovered:
                ### if I make the hovered text smaller.. then it should be ok
                Div(cls="absolute p-2 sm:p-8 lg:p-8 opacity-0 transition-opacity group-hover:relative group-hover:opacity-100 group-[.touch-active]:relative group-[.touch-active]:opacity-100")(
                    H2(cls="font-medium text-xl lg:text-2xl")(site),
                    P(cls="mt-2 text-md sm:text-lg line-clamp-3")(summary),
                    P(cls='mt-4 font-bold')('Read more')
                )
            )
        )                
    )


def toggle():
    ## tried to get a post call to swap the svgs.. couldn't get it to work
    return Div(cls='m-0 flex flex-row gap-2 backdrop-blur-sm')(
        Span()(svgs['sun']),
        Div(cls='inline-block w-10')(
            Span(data_toggle_theme='dark', data_act_class='pl-4', 
                 cls='border rounded-full border-base-700 flex items-center cursor-pointer w-10 transition-all duration-300 ease-in-out pl-0')(
                Span(cls='rounded-full w-3 h-3 m-1 bg-gray-700')
            )
        ),
        Span()(svgs['moon'])
    )
    
def title_bar(req: Request={}, diego=None):
    return (
        Div(cls='mx-auto max-w-screen-lg w-full flex flex-col sm:flex-row items-center justify-between pt-6 pb-2 gap-2')(
            Div(cls='flex items-center')(
                A(href='/', cls='flex items-center')(
                    P('Hoosier News', cls='pl-2 sm:pl-0 text-3xl xs:text-4xl sm:text-5xl md:text-6xl text-base-content leading-none m-0 backdrop-blur-sm whitespace-nowrap')),
                Div(cls='pl-2')(svgs['indiana']),
            ), 
            Div(cls='flex items-center gap-2')(
                toggle(),
                site_filter(req=req) if not diego else None,
                (A(href='/where-is-diego',cls='btn btn-sm sm:btn-md lg:btn-lg backdrop-blur-sm m-0')("Where is Diego?")) if not diego else None
            ),
            
        )
    )

def site_filter(req: Request):
    all_sites = list_sites()
    selected_sites = req.session.get('sites', all_sites)
    return Div(cls='flex items-center gap-2')(
        Button('Sites', popovertarget='popover-1', style='anchor-name:--anchor-1', type='button', cls='btn btn-sm sm:btn-md lg:btn-lg backdrop-blur-sm m-0'),
        Ul(popover=True, id='popover-1', style='position-anchor:--anchor-1',
            # key bits: block + columns-2 + wider + scrollable
            cls=(
                'dropdown menu rounded-box bg-base-100 shadow-sm p-2 '
                'w-[24rem] max-h-96 overflow-auto'
            )
        )(
            *[
                Li(cls='break-inside-avoid mb-2 rounded-lg has-[:checked]:bg-base-300 has-[:checked]:text-base-content')(
                    Label(cls='label gap-2 w-full cursor-pointer')(
                        Input(
                            type='checkbox',
                            name='sites',
                            value=s,
                            checked='checked' if s in selected_sites else None,
                            cls='checkbox peer',
                            hx_post='/filter',
                            hx_trigger='change',
                            hx_target='#content',
                            hx_swap='outerHTML',
                            hx_include='#feed',
                        ),
                        Span(s, cls='px-2 py-1 rounded-lg')
                    )
                )
                for s in all_sites
            ]
        )
    )
    
def scroll_sentinel():
    return Div(
        id='scroll-sentinel',
        cls='h-10',
        hx_target='#content',
        hx_trigger='revealed',
        hx_swap='beforeend',
        hx_post='/scroll',
        hx_include='#feed',
        hx_on__before_request="this.remove();"   # removes itself before the fetch
    )   
 
def grid():
    return Div(id='content', cls='pb-4 gap-4 mx-auto max-w-screen-lg grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))]')

## if I had a user store I could set their defaults..
@rt('/')
async def get(req: Request):
    # Default: all sites
    sites = req.session.get('sites', list_sites())
        
    return Body()(
        Div(cls='px-5 bg-base-100 min-h-screen w-full bg-[radial-gradient(#979797_1px,transparent_1px)] [background-size:24px_24px]')(
            Form(id='feed')(
            title_bar(req),                
            Div(cls='mx-auto font-sans antialiased h-full w-full')(
                grid()(*[Div(cls=f'fade-in-{random.choice(["one","two","three","four","five","six"])}')(card(**i)) for i in get_posts(sites=sites)]),
                Input(id='p', name='p', value=1, type='hidden'),
                Div(cls='h-10', hx_target='#content', hx_trigger='revealed', hx_swap='beforeend', hx_post='/scroll', hx_include='#feed', hx_on__before_request="this.remove();")
                )
            )                 
        ),
        Script(src='/static/js/touch.js'),
    )
    
@rt('/potholes')
async def get(req: Request):
    ## an actually working pothole viewer
    pass
    
    
@rt('/filter')
async def post(req: Request):
    form = await req.form()
    sites = form.getlist('sites')
    
    # save sites in session..
    req.session['sites'] = sites
    
    p = 0
    cards = [
        Div(cls=f'fade-in-{random.choice(["one","two","three","four","five","six"])}')(card(**i))
        for i in get_posts(page=p, sites=sites)
    ]
    # Build children list
    children = [
        *cards,
        Input(id='p', name='p', value=p, type='hidden'),
    ]
    if cards:  # only add sentinel if there was something to load
        children.append(scroll_sentinel())
    else:
        children.append(Div(cls='py-8 text-center text-sm opacity-60')('No posts for these filters.'))
    
    return Div(
        id='content',
        cls='pb-4 gap-4 mx-auto max-w-screen-lg grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))]'
    )(*children)
    
    
@rt('/scroll')
async def post(req: Request):
    form = await req.form()
    sites = form.getlist('sites')
    p_vals = [i for i in form.getlist('p') if i != ''] ## empty values on filter
    try:
        p = max(map(int, p_vals))
    except ValueError:
        print('error!')
        p = 0
    next_page = p + 1
    new_cards = [
        Div(cls=f'fade-in-{random.choice(["one","two","three","four","five","six"])}')(card(**i))
        for i in get_posts(page=next_page, sites=sites)
    ]
    # print(len(new_cards))
    
    if not new_cards:
        # Return nothing -> the old sentinel already removed itself.
        # No new sentinel means no more requests (clean stop).
        return ()

    # Otherwise append new p + a fresh sentinel
    return (
        new_cards,
        Input(name='p', value=next_page, type='hidden'),
        scroll_sentinel(),
    )



    
@rt('/post/{id}')
def get(id:int, req: Request):
    post = get_post_by_id(id)
    
    return Body()(
        Div(cls='px-5 bg-base-100 min-h-screen w-full bg-[radial-gradient(#979797_1px,transparent_1px)] [background-size:24px_24px]')(
            title_bar(req), 
            NotStr(post.get('content'))
            
        ),
    )    

@rt('/where-is-diego')
def get(req:Request):
    return(
        Body()(
            Div(cls='px-5 bg-base-100 min-h-screen w-full bg-[radial-gradient(#979797_1px,transparent_1px)] [background-size:24px_24px]')(
                title_bar(diego=True, req=req),
                H1('Where in the world is Diego Morales?', cls='text-5xl py-2 '),
                Div(id='map', cls='w-full h-[500px]'),
                diego_form()
  
            )    
        ),
        Script(src='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'),
        Script(src='/static/js/leaf.js'),
    )
    

@rt('/diego-location')
def post(d:DiegoLocation):
    create_locations_table("data.db")
    location_id = insert_location("data.db", d)
    print(f"Inserted location with ID: {location_id}") 
    return H1('Thank you for spotting Diego!', cls='text-5xl')
    


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
    



