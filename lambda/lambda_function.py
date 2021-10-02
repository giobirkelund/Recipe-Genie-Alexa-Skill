"""
lambda_function.py
The lambda function which runs recipe genie. 
The classes witihin this module are the bare bones for the alexa skill.
They handle things such as startup, fallback, and ending, as well as initializing intents.
"""
# Standard 
import logging

# Internal
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_core.utils import get_supported_interfaces
from ask_sdk_model.interfaces.alexa.presentation.apl import RenderDocumentDirective
from helper_functions import *
from intents.ingredients import *
from intents.recipes import *

# Globals
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
    
class LaunchRequestHandler(AbstractRequestHandler):
    """
    Handler which runs when skill is launched. 
    Prompt user to start adding ingredients, and initialize attributes.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr["ingredients"] = [] #create an empty ingredients list.
        session_attr["recipeIndex"] = 0 #initialize index
        session_attr["cuisine"] = None
        session_attr["recipes"] = []
        session_attr['selectedIndex'] = None
        
        speak_output = "Welcome to Recipe Genie! Tell us some ingredients you have at home and we'll find you recipes using them."
        if session_attr["ingredients"] ==[]:
            reprompt = "Begin adding ingredients to the search and say search recipes when ready!"
        else:
            reprompt = "Ready to search? say search recipes. If not, tell us some more ingredients!"
            
        datasources = _load_apl_document("launch_data.json")
            
        if get_supported_interfaces(handler_input).alexa_presentation_apl is not None:
            handler_input.response_builder.add_directive(
                RenderDocumentDirective(
                    token="launch",
                    document=_load_apl_document("launch_APL.json"),
                    datasources=datasources
                )
        )
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt)
                .response
                
        )
        
class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "I didn't quite catch what you said, could you repeat that?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("If you're unsure of what to do, say help, or repeat what you said.")
                .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "The steps to search for a recipe are first to add ingredients and search for recipes. After that, select a the current recipe or hear next recipe. Once you've selected a recipe, you can choose to hear ingredients, hear instructions, or send recipe to phone."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("If you would like to hear the help message again, say help. You can always continue adding ingredients at any time, then searching again.")
                .response
        )

class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        return (
        handler_input.response_builder.response
        )

class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session  for the user to respond")
                .response
        )

class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(selectCuisineIntentHandler())
sb.add_request_handler(addIngredientsIntentHandler())
sb.add_request_handler(SendEventHandler())
sb.add_request_handler(removeIngredientsIntentHandler())
sb.add_request_handler(displayRecipesIntentHandler())
sb.add_request_handler(selectRecipeIntentHandler())
sb.add_request_handler(ingredientsIntentHandler())
sb.add_request_handler(instructionsIntentHandler())
sb.add_request_handler(sendRecipeIntentHandler())
sb.add_request_handler(RepeatStepIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())
lambda_handler = sb.lambda_handler()
