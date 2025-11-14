from fasthtml.common import *
from svgs import svgs
import random
import sqlite3
from datetime import date, datetime
from dataclasses import dataclass
from locations import *
from typing import Any
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from attribution import attribution_before
import os
from dotenv import load_dotenv
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import json
import uuid
load_dotenv()

## search!
# https://www.purdueexponent.org/
# http://mywabashvalley.com/news/local-news/
# https://indianacitizen.org/
# https://fox59.com/
# https://www.journalgazette.net/local/


BASE_DIR = Path(__file__).resolve().parent
model = SentenceTransformer( "all-MiniLM-L6-v2")
index = faiss.read_index(str(BASE_DIR / "static" / "data" / "indiana_budget.index"))
budget_data =  (
    pd.read_parquet(BASE_DIR / "static" / "data" / "indiana_budget.parquet")
    .drop(columns=['row_indices'])
    .rename(columns={'Total Amount':'Amount'})   
)


@dataclass
class DiegoLocation:
    location: str
    date_visited: date
    proof: str
    latval: float
    lonval: float
    
    
def theme_script():
    """
    Generates the client-side script to manage theme persistence in localStorage.
    This should be placed in the <head> of your HTML to prevent FOUC (Flash of Unstyled Content).
    """
    js_code = """
    (function() {
        // Part 1: Apply the theme immediately on page load
        // This part runs before the DOM is fully loaded to prevent the page from flashing with the wrong theme.
        try {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                // If a theme is saved, set it on the root <html> element.
                // DaisyUI reads this attribute to apply the correct theme.
                document.documentElement.setAttribute('data-theme', savedTheme);
            }
        } catch (e) {
            console.error('Could not access localStorage for theme.', e);
        }

        // Part 2: Update the toggle state and save changes
        // This part waits for the DOM to be ready before trying to find the checkbox.
        document.addEventListener('DOMContentLoaded', () => {
            const themeController = document.querySelector('.theme-controller');
            if (!themeController) return;

            // Sync the checkbox's 'checked' state with the current theme.
            // The value of the checkbox is 'dark'. If the current theme is 'dark', it should be checked.
            const currentTheme = document.documentElement.getAttribute('data-theme');
            if (currentTheme === themeController.value) {
                themeController.checked = true;
            }

            // Add an event listener to the checkbox.
            themeController.addEventListener('change', function() {
                let newTheme;
                if (this.checked) {
                    // When checked, the theme is the checkbox's value (e.g., 'dark').
                    newTheme = this.value;
                } else {
                    // When unchecked, you might want to revert to a default theme, like 'light'.
                    // DaisyUI's default behavior is to remove the data-theme attribute.
                    // We will store 'light' as our default.
                    newTheme = 'light';
                }
                
                // Apply the new theme to the <html> element.
                document.documentElement.setAttribute('data-theme', newTheme);
                
                // Save the new theme to localStorage.
                try {
                    localStorage.setItem('theme', newTheme);
                } catch (e) {
                    console.error('Could not save theme to localStorage.', e);
                }
            });
        });
    })();
    """
    return Script(js_code)

