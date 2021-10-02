"""
recipes.py consists of several intent handlers which deal with recipes. Functionality 
ranges from displaying recipes, selecting a cuisine, hearing instructions, hearing ingredients for a recipe,
sending recipe to phone, etc. 
"""
# Standard 
import logging

# Internal
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model.ui import StandardCard
from ask_sdk_model import Response
from ask_sdk_core.utils import get_supported_interfaces
from ask_sdk_model.interfaces.alexa.presentation.apl import RenderDocumentDirective
from ask_sdk_model.interfaces.alexa.presentation.apl import UserEvent
from helper_functions import *
from ..lambda_function import LaunchRequestHandler
# External
from recipe_scrapers import scrape_me

# Globals
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
BLING_SOUND = '<audio src="soundbank://soundlibrary/ui/gameshow/amzn_ui_sfx_gameshow_neutral_response_01"/>'

class selectCuisineIntentHandler(AbstractRequestHandler):

    """Handler forselecting the cuisine"""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("selectCuisineIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        slots = handler_input.request_envelope.request.intent.slots
        cuisine = slots["cuisine"].value
        
        session_attr["cuisine"] = cuisine
        if len(session_attr["ingredients"])==0:
            speak_output = 'Selected recipe type is {cuisine}. Add some ingredients to your search and say search recipes when ready'.format(cuisine=cuisine)
        else:
            speak_output = 'Selected recipe type is {cuisine}. keep adding ingredients to your search or say search recipes when ready'.format(cuisine=cuisine)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class displayRecipesIntentHandler(AbstractRequestHandler):

    """Handler displaying recipes, envoked when user says find recipes, or something similar
    after adding ingredients."""
    
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("displayRecipesIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        session_attr = handler_input.attributes_manager.session_attributes
        
        
        numIngredientsUsed = 0
        ingredients = session_attr["ingredients"] #get ingredients from attributes_manager
        recipeIndex = session_attr["recipeIndex"] #get recipe index from attributes_manager
        
        cuisine = session_attr["cuisine"] #get recipe index from attributes_manager
        #if for some reason there is a bad combo of ingredients causing an error with recipe api
        #we only need to find recipes the first time around.
        
        if slots['displayRecipes'].resolutions: #if search recipes
            session_attr["extraIngredientUsed"] = False
            try:
                recipeDataList = removeBadRecipes(ingredients,cuisine) #finds and filters out bad recipes
            except:
                #add salt since it's the most common which usually fixes the problem
                try:
                    ingredients.append("salt")
                    recipeDataList = removeBadRecipes(ingredients,cuisine) #finds and filters out bad recipes
                    #since they didn't actually add this ingredient, we need to reduce the number of ingredients.
                    session_attr["extraIngredientUsed"] = True
                    
                except:
                    ingredients[-1] = 'water'
                    session_attr["extraIngredientUsed"] = True
                    recipeDataList = removeBadRecipes(ingredients,cuisine) #finds and filters out bad recipes
            
            urls = [recipe['href'] for recipe in recipeDataList] #save recipes to attributes_manager
            recipes = [recipe['title'] for recipe in recipeDataList] #save recipes to attributes_manager
            allIngredients = [recipe['ingredients'] for recipe in recipeDataList] #save recipes to attributes_manager
            session_attr["allIngredients"] = allIngredients
            session_attr["recipeUrls"] = urls
            session_attr["recipes"] = recipes
        urls = session_attr["recipeUrls"]
        recipes = session_attr["recipes"]
        allIngredients = session_attr["allIngredients"]
        recipe = "recipe"
        ifExtra = session_attr["extraIngredientUsed"] #we solved the edgecase with salt as extra ingredient
        #switch to next recipe. 
        
        if len(ingredients)>0:
            numTotal=len(ingredients)
            if ifExtra == True:
                numTotal-=1
                
            for ing in ingredients:
                if ing in allIngredients[recipeIndex]:
                    if ifExtra == True and ing == "salt" or ing == "water": 
                        continue #skip counting salt as one of the ingredients
                    numIngredientsUsed+=1
                    
            slots = handler_input.request_envelope.request.intent.slots
            if not slots['displayRecipes'].resolutions and session_attr["recipes"]!=[]: #if next recipe
                
                if recipeIndex < len(recipes)-1:
                    session_attr["recipeIndex"]+=1 
                    recipeIndex = session_attr["recipeIndex"]
                    recipe = recipes[recipeIndex]
                else: 
                    speak_output="You've reached the last recipe in the search. Say start recipe!"
                    return (
                    handler_input.response_builder
                    .speak(speak_output)
                    .ask(speak_output)
                    .response
                    )
            else:#if search recipe
                
                session_attr['display_recipes_documents'] = [_load_apl_document("display_recipes_data.json"),_load_apl_document("display_recipes_APL.json")]
                session_attr["recipeIndex"] = 0
                recipeIndex = 0
                recipe = recipes[recipeIndex]

            #if using an APL interface, let's load recipes one by one.
            if get_supported_interfaces(handler_input).alexa_presentation_apl is not None:
                
                recipe = recipes[recipeIndex]
                scraper = scrape_me(urls[recipeIndex])
                image = scraper.image()
                yields = scraper.yields()
                cookingTime = scraper.total_time()
                
                if cookingTime == None or str(cookingTime) == '0': 
                    cookingTime = ""
                else:
                    cookingTime = str(cookingTime)+' minutes,'
                    
                if yields == None: 
                    yields = ""
                if 'item' in yields:
                    yields = '2 serving(s)'
                datasources = _load_apl_document("display_recipes_data.json")
                document = _load_apl_document("display_recipes_APL.json")
                if session_attr['display_recipes_documents']:
                    datasources = session_attr['display_recipes_documents'][0]
                    document = session_attr['display_recipes_documents'][1]
                datasources['textListData']['listItemsToShow'].append(
                
                {
                    "primaryText": recipe,
                    "secondaryText": "{cookingTime} {servingSize}".format(cookingTime=cookingTime,servingSize=yields),
                    "secondaryTextPosition": "bottom",
                    "tertiaryText": "({}/{}) ingredients".format(numIngredientsUsed,numTotal),
                    "tertiaryTextPosition": "bottom",
                    "imageThumbnailSource": image,
                    "touchForward": True
                })
                print("APL UserEvent sent to skill: {}".format(datasources))
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        token="displayRecipes",
                        document=document,
                        datasources=datasources
                    )
                )
            recipe = escape(recipe)
            
            speak_output = BLING_SOUND
            if recipeIndex == 0:
                speak_output+='The first recipe we found is {recipe} using {numUsed} of {numTotal} of your ingredients. Say start recipe or next recipe to continue.'.format(recipe=recipe,numUsed=numIngredientsUsed,numTotal=numTotal)
            else:
                speak_output+='We also found {recipe} using {numUsed} of {numTotal} of your ingredients. Say start recipe or next recipe to continue.'.format(recipe=recipe,numUsed=numIngredientsUsed,numTotal=numTotal)
            return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
            )
        else:
            speak_output = "You can't search for a recipe with 0 ingredients! Add an ingredient to search by saying add ingredient."
            return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("say either start recipe or next recipe")
                .response
            )

