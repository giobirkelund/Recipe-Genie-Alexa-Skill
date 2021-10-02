"""
helper_functions.py is comprised of all the helper functions used for parsing, loading, building sentences, doing nlp. 
"""
# Standard
import json
import requests

# Third Party
from pluralizer import Pluralizer

def _load_apl_document(file_path):
    with open(f'APL/{file_path}') as f:
        return json.load(f)

def testIngredient(ingredient):
    """
    Make sure an ingredient is valid by passing it into the api endpoint
    and verifying the response is valid. 
    """
    
    try: 
        result = findRecipes([ingredient],None,1)
        if result == None:
            return False
        else:
            return True
    except: 
        return False

def sentenceMaker(theList):
    """
    Build a readable sentence with a list. 
    """
    sentence = ""
    if len(theList) == 1:
        return theList[0]
    for index,element in enumerate(theList):
        if(index == len(theList)-1):
            sentence+= "and " + element
        else:
            sentence += element + ", "
    return sentence

def makePlural(ingredient):
    """
    Used by the add ingredients intent to make a word either plural
    or singular, so that we can test it again with the api. 
    """
    pluralizer = Pluralizer()
    if pluralizer.isPlural(ingredient) == True:
        pluralIng = pluralizer.singular(ingredient)
    else:
        pluralIng = pluralizer.plural(ingredient)
    return pluralIng
    
def findRecipes(ingredients,cuisine,page):
    """
    Hit the api with the ingredients we have gathered, and return the response. 
    """
    ingredients = ','.join(ingredients)
    url = "http://www.recipepuppy.com/api"
    querystring = {}
    if(cuisine==None):
        querystring = {"p":page,"i":ingredients}
    else:
        querystring = {"p":page,"i":ingredients,"q":cuisine}
    headers = {
        'x-rapidapi-host': "recipe-puppy.p.rapidapi.com",
        'x-rapidapi-key': "0e1d971feamsh1c4950183e3e38fp14df74jsn1d7a42fe2b63"
        }
    response = requests.request("GET", url, headers=headers, params=querystring)    
    
    if str(response) != '<Response [200]>':
        print("respsone not good! increasing page to see if it fixes problem.")
    data = response.json()['results']
    recipeData = [recipe for recipe in data] #save recipe
    
    if data == None or recipeData == []:
        raise Exception("Error with input to findRecipes") 
        return None
    return recipeData

def removeBadRecipes(ingredients,cuisine):
    """
    Remove recipies from response that have missing data, or urls that cannot be scraped from the list. 
    """
    NUM_RECIPES = 10
    recipes = []
    goodRecipes = []
    start = 1
    numPages = 5
    #retrieve batches of recipes from api.
    for page in range(start,numPages+1):
        try:
            recipeData = findRecipes(ingredients,cuisine,page)
            [recipes.append(recipe) for recipe in recipeData]
        except: 
            page+=1
            recipeData = findRecipes(ingredients,cuisine,page+1)
            [recipes.append(recipe) for recipe in recipeData]
            numPages+=1

    canDoURLs = 'https://www.acouplecooks.com/ https://allrecipes.com/ https://archanaskitchen.com/ https://averiecooks.com/ https://bbc.com/ https://bbc.co.uk/ https://bbcgoodfood.com/ https://bettycrocker.com/ https://bonappetit.com/ https://bowlofdelicious.com/ https://budgetbytes.com/ https://closetcooking.com/ https://cookieandkate.com/ https://cookpad.com/ https://cookstr.com/ https://copykat.com/ https://countryliving.com/ https://cybercook.com.br/ https://delish.com/ https://epicurious.com/ https://fifteenspatulas.com/ https://finedininglovers.com/ https://fitmencook.com/ https://food.com/ https://foodnetwork.com/ https://foodrepublic.com/ https://geniuskitchen.com/ https://giallozafferano.it/ https://gimmesomeoven.com/ https://gonnawantseconds.com/ https://gousto.co.uk/ https://greatbritishchefs.com/ https://halfbakedharvest.com/ https://heinzbrasil.com.br/ https://hellofresh.com/ https://hellofresh.co.uk/ https://hostthetoast.com/ https://101cookbooks.com/ https://receitas.ig.com.br/ https://inspiralized.com/ https://jamieoliver.com/ https://justbento.com/ https://kennymcgovern.com/ https://kochbar.de/ https://lovingitvegan.com/ https://lecremedelacrumb.com/ https://marmiton.org/ https://matprat.no/ http://mindmegette.hu/ https://minimalistbaker.com/ https://misya.info/ https://momswithcrockpots.com/ http://motherthyme.com/ https://mybakingaddiction.com/ https://myrecipes.com/ https://healthyeating.nhlbi.nih.gov/ https://cooking.nytimes.com/ https://ohsheglows.com/ https://www.panelinha.com.br/ https://paninihappy.com/ https://przepisy.pl/ https://realsimple.com/ https://seriouseats.com/ https://simplyquinoa.com/ https://simplyrecipes.com/ https://skinnytaste.com/ https://southernliving.com/ https://spendwithpennies.com/ https://steamykitchen.com/ https://tastesoflizzyt.com/ https://tasteofhome.com/ https://tasty.co/ https://tastykitchen.com/ https://thehappyfoodie.co.uk/ https://thekitchn.com/ https://thepioneerwoman.com/ https://thespruceeats.com/ https://thevintagemixer.com/ https://thewoksoflife.com/ https://tine.no/ https://tudogostoso.com.br/ https://twopeasandtheirpod.com/ https://vegolosi.it/ https://watchwhatueat.com/ https://whatsgabycooking.com/ https://en.wikibooks.org/ https://yummly.com/'
    #reformat urls
    for index in range(len(recipes)):
        #remove noise
        current = recipes[index]
        #replace domain name since it changed
        url = current['href']
        if 'recipezaar' in url:
            current['href'] = current['href'].replace('recipezaar.com','food.com')
        domain=current['href'].split('//')[-1].split('/')[0] 
        try:
            domain = domain.replace('www.','')
        except:
            pass
        if '//'+ domain in canDoURLs:
            goodRecipes.append(current)

    without_duplicates = []
    goodList = []
    #remove duplicates, and create final list.
    for index,recipe in enumerate(goodRecipes):
        
        recipe['title']=recipe['title'].strip()
        
        if recipe['title'] in without_duplicates:
            continue
        elif len(goodList)>=NUM_RECIPES:
            break;
        else:
            goodList.append(recipe)
            without_duplicates.append(recipe['title'])
    return goodList

def escape(str):
    """remove escape characters"""
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str

def revert(str):
    """revert escaped characters"""
    str = str.replace("&amp;","and")
    str = str.replace("<", "")
    str = str.replace(">", "")
    str = str.replace("\"", "/")
    str = str.replace("?", "")
    str = str.replace("'", "")
    return str