headers=[
    theme_script(), 
    Meta(charset='UTF-8'),
    Meta(name='viewport', content='width=device-width, initial-scale=1.0, maximum-scale=1.0'),

    ### testing... ###
    Script(src="https://unpkg.com/htmx.org@next/dist/htmx.min.js"),
    Script(src='https://cdn.jsdelivr.net/npm/theme-change@2.5.0/index.min.js'),
    Link(href='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css', rel='stylesheet'), 
    Link(href='https://cdn.jsdelivr.net/npm/daisyui@5', rel='stylesheet', type='text/css'),
    Script(src='https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4'),
    ##################
    
    # Script(src="/static/js/htmx.min.js"),
    Script(src="/static/js/surreal.js"),
    # Script(src='/static/js/theme-change.js'),
    # # I had to move the market images to the static/css file because I believe the leaflet.min.css went looking for them there...
    # Link(href='/static/css/leaflet.min.css', rel='stylesheet'),
    # ## pathing was messed up. static file server was not working correctly
    # ## still unsure if the tailwind exe file will build this correctly while nested in the static/css/... 
    # Link(rel="stylesheet", href="/static/css/output-v1.css", type="text/css"), 
    # Link(rel="stylesheet", href="/static/css/output.css", type="text/css"), 
    
    Link(rel="stylesheet", href="/static/css/custom.css", type="text/css"), 
    Link(rel='icon', href='/static/assets/state.svg', type='image/svg+xml'),    
    
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

app = FastHTMLWithLiveReload(title='Hoosier News', before=attribution_before, hdrs=headers, default_hdrs=False)
# app = FastHTML(title='Hoosier News', before=attribution_before, hdrs=headers, default_hdrs=False)
app.add_middleware(SessionMiddleware, secret_key=os.environ['SESSION_SECRET'])

rt = app.route  
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
        SELECT id, title, summary, url, site, email, ROW_NUMBER() OVER (PARTITION BY site ORDER BY created_at DESC ) AS rn
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
    return (
        Label(cls='swap swap-rotate text-base-content')(
            Input(type='checkbox', value='dark', cls='theme-controller'),
            # lesson here is something like I can't define svgs in this main file? maybe it is because of the import from svgs?
            svgs['Sun'],
            svgs['Moon'],
        )
    )
    
        
def title_bar(req: Request={}, sites:bool=True):    
    return (
        Div(cls='mx-auto max-w-screen-lg w-full flex flex-col sm:flex-row items-center justify-between pt-6 pb-2 gap-2')(
            Div(cls='flex items-center')(
                A(href='/', cls='flex items-center')(
                    P('Hoosier News', cls='pl-2 sm:pl-0 text-3xl xs:text-4xl sm:text-5xl md:text-6xl text-base-content leading-none m-0 backdrop-blur-sm whitespace-nowrap')),
                Div(cls='pl-2')(svgs['indiana']),
            ), 
            Div(cls='flex items-center gap-2')(
                toggle(),
                site_filter(req=req) if sites else None,
                Button('Apps', popovertarget='popover-2', style='anchor-name:--anchor-2', type='button', cls='btn btn-sm sm:btn-md lg:btn-lg backdrop-blur-sm m-0'),
                    Ul(popover=True, id='popover-2', style='position-anchor:--anchor-2',cls='dropdown menu rounded-box bg-base-100 shadow-sm p-2 max-h-96 overflow-auto')(
                        Li(A(href='/where-is-diego', cls='text-lg p-3')("Where is Diego?")),
                        Li(A(href='/budget',cls='text-lg p-3')('Indiana Budget'))
                    )                
                )
            ),
            
        )
    

def site_filter(req: Request):
    all_sites = list_sites()
    selected_sites = req.session.get('sites', all_sites)
    return Div(cls='flex items-center gap-2')(
        Button('Sites', popovertarget='popover-1', style='anchor-name:--anchor-1', type='button', cls='btn btn-sm sm:btn-md lg:btn-lg backdrop-blur-sm m-0'),
        Ul(popover=True, id='popover-1', style='position-anchor:--anchor-1',
            # key bits: block + columns-2 + wider + scrollable
            cls='dropdown menu rounded-box bg-base-100 shadow-sm p-2 max-h-96 overflow-auto')(
            Div(cls='grid grid-cols-2 gap-2')(
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
        ))
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

def fmt_amount(x: float) -> str:
    if x < 0:
        return f"(${abs(x):,.2f})"
    return f"${x:,.2f}"
    
def format_table_total(total, swap_oob:str=None):
    return (
        Tr(cls="border-t-2 border-base-300 bg-base-200 font-semibold", 
           id='total_row',  hx_swap_oob=swap_oob)(
            Td("Total", cls="text-base-content"),
            Td("", cls="text-base-content"),  # empty cells to align
            Td("", cls="text-base-content"),
            Td("", cls="text-base-content"),
            Td("", cls="text-base-content"),
            Td(fmt_amount(total), cls="text-base-content text-right font-mono"),
        ),
    )

def format_table_rows(rows:list,batch_id: str | None = None):
    batch_attr = {"data-id": batch_id} if batch_id else {}
    return (
            [
                Tr(cls="hover:bg-base-300", **batch_attr)(
                    Td(row["BU Name"], cls="text-base-content"),
                    Td(row["PS Fund Description"], cls="text-base-content"),
                    Td(row["ACFR Name"], cls="text-base-content"),
                    Td(row["Year"], cls="text-base-content"),
                    Td(row["Row Count"], cls="text-base-content"),
                    Td(fmt_amount(row["Amount"]), cls="text-base-content text-right font-mono"),
                )
                for row in rows
            ] if rows else []
    )
    
@rt('/delete-batch')
def post(batch_id:str, batch_total:str, current_total:str, current_idx:str):
    
    updated_total = float(current_total) - float(batch_total)
    current_idx = json.loads(current_idx)
    current_idx.pop(batch_id)
    
    return (
        Script(f'document.querySelectorAll(\'tr[data-id="{batch_id}"]\').forEach(e => e.remove());'),
        format_table_total(updated_total, swap_oob='outerHTML'),
        Input(
            type='hidden',
            id='current_total',
            name='current_total',
            value=updated_total,
            hx_swap_oob='outerHTML'
        ),
        Input(
            type='hidden',
            id='current_idx',
            name='current_idx',
            value=json.dumps(current_idx),
            hx_swap_oob='outerHTML'
        ),
    )
  
def search_tag(text, batch_id: str, batch_total:str):
    return Div(cls='p-2')(
        Div(
            hx_post='/delete-batch',
            hx_target='this',
            hx_swap='outerHTML',
            hx_vals={'batch_id':batch_id, 'batch_total':batch_total},
            hx_on__after_swap='this.remove()',
            cls=(
                'group relative inline-flex items-center gap-1 text-xs font-medium '
                'text-primary-content focus:outline-none focus:ring-2 '
                'focus:ring-offset-2 focus:ring-primary/50 rounded-lg'
            )
        )(
            Span(cls='absolute inset-0 rounded-lg bg-primary/80 translate-y-[2px] transition-transform'),
            Span(
                cls=(
                    'relative flex items-center gap-1 rounded-lg border border-primary '
                    'bg-primary px-2 py-1 transition-transform group-hover:-translate-y-[2px]'
                )
            )(
                Span(text, cls="whitespace-nowrap"),
                svgs.get("close")
            )
        )
    )


@rt('/budget-search')
async def post(req: Request, search_input:str, search_type:str, current_idx:str, current_total:str, num_entries:int=100):
    current_idx = json.loads(current_idx) 
    current_flat_idx = [item for sublist in current_idx.values() for item in sublist]
    current_total=float(current_total or 0)
        
    if search_input.strip().replace(' ',"") == "":
        return (
        format_table_total(current_total),
        Div(id="alerts-layer", hx_swap_oob="afterbegin")(
            Div(cls='alert alert-error')(
                Span('Input text!'),
                Script("""
                    (async (el = me()) => {
                    await sleep(2000) 
                    me(el).fadeOut() 
                    })()
                """)
            ),
        )            
        )
        
    if search_type not in ['keyword','semantic']:
        return None
    
    if search_type == 'semantic':
        q_emb = model.encode([search_input], normalize_embeddings=True).astype("float32")
        scores, idxs = index.search(q_emb, num_entries+len(current_flat_idx)) # make room for current found.. faiss index cannot exclude
        idxs, scores = idxs[0], scores[0]
        filtered = [(i, s) for i, s in zip(idxs, scores) if i not in set(current_flat_idx)] # filter out current idxs
        results = []
        new_total = 0
        new_idx = [int(i[0]) for i in filtered]
        for i, s in filtered:
            row = budget_data.iloc[i].to_dict()
            new_total += row.get('Amount')
            results.append({"rank": len(results) + 1, "score": round(float(s), 4)} | row)
    else:
        ## filter indexes
        results = budget_data.loc[lambda df: (~df.index.isin(current_flat_idx)) & (df['Text'].str.lower().str.contains(search_input))].iloc[:num_entries]
        new_idx=results.index.to_list()
        new_total = results['Amount'].sum()
        results=results.to_dict(orient='records')
        
    batch_id = f"batch-{uuid.uuid4().hex[:8]}"
    new_idx = current_idx | {batch_id:new_idx}
    updated_total = new_total + current_total
    
    return (
        *format_table_rows(results, batch_id),
        format_table_total(updated_total),

        Input(
            type='hidden',
            id='current_total',
            name='current_total',
            value=updated_total,
            hx_swap_oob='outerHTML'
        ),
        
        Input(
            type='hidden',
            id='current_idx',
            name='current_idx',
            value=json.dumps(new_idx),
            hx_swap_oob='outerHTML'
        ),
        
        Div(id='search-tags', hx_swap_oob='afterbegin')(
            search_tag(search_input, batch_id, new_total)
        ) if results else None,
        
        
        Div(id="alerts-layer", hx_swap_oob="afterbegin")(
            Div(cls='alert alert-error')(
                Span('No results found!'),
                Script("""
                    (async (el = me()) => {
                    await sleep(2000) 
                    me(el).fadeOut() 
                    })()
                """)
            ),
        ) if not results else None
    )

@rt('/budget')
async def get(req: Request):
    
    current_total=0.0
    current_idx = {}
    rows = {}
    table = Table(cls="table bg-base-100 rounded-xl shadow-lg w-full")(
        Thead()(
            Tr()(
                Th("BU Name", cls="text-base-content font-semibold"),
                Th("PS Fund Description", cls="text-base-content font-semibold"),
                Th("ACFR Name", cls="text-base-content font-semibold"),
                Th("Year", cls="text-base-content font-semibold"),
                Th("Num. Entries", cls="text-base-content font-semibold"),
                Th("Amount", cls="text-base-content font-semibold"),
            )   
        ),
        Tbody()(*format_table_rows(rows), format_table_total(current_total)),  
    )
    
    search_input = Label(cls="input input-bordered flex items-center gap-1 w-full")(
        svgs.get("mag_glass"),
        Input(type="text", required=True, name="search_input", placeholder="Search", cls="grow")
    )
    
    search_controls = Div(
        cls="flex flex-col items-start gap-2 w-full sm:w-auto"
    )(
        # Row 1: Radios + number input
        Div(cls="flex flex-row items-center gap-2 w-full sm:w-auto")(
            Div(cls="join")(
                Div(cls='tooltip', data_tip='Find rows with your exact search text.')(
                    Input(
                    cls="join-item btn btn-sm",
                    type="radio",
                    name="search_type",
                    value="keyword",
                    aria_label="Keyword",
                    checked=True
                )),
                Div(cls='tooltip', data_tip='Find rows with similar meaning to your search text.')(
                    Input(
                    cls="join-item btn btn-sm",
                    type="radio",
                    name="search_type",
                    value="semantic",
                    aria_label="Semantic"
                )),
            ),
            Div(cls='tooltip', data_tip='The number of rows to return.')(
                Input(
                    type="number",
                    min="1",
                    max="200",
                    value="50",
                    name="num_entries",
                    cls="input input-bordered input-sm w-20"
                )
            )
        ),

        # Row 2: Full-width search button
        Button(
            "Search",
            cls="btn btn-primary btn-sm w-full",   # now appropriate
            type="submit",
            hx_post="/budget-search",
            hx_target="#total_row",
            hx_swap="outerHTML",
        )
    )

    
    search_grid = Div(
        cls="grid grid-cols-1 sm:grid-cols-[1fr_auto] items-center gap-3"
    )(
        search_input,
        search_controls
    )
    
    search_form = Form(id="search-form", cls="w-full")(
        search_grid, 
        Input(type='hidden', id='current_total', name='current_total', value=current_total),
        Input(type='hidden', id='current_idx', name='current_idx', value=json.dumps(current_idx)),
    ) 
    return Body()(
        Div(cls="px-5 bg-base-100 min-h-screen w-full bg-[radial-gradient(#979797_1px,transparent_1px)] [background-size:24px_24px]")(
            Form(id="feed")(
                title_bar(sites=False),
                Div(id="alerts-layer", cls='toast toast-top toast-end fixed z-[9999]'),
                Div(cls="mx-auto font-sans antialiased h-full w-full")(
                    Div(cls="mx-auto max-w-screen-lg space-y-3")(
                        search_form,
                        Div(id="search-tags", cls='flex flex-row'),
                        table
                    )
                )
            )
        ),
    )
  
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
                title_bar(req=req),
                H1('Where in the world is Diego Morales?', cls='text-5xl py-2 '),
                Div(id='map', cls='w-full h-[500px]'),
                diego_form()
  
            )    
        ),
        Script(src='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'),
        Script(src='/static/js/leaf.js'),
    )


