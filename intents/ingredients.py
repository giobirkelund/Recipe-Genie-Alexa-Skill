"""
ingredients.py has the intents which handle tasks such as adding ingredients,
making sure the api recognizes those ingredients, displaying ingredients, and removing them.
"""
# Standard 
import logging

# Internal
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_core.utils import get_supported_interfaces
from ask_sdk_model.interfaces.alexa.presentation.apl import RenderDocumentDirective
from helper_functions import *
from ..lambda_function import FallbackIntentHandler

# Globals
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ingredientsIntentHandler(AbstractRequestHandler):
    """
    Handler for hearing what your ingredients are. 
    """
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("IngredientsIntent")(handler_input)

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        if len(session_attr["recipes"]) <1:
            speech_text = "Before you can hear ingredients, you must find a recipe! Continue adding ingredients or say search recipes."
            return (
                handler_input.response_builder
                    .speak(speech_text)
                    .ask(speech_text)
                    .response
            )
        
        ingredients = session_attr["selectedIngredients"] 
        ingredientsReadable = ', '.join(ingredients)
        speak_output = ingredientsReadable + ". Say repeat ingredients, hear instructions, or send recipe to phone to continue."
        return (
        handler_input.response_builder
            .speak(speak_output)
            .ask("repeat ingredients or start instructions")
            .response
        )   

class addIngredientsIntentHandler(AbstractRequestHandler):
    """Handler for Ingredients Intent. This is envoked when a user specifies ingredient(s)"""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("addIngredientsIntent")(handler_input)

    def handle(self, handler_input):
        """
        Here, we will test each ingredient in the api to make sure it recognizes it. The API doesn't recognize many ingredients,
        so this is an important step. Also, some ingredients work if they're plural, some when they're singular.
        If the ingredients are good, we add them, Otherwise, they're added to a bad ingredient list for debugging purposes. 
        """

        session_attr = handler_input.attributes_manager.session_attributes
        slots = handler_input.request_envelope.request.intent.slots["ingredient"].slot_value

        session_attr['badingredients'] = []
        sessionIngredients = []

        if slots == None:
            FallbackIntentHandler().handle(handler_input)
        
        if slots.object_type == 'Simple':
            print("in simple!")
            ingredients = [slots.value]
        else: 
            ingredients = slots.values

        for index in range(len(ingredients)):
            if slots.object_type == 'Simple':
                ingredient = ingredients[index]
            else:
                ingredient = ingredients[index].value
            print(ingredient)
            if ingredient == '' or ingredient == None:
                break
            if testIngredient(ingredient) == False:
                print("BAD INGREDIENT: "+ingredient)
                pluralIng = makePlural(ingredient)
                #can only try to split it if and is present, because that means it wasn't meant to be one ingredient. i.e. rice cakes is one ingredient, and should be treated as such.
                if testIngredient(pluralIng) == False:
                    
                    #now try to split ingredient to see if it just mashed two together, and try each part seperately. if a part works, add it as an ingredient!
                    splitIngs = ingredient.split()
                    for each in splitIngs:
                        if each == 'and': continue #handle weird edge case where and is part of the ingredient
                        elif testIngredient(each) == False:
                             #as a last test see if making it plural will make it valid
                            pluralIng = makePlural(each)
                             #if not it's just an invalid ingredient
                            if testIngredient(pluralIng) == True:
                                session_attr['ingredients'].append(pluralIng)
                                sessionIngredients.append(each)
                            else: 
                                session_attr['badingredients'].append(each)
                        else:
                            session_attr['ingredients'].append(each)
                            sessionIngredients.append(each)
                else:
                    #display user with original ingredient
                    sessionIngredients.append(ingredient)
                    session_attr['ingredients'].append(pluralIng)
            else:
                sessionIngredients.append(ingredient)
                session_attr['ingredients'].append(ingredient)
        
        badIngredients = session_attr['badingredients']
        bad = sentenceMaker(badIngredients)
        good = sentenceMaker(sessionIngredients)
        if good == "":
            speak_output = ""
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask("If you're unsure of what to do, say help, or repeat what you said.")
                    .response
            )
        speak_output = "added {}".format(good)
        speak_output += "<break time= '0.5s'/> add more ingredients or say search recipes"

        # Display the apl document
        datasources = _load_apl_document("ingredients_data.json")
        for index, val in enumerate(session_attr['ingredients']):
            datasources['textListData']['listItems'].append({"primaryText": val})
        document=_load_apl_document("ingredients_APL.json")
        if get_supported_interfaces(handler_input).alexa_presentation_apl is not None:
            handler_input.response_builder.add_directive(
                RenderDocumentDirective(
                    token="ingredients",
                    document=document,
                    datasources=datasources
                )
        )
        session_attr['display_ingredients_documents'] = [datasources, document]
        bad = []
        sessionIngredients = []
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask('Continue adding ingredients or say search recipes at any time.')
                .response
        )

class removeIngredientsIntentHandler(AbstractRequestHandler):
    """Handler for removing ingredients."""
    
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("removeIngredientsIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        if len(session_attr["ingredients"])<1: 
            speak_output = "You have zero ingredients. start by adding some!"
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask("continue adding some ingredients and say search when ready")
                    .response
            )
        slots = handler_input.request_envelope.request.intent.slots
        session_attr = handler_input.attributes_manager.session_attributes
        ing = slots["ingredient"].value
        if ing in session_attr["ingredients"]:
            speak_output = 'removed {ing} from ingredients.'.format(ing=ing)
            index = session_attr["ingredients"].index(ing)
            removedItem = session_attr["ingredients"].remove(ing)
            session_attr['display_ingredients_documents'][0]['textListData']['listItems'].pop(index)
            datasources = session_attr['display_ingredients_documents'][0]
            apl = session_attr['display_ingredients_documents'][1]
            handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document = apl,
                        datasources = datasources
                        )
                )
            session_attr['display_ingredients_documents'] = [datasources,apl]
        else:
            speak_output = "{ing} is not one of your ingredients".format(ing=ing)
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("Continue adding ingredients or search recipes")
                .response
        )