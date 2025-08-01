from fasthtml.svg import *
from fasthtml.common import ft_hx, Style

svgs = {
    
    'indiana': Svg(xmlns="http://www.w3.org/2000/svg",fill="#FFFFFF", viewBox="0 0 width height", width='80px' ,height='80px',preserveAspectRatio="xMidYMid meet", stroke="#000")(
        Path(stroke_width="2.5", d="M46.24 2.16v-.8l-25.04-.08-2.4 1.28-2.96.8-1.6-.32-1.24-1.04-.88 38.64-1.12.56.16 1.92-.8 1.44 1.6 2.64-.24 1.36.48 2L10 53.2l.08 1.28-1.52.48.08.56-1.12 2.08-.24-.32-.48.64-.48-.32-.72 1.12.72 1.04-1.2 1.04.8.32-.88.4v2.4L4 64.16l1.04 1.04-.88.32L6 66l.56-.72-.24-1.12.24-.4 1.44.56 1.6-.16v1.12h.64l.48-.96.28-.32 1.92-.4 3.36 1.76.48.8 1.36-2.16 2.56-1.2.48 1.2 1.6.4-.08.48.4.4.48-1.04.88-.32.08-1.84.8-.4.3-.6 1.28-.8.1.2.32 1.52 2.72 1.76 1.52-1.12.32-2.48 1.04-1.76.8.32 1.44-.72.8-2.4.96-.16 1.28-1.52-.48-2.64 2.48-.24 1.04.64 3.04-1.68h1.76l.16-1.52-1.12-.32.72-1.12-.72-1.36.72-.56z")
    ),
    
    'moon': Svg(
        cls='w-5 h-5',
        # cls='absolute inset-0 h-full w-full transition-opacity duration-500 ease-in-out', 
        xmlns='http://www.w3.org/2000/svg', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round')(
        Path(d='M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z')
    ),
    
    'sun': Svg(
        cls='w-5 h-5',
        # cls='absolute inset-0 h-full w-full transition-opacity duration-500 ease-in-out',
        xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round')(
        Circle(cx='12', cy='12', r='4'),
        Path(d='M12 2v2'),
        Path(d='M12 20v2'),
        Path(d='m4.93 4.93 1.41 1.41'),
        Path(d='m17.66 17.66 1.41 1.41'),
        Path(d='M2 12h2'),
        Path(d='M20 12h2'),
        Path(d='m6.34 17.66-1.41 1.41'),
        Path(d='m19.07 4.93-1.41 1.41')
    ),
        
    
    'Hoosier Ag Today': Svg(cls="size-10 sm:size-12", version='1.1', viewbox='0 0 512 512', fill='currentColor', stroke='currentColor')(
        ft_hx('g', id='SVGRepo_bgCarrier', stroke_width='2.5'),
        ft_hx('g', id='SVGRepo_tracerCarrier', stroke_linecap='round', stroke_linejoin='round'),
        ft_hx('g', id='SVGRepo_iconCarrier')(
            Style('.st0{fill:currentColor;}', type='text/css'),
            ft_hx('g', 
                Path(d='M441.012,266.373c38.044-55.965,79.444-147.642,19.276-208.446c-61.274-61.942-155.754-18.852-211.81,19.124 c0.068-33.796-9.672-60.487-26.07-77.052c-6.748,12.656-13.285,43.907-59.479,89.601c-53.413,52.852-117.74,119.898-137.75,160.208 C7.591,285.225-16.699,375.365,38.426,448.773l-24.851,24.843l34.985,34.993l25.01-25.003 c52.996,38.318,122.079,35.379,182.482,5.961c54.662-26.63,219.02-192.738,251.566-204.448 C492.492,265.828,461.818,264.601,441.012,266.373z M461.03,177.332l-24.366-24.631l30.774-30.44 C469.709,140.014,466.862,158.852,461.03,177.332z M443.806,74.242c8.96,9.066,14.906,19.17,18.579,29.902l-37.098,36.689 L377.01,92.048l37.098-36.704C424.803,59.124,434.839,65.19,443.806,74.242z M233.39,234.116l36.166-35.772l48.277,48.792 l-36.166,35.78L233.39,234.116z M269.996,294.458l-36.173,35.78l-48.27-48.792l36.166-35.78L269.996,294.458z M281.228,186.792 l36.166-35.772l48.277,48.784l-36.166,35.78L281.228,186.792z M329.074,139.462l36.166-35.766l48.27,48.785l-36.174,35.772 L329.074,139.462z M396.036,50.103l-30.766,30.44l-24.373-24.647C359.446,50.27,378.314,47.626,396.036,50.103z M324.204,62.198 l29.221,29.546l-36.166,35.78l-40.794-41.249C290.901,77.4,307.208,68.781,324.204,62.198z M246.728,106.908 c4.802-3.62,10.097-7.422,15.868-11.3L305.518,139l-36.166,35.78l-31.19-31.516C242.131,130.585,244.979,118.436,246.728,106.908z M231.792,160.17l26.176,26.456l-36.159,35.772l-12.99-13.133C218.333,192.269,225.915,175.878,231.792,160.17z M200.284,223.844 c0,0,0.007-0.022,0.015-0.037l10.18,10.293l-29.812,29.494C185.62,250.786,191.998,237.486,200.284,223.844z M174.184,403.245 c0,0-0.296-0.704-0.757-2.052l1.901,1.916C174.964,403.162,174.54,403.184,174.184,403.245z M166.087,360.898 c-1.47-17.526-0.901-39.9,5.105-65.236l2.666-2.643l48.27,48.808l-37.878,37.446L166.087,360.898z M205.382,400.632l-9.392-9.498 l37.87-37.454l35.734,36.136C245.728,397.375,223.514,399.511,205.382,400.632z M312.154,370.071 c-8.718,5.278-17.405,9.603-25.972,13.11l-40.454-40.908l36.166-35.78l46.755,47.27 C323.272,359.073,317.751,364.542,312.154,370.071z M340.321,342.205l-46.755-47.255l36.166-35.78l46.763,47.27 C366.589,316.226,354.144,328.542,340.321,342.205z M390.545,292.504c-0.727,0.735-1.591,1.591-2.386,2.37l-46.755-47.247 l36.173-35.787l42.93,43.4C408.64,272.478,397.279,285.861,390.545,292.504z M389.159,200.206l36.174-35.788l29.22,29.547 c-6.778,16.928-15.564,33.137-24.608,47.474L389.159,200.206z', cls='st0')
            )
        )
    ),
    
    'IBJ':Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z'),
        Path(d='M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2'),
        Path(d='M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2'),
        Path(d='M10 6h4'),
        Path(d='M10 10h4'),
        Path(d='M10 14h4'),
        Path(d='M10 18h4')
    ),
    
    'Jesse Brown': Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
    Path(d='M18 11.5V9a2 2 0 0 0-2-2a2 2 0 0 0-2 2v1.4'),
    Path(d='M14 10V8a2 2 0 0 0-2-2a2 2 0 0 0-2 2v2'),
    Path(d='M10 9.9V9a2 2 0 0 0-2-2a2 2 0 0 0-2 2v5'),
    Path(d='M6 14a2 2 0 0 0-2-2a2 2 0 0 0-2 2'),
    Path(d='M18 11a2 2 0 1 1 4 0v3a8 8 0 0 1-8 8h-4a8 8 0 0 1-8-8 2 2 0 1 1 4 0')
    ),
    


    
    
    "IndyPolitics.Org": Svg(xmlns='http://www.w3.org/2000/svg', width='32', height='32', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2.5', stroke_linecap='round', stroke_linejoin='round', cls="size-10 sm:size-12")(
        Path(d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'),
        Path(d='M8 10h.01'),
        Path(d='M12 10h.01'),
        Path(d='M16 10h.01')
    ),
    
    "Indiana Capital Chronicle": Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='M12 7v14'),
        Path(d='M16 12h2'),
        Path(d='M16 8h2'),
        Path(d='M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z'),
        Path(d='M6 12h2'),
        Path(d='M6 8h2')
    ),
    
    "Coffee": Svg(cls="size-10 sm:size-12", xmlns='http://www.w3.org/2000/svg', width='32', height='32', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2.5', stroke_linecap='round', stroke_linejoin='round')(
        Path(d='M10 2v2'),
        Path(d='M14 2v2'),
        Path(d='M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1'),
        Path(d='M6 2v2')
    ),
    "Indianapolis Recorder":Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='m11 7.601-5.994 8.19a1 1 0 0 0 .1 1.298l.817.818a1 1 0 0 0 1.314.087L15.09 12'),
        Path(d='M16.5 21.174C15.5 20.5 14.372 20 13 20c-2.058 0-3.928 2.356-6 2-2.072-.356-2.775-3.369-1.5-4.5'),
        Circle(cx='16', cy='7', r='5')
    ),
    
    'Mirror Indy': Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='M5 17H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-1'),
        Path(d='m12 15 5 6H7Z')
    ),
    
    'IndyStar':Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z')
    ),
    'Tribstar':Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='M10.268 21a2 2 0 0 0 3.464 0'),
        Path(d='M22 8c0-2.3-.8-4.3-2-6'),
        Path(d='M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326'),
        Path(d='M4 2C2.8 3.7 2 5.7 2 8')
    ),
    'YouAreCurrent':Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8'),
        Path(d='M21 3v5h-5'),
        Path(d='M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16'),
        Path(d='M8 16H3v5')
    ),
    "Indiana Public Media":Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Rect(width='18', height='18', x='3', y='3', rx='2'),
        Path(d='M7 7v10'),
        Path(d='M11 7v10'),
        Path(d='m15 7 2 10')
    ),
    "WRTV":Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='m17 2-5 5-5-5'),
        Rect(width='20', height='15', x='2', y='7', rx='2')
    ),
    "NWI Times": Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='M4.9 16.1C1 12.2 1 5.8 4.9 1.9'),
        Path(d='M7.8 4.7a6.14 6.14 0 0 0-.8 7.5'),
        Circle(cx='12', cy='9', r='2'),
        Path(d='M16.2 4.8c2 2 2.26 5.11.8 7.47'),
        Path(d='M19.1 1.9a9.96 9.96 0 0 1 0 14.1'),
        Path(d='M9.5 18h5'),
        Path(d='m8 22 4-11 4 11')
    ),
    "Courier & Press":Svg(xmlns='http://www.w3.org/2000/svg', width='24', height='24', viewbox='0 0 24 24', fill='none', stroke='currentColor', stroke_width='2', stroke_linecap='round', stroke_linejoin='round', cls='size-10 sm:size-12')(
        Path(d='M12 3V2'),
        Path(d='m15.4 17.4 3.2-2.8a2 2 0 1 1 2.8 2.9l-3.6 3.3c-.7.8-1.7 1.2-2.8 1.2h-4c-1.1 0-2.1-.4-2.8-1.2l-1.302-1.464A1 1 0 0 0 6.151 19H5'),
        Path(d='M2 14h12a2 2 0 0 1 0 4h-2'),
        Path(d='M4 10h16'),
        Path(d='M5 10a7 7 0 0 1 14 0'),
        Path(d='M5 14v6a1 1 0 0 1-1 1H2')
    )
    
}


