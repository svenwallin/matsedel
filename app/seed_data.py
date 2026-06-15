"""Sample data loader for the recipe database."""
from database import init_db, add_recipe, get_all_recipes

# Sample recipes for storkok (large-scale cooking) and outdoor cooking
# Based on typical Swedish scout camp food

SAMPLE_RECIPES = [
    {
        'name': 'Köttfärssås',
        'description': 'Klassisk köttfärssås perfekt för läger. Serveras med pasta eller ris.',
        'category': 'Huvudrätt',
        'base_servings': 10,
        'cooking_time': '45 min',
        'instructions': '''1. Fräs löken i en stor gryta tills den mjuknar.
2. Tillsätt köttfärsen och bryn ordentligt.
3. Häll i krossade tomater och tomatpuré.
4. Krydda med salt, peppar, oregano och basilika.
5. Låt sjuda i 30 minuter.
6. Smaka av och servera med kokt pasta.''',
        'image_url': '/static/images/kottfarssas.jpg',
        'ingredients': [
            {'name': 'Nötfärs', 'amount': 1000, 'unit': 'g'},
            {'name': 'Krossade tomater', 'amount': 800, 'unit': 'g'},
            {'name': 'Gul lök', 'amount': 3, 'unit': 'st'},
            {'name': 'Vitlök', 'amount': 4, 'unit': 'klyftor'},
            {'name': 'Tomatpuré', 'amount': 3, 'unit': 'msk'},
            {'name': 'Olivolja', 'amount': 3, 'unit': 'msk'},
            {'name': 'Salt', 'amount': 2, 'unit': 'tsk'},
            {'name': 'Svartpeppar', 'amount': 1, 'unit': 'tsk'},
            {'name': 'Oregano', 'amount': 2, 'unit': 'tsk'},
            {'name': 'Basilika', 'amount': 2, 'unit': 'tsk'}
        ]
    },
    {
        'name': 'Stormkok Pannkakor',
        'description': 'Fluffiga pannkakor som enkelt tillagas på stormkök.',
        'category': 'Frukost',
        'base_servings': 4,
        'cooking_time': '30 min',
        'instructions': '''1. Blanda mjöl och salt i en skål.
2. Vispa ner ägg och hälften av mjölken.
3. Tillsätt resten av mjölken och vispa till slät smet.
4. Låt svälln i 10 minuter.
5. Smält lite smör i stekpannan.
6. Häll i lagom med smet och stek på medelvärme.
7. Vänd när undersidan är gyllene.
8. Servera med sylt och grädde.''',
        'image_url': '/static/images/pannkakor.jpg',
        'ingredients': [
            {'name': 'Vetemjöl', 'amount': 300, 'unit': 'g'},
            {'name': 'Mjölk', 'amount': 600, 'unit': 'ml'},
            {'name': 'Ägg', 'amount': 3, 'unit': 'st'},
            {'name': 'Salt', 'amount': 0.5, 'unit': 'tsk'},
            {'name': 'Smör', 'amount': 50, 'unit': 'g'}
        ]
    },
    {
        'name': 'Ärtsoppa',
        'description': 'Värmande ärtsoppa - perfekt efter en dag i naturen.',
        'category': 'Soppa',
        'base_servings': 8,
        'cooking_time': '90 min',
        'instructions': '''1. Blötlägg ärterna i kallt vatten över natten.
2. Häll bort blötläggningsvattnet.
3. Koka ärterna i nytt vatten med fläsk/korv.
4. Lägg i lök, morot och timjan.
5. Låt koka tills ärterna är mjuka (ca 1-1.5 timme).
6. Krydda med salt och peppar.
7. Servera med senap och pannkakor.''',
        'image_url': '/static/images/artsoppa.jpg',
        'ingredients': [
            {'name': 'Gula ärter', 'amount': 500, 'unit': 'g'},
            {'name': 'Fläskkorv', 'amount': 400, 'unit': 'g'},
            {'name': 'Gul lök', 'amount': 2, 'unit': 'st'},
            {'name': 'Morot', 'amount': 2, 'unit': 'st'},
            {'name': 'Timjan', 'amount': 1, 'unit': 'tsk'},
            {'name': 'Salt', 'amount': 2, 'unit': 'tsk'},
            {'name': 'Vatten', 'amount': 2, 'unit': 'liter'}
        ]
    },
    {
        'name': 'Grillspett med grönsaker',
        'description': 'Färgglada grillspett med kött och grönsaker - klassisk lägermat.',
        'category': 'Huvudrätt',
        'base_servings': 6,
        'cooking_time': '40 min',
        'instructions': '''1. Skär kycklingen i bitar (ca 3 cm).
2. Skär paprika, lök och zucchini i bitar.
3. Blanda marinad: olja, citron, vitlök, örter och salt.
4. Lägg kött och grönsaker i marinaden i 30 min.
5. Trä på spett: kött, paprika, lök, zucchini, upprepa.
6. Grilla på medelvärme, vänd regelbundet.
7. Grilla tills kycklingen är genomstekt (ca 15-20 min).''',
        'image_url': '/static/images/grillspett.jpg',
        'ingredients': [
            {'name': 'Kycklingfilé', 'amount': 600, 'unit': 'g'},
            {'name': 'Paprika röd', 'amount': 2, 'unit': 'st'},
            {'name': 'Paprika gul', 'amount': 2, 'unit': 'st'},
            {'name': 'Zucchini', 'amount': 1, 'unit': 'st'},
            {'name': 'Rödlök', 'amount': 2, 'unit': 'st'},
            {'name': 'Olivolja', 'amount': 4, 'unit': 'msk'},
            {'name': 'Citronjuice', 'amount': 2, 'unit': 'msk'},
            {'name': 'Vitlök', 'amount': 3, 'unit': 'klyftor'},
            {'name': 'Rosmarin', 'amount': 1, 'unit': 'msk'},
            {'name': 'Salt', 'amount': 1, 'unit': 'tsk'}
        ]
    },
    {
        'name': 'Korvgryta',
        'description': 'Enkel och mättande korvgryta som alla gillar.',
        'category': 'Huvudrätt',
        'base_servings': 8,
        'cooking_time': '35 min',
        'instructions': '''1. Skär korven i skivor.
2. Fräs korven i en stor gryta.
3. Tillsätt hackad lök och fräs vidare.
4. Häll i krossade tomater och vatten.
5. Lägg i potatis skuren i bitar.
6. Krydda med paprika, salt och peppar.
7. Låt sjuda tills potatisen är mjuk (ca 20 min).
8. Rör ner crème fraiche och servera.''',
        'image_url': '/static/images/korvgryta.jpg',
        'ingredients': [
            {'name': 'Falukorv', 'amount': 800, 'unit': 'g'},
            {'name': 'Potatis', 'amount': 1000, 'unit': 'g'},
            {'name': 'Krossade tomater', 'amount': 400, 'unit': 'g'},
            {'name': 'Gul lök', 'amount': 2, 'unit': 'st'},
            {'name': 'Vatten', 'amount': 400, 'unit': 'ml'},
            {'name': 'Crème fraiche', 'amount': 200, 'unit': 'ml'},
            {'name': 'Paprikapulver', 'amount': 1, 'unit': 'msk'},
            {'name': 'Salt', 'amount': 1, 'unit': 'tsk'},
            {'name': 'Peppar', 'amount': 0.5, 'unit': 'tsk'}
        ]
    },
    {
        'name': 'Pinbrödsdeg',
        'description': 'Klassisk pinbrödsdeg som gräddas över öppen eld.',
        'category': 'Bröd',
        'base_servings': 10,
        'cooking_time': '20 min + jäsning',
        'instructions': '''1. Lös upp jästen i ljummen mjölk.
2. Tillsätt socker, salt och smör.
3. Arbeta in mjölet lite i taget.
4. Knåda tills degen släpper från händerna.
5. Låt jäsa under duk i 30-40 min.
6. Dela degen i portionsbitar.
7. Rulla till långa strängar.
8. Linda runt en pinne och grädda över glöd.''',
        'image_url': '/static/images/pinbrod.jpg',
        'ingredients': [
            {'name': 'Vetemjöl', 'amount': 600, 'unit': 'g'},
            {'name': 'Mjölk', 'amount': 300, 'unit': 'ml'},
            {'name': 'Jäst', 'amount': 25, 'unit': 'g'},
            {'name': 'Socker', 'amount': 2, 'unit': 'msk'},
            {'name': 'Salt', 'amount': 1, 'unit': 'tsk'},
            {'name': 'Smör', 'amount': 50, 'unit': 'g'}
        ]
    },
    {
        'name': 'Friluftshavregrynsgröt',
        'description': 'Nyttig och energirik frukostgröt för aktiva dagar.',
        'category': 'Frukost',
        'base_servings': 4,
        'cooking_time': '15 min',
        'instructions': '''1. Koka upp vatten i en kastrull.
2. Rör ner havregryn och salt.
3. Låt koka på låg värme i 5-7 minuter.
4. Rör om då och då.
5. Ta av från värmen och låt stå 2-3 min.
6. Servera med mjölk, kanel och sylt.''',
        'image_url': '/static/images/grot.jpg',
        'ingredients': [
            {'name': 'Havregryn', 'amount': 300, 'unit': 'g'},
            {'name': 'Vatten', 'amount': 800, 'unit': 'ml'},
            {'name': 'Salt', 'amount': 0.5, 'unit': 'tsk'},
            {'name': 'Mjölk', 'amount': 200, 'unit': 'ml'},
            {'name': 'Kanel', 'amount': 1, 'unit': 'tsk'},
            {'name': 'Sylt', 'amount': 100, 'unit': 'g'}
        ]
    },
    {
        'name': 'Foliepotatis',
        'description': 'Potatis bakt i folie över öppen eld med smör och gräddfil.',
        'category': 'Tillbehör',
        'base_servings': 6,
        'cooking_time': '45 min',
        'instructions': '''1. Tvätta potatisen ordentligt.
2. Gör snitt i potatisen utan att skära igenom.
3. Lägg lite smör i snitten.
4. Slå in varje potatis i dubbla lager aluminiumfolie.
5. Lägg i glöden (inte öppen låga).
6. Vänd efter 20-25 minuter.
7. Kolla att de är klara med en sticka.
8. Servera med gräddfil och gräslök.''',
        'image_url': '/static/images/foliepotatis.jpg',
        'ingredients': [
            {'name': 'Bakpotatis', 'amount': 6, 'unit': 'st'},
            {'name': 'Smör', 'amount': 50, 'unit': 'g'},
            {'name': 'Gräddfil', 'amount': 200, 'unit': 'ml'},
            {'name': 'Gräslök', 'amount': 1, 'unit': 'knippe'},
            {'name': 'Salt', 'amount': 1, 'unit': 'tsk'},
            {'name': 'Peppar', 'amount': 0.5, 'unit': 'tsk'}
        ]
    }
]

def load_sample_data():
    """Load sample recipes into the database."""
    init_db()
    
    # Check if data already exists
    existing = get_all_recipes()
    if existing:
        print(f"Database already contains {len(existing)} recipes. Skipping sample data.")
        return
    
    print("Loading sample recipes...")
    for recipe in SAMPLE_RECIPES:
        ingredients = recipe.pop('ingredients')
        recipe_id = add_recipe(**recipe, ingredients=ingredients)
        print(f"  Added: {recipe['name']} (ID: {recipe_id})")
    
    print(f"\nLoaded {len(SAMPLE_RECIPES)} sample recipes successfully!")

if __name__ == '__main__':
    load_sample_data()
