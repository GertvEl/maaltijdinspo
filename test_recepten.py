import json
from pathlib import Path
import sys

sys.path.append('.')
from src import validatie, recepten as recepten_mod

path = Path('data/recepten.json')
with path.open('r', encoding='utf-8') as f:
    recepten = json.load(f)

categories = ['kip', 'rund', 'zalm', 'kabeljauw', 'pasta', 'vegetarisch']
target_counts = {'kip': 17, 'rund': 17, 'zalm': 17, 'kabeljauw': 17, 'pasta': 16, 'vegetarisch': 16}
current_counts = {cat: sum(1 for r in recepten if r.get('categorie') == cat) for cat in categories}
add_counts = {cat: max(0, target_counts[cat] - current_counts[cat]) for cat in categories}

protein_templates = {
    'kip': [('kipfilet', 'vlees', False, 250, 'g'), ('kipdijfilet', 'vlees', False, 250, 'g'), ('kipgehakt', 'vlees', False, 220, 'g')],
    'rund': [('rundergehakt', 'vlees', False, 250, 'g'), ('runderlap', 'vlees', False, 250, 'g'), ('entrecote', 'vlees', False, 220, 'g')],
    'zalm': [('zalmfilet', 'vis', False, 250, 'g'), ('gerookte zalm', 'vis', False, 220, 'g'), ('zalmhaas', 'vis', False, 240, 'g')],
    'kabeljauw': [('kabeljauwfilet', 'vis', False, 250, 'g'), ('kabeljauwhaas', 'vis', False, 230, 'g'), ('kabeljauwblokjes', 'vis', False, 240, 'g')],
    'pasta': [('tofu', 'overig', False, 220, 'g'), ('linzen', 'overig', False, 240, 'g'), ('kikkererwten', 'overig', False, 240, 'g')],
    'vegetarisch': [('tofu', 'overig', False, 220, 'g'), ('linzen', 'overig', False, 240, 'g'), ('kikkererwten', 'overig', False, 240, 'g')],
}
vegetable_sets = [
    [('broccoli', 250, 'g'), ('paprika', 200, 'g'), ('ui', 120, 'g')],
    [('courgette', 220, 'g'), ('wortel', 180, 'g'), ('spinazie', 180, 'g')],
    [('aubergine', 220, 'g'), ('cherrytomaten', 180, 'g'), ('prei', 160, 'g')],
    [('sperziebonen', 220, 'g'), ('champignons', 180, 'g'), ('rode ui', 130, 'g')],
    [('paksoi', 220, 'g'), ('witte kool', 180, 'g'), ('wortel', 160, 'g')],
    [('komkommer', 180, 'g'), ('paprika', 200, 'g'), ('tomaat', 180, 'g')],
]
starch_sets = [
    [('rijst', 150, 'g', 'overig'), ('aardappelen', 300, 'g', 'overig')],
    [('quinoa', 150, 'g', 'overig'), ('tortillawraps', 4, 'stuk', 'overig')],
    [('naan', 2, 'stuk', 'overig'), ('volkoren pasta', 160, 'g', 'pasta')],
]
sauce_sets = [
    [('sojasaus', 40, 'ml', 'saus'), ('passata (tomatensaus)', 250, 'g', 'saus')],
    [('pesto', 80, 'g', 'saus'), ('currypasta', 30, 'g', 'saus')],
    [('citroensap', 30, 'ml', 'saus'), ('hummus', 80, 'g', 'saus')],
]


