"""Generate repository-native SVG artwork. All posters are fictional examples."""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parents[1] / 'frontend' / 'public' / 'posters'
OUT.mkdir(parents=True, exist_ok=True)


def save(name, content):
    (OUT / f'{name}.svg').write_text(content, encoding='utf-8')


def poster(bg, art, en, title, label, ink='#293733'):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 780">
    <rect width="600" height="780" fill="{bg}"/>{art}
    <g font-family="Arial,Malgun Gothic,sans-serif" fill="{ink}">
      <text x="40" y="49" font-size="12" letter-spacing="2">CulturePick presents</text>
      <text x="40" y="{145 if label != 'top' else 102}" font-size="50" font-weight="700" letter-spacing="-2">{escape(en)}</text>
      <text x="40" y="{184 if label != 'top' else 141}" font-size="24" font-weight="600" letter-spacing="-1">{escape(title)}</text>
      <path d="M40 711H560" stroke="{ink}" stroke-opacity=".4"/>
      <text x="40" y="746" font-size="13">문화의 새로운 장면을 만나다</text>
      <text x="560" y="746" text-anchor="end" font-size="12">Sample exhibition</text>
    </g></svg>'''

save('hero', '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 650">
<defs><linearGradient id="wall" x2="1" y2="1"><stop stop-color="#ded6e8"/><stop offset="1" stop-color="#cbc4de"/></linearGradient>
<linearGradient id="arch" x1="0" x2="1"><stop stop-color="#f3eee5"/><stop offset=".6" stop-color="#fffaf0"/><stop offset="1" stop-color="#c5bcba"/></linearGradient>
<linearGradient id="blue" x2="1" y2="1"><stop stop-color="#bdc4ed"/><stop offset=".45" stop-color="#8493d1"/><stop offset="1" stop-color="#5662a2"/></linearGradient>
<radialGradient id="orb" cx=".3" cy=".25" r=".8"><stop stop-color="#b4c5ad"/><stop offset=".5" stop-color="#8b9c7d"/><stop offset="1" stop-color="#455b48"/></radialGradient>
<filter id="shadow" x="-50%" y="-100%" width="200%" height="300%"><feGaussianBlur stdDeviation="14"/></filter>
<pattern id="grain" width="4" height="4" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".4" fill="#fff" opacity=".15"/></pattern></defs>
<rect width="700" height="650" fill="url(#wall)"/><path d="M0 466L700 371V650H0Z" fill="#ccc6d5"/>
<ellipse cx="344" cy="462" rx="212" ry="24" fill="#5a526c" opacity=".2" filter="url(#shadow)"/>
<path d="M85 445V227a153 153 0 0 1 306 0v218h-73V227a80 80 0 0 0-160 0v218z" fill="#b0a5b7" transform="translate(21 -8)"/>
<path d="M85 445V227a153 153 0 0 1 306 0v218h-73V227a80 80 0 0 0-160 0v218z" fill="url(#arch)"/>
<path d="M404 416V276a116 116 0 0 1 232 0v140h-58V276a58 58 0 0 0-116 0v140z" fill="#7b80b3" transform="translate(13 -5)"/>
<path d="M404 416V276a116 116 0 0 1 232 0v140h-58V276a58 58 0 0 0-116 0v140z" fill="url(#blue)"/>
<ellipse cx="385" cy="449" rx="88" ry="19" fill="#455442" opacity=".24" filter="url(#shadow)"/><circle cx="353" cy="366" r="88" fill="url(#orb)"/>
<path d="M180 451l64-86 59 79z" fill="#dfb77a"/><path d="M244 365l19 1 59 78h-19z" fill="#bb9363"/>
<rect width="700" height="650" fill="url(#grain)"/>
<g fill="#635c77" font-family="Georgia,serif" font-size="17"><text x="39" y="45">Shapes of the ordinary</text></g>
</svg>''')