class selectRecipeIntentHandler(AbstractRequestHandler):
    """
    Handler for selecting a recipe. 
    """
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("selectRecipeIntent")(handler_input)

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        recipes = session_attr["recipes"]
        if len(recipes) <1:
            speech_text = "You can't select a recipe until you've searched for one, say search recipes once you've added ingredients."
            return (
                handler_input.response_builder
                    .speak(speech_text)
                    .ask(speech_text)
                    .response
            )
            
        recipeIndex = session_attr["recipeIndex"] 
        if session_attr['selectedIndex'] is not None: #if envoked by clicking..
            print("in here")
            print(recipeIndex)
            recipeIndex = session_attr['selectedIndex']
        session_attr["instructionsIndex"] = 0 
        recipes = session_attr["recipes"]
        url = session_attr["recipeUrls"][recipeIndex]
        
        recipeTitle = recipes[recipeIndex].strip()
        scraper = scrape_me(url)
        # time, yields, ing, instructions
        temp = scraper.instructions().split('\n')
        #if the instructions aren't divided by \n, we need to split them manually by periods.
        if len(temp)==1:
            temp = temp[0].split('.')
        session_attr["instructions"] = temp
        instructions = []
        
        for index,step in enumerate(temp):
            if len(step)>=2:
                instructions.append("<b>Step {}:</b> {}".format(index+1,step))
                
        session_attr["selectedIngredients"] = scraper.ingredients()
        session_attr["selectedYields"] = scraper.yields()
        session_attr["selectedCookingTime"] = scraper.total_time()
        session_attr["selectedImage"] = scraper.image()
        instructions = '<br>'.join(instructions)
        ingredients = session_attr["selectedIngredients"]
        ingredients = '<br>'.join(ingredients)
        print(ingredients)
        print(instructions)
        yields = session_attr["selectedYields"]
        if yields == None: yields = '1'
        
        cookingTime = session_attr["selectedCookingTime"]
        cookingTime = str(cookingTime)
        if cookingTime == '0':
            cookingTime = ""
        else:
            cookingTime += ' minutes, '
        
        image = session_attr["selectedImage"]
        

        datasources = _load_apl_document("recipe_output_data.json")
        if get_supported_interfaces(handler_input).alexa_presentation_apl is not None:
            handler_input.response_builder.add_directive(
                RenderDocumentDirective(
                    token="recipe_output",
                    document=_load_apl_document("recipe_output_APL.json"),
                    datasources=datasources
                )
        )
        datasources["detailImageRightData"]["title"] = revert(recipeTitle)
        datasources["detailImageRightData"]["image"]["sources"][0]["url"] = image
        datasources["detailImageRightData"]["image"]["sources"][1]["url"] = image
        
        datasources["detailImageRightData"]["buttons"][0]["text"] = "Ingredients"
        datasources["detailImageRightData"]["buttons"][1]["text"] = "Instructions"
        datasources["detailImageRightData"]["buttons"][0]["action"][1]["value"] = ingredients
        print(ingredients)
        print()
        print(instructions)
        datasources["detailImageRightData"]["buttons"][1]["action"][1]["value"] = instructions
        
        datasources["detailImageRightData"]["textContent"]["secondaryText"]["text"] = "{}serves {}".format(cookingTime,yields) 
        datasources["detailImageRightData"]["textContent"]["content"]["text"] = ingredients
        speech_text = "Would you like to hear ingredients, hear instructions, or send recipe to phone?"
    
        return (
        handler_input.response_builder
            .speak(speech_text)
            .ask(speech_text)
            .response
            
        )