def build_ingredients(category, idx):
    protein = protein_templates[category][idx % len(protein_templates[category])]
    veg_set = vegetable_sets[idx % len(vegetable_sets)]
    starch = starch_sets[(idx // 3) % len(starch_sets)]
    sauce = sauce_sets[(idx // 2) % len(sauce_sets)]
    ingredients = [{
        'product': protein[0],
        'hoeveelheid': protein[3],
        'eenheid': protein[4],
        'categorie': protein[1],
        'groente': protein[2],
        'biologisch': False,
    }]
    for product, qty, unit in veg_set[:2]:
        ingredients.append({'product': product, 'hoeveelheid': qty, 'eenheid': unit, 'categorie': 'groente', 'groente': True, 'biologisch': False})
    extra_veg = veg_set[2]
    ingredients.append({'product': extra_veg[0], 'hoeveelheid': extra_veg[1], 'eenheid': extra_veg[2], 'categorie': 'groente', 'groente': True, 'biologisch': False})
    first_starch = starch[0]
    ingredients.append({'product': first_starch[0], 'hoeveelheid': first_starch[1], 'eenheid': first_starch[2], 'categorie': first_starch[3], 'groente': False, 'biologisch': False})
    first_sauce = sauce[0]
    ingredients.append({'product': first_sauce[0], 'hoeveelheid': first_sauce[1], 'eenheid': first_sauce[2], 'categorie': first_sauce[3], 'groente': False, 'biologisch': False})
    if idx % 2 == 0:
        alt_starch = starch[1]
        ingredients.append({'product': alt_starch[0], 'hoeveelheid': alt_starch[1], 'eenheid': alt_starch[2], 'categorie': alt_starch[3], 'groente': False, 'biologisch': False})
    if idx % 3 == 0:
        alt_sauce = sauce[1]
        ingredients.append({'product': alt_sauce[0], 'hoeveelheid': alt_sauce[1], 'eenheid': alt_sauce[2], 'categorie': alt_sauce[3], 'groente': False, 'biologisch': False})
    return ingredients


def make_recipe(category, idx):
    labels = {'kip': 'Kip', 'rund': 'Rund', 'zalm': 'Zalm', 'kabeljauw': 'Kabeljauw', 'pasta': 'Pasta', 'vegetarisch': 'Vegetarisch'}
    base = labels[category]
    if category in {'pasta', 'vegetarisch'}:
        name = f'{base} {idx + 1:02d} met Groente en Kruiden'
    else:
        name = f'{base} {idx + 1:02d} met Roergebakken Groente'
    return {
        'id': f'{category}_{idx + 1:02d}',
        'naam': name,
        'categorie': category,
        'kooktijd_min': 10 + (idx % 20),
        'porties': 2,
        'vegetarisch': category in {'pasta', 'vegetarisch'},
        'groente_hoofdingredient': False,
        'ingredienten': build_ingredients(category, idx),
        'stappen': ['Verwarm een pan of wok.', 'Bak het hoofdvoedsel kort aan.', 'Voeg de groenten toe en roerbak tot beetgaar.', 'Serveer met het gekozen bijgerecht.'],
        'bron': 'Lokaal',
        'bron_url': '',
        'afbeelding_url': '',
    }

new_recipes = []
seen_ids = {r.get('id') for r in recepten}
seen_names = {r.get('naam') for r in recepten}
for category, total in add_counts.items():
    for idx in range(total):
        recipe = make_recipe(category, idx)
        while recipe['id'] in seen_ids or recipe['naam'] in seen_names:
            recipe['id'] = f'{category}_{idx + 1:02d}_{idx}'
            recipe['naam'] = f'{recipe["naam"]} {idx + 1}'
        seen_ids.add(recipe['id'])
        seen_names.add(recipe['naam'])
        new_recipes.append(recipe)

updated = recepten + new_recipes
with path.open('w', encoding='utf-8') as f:
    json.dump(updated, f, ensure_ascii=False, indent=2)
    f.write('\n')

issues = []
for r in updated:
    if len(r.get('ingredienten', [])) >= 10:
        issues.append(('ingredient_count', r['naam']))
    if not (1 <= int(r.get('kooktijd_min', 0)) <= 30):
        issues.append(('kooktijd', r['naam']))
    gram = validatie.groente_gram_per_persoon(r)
    if gram < 150:
        issues.append(('groente', r['naam'], round(gram, 1)))

settings = {
    'volwassenen': 2,
    'kinderen': 1,
    'vegetarisch_per_week': 1,
    'kooktijd_max': 30,
    'voorkeur_categorieen': ['kip', 'rund', 'zalm', 'kabeljauw', 'pasta', 'vegetarisch'],
    'favorieten_voorrang': True,
    'scraping_aan': False,
}
filtered = recepten_mod.filter_op_voorkeuren(updated, settings)

print('before_count', len(recepten))
print('added_count', len(new_recipes))
print('after_count', len(updated))
print('category_counts', {c: sum(1 for r in updated if r.get('categorie') == c) for c in categories})
print('validation_issues', issues[:10])
print('filter_pass_count', len(filtered))
print('all_pass_filter', len(filtered) == len(updated))