save('shapes', poster('#e7e7d8', '''<defs><linearGradient id="s" x2="1" y2="1"><stop stop-color="#9eb099"/><stop offset="1" stop-color="#3f5a50"/></linearGradient></defs>
<circle cx="424" cy="365" r="145" fill="#bdc9b1"/><path d="M83 628V375a102 102 0 0 1 204 0v253h-55V375a47 47 0 0 0-94 0v253z" fill="url(#s)"/>
<rect x="315" y="392" width="175" height="236" rx="87" fill="#f4f0df"/><path d="M315 539h175v89H315z" fill="#d6bb84"/><circle cx="410" cy="540" r="64" fill="#e1a67e"/>
<path d="M52 659H553" stroke="#859485"/>''', 'Fragments', '감각의 조각들', 'top'))
save('garden', poster('#e1e8e2', '''<defs><radialGradient id="g"><stop stop-color="#f1ecae"/><stop offset=".5" stop-color="#b2cb7b"/><stop offset="1" stop-color="#6b967e"/></radialGradient></defs>
<circle cx="302" cy="443" r="200" fill="url(#g)"/><path d="M300 246v397M104 443h396M163 303l278 280M442 303L163 583" stroke="#f2f2c6" stroke-width="1"/>
<g fill="none" stroke="#f3efce"><ellipse cx="302" cy="443" rx="120" ry="200"/><ellipse cx="302" cy="443" rx="48" ry="200"/><ellipse cx="302" cy="443" rx="200" ry="120"/><ellipse cx="302" cy="443" rx="200" ry="48"/></g>
<circle cx="302" cy="443" r="20" fill="#e6e8bc"/>''', 'Light Garden', '빛이 머무는 정원', 'top'))
save('musical', poster('#142a43', '''<defs><radialGradient id="m"><stop stop-color="#ffcc88"/><stop offset="1" stop-color="#a78879" stop-opacity="0"/></radialGradient></defs>
<circle cx="300" cy="390" r="210" fill="url(#m)" opacity=".65"/><rect x="171" y="276" width="254" height="351" rx="126" fill="#f0c894" opacity=".85"/>
<path d="M190 621V399a109 109 0 0 1 218 0v222z" fill="#334a61"/><circle cx="256" cy="440" r="22" fill="#d4b69b"/><path d="M235 465h41l19 135h-75z" fill="#172e47"/>
<circle cx="345" cy="449" r="22" fill="#cfb194"/><path d="M324 474h41l21 126h-81z" fill="#8e5b4c"/>
<circle cx="100" cy="249" r="2" fill="#e0cda6"/><circle cx="505" cy="337" r="3" fill="#e0cda6"/>''', 'Maybe, Happy', '어쩌면, 해피엔딩', 'top', '#f6e9d4'))
save('jazz', poster('#3442a0', '''<g fill="none" stroke="#e5ba63" stroke-width="35"><path d="M397 276v221a106 106 0 0 1-212 0"/><path d="M394 279l57-36"/></g>
<path d="M398 403l103-69 41 78-144 43z" fill="#ebc377"/><circle cx="282" cy="499" r="29" fill="#dc996b"/>
<g fill="#e2bb72"><circle cx="351" cy="400" r="8"/><circle cx="351" cy="445" r="8"/><circle cx="351" cy="490" r="8"/></g>
<path d="M83 645l56-56M463 622l57-56" stroke="#a9b6ed" stroke-width="8"/>''', 'Jazz After Dark', '밤의 재즈, 서울', 'top', '#fcf0d8'))
save('photo', poster('#e8e8e7', '''<rect x="65" y="240" width="470" height="414" fill="#95b0b2"/>
<path d="M65 460q120-70 241 0t229 0v194H65z" fill="#62878a"/><path d="M65 529q120-65 241 0t229 0v125H65z" fill="#335b64"/>
<rect x="128" y="271" width="344" height="348" fill="none" stroke="#f4efe4" stroke-width="9"/><circle cx="384" cy="346" r="45" fill="#eece9e"/>
<path d="M301 237v422" stroke="#f4efe4" stroke-width="4"/>''', 'Private Views', '사적인 풍경', 'top'))
save('theatre', poster('#dfbf73', '''<circle cx="301" cy="420" r="192" fill="#f1dca0"/>
<path d="M292 250l39 101 109 4-86 67 30 109-92-62-92 62 30-109-86-67 109-4z" fill="#416c69"/>
<path d="M119 606q179-67 357 0" fill="none" stroke="#a8884c" stroke-width="2"/>
<g fill="#416c69"><circle cx="138" cy="266" r="7"/><circle cx="479" cy="420" r="5"/><circle cx="217" cy="599" r="4"/></g>''', 'A Little Star', '작은 별의 여행', 'top', '#344f4b'))
save('dance', poster('#efd8d6', '''<g fill="none" stroke-linecap="round"><path d="M304 275q-112 56-88 175t181 157" stroke="#aa5a67" stroke-width="50"/>
<path d="M215 435q73-28 169-148" stroke="#aa5a67" stroke-width="40"/><path d="M256 501q-60 72-108 105" stroke="#aa5a67" stroke-width="40"/></g>
<circle cx="327" cy="244" r="38" fill="#aa5a67"/><path d="M104 569q153 97 386-158" fill="none" stroke="#f7ece7" stroke-width="3"/>
<path d="M141 642q160 34 328-115" fill="none" stroke="#c3848e"/>''', 'Body Language', '몸의 언어', 'top', '#6e3542'))
save('festival', poster('#dfebd1', '''<path d="M50 620L153 327l109 293z" fill="#9aaf73"/><path d="M314 620l108-347 129 347z" fill="#6d8e63"/>
<circle cx="302" cy="350" r="90" fill="#eec77c"/><path d="M230 620V443a70 70 0 0 1 140 0v177z" fill="#f0a681"/>
<path d="M45 649q125-55 257-13t258-7" fill="none" stroke="#567653" stroke-width="4"/>
<g fill="#f8f4df"><circle cx="176" cy="469" r="13"/><circle cx="438" cy="452" r="11"/></g>''', 'Park, Together', '가을, 공원에서', 'top', '#38573a'))
save('fallback', poster('#e9ebf3', '<circle cx="300" cy="438" r="155" fill="#c8cfea"/><path d="M226 510V365h50v145m49 0V322h50v188" stroke="#6e81bc" stroke-width="13" fill="none"/>', 'CulturePick', '새로운 문화를 만나다', 'top', '#566a99'))
print('Generated 10 fictional SVG artworks.')
