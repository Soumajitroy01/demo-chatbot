import os
import json
import logging
import argparse
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
import config
from ngrok_manager import start_ngrok
from twilio_handler import initialize_twilio_client, make_outbound_call, call_sales_prospects
from sales_bot import get_user_info_from_call, generate_response, generate_introduction, generate_closing
from conversation import detect_conversation_end, reset_conversation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

@app.route("/voice", methods=['POST'])
def voice_webhook():
    """Handle incoming voice calls or answered outbound calls."""
    # Create a TwiML response
    response = VoiceResponse()
    
    # Get call information
    call_sid = request.values.get('CallSid', '')
    caller = request.values.get('From', '')
    
    logger.info(f"Received call from {caller} with SID: {call_sid}")
    
    # Generate introduction for the call
    user_info = get_user_info_from_call(call_sid, caller)
    introduction = generate_introduction(call_sid, user_info)
    
    # Add the introduction to the TwiML response with Amazon Polly Neural voice
    response.say(introduction, voice="Polly.Joanna-Neural")
    
    # Add a Gather to collect customer speech
    gather = Gather(
        input='speech',
        action='/transcribe',
        speechTimeout='auto',
        speechModel='experimental_conversations',
        language='en-US',
        hints=','.join(config.CLOSING_INDICATORS)  # Help Twilio recognize closing phrases
    )
    
    # Add instructions to the Gather
    gather.say("Please speak after the tone.", voice="Polly.Joanna-Neural")
    
    # Add the Gather to the response
    response.append(gather)
    
    # If customer doesn't say anything, try again
    response.redirect('/voice')
    
    return str(response)

@app.route("/transcribe", methods=['POST'])
def transcribe_webhook():
    """Handle the transcribed speech from the customer."""
    # Get the transcribed speech from Twilio
    transcription = request.values.get('SpeechResult', '')
    call_sid = request.values.get('CallSid', '')
    
    logger.info(f"Transcription for call {call_sid}: {transcription}")
    
    # Check if the conversation should end
    is_conversation_end = detect_conversation_end(transcription)
    
    # Create a TwiML response
    response = VoiceResponse()
    
    if is_conversation_end:
        # Generate closing statement
        user_info = get_user_info_from_call(call_sid)
        closing = generate_closing(call_sid, user_info)
        response.say(closing, voice="Polly.Joanna-Neural")
        response.hangup()
    else:
        # Get user info from the call
        user_info = get_user_info_from_call(call_sid)
        
        # Generate response
        bot_response = generate_response(transcription, call_sid, user_info)
        
        # Say the response
        response.say(bot_response, voice="Polly.Joanna-Neural")
        
        # Add another Gather for continued conversation
        gather = Gather(
            input='speech',
            action='/transcribe',
            speechTimeout='auto',
            speechModel='experimental_conversations',
            language='en-US',
            hints=','.join(config.CLOSING_INDICATORS)
        )
        response.append(gather)
        
        # If customer doesn't say anything, try again
        response.redirect('/voice')
    
    return str(response)

@app.route("/call-status", methods=['POST'])
def call_status_webhook():
    """Handle call status callbacks from Twilio."""
    call_sid = request.values.get('CallSid', '')
    call_status = request.values.get('CallStatus', '')
    
    logger.info(f"Call {call_sid} status: {call_status}")
    
    # You can add logic here to handle different call statuses
    # (e.g., completed, busy, failed, no-answer)
    
    return "OK"

def main():
    """Main function with command line arguments."""
    parser = argparse.ArgumentParser(description=f"{config.BOT_NAME} - Sales Representative for {config.COMPANY_NAME}")
    parser.add_argument("--reset", action="store_true", help="Reset conversation history")
    parser.add_argument("--mode", choices=["server", "outbound"], default="server", 
                        help="Run as webhook server or make outbound calls")
    parser.add_argument("--port", type=int, default=config.FLASK_PORT, help="Port for webhook server")
    parser.add_argument("--call", type=str, help="Phone number to call in outbound mode")
    parser.add_argument("--prospects-file", type=str, help="JSON file with prospects list for outbound calls")
    
    args = parser.parse_args()
    
    if args.reset:
        reset_conversation()
    
    # Override port if specified
    if args.port:
        config.FLASK_PORT = args.port
    
    # Set up ngrok tunnel
    public_url = start_ngrok()
    
    if not public_url:
        logger.error("Failed to establish ngrok tunnel. Exiting.")
        return
    
    logger.info(f"Public URL: {public_url}")
    
    if args.mode == "server":
        # Run Flask app to handle Twilio webhooks
        logger.info(f"Starting {config.BOT_NAME} webhook server on port {config.FLASK_PORT}...")
        app.run(host='0.0.0.0', port=config.FLASK_PORT)
    
    elif args.mode == "outbound":
        if args.call:
            # Make a single outbound call
            logger.info(f"Making outbound call to {args.call}...")
            make_outbound_call(args.call, public_url)
        
        elif args.prospects_file:
            # Make calls to a list of prospects
            try:
                with open(args.prospects_file, 'r') as f:
                    prospects = json.load(f)
                
                logger.info(f"Loaded {len(prospects)} prospects from {args.prospects_file}")
                call_sales_prospects(prospects, public_url)
            
            except Exception as e:
                logger.error(f"Error loading prospects file: {e}")
                logger.error("Please provide a valid JSON file with a list of prospects")
        
        else:
            logger.error("Please provide either --call or --prospects-file for outbound mode")

if __name__ == "__main__":
    main()