@rt('/delete-test')
def post(batch_id:str):
    ## but I also need to supply the BATCH SUM, which I have! then I 
    return Script(f'document.querySelectorAll(\'tr[data-id="{batch_id}"]\').forEach(e => e.remove());')

@rt('/test')
def get():
    return (
        Form(id='delete-form', cls='p-5')(
            Table()(
                Thead()(
                    Tr(
                        Th('Select'),
                        Th('ID'),
                        Th('Data')
                    )
                ),
                Tbody()(
                    Tr(data_id='gs10')(
                        Td('101'),
                        Td('Item A')
                    ),
                    Tr(data_id='gs10')(
                        Td('103'),
                        Td('Item C')
                    ),                
                    Tr(data_id='fasd3')(
                        Td('102'),
                        Td('Item B')
                    )
                )
            ),
            Div(
                'Delete Rows',
                cls='btn',
                hx_post='/delete-test',
                hx_swap='outerHTML',
                hx_target='this',
                hx_vals={'batch_id':"fasd3"}
            )
        )
    )

    
    

@rt('/diego-location')
def post(d:DiegoLocation):
    create_locations_table("data.db")
    location_id = insert_location("data.db", d)
    print(f"Inserted location with ID: {location_id}") 
    return H1('Thank you for spotting Diego!', cls='text-5xl')

if __name__ == "__main__":
    # import uvicorn
    # uvicorn.run("main:app", host="127.0.0.1", port=8000)
    serve(host="127.0.0.1", port=8000)
    



