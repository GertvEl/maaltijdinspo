import json
from pathlib import Path

p = Path('data/recepten.json')
with p.open('r', encoding='utf-8') as f:
    recipes = json.load(f)
print('count', len(recipes))
print('categories', {c: sum(1 for r in recipes if r.get('categorie') == c) for c in ['kip','rund','zalm','kabeljauw','pasta','vegetarisch']})
