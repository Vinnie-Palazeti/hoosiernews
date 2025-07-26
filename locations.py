import sqlite3
from dataclasses import asdict
from fasthtml.common import *

def create_locations_table(db_path):
    """Create the diego_locations table if it doesn't exist"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS diego_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location TEXT NOT NULL,
        date_visited TEXT NOT NULL,
        proof TEXT,
        latval REAL NOT NULL,
        lonval REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()   
    

def truncate_locations_table(db_path):
    """
    Delete all rows from the diego_locations table
    
    Args:
        db_path: Path to the SQLite database file
    
    Returns:
        int: Number of rows deleted
    """
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Execute DELETE statement
    cursor.execute("DELETE FROM diego_locations")
    
    # Get number of rows deleted
    rows_deleted = cursor.rowcount
    
    # Commit and close
    conn.commit()
    conn.close()
    
    return rows_deleted    
   
    
def insert_location(db_path, location_data):
    """
    Insert a DiegoLocation object into SQLite database
    
    Args:
        db_path: Path to the SQLite database file
        location_data: DiegoLocation instance to insert
    """
    # Convert dataclass to dictionary
    data_dict = asdict(location_data)
    
    # Convert date object to string for SQLite
    data_dict['date_visited'] = data_dict['date_visited'].isoformat()
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Simple insert statement
    query = '''
    INSERT INTO diego_locations 
    (location, date_visited, proof, latval, lonval) 
    VALUES 
    (?, ?, ?, ?, ?)
    '''
    # Execute with values from dataclass
    cursor.execute(query, (
        data_dict['location'],
        data_dict['date_visited'],
        data_dict['proof'],
        data_dict['latval'],
        data_dict['lonval']
    ))
    
    # Commit and close
    conn.commit()
    conn.close()
    
    return cursor.lastrowid


## just put errors underneath
def diego_form(errors=None):
    return Div(cls='mx-auto w-full max-w-lg p-4')(
            Form(id='haveyouseen')(
                H2('Have you seen Diego?', cls='text-3xl backdrop-blur-sm pb-2'),
                Fieldset(cls='fieldset  w-full max-w-lg bg-base-100 border border-base-500 p-4 rounded-box text-lg')(
                    Legend('Details', cls='fieldset-legend'),
                    Label('Location Name', cls='fieldset-label'),
                    Input(type='text', placeholder='Antarctica', name ='location', cls='input w-full'),
                    Label('Date', cls='fieldset-label'),
                    Input(type='date', name='date_visited', cls='input w-full'),
                    Label('Proof', cls='fieldset-label'),
                    Input(type='text', placeholder='Link', name='proof', cls='input w-full'),
                    Div(cls='flex flex-row gap-4 w-full pt-2')( 
                        Div(cls='w-1/2')(
                            Label('Latitude', cls='fieldset-label'),
                            Div(id='latitude')
                        ),
                        Div(cls='w-1/2')(
                            Label('Longitude', cls='fieldset-label'),
                            Div(id='longitude')
                        )
                    ),
                    Input(type='hidden', name='latval', id='latval'),
                    Input(type='hidden', name='lonval', id='lonval'),
                    Div(cls='mt-6')(
                        Button('Submit', 
                            hx_post='/diego-location',
                            hx_target='#haveyouseen', 
                            hx_swap='innerHTML',
                            cls='btn btn-primary btn btn-primary px-8 border-2 border-base-300 shadow-md')
                    ),
                    errors             
                )
            )
        )  