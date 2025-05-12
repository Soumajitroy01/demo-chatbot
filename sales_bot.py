import logging
from openai import OpenAI
import config
from conversation import load_conversation_history, save_conversation_history, detect_hesitation

logger = logging.getLogger(__name__)

def get_user_info_from_call(call_sid=None, phone_number=None):
    """
    Get user information based on the call.
    In a real implementation, you would look up the caller in your CRM system.
    
    Args:
        call_sid: The Twilio Call SID
        phone_number: The caller's phone number
    """
    # For demonstration purposes, return default user info
    # In a real implementation, you would look up the caller in your database
    return {
        "name": "Michael",
        "last_visit_date": "April 10, 2025",
        "products_viewed": "Smart Home Hub, Voice Assistant Speaker",
        "previous_purchases": "Annual Premium Subscription (expired last month)",
        "interests": "Home automation, Music streaming, Productivity apps",
        "age_group": "30-45",
        "device_usage": "Smartphone, Laptop, Smart TV"
    }

def generate_response(input_text, call_sid=None, user_info=None):
    """
    Generate a response based on input text using OpenAI model.
    
    Args:
        input_text: Input text to generate response from
        call_sid: The Twilio Call SID for conversation tracking
        user_info: User information dictionary
    """
    try:
        logger.info("Generating response...")
        
        # Initialize the client with global configuration
        client = OpenAI(
            base_url=config.API_BASE_URL,
            api_key=config.API_KEY,
        )
        
        # Load conversation history
        conversation = load_conversation_history(call_sid, user_info)
        
        # Check for hesitation and add special handling if needed
        if detect_hesitation(input_text):
            # Add a special instruction for handling hesitation with flattery
            conversation.append({
                "role": "system",
                "content": f"The customer is showing hesitation. Use flattery and personalization to make them feel special. Compliment their taste, insight, or decision-making process. Make them feel valued and understood. Focus on how they specifically will benefit from our product in ways that align with their interests and lifestyle. Use phrases like 'Someone with your taste would appreciate...' or 'Given your interest in {user_info.get('interests', 'technology')}, you'd especially enjoy...' to make them feel special."
            })
        
        # Add user message to conversation
        conversation.append({
            "role": "user",
            "content": input_text
        })
        
        # Generate response using global model name
        response = client.chat.completions.create(
            messages=conversation,
            model=config.MODEL_NAME,
            temperature=0.7,  # Higher temperature for more creative sales responses
            max_tokens=150,
            top_p=0.9
        )
        
        result = response.choices[0].message.content
        
        # Add assistant response to conversation
        conversation.append({
            "role": "assistant",
            "content": result
        })
        
        # Remove any temporary system messages for hesitation handling
        conversation = [msg for msg in conversation 
                       if not (msg["role"] == "system" and "The customer is showing hesitation" in msg.get("content", ""))]
        
        # Save updated conversation
        save_conversation_history(conversation, call_sid)
        
        logger.info(f"Response: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error in response generation: {e}")
        return f"I'm sorry, I couldn't generate a response at this time. Please try again."

def generate_introduction(call_sid=None, user_info=None):
    """Generate an introduction for the sales bot."""
    try:
        # Initialize the client with global configuration
        client = OpenAI(
            base_url=config.API_BASE_URL,
            api_key=config.API_KEY,
        )
        
        # Initialize a new conversation with sales context
        conversation = load_conversation_history(call_sid, user_info)
        
        # Create a personalized introduction prompt based on user info
        intro_prompt = f"As {config.BOT_NAME}, generate a warm, personalized introduction to start the sales call."
        
        if user_info:
            if user_info.get('name'):
                intro_prompt += f" Address {user_info.get('name')} by name."
            
            if user_info.get('last_visit_date'):
                intro_prompt += f" Mention their last visit on {user_info.get('last_visit_date')}."
            
            if user_info.get('products_viewed'):
                intro_prompt += f" Reference their interest in {user_info.get('products_viewed')}."
            
            if user_info.get('previous_purchases'):
                intro_prompt += f" Acknowledge their previous purchase of {user_info.get('previous_purchases')}."
        
        intro_prompt += " Ask an open-ended question about their needs or interests. Be friendly, conversational, and enthusiastic. Keep it concise (2-3 sentences)."
        
        # Add the prompt for generating the introduction
        conversation.append({
            "role": "user",
            "content": intro_prompt
        })
        
        # Generate introduction using global model name
        response = client.chat.completions.create(
            messages=conversation,
            model=config.MODEL_NAME,
            temperature=0.7,
            max_tokens=150,
            top_p=0.9
        )
        
        introduction = response.choices[0].message.content
        
        # Add the introduction to the conversation history
        conversation.pop()  # Remove the prompt
        conversation.append({
            "role": "assistant",
            "content": introduction
        })
        
        # Save the conversation with the introduction
        save_conversation_history(conversation, call_sid)
        
        return introduction
        
    except Exception as e:
        logger.error(f"Error generating introduction: {e}")
        return f"Hello, this is {config.BOT_NAME} from {config.COMPANY_NAME}. How can I help you today?"

def generate_closing(call_sid=None, user_info=None):
    """Generate a closing statement for the sales bot."""
    try:
        # Initialize the client with global configuration
        client = OpenAI(
            base_url=config.API_BASE_URL,
            api_key=config.API_KEY,
        )
        
        # Load conversation history
        conversation = load_conversation_history(call_sid, user_info)
        
        # Add a prompt for generating the closing
        conversation.append({
            "role": "system",
            "content": "The conversation is ending. Generate a warm, friendly closing statement that thanks the customer for their time, summarizes any commitments or next steps, and includes a clear call to action. Mention a special offer or limited-time discount if appropriate to encourage immediate action. Keep it concise and personalized."
        })
        
        # Generate closing using global model name
        response = client.chat.completions.create(
            messages=conversation,
            model=config.MODEL_NAME,
            temperature=0.7,
            max_tokens=150,
            top_p=0.9
        )
        
        closing = response.choices[0].message.content
        
        return closing
        
    except Exception as e:
        logger.error(f"Error generating closing: {e}")
        return f"Thank you for your time today. If you'd like to try our products, we're offering a special 15% discount for new customers. Just visit our website or call us back when you're ready. Have a wonderful day!"