class SendEventHandler(AbstractRequestHandler):
    """APL UserEvent handler (TouchWrapper)"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        request = handler_input.request_envelope.request
        if isinstance(request, UserEvent):
            # return true for userEvent request with at least 1 argument
            return len(request.arguments) > 0

        return False
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        request = handler_input.request_envelope.request  # type: UserEvent
        session_attr = handler_input.attributes_manager.session_attributes

        print('request argument: ' +str(request.arguments))
        speak_output = ""
        if request.arguments[0] == 'Instructions':
            speak_output = "Here are the instructions:"
        elif request.arguments[0] =='Ingredients':
            speak_output = "Here are the ingredients:"
        elif request.arguments[0] == 'ListItemSelected' and request.arguments[1]:
            recipes = session_attr['recipes']
            index = request.arguments[1]
            
            speak_output = "Selected recipe is {} Enjoy your recipe!".format(recipes[index-1]+'.')
            session_attr['selectedIndex'] = index-1
            selectRecipeIntentHandler().handle(handler_input)
            
        elif request.arguments[0] == 'IngredientSelected' and request.arguments[1]:
            index = request.arguments[1]
            ingredient = session_attr['ingredients'].pop(index-1)
            
            speak_output = "removed {}".format(ingredient)
            
            session_attr['display_ingredients_documents'][0]['textListData']['listItems'].pop(index-1)
            datasources = session_attr['display_ingredients_documents'][0]
            apl = session_attr['display_ingredients_documents'][1]
            handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document = apl,
                        datasources = datasources
                        )
                )
            session_attr['display_ingredients_documents'] = [datasources,apl]
            return (
            handler_input.response_builder
                .speak(speak_output)
                .response
            )
        elif request.arguments[0] == 'goBack':
            if request.arguments[1]  == 0:
                LaunchRequestHandler().handle(handler_input)
            elif request.arguments[1]  == 1:
                datasources = session_attr['display_ingredients_documents'][0]
                apl = session_attr['display_ingredients_documents'][1]
                speak_output = "Here are your ingredients. Continue adding or say search recipes"
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document = apl,
                        datasources = datasources
                        )
                )
            elif request.arguments[1]  == 2:
                datasources = session_attr['display_recipes_documents'][0]
                apl= session_attr['display_recipes_documents'][1]
                speak_output = "select a recipe on your screen, or say next recipe."
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document = apl,
                        datasources = datasources
                        )
                )

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class sendRecipeIntentHandler(AbstractRequestHandler):
    """
    Handler for sending a recipe to a user's phone. 
    """
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("sendRecipeIntent")(handler_input)
    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        recipes = session_attr["recipes"]
        try:
            instructions = session_attr["instructions"]
        except:
            speech_text = "You can't send a recipe until you've found and selected one!"
            return (
                handler_input.response_builder
                    .speak(speech_text)
                    .ask(speech_text)
                    .response
            )
        speak_output = BLING_SOUND
        speak_output += "Recipe sent. Go to your alexa app to view the recipe. Once in the alexa app, click on More, then Activity to view it."
        recipeIndex = session_attr["recipeIndex"]
        
        instructions = '\r\n'.join(instructions)
        ingredients = session_attr["selectedIngredients"]
        ingredients = '\n'.join(ingredients)
        yields = session_attr["selectedYields"]
        cookingTime = session_attr["selectedCookingTime"]
        image = session_attr["selectedImage"]
        
        card_title = revert(session_attr["recipes"][recipeIndex].strip())
        card_text = "INSTRUCTIONS:\n  {}\n\n INGREDIENTS:\n {}".format(instructions,ingredients)
        images = {
                'smallImageUrl': image,
                'largeImageUrl': image
        }

        return (
            handler_input.response_builder
                .speak(speak_output)
                .set_card(StandardCard(
                    card_title,card_text,images))
                .ask("If you can't see the recipe, Click on More, then Activity to view it.")
                .set_should_end_session(True)
                .response
        )
    
class instructionsIntentHandler(AbstractRequestHandler):
    """Handler for hearing the instrucitons for a given recipe"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("instructionsIntent")(handler_input)

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        recipes = session_attr["recipes"]
        if len(recipes) <1:
            speech_text = "You can't hear instructions until you find a recipe! Continue adding ingredients or say search recipes."
            return (
                handler_input.response_builder
                    .speak(speech_text)
                    .ask(speech_text)
                    .response
            )
        instructions = session_attr["instructions"] 
        instructionsIndex = session_attr["instructionsIndex"] 
        
        if(instructionsIndex <= len(instructions)-1):
            instructionsIndex = session_attr["instructionsIndex"]
            currentInstruction = instructions[instructionsIndex] 
            session_attr["instructionsIndex"] += 1 
            speak_output = "{} Say next step or repeat step when ready".format(currentInstruction)
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask("You could also say send recipe to phone to see the recipe visually.")
                    .response
            )
        else:
            speak_output = "You are done with the instructions, Enjoy your meal!"
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .set_should_end_session(True)
                    .response
            )

class RepeatStepIntentHandler(AbstractRequestHandler):
    """Handler for repeating a step once hearing instructions for a recipe"""
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("repeatStepIntent")(handler_input)
    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        recipes = session_attr["recipes"]
        if len(recipes) <1:
            speech_text = "You can't repeat the step until you find a recipe! Continue adding ingredients or say search recipes."
            return (
                handler_input.response_builder
                    .speak(speech_text)
                    .ask(speech_text)
                    .response
            )
        session_attr = handler_input.attributes_manager.session_attributes
        instructions = session_attr["instructions"] #get ingredients from attributes_manager
        instructionsIndex = session_attr["instructionsIndex"] #get recipe index from attributes_manager
        
        currentInstruction = instructions[instructionsIndex-1]
        speak_output = "{currentInstruction}.  Say next step or repeat step when ready".format(currentInstruction=currentInstruction)
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("You could also say send recipe to phone to see the recipe visually.")
                .response
        )