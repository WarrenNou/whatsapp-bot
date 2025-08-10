import os
import json
import logging
import re
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import redis
import uuid
from functools import wraps
from flask import Flask, request, jsonify, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from openai import OpenAI
from openai.types.chat import ChatCompletion
import pytz
from dotenv import load_dotenv
from fx_trader import fx_trader
from enhanced_scheduler import initialize_enhanced_scheduler, enhanced_scheduler
from external_keepalive import external_keep_alive, print_setup_instructions

# Load environment variables
load_dotenv()

# Configure logging with rotating file handler
import logging.handlers

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = logging.handlers.RotatingFileHandler(
    'logs/whatsapp_bot.log', 
    maxBytes=10485760,  # 10MB
    backupCount=5
)
log_handler.setFormatter(log_formatter)

# Add console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(console_handler)

# Initialize Flask app
app = Flask(__name__)

# Setup rate limiting with fallback
def get_limiter_storage():
    """Get appropriate storage for rate limiter based on Redis availability"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # On Render, use memory storage initially to prevent crashes
    if os.getenv('RENDER'):
        logger.info("Using memory storage for rate limiter on Render deployment")
        return "memory://"
    
    # For local development, try Redis first
    try:
        import redis
        test_client = redis.from_url(redis_url, socket_connect_timeout=5)
        test_client.ping()
        logger.info("Using Redis storage for rate limiter")
        return redis_url
    except Exception as e:
        logger.warning(f"Redis not available for rate limiter, using memory storage: {e}")
        return "memory://"

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=get_limiter_storage()
)

# Error handling for Redis connection
redis_client = None

def initialize_redis():
    """Initialize Redis with retry logic and fallback"""
    global redis_client
    
    # More aggressive retry settings for cloud deployment
    max_retries = 15 if os.getenv('RENDER') else 5
    base_delay = 5 if os.getenv('RENDER') else 3
    max_delay = 120  # Max 2 minutes between retries
    
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # Log environment info
    logger.info(f"Initializing Redis with URL: {redis_url[:20]}...")
    logger.info(f"Cloud deployment: {'Yes' if os.getenv('RENDER') else 'No'}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to Redis (attempt {attempt + 1}/{max_retries})")
            
            if redis_url and redis_url != 'redis://localhost:6379':
                # Cloud Redis URL provided
                client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=30,  # Much longer timeout for cloud
                    socket_timeout=30,
                    retry_on_timeout=True,
                    health_check_interval=60
                )
            else:
                # Local Redis
                redis_pool = redis.ConnectionPool(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=15,
                    socket_timeout=15,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                client = redis.Redis(connection_pool=redis_pool)
            
            # Test the connection with more retries for cloud
            ping_retries = 5 if os.getenv('RENDER') else 3
            for ping_attempt in range(ping_retries):
                try:
                    client.ping()
                    logger.info("Redis connection successful!")
                    redis_client = client
                    return redis_client
                except Exception as ping_e:
                    if ping_attempt < ping_retries - 1:
                        wait_time = 3 if os.getenv('RENDER') else 1
                        logger.warning(f"Redis ping failed, retrying in {wait_time}s... ({ping_e})")
                        time.sleep(wait_time)
                    else:
                        raise ping_e
            
        except Exception as e:
            logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("All Redis connection attempts failed, using fallback client")
                redis_client = create_fallback_redis()
                return redis_client

def create_fallback_redis():
    """Create a fallback Redis client that doesn't crash the app"""
    class FallbackRedis:
        def ping(self):
            return True
        def get(self, key):
            return None
        def set(self, key, value, ex=None):
            return True
        def delete(self, key):
            return 0
        def exists(self, key):
            return False
        def lrange(self, key, start, end):
            return []
        def lpush(self, key, *values):
            return 1
        def rpush(self, key, *values):
            return 1
        def ltrim(self, key, start, end):
            return True
        def lset(self, key, index, value):
            return True
        def expire(self, key, time):
            return True
        def incr(self, key):
            return 1
        def decr(self, key):
            return 0
        def hget(self, name, key):
            return None
        def hset(self, name, key, value):
            return 1
        def hdel(self, name, *keys):
            return 0
    
    logger.warning("Using fallback Redis client - some features may be limited")
    return FallbackRedis()

# Initialize Redis connection when module loads - but don't block on failure
try:
    if not os.getenv('RENDER'):
        # Only initialize immediately for local development
        initialize_redis()
    else:
        # For Render, start with fallback and connect later
        logger.info("Render deployment detected - starting with fallback Redis")
        redis_client = create_fallback_redis()
except Exception as e:
    logger.warning(f"Initial Redis initialization failed: {e}")
    redis_client = create_fallback_redis()

# Production-friendly initialization using threading
import threading
import atexit

def initialize_background_services():
    """Initialize background services for production"""
    global redis_client
    
    try:
        logger.info("Initializing background services for production...")
        
        # Try to connect to real Redis if we're using fallback
        if os.getenv('RENDER') and isinstance(redis_client, type(create_fallback_redis())):
            logger.info("Attempting to upgrade from fallback Redis to real Redis...")
            try:
                real_redis = initialize_redis()
                if real_redis and hasattr(real_redis, 'ping'):
                    real_redis.ping()
                    redis_client = real_redis
                    logger.info("Successfully upgraded to real Redis connection!")
            except Exception as e:
                logger.warning(f"Failed to upgrade to real Redis, continuing with fallback: {e}")
        
        # Initialize enhanced scheduler with keep-alive (use environment PORT)
        server_port = os.getenv('PORT', 5000)
        server_url = f"http://0.0.0.0:{server_port}"
        
        try:
            initialize_enhanced_scheduler(twilio_client, server_url=server_url)
            logger.info("Enhanced scheduler initialized - Broadcasting at 9AM, 3PM, 7PM Gulf Time + Keep-alive")
        except Exception as e:
            logger.warning(f"Enhanced scheduler initialization failed: {e}")
        
        # Start external keep-alive service
        try:
            external_keep_alive.start()
            logger.info("External keep-alive service started")
        except Exception as e:
            logger.warning(f"External keep-alive service failed to start: {e}")
        
        logger.info("Background services initialization complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize background services: {e}")

# Background Redis connection upgrader for Render
def redis_upgrader():
    """Periodically try to upgrade from fallback Redis to real Redis"""
    global redis_client
    
    if not os.getenv('RENDER'):
        return
        
    for attempt in range(12):  # Try for about 10 minutes
        try:
            time.sleep(50)  # Wait 50 seconds between attempts
            
            # Skip if we already have a real Redis connection
            if not isinstance(redis_client, type(create_fallback_redis())):
                logger.info("Real Redis connection already established")
                break
                
            logger.info(f"Redis upgrade attempt {attempt + 1}/12...")
            real_redis = initialize_redis()
            if real_redis and hasattr(real_redis, 'ping'):
                real_redis.ping()
                redis_client = real_redis
                logger.info("Successfully upgraded to real Redis connection!")
                break
                
        except Exception as e:
            logger.warning(f"Redis upgrade attempt {attempt + 1} failed: {e}")
    
    logger.info("Redis upgrader task completed")

# Initialize background services in a separate thread for production
def delayed_initialization():
    """Delay initialization to allow app to start first"""
    # Wait longer on Render to allow Redis service to be ready
    wait_time = 30 if os.getenv('RENDER') else 10
    logger.info(f"Waiting {wait_time} seconds for services to be ready...")
    time.sleep(wait_time)
    initialize_background_services()

# Start background initialization if not running in main thread
if os.getenv('RENDER'):  # Only on Render
    logger.info("Render deployment detected - starting delayed initialization")
    init_thread = threading.Thread(target=delayed_initialization, daemon=True)
    init_thread.start()
    
    # Also start Redis upgrader in background
    redis_thread = threading.Thread(target=redis_upgrader, daemon=True)
    redis_thread.start()
    logger.info("Redis upgrader started in background")
else:
    logger.info("Local deployment - no delayed initialization needed")

# Environment validation
required_env_vars = [
    'TWILIO_ACCOUNT_SID', 
    'TWILIO_AUTH_TOKEN', 
    'OPENAI_API_KEY'
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.critical(error_msg)
    raise EnvironmentError(error_msg)

# Twilio and OpenAI initialization
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')  # Using a more capable model

# Initialize clients with error handling
try:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    logger.info("Twilio client initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize Twilio client: {e}")
    raise

try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize OpenAI client: {e}")
    raise

# Custom exceptions for better error handling
class MemoryError(Exception):
    """Exception raised for errors in the memory operations."""
    pass

class ActionError(Exception):
    """Exception raised for errors in the action operations."""
    pass

class RedisOperationError(Exception):
    """Exception raised for Redis operation errors."""
    pass

# Decorator for Redis error handling
def redis_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.RedisError as e:
            logger.error(f"Redis error in {func.__name__}: {e}")
            raise RedisOperationError(f"Database operation failed: {e}")
    return wrapper

class AdvancedMemoryManager:
    """
    Advanced memory management system with multiple memory types
    and error handling
    """
    
    MEMORY_TYPES = ['personal', 'reminder', 'event', 'contact', 'preference']
    
    @staticmethod
    @redis_error_handler
    def save_long_term_memory(phone_number: str, memory_type: str, content: Any) -> str:
        """
        Save long-term memory for a user
        
        Args:
            phone_number (str): User's phone number
            memory_type (str): Type of memory (personal, work, goals, etc.)
            content (Any): Memory content to store
        
        Returns:
            str: Memory ID
            
        Raises:
            MemoryError: If memory operation fails
            ValueError: If invalid memory type provided
        """
        try:
            # Validate memory type
            if memory_type not in AdvancedMemoryManager.MEMORY_TYPES:
                raise ValueError(f"Invalid memory type: {memory_type}. Allowed types: {AdvancedMemoryManager.MEMORY_TYPES}")
                
            # Sanitize phone number
            phone_number = AdvancedMemoryManager._sanitize_phone(phone_number)
            
            # Generate a unique memory ID
            memory_id = str(uuid.uuid4())
            
            # Prepare memory object
            memory_entry = {
                'id': memory_id,
                'type': memory_type,
                'content': json.dumps(content),
                'created_at': datetime.now(pytz.utc).isoformat(),
                'updated_at': datetime.now(pytz.utc).isoformat()
            }
            
            # Save to Redis list of memories
            redis_key = f"long_term_memory:{phone_number}"
            redis_client.rpush(redis_key, json.dumps(memory_entry))
            
            # Limit memory storage (e.g., keep last 100 memories)
            redis_client.ltrim(redis_key, -100, -1)
            
            # Also save to a memory type-specific index for faster retrieval
            type_key = f"memory_by_type:{phone_number}:{memory_type}"
            redis_client.rpush(type_key, memory_id)
            redis_client.ltrim(type_key, -50, -1)
            
            logger.info(f"Memory saved for {phone_number}: {memory_type} with ID {memory_id}")
            return memory_id
        except ValueError as e:
            # Re-raise validation errors
            raise
        except RedisOperationError as e:
            # Re-raise Redis errors
            raise
        except Exception as e:
            logger.error(f"Error saving long-term memory: {e}")
            raise MemoryError(f"Failed to save memory: {str(e)}")

    @staticmethod
    @redis_error_handler
    def retrieve_long_term_memories(
        phone_number: str, 
        memory_type: Optional[str] = None, 
        limit: int = 10,
        days_back: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve long-term memories for a user with filtering options
        
        Args:
            phone_number (str): User's phone number
            memory_type (Optional[str]): Filter by memory type
            limit (int): Number of memories to retrieve
            days_back (Optional[int]): Only retrieve memories from the last X days
        
        Returns:
            List of memory entries
            
        Raises:
            MemoryError: If memory retrieval fails
        """
        try:
            # Sanitize phone number
            phone_number = AdvancedMemoryManager._sanitize_phone(phone_number)
            
            # Optimize retrieval if memory_type is specified
            if memory_type:
                if memory_type not in AdvancedMemoryManager.MEMORY_TYPES:
                    logger.warning(f"Invalid memory type requested: {memory_type}")
                    return []
                
                # Get memory IDs from type-specific index
                type_key = f"memory_by_type:{phone_number}:{memory_type}"
                memory_ids = redis_client.lrange(type_key, -limit, -1)
                
                # Early return if no memories found
                if not memory_ids:
                    return []
                
                # Get all memories
                redis_key = f"long_term_memory:{phone_number}"
                all_memories = redis_client.lrange(redis_key, 0, -1)
                
                # Filter by memory IDs
                parsed_memories = []
                for memory_json in all_memories:
                    memory = json.loads(memory_json)
                    if memory['id'] in memory_ids:
                        # Apply time filter if specified
                        if days_back:
                            created_date = datetime.fromisoformat(memory['created_at'])
                            cutoff_date = datetime.now(pytz.utc) - timedelta(days=days_back)
                            if created_date < cutoff_date:
                                continue
                        
                        memory['content'] = json.loads(memory['content'])
                        parsed_memories.append(memory)
                        
                        # Stop if we've found enough memories
                        if len(parsed_memories) >= limit:
                            break
                
                return parsed_memories
            else:
                # Get all memories and filter
                redis_key = f"long_term_memory:{phone_number}"
                memories = redis_client.lrange(redis_key, -limit*2, -1)  # Get more to allow for filtering
                
                # Parse and filter memories
                parsed_memories = []
                for memory_json in memories:
                    memory = json.loads(memory_json)
                    
                    # Apply time filter if specified
                    if days_back:
                        created_date = datetime.fromisoformat(memory['created_at'])
                        cutoff_date = datetime.now(pytz.utc) - timedelta(days=days_back)
                        if created_date < cutoff_date:
                            continue
                    
                    memory['content'] = json.loads(memory['content'])
                    parsed_memories.append(memory)
                    
                    # Limit results
                    if len(parsed_memories) >= limit:
                        break
                
                return parsed_memories
        except RedisOperationError as e:
            # Re-raise Redis errors
            raise
        except Exception as e:
            logger.error(f"Error retrieving long-term memories: {e}")
            raise MemoryError(f"Failed to retrieve memories: {str(e)}")
    
    @staticmethod
    @redis_error_handler
    def update_memory(phone_number: str, memory_id: str, updated_content: Dict) -> bool:
        """
        Update an existing memory
        
        Args:
            phone_number (str): User's phone number
            memory_id (str): ID of the memory to update
            updated_content (Dict): New content for the memory
            
        Returns:
            bool: Success status
            
        Raises:
            MemoryError: If memory update fails
        """
        try:
            # Sanitize phone number
            phone_number = AdvancedMemoryManager._sanitize_phone(phone_number)
            
            redis_key = f"long_term_memory:{phone_number}"
            memories = redis_client.lrange(redis_key, 0, -1)
            
            for i, memory_json in enumerate(memories):
                memory = json.loads(memory_json)
                if memory['id'] == memory_id:
                    # Update content and timestamp
                    memory['content'] = json.dumps(updated_content)
                    memory['updated_at'] = datetime.now(pytz.utc).isoformat()
                    
                    # Replace the memory in the list
                    redis_client.lset(redis_key, i, json.dumps(memory))
                    logger.info(f"Memory {memory_id} updated for {phone_number}")
                    return True
            
            logger.warning(f"Memory {memory_id} not found for {phone_number}")
            return False
        except RedisOperationError as e:
            # Re-raise Redis errors
            raise
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            raise MemoryError(f"Failed to update memory: {str(e)}")
    
    @staticmethod
    def _sanitize_phone(phone_number: str) -> str:
        """Sanitize phone number to ensure consistent format"""
        # Remove WhatsApp prefix if present
        return phone_number.replace('whatsapp:', '').strip()

class ActionHandler:
    """
    Advanced action handling system with validation, execution tracking and error handling
    """
    ACTIONS = {
        'create_reminder': {
            'description': 'Create a personal reminder',
            'required_params': ['message', 'date'],
            'optional_params': ['time', 'priority']
        },
        'send_message': {
            'description': 'Send a message to another contact',
            'required_params': ['recipient', 'message'],
            'optional_params': ['template_name']
        },
        'schedule_event': {
            'description': 'Schedule an event in user\'s calendar',
            'required_params': ['title', 'date', 'time'],
            'optional_params': ['duration', 'description', 'location']
        },
        'update_preference': {
            'description': 'Update user preference setting',
            'required_params': ['preference_name', 'preference_value'],
            'optional_params': ['category']
        },
        'set_goal': {
            'description': 'Set a personal or professional goal',
            'required_params': ['goal_description', 'target_date'],
            'optional_params': ['milestones', 'priority', 'category']
        }
    }

    @staticmethod
    def validate_action(action_name: str, params: Dict) -> Dict:
        """
        Validate action parameters
        
        Args:
            action_name (str): Name of the action
            params (Dict): Action parameters
        
        Returns:
            Dict with validation result
        """
        if action_name not in ActionHandler.ACTIONS:
            return {
                'valid': False, 
                'error': f"Unknown action: {action_name}"
            }
        
        action_details = ActionHandler.ACTIONS[action_name]
        missing_params = [
            param for param in action_details['required_params'] 
            if param not in params
        ]
        
        if missing_params:
            return {
                'valid': False,
                'error': f"Missing required parameters: {', '.join(missing_params)}"
            }
        
        # Validate date format if present
        if 'date' in params:
            try:
                # Try parsing the date
                datetime.strptime(params['date'], '%Y-%m-%d')
            except ValueError:
                return {
                    'valid': False,
                    'error': f"Invalid date format for 'date'. Use YYYY-MM-DD format."
                }
        
        # Validate time format if present
        if 'time' in params:
            try:
                # Try parsing the time
                datetime.strptime(params['time'], '%H:%M')
            except ValueError:
                return {
                    'valid': False,
                    'error': f"Invalid time format for 'time'. Use 24-hour HH:MM format."
                }
                
        return {'valid': True}

    @staticmethod
    @redis_error_handler
    def execute_action(
        phone_number: str, 
        action_name: str, 
        params: Dict
    ) -> Dict:
        """
        Execute a specific action with extensive error handling
        
        Args:
            phone_number (str): User's phone number
            action_name (str): Name of the action to execute
            params (Dict): Action parameters
        
        Returns:
            Dict with action execution result
            
        Raises:
            ActionError: If action execution fails
        """
        try:
            # Start tracking the action execution
            action_id = str(uuid.uuid4())
            action_tracking = {
                'id': action_id,
                'phone_number': phone_number,
                'action_name': action_name,
                'params': params,
                'status': 'pending',
                'created_at': datetime.now(pytz.utc).isoformat()
            }
            
            # Log action start
            logger.info(f"Starting action execution: {action_name} for {phone_number} - ID: {action_id}")
            
            # Save action tracking to Redis
            redis_client.set(
                f"action:{action_id}", 
                json.dumps(action_tracking),
                ex=86400  # Expire after 24 hours
            )
            
            # Validate action
            validation = ActionHandler.validate_action(action_name, params)
            if not validation['valid']:
                action_tracking['status'] = 'failed'
                action_tracking['error'] = validation['error']
                action_tracking['completed_at'] = datetime.now(pytz.utc).isoformat()
                redis_client.set(
                    f"action:{action_id}", 
                    json.dumps(action_tracking),
                    ex=86400
                )
                return validation
            
            # Action-specific logic
            result = {}
            
            if action_name == 'create_reminder':
                # Sanitize parameters
                reminder = {
                    'message': params['message'].strip(),
                    'date': params['date'],
                    'time': params.get('time', '09:00'),  # Default to 9 AM if time not specified
                    'priority': params.get('priority', 'normal'),
                    'status': 'pending',
                    'created_at': datetime.now(pytz.utc).isoformat()
                }
                
                try:
                    memory_id = AdvancedMemoryManager.save_long_term_memory(
                        phone_number, 
                        'reminder', 
                        reminder
                    )
                    
                    # Schedule notification if necessary
                    # (implementation depends on your notification system)
                    
                    result = {
                        'success': True,
                        'message': f"Reminder created: {params['message']}",
                        'memory_id': memory_id,
                        'reminder_details': reminder
                    }
                except MemoryError as e:
                    raise ActionError(f"Failed to save reminder: {str(e)}")
            
            elif action_name == 'send_message':
                # Sanitize parameters
                recipient = params['recipient']
                if not recipient.startswith('whatsapp:'):
                    recipient = f"whatsapp:{recipient}"
                
                message_body = params['message'].strip()
                
                # Send message via Twilio
                try:
                    message = twilio_client.messages.create(
                        from_=TWILIO_WHATSAPP_NUMBER,
                        body=message_body,
                        to=recipient
                    )
                    
                    # Record the message in memory
                    sent_message = {
                        'recipient': recipient,
                        'message': message_body,
                        'sid': message.sid,
                        'sent_at': datetime.now(pytz.utc).isoformat()
                    }
                    
                    AdvancedMemoryManager.save_long_term_memory(
                        phone_number, 
                        'contact', 
                        {
                            'type': 'sent_message',
                            'data': sent_message
                        }
                    )
                    
                    result = {
                        'success': True,
                        'message': f"Message sent to {recipient}",
                        'sid': message.sid
                    }
                except TwilioRestException as e:
                    error_msg = f"Twilio error: {e.msg}"
                    logger.error(f"Failed to send message via Twilio: {error_msg}")
                    raise ActionError(error_msg)
            
            elif action_name == 'schedule_event':
                # Sanitize parameters
                event = {
                    'title': params['title'].strip(),
                    'date': params['date'],
                    'time': params['time'],
                    'duration': params.get('duration', '60'),  # Default 60 minutes
                    'description': params.get('description', ''),
                    'location': params.get('location', ''),
                    'status': 'scheduled',
                    'created_at': datetime.now(pytz.utc).isoformat()
                }
                
                try:
                    memory_id = AdvancedMemoryManager.save_long_term_memory(
                        phone_number, 
                        'event', 
                        event
                    )
                    
                    result = {
                        'success': True,
                        'message': f"Event scheduled: {params['title']}",
                        'memory_id': memory_id,
                        'event_details': event
                    }
                except MemoryError as e:
                    raise ActionError(f"Failed to save event: {str(e)}")
            
            elif action_name == 'update_preference':
                # Sanitize parameters
                preference = {
                    'name': params['preference_name'].strip().lower(),
                    'value': params['preference_value'],
                    'category': params.get('category', 'general'),
                    'updated_at': datetime.now(pytz.utc).isoformat()
                }
                
                try:
                    # Check if this preference already exists
                    existing_memories = AdvancedMemoryManager.retrieve_long_term_memories(
                        phone_number, 
                        'preference', 
                        limit=10
                    )
                    
                    found = False
                    for memory in existing_memories:
                        if (memory['content']['name'] == preference['name'] and 
                            memory['content']['category'] == preference['category']):
                            # Update existing preference
                            AdvancedMemoryManager.update_memory(
                                phone_number, 
                                memory['id'], 
                                preference
                            )
                            found = True
                            memory_id = memory['id']
                            break
                    
                    if not found:
                        # Create new preference
                        memory_id = AdvancedMemoryManager.save_long_term_memory(
                            phone_number, 
                            'preference', 
                            preference
                        )
                    
                    result = {
                        'success': True,
                        'message': f"Preference updated: {params['preference_name']}",
                        'memory_id': memory_id,
                        'preference_details': preference
                    }
                except MemoryError as e:
                    raise ActionError(f"Failed to save preference: {str(e)}")
            
            elif action_name == 'set_goal':
                # Sanitize parameters
                goal = {
                    'description': params['goal_description'].strip(),
                    'target_date': params['target_date'],
                    'milestones': params.get('milestones', []),
                    'priority': params.get('priority', 'medium'),
                    'category': params.get('category', 'personal'),
                    'status': 'active',
                    'progress': 0,
                    'created_at': datetime.now(pytz.utc).isoformat()
                }
                
                try:
                    memory_id = AdvancedMemoryManager.save_long_term_memory(
                        phone_number, 
                        'personal', 
                        {
                            'type': 'goal',
                            'data': goal
                        }
                    )
                    
                    result = {
                        'success': True,
                        'message': f"Goal set: {params['goal_description']}",
                        'memory_id': memory_id,
                        'goal_details': goal
                    }
                except MemoryError as e:
                    raise ActionError(f"Failed to save goal: {str(e)}")
            
            else:
                raise ActionError(f"Unhandled action: {action_name}")
            
            # Update action tracking with successful completion
            action_tracking['status'] = 'completed'
            action_tracking['result'] = result
            action_tracking['completed_at'] = datetime.now(pytz.utc).isoformat()
            redis_client.set(
                f"action:{action_id}", 
                json.dumps(action_tracking),
                ex=86400
            )
            
            logger.info(f"Action completed successfully: {action_name} - ID: {action_id}")
            return result
        
        except ActionError as e:
            # Re-raise action-specific errors
            logger.error(f"Action error: {e}")
            
            # Update action tracking
            if 'action_tracking' in locals() and 'action_id' in locals():
                action_tracking['status'] = 'failed'
                action_tracking['error'] = str(e)
                action_tracking['completed_at'] = datetime.now(pytz.utc).isoformat()
                redis_client.set(
                    f"action:{action_id}", 
                    json.dumps(action_tracking),
                    ex=86400
                )
            
            return {
                'success': False, 
                'error': str(e)
            }
        except RedisOperationError as e:
            logger.error(f"Redis error in action execution: {e}")
            return {
                'success': False, 
                'error': f"Database error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in action execution: {e}", exc_info=True)
            
            # Update action tracking
            if 'action_tracking' in locals() and 'action_id' in locals():
                action_tracking['status'] = 'failed'
                action_tracking['error'] = f"Unexpected error: {str(e)}"
                action_tracking['completed_at'] = datetime.now(pytz.utc).isoformat()
                redis_client.set(
                    f"action:{action_id}", 
                    json.dumps(action_tracking),
                    ex=86400
                )
            
            return {
                'success': False, 
                'error': f"Unexpected error: {str(e)}"
            }

def generate_ai_response_with_action_parsing(
    conversation_history: List[Dict], 
    phone_number: str
) -> Dict:
    """
    Generate AI response with advanced action parsing and error handling
    
    Args:
        conversation_history (List[Dict]): Conversation messages
        phone_number (str): User's phone number
    
    Returns:
        Dict with response and potential action
    """
    try:
        # Retrieve recent memories for context
        recent_memories = []
        try:
            # Get general memories from the last 30 days
            recent_memories = AdvancedMemoryManager.retrieve_long_term_memories(
                phone_number,
                days_back=30,
                limit=5
            )
            
            # Get all reminders (active ones are important)
            reminders = AdvancedMemoryManager.retrieve_long_term_memories(
                phone_number,
                memory_type='reminder',
                limit=5
            )
            
            # Get active events
            events = AdvancedMemoryManager.retrieve_long_term_memories(
                phone_number,
                memory_type='event',
                limit=5
            )
            
            # Get user preferences
            preferences = AdvancedMemoryManager.retrieve_long_term_memories(
                phone_number,
                memory_type='preference',
                limit=10
            )
            
            # Combine all memories
            recent_memories = recent_memories + reminders + events + preferences
        except MemoryError as e:
            logger.error(f"Memory retrieval error: {e}")
            # Continue with empty memories rather than failing the response
            recent_memories = []
        
        # Prepare memory context
        memory_context = "No recent memories available."
        if recent_memories:
            memory_sections = []
            
            # Group memories by type
            memory_by_type = {}
            for memory in recent_memories:
                memory_type = memory['type']
                if memory_type not in memory_by_type:
                    memory_by_type[memory_type] = []
                memory_by_type[memory_type].append(memory)
            
            # Format each memory type section
            for memory_type, memories in memory_by_type.items():
                formatted_memories = [
                    f"- {json.dumps(memory['content'], ensure_ascii=False)}" 
                    for memory in memories
                ]
                memory_sections.append(
                    f"{memory_type.capitalize()} memories:\n" + 
                    "\n".join(formatted_memories)
                )
            
            memory_context = "\n\n".join(memory_sections)
        
        # Inject memories into system prompt
        system_prompt = """
        You are a professional FX Trading Assistant specializing in currency exchange between XAF (Central African Franc), XOF (West African Franc) and major currencies (USD, AED, USDT), communicating via WhatsApp.

        Primary Functions:
        - Provide real-time exchange rates with markup included
        - Calculate currency conversions for XAF/USD, XAF/AED, XAF/USDT, XOF/USD, XOF/AED, XOF/USDT
        - Offer professional trading advice and market insights
        - Handle client inquiries about exchange services
        - Guide clients through actual trading process when they want to trade
        
        Trading Information:
        - XAF rates: 9% markup on USD/USDT, 8.5% on AED
        - XOF rates: 3.5% markup (better rates for West Africa)
        - Rates sourced from live market data for accuracy
        - Operating 24/7 for client convenience
        - Specializing in African currency exchange
        
        IMPORTANT - ACTUAL TRADING PROCESS:
        When clients show SERIOUS INTENT to trade (not just asking for rates), explain the trading process:
        1. They must deposit cash equivalent in XAF/XOF first (versement/bank deposit)
        2. Share deposit slip/receipt for verification
        3. We verify the deposit (15-30 minutes)
        4. We release their USD/USDT/AED after verification
        5. No deposit = No exchange (security policy)
        
        PERSONAL CONTACT FOR REAL TRADES:
        Only share this contact when you're confident the client wants to actually trade (not just getting rates):
        📞 **Personal Trading Contact:** +1 (302) 582-0825
        
        Response Style:
        - Professional yet friendly trading assistant
        - Use currency emojis and trading symbols
        - Provide clear rate calculations
        - Include general contact: +1 (415) 523-8886
        - Share personal contact +1 (302) 582-0825 ONLY for actual trading intent
        - Focus on FX trading topics primarily
        
        Available Currencies:
        - USD (US Dollar) ➡️ XAF/XOF
        - AED (UAE Dirham) ➡️ XAF/XOF  
        - USDT (Tether) ➡️ XAF/XOF
        
        For non-FX topics, provide brief helpful responses but always redirect to currency services.
        Recent User Information:
        {memories}
        """.format(
            memories=memory_context
        )
        
        # Prepare messages for AI with summarization for long conversations
        processed_messages = []
        
        # If conversation history is very long, summarize older messages
        if len(conversation_history) > 10:
            # Get recent messages (last 5)
            recent_messages = conversation_history[-5:]
            
            # Summarize older messages
            older_messages = conversation_history[:-5]
            
            # Add summary message
            processed_messages.append({
                "role": "system",
                "content": f"Prior conversation summary: The user and assistant have exchanged {len(older_messages)} messages discussing various topics including {', '.join(set([msg.get('content', '')[:20] + '...' for msg in older_messages if msg.get('role') == 'user']))}"
            })
            
            # Add recent messages
            processed_messages.extend(recent_messages)
        else:
            processed_messages = conversation_history
        
        # Prepare final messages for AI
        messages = [
            {"role": "system", "content": system_prompt}
        ] + processed_messages
        
        # Set timeout and retry logic for OpenAI API
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Generate response with function calling capabilities
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7,
                    tools=[
                        {
                            "type": "function",
                            "function": {
                                "name": "execute_action",
                                "description": "Execute a specific action based on user request",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "action_name": {
                                            "type": "string",
                                            "enum": list(ActionHandler.ACTIONS.keys())
                                        },
                                        "params": {
                                            "type": "object",
                                            "additionalProperties": True
                                        }
                                    },
                                    "required": ["action_name", "params"]
                                }
                            }
                        }
                    ],
                    timeout=15  # 15-second timeout
                )
                break  # Exit retry loop on success
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"OpenAI API call failed (attempt {retry_count}/{max_retries}): {e}")
                
                if retry_count >= max_retries:
                    logger.error(f"Failed to get response from OpenAI API after {max_retries} attempts")
                    return {
                        'reply': "I'm experiencing connectivity issues at the moment. Please try again in a few moments.",
                        'action_result': None
                    }
                
                # Exponential backoff
                time.sleep(2 ** retry_count)
        
        # Extract response
        bot_reply = response.choices[0].message.content
        if bot_reply:
            bot_reply = bot_reply.strip()
        else:
            bot_reply = "I understand your message and I'm working on it."
        
        # Check for tool calls (actions)
        tool_calls = response.choices[0].message.tool_calls
        action_result = None
        
        if tool_calls:
            try:
                # Execute the first tool call
                tool_call = tool_calls[0]
                
                if tool_call.function.name == 'execute_action':
                    # Parse action parameters
                    function_args = json.loads(tool_call.function.arguments)
                    action_name = function_args.get('action_name')
                    action_params = function_args.get('params', {})
                    
                    # Execute action
                    action_result = ActionHandler.execute_action(
                        phone_number, 
                        action_name, 
                        action_params
                    )
                    
                    # Save the action in user memory
                    try:
                        AdvancedMemoryManager.save_long_term_memory(
                            phone_number,
                            'personal',
                            {
                                'type': 'executed_action',
                                'action_name': action_name,
                                'result': action_result
                            }
                        )
                    except Exception as e:
                        logger.error(f"Failed to save action in memory: {e}")
            except Exception as e:
                logger.error(f"Error executing action: {e}")
                action_result = {
                    'success': False,
                    'error': f"Failed to execute action: {str(e)}"
                }
        
        return {
            'reply': bot_reply,
            'action_result': action_result
        }
    
    except Exception as e:
        logger.error(f"AI response generation error: {e}", exc_info=True)
        return {
            'reply': "I'm experiencing some technical difficulties. Please try again in a moment.",
            'action_result': None
        }

def handle_fx_commands(message: str) -> Optional[str]:
    """
    Handle FX trading related commands and queries
    
    Args:
        message: The incoming message to analyze
        
    Returns:
        FX response string if message is FX-related, None otherwise
    """
    message_lower = message.lower().strip()
    
    # Check for rate requests - improved detection
    if any(keyword in message_lower for keyword in ['rate', 'rates']):
        return fx_trader.get_daily_rates()
    
    # Check for general rate/exchange keywords including XOF
    if any(keyword in message_lower for keyword in ['exchange', 'fx', 'currency', 'price', 'usd', 'aed', 'usdt', 'xaf', 'xof']):
        if any(keyword in message_lower for keyword in ['today', 'current', 'now', 'latest', 'daily']):
            return fx_trader.get_daily_rates()
    
    # Check for exchange calculations (e.g., "100 USD", "500 AED", "1000 USDT")
    exchange_pattern = r'(\d+(?:\.\d+)?)\s*(usd|aed|usdt|tether)\b'
    match = re.search(exchange_pattern, message_lower)
    if match:
        amount = match.group(1)
        currency = match.group(2)
        return fx_trader.calculate_exchange(amount, currency)
    
    # Check for trading intent - when users want to actually trade
    trading_intent_keywords = [
        'want to trade', 'need to exchange', 'ready to trade', 'proceed with trade',
        'trade now', 'exchange now', 'buy', 'sell', 'need cash', 'urgent exchange',
        'deposit', 'versement', 'transfer money', 'send money', 'i want to',
        'can you help me', 'process', 'complete trade', 'make exchange'
    ]
    
    if any(keyword in message_lower for keyword in trading_intent_keywords):
        # Extract amount and currency if present
        trading_pattern = r'(\d+(?:\.\d+)?)\s*(usd|aed|usdt|tether|dollars?|dirhams?)\b'
        trade_match = re.search(trading_pattern, message_lower)
        
        if trade_match:
            amount = trade_match.group(1)
            currency = trade_match.group(2)
            if currency in ['dollar', 'dollars']:
                currency = 'USD'
            elif currency in ['dirham', 'dirhams']:
                currency = 'AED'
            
            # Return trading process information
            return fx_trader.get_trading_process_info(amount, currency)
        else:
            return """
🏦 **READY TO TRADE?** 💱

To help you with your trade, please specify:
• Amount you want to exchange
• Source currency (USD, AED, USDT)
• Target currency (XAF or XOF)

**Example:** "I want to trade 500 USD to XAF"

📞 **General inquiries:** +1 (415) 523-8886

💡 **Note:** You'll need to deposit the equivalent amount in XAF/XOF first before we can process your exchange.
            """.strip()
    
    # Check for subscription commands
    if any(keyword in message_lower for keyword in ['subscribe', 'daily', 'automatic', 'alerts']):
        return f"""
📬 **DAILY RATE SUBSCRIPTION**

🕘 **Automatic daily rates at 9:00 AM Gulf Time**

Features:
• Daily rate broadcasts
• Live market updates  
• Professional FX insights
• XAF & XOF rates included

📞 **Contact:** +1 (415) 523-8886
⚠️ AI FX Trading Service
        """.strip()
    
    # Check for general FX greetings/help
    if any(keyword in message_lower for keyword in ['hello', 'hi', 'help', 'start', 'menu']):
        return f"""
🏦 **Welcome to FX Trading!** 💱
💼 *AI FX Trading Assistant*

**Available Commands:**
• "rates" - Get current XAF & XOF exchange rates
• "100 USD" - Calculate XAF/XOF equivalent for any amount
• "500 AED" - Calculate XAF/XOF equivalent for AED
• "1000 USDT" - Calculate XAF/XOF equivalent for USDT

**Supported Currencies:**
• USD (US Dollar) to XAF/XOF
• AED (UAE Dirham) to XAF/XOF
• USDT (Tether) to XAF/XOF

**Features:**
• Live rates from market data
• XOF rates with better markup (3.5%)
• 24/7 availability
• Real-time calculations
• Daily rate broadcasts at 9AM, 3PM, 7PM Gulf Time

📞 **Contact:** +1 (415) 523-8886
Send "rates" to get started! 📈
        """.strip()
    
    # If no FX command detected, return None to let AI handle it
    return None

def parse_direct_command(message: str) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Parse direct command messages from users
    
    Args:
        message (str): The user's message
        
    Returns:
        Tuple containing action name and parameters if detected, or (None, None)
    """
    # Check for direct command pattern
    command_patterns = [
        # Pattern 1: "send_message to +123456 saying hello world"
        r'send_message to (\+\d+) saying "(.*?)"',
        r'send_message to (\+\d+) saying (.*)',
        
        # Pattern 2: "send_message\nrecipient: +123456\nmessage: hello world"
        r'send_message\s*\nrecipient:\s*(\+\d+)\s*\nmessage:\s*(.*)',
        
        # Pattern 3: "Send a message to +123456 saying hello world"
        r'[Ss]end a message to (\+\d+) saying "(.*?)"',
        r'[Ss]end a message to (\+\d+) saying (.*)'
    ]
    
    for pattern in command_patterns:
        match = re.search(pattern, message, re.DOTALL)
        if match:
            recipient = match.group(1).strip()
            message_text = match.group(2).strip()
            
            # Format properly for WhatsApp
            if not recipient.startswith('whatsapp:'):
                recipient = f"whatsapp:{recipient}"
                
            return "send_message", {
                "recipient": recipient,
                "message": message_text
            }
    
    # Check for other command patterns (can be extended)
    # For create_reminder
    reminder_pattern = r'(?:create_reminder|[Rr]emind me|[Ss]et a reminder).*?(.*?)(?:on|for|at)\s+(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})'
    match = re.search(reminder_pattern, message, re.DOTALL)
    if match:
        reminder_text = match.group(1).strip()
        date_text = match.group(2).strip()
        
        # Convert date if needed
        if '/' in date_text:
            parts = date_text.split('/')
            if len(parts) == 3:
                if len(parts[2]) == 2:
                    parts[2] = f"20{parts[2]}"
                date_text = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
        
        return "create_reminder", {
            "message": reminder_text,
            "date": date_text
        }
    
    return None, None

@app.route('/webhook', methods=['POST'])
@limiter.limit("30 per minute")
def webhook() -> Response:
    """
    Advanced webhook handler with memory, action capabilities and proper error handling
    
    Returns:
        Flask Response object
    """
    try:
        # Extract message details
        incoming_msg = request.values.get('Body', '').strip()
        from_number = request.values.get('From', '')
        
        # Basic validation
        if not from_number or not incoming_msg:
            logger.warning("Missing required parameters in webhook request")
            resp = MessagingResponse()
            resp.message("Sorry, I couldn't process your message. Please try again.")
            return str(resp)
        
        # Log message receipt (without sensitive data)
        logger.info(f"Received message from {from_number[:6]}*** (length: {len(incoming_msg)})")
        
        # Create Twilio response
        resp = MessagingResponse()
        
        # Check message size
        if len(incoming_msg) > 4096:
            resp.message("Your message is too long for me to process. Please send a shorter message.")
            return str(resp)
        
        # Retrieve or initialize conversation history with error handling
        conversation_key = f"conversation:{from_number}"
        
        try:
            conversation_raw = redis_client.get(conversation_key)
            if conversation_raw:
                conversation_history = json.loads(conversation_raw)
            else:
                conversation_history = []
        except (json.JSONDecodeError, RedisOperationError) as e:
            logger.error(f"Error retrieving conversation history: {e}")
            conversation_history = []  # Start fresh if retrieval fails
        
        # Add user message to conversation
        conversation_history.append({
            "role": "user", 
            "content": incoming_msg
        })
        
        # Store sentiment and important information in memory
        try:
            # Basic detection of important information patterns
            if re.search(r'\b(remember|note|don\'t forget|important)\b', incoming_msg, re.IGNORECASE):
                AdvancedMemoryManager.save_long_term_memory(
                    from_number,
                    'personal',
                    {
                        'type': 'important_note',
                        'content': incoming_msg
                    }
                )
                logger.info(f"Saved important information for {from_number[:6]}***")
        except Exception as e:
            logger.error(f"Failed to save important information: {e}")
        
        # Check for FX trading commands first
        fx_response = handle_fx_commands(incoming_msg)
        if fx_response:
            bot_reply = fx_response
            response = {'reply': bot_reply, 'action_result': None}
        else:
            # First try to parse as a direct command
            action_name, action_params = parse_direct_command(incoming_msg)
            
            if action_name and action_params:
                # Execute the direct command
                logger.info(f"Detected direct command: {action_name}")
                action_result = ActionHandler.execute_action(
                    from_number,
                    action_name,
                    action_params
                )
                
                # Generate a simple response
                if action_result.get('success', False):
                    bot_reply = f"✅ {action_result.get('message', 'Action completed successfully.')}"
                else:
                    bot_reply = f"❌ {action_result.get('error', 'Action failed.')}"
                    
                response = {
                    'reply': bot_reply,
                    'action_result': action_result
                }
            else:
                # Generate AI response with action parsing
                response = generate_ai_response_with_action_parsing(
                    conversation_history, 
                    from_number
                )
        
        # Prepare response message
        if response['action_result'] and response['action_result'].get('success', False):
            # Format success action result message
            action_result = response['action_result']
            result_message = action_result.get('message', 'Action completed successfully.')
            
            # Only append action result if the bot's reply doesn't already mention it
            if result_message.lower() not in response['reply'].lower():
                bot_reply = f"{response['reply']}\n\n✅ {result_message}"
            else:
                bot_reply = response['reply']
        elif response['action_result'] and not response['action_result'].get('success', False):
            # Format error action result
            error_msg = response['action_result'].get('error', 'Action could not be completed.')
            
            # Only append error if the bot's reply doesn't already mention it
            if error_msg.lower() not in response['reply'].lower():
                bot_reply = f"{response['reply']}\n\n❌ {error_msg}"
            else:
                bot_reply = response['reply']
        else:
            bot_reply = response['reply']
        
        # Add AI response to conversation
        conversation_history.append({
            "role": "assistant", 
            "content": bot_reply
        })
        
        # Limit conversation history
        conversation_history = conversation_history[-20:]  # Keep last 20 messages
        
        # Save updated conversation history
        try:
            redis_client.set(
                conversation_key, 
                json.dumps(conversation_history),
                ex=604800  # 7-day expiry (increased from 24 hours)
            )
        except RedisOperationError as e:
            logger.error(f"Failed to save conversation history: {e}")
        
        # Send reply via Twilio
        resp.message(bot_reply)
        
        # Log successful processing (without sensitive data)
        logger.info(f"Successfully processed message from {from_number[:6]}*** (response length: {len(bot_reply)})")
        
        return str(resp)
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        
        # Return graceful error message
        resp = MessagingResponse()
        resp.message("Sorry, I'm experiencing technical difficulties. Please try again in a moment.")
        
        return str(resp)

@app.route('/health', methods=['GET'])
@limiter.exempt
def health_check() -> Dict:
    """
    Health check endpoint for monitoring
    
    Returns:
        Dict with service status
    """
    try:
        # Check Redis connection safely
        redis_status = "fallback"
        try:
            if redis_client and hasattr(redis_client, 'ping'):
                redis_client.ping()
                redis_status = "ok"
            else:
                redis_status = "fallback"
        except Exception:
            redis_status = "fallback"
        
        # Check FX trader functionality
        fx_status = "ok"
        try:
            fx_trader.calculate_rates()
            fx_status = "ok"
        except:
            fx_status = "error"
        
        # Basic service status
        status = {
            "service": "evocash-fx-trading-bot",
            "status": "ok",
            "timestamp": datetime.now(pytz.utc).isoformat(),
            "version": "3.0.0",
            "features": [
                "fx-trading",
                "daily-broadcasts",
                "keep-alive",
                "enhanced-scheduler"
            ],
            "dependencies": {
                "redis": redis_status,
                "fx_trader": fx_status,
                "scheduler": "active"
            },
            "keep_alive": "success"
        }
        
        # Return 200 OK with status
        return jsonify(status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        # Return 500 error
        status = {
            "service": "evocash-fx-trading-bot",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(pytz.utc).isoformat()
        }
        
        return jsonify(status), 500

@app.route('/', methods=['GET'])
def home():
    """Home page with bot information and instructions"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Evocash FX Trading Bot</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #1a1a2e;
                color: white;
                line-height: 1.6;
                min-height: 100vh;
            }
            
            .container {
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                text-align: center;
                padding: 60px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 20px;
                margin-bottom: 40px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            }
            
            .logo {
                font-size: 5rem;
                margin-bottom: 20px;
            }
            
            .title {
                font-size: 3.5rem;
                font-weight: 900;
                margin-bottom: 15px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            
            .subtitle {
                font-size: 1.4rem;
                opacity: 0.9;
                margin-bottom: 25px;
            }
            
            .status {
                display: inline-block;
                background: #00ff88;
                color: #000;
                padding: 12px 30px;
                border-radius: 30px;
                font-weight: 700;
                font-size: 1rem;
                box-shadow: 0 5px 15px rgba(0,255,136,0.3);
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 30px;
                margin: 40px 0;
            }
            
            .feature {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 30px;
                text-align: center;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.3s ease;
            }
            
            .feature:hover {
                transform: translateY(-10px);
            }
            
            .feature-icon {
                font-size: 3rem;
                margin-bottom: 20px;
            }
            
            .feature h3 {
                font-size: 1.5rem;
                margin-bottom: 15px;
            }
            
            .whatsapp-cta {
                background: #25d366;
                border-radius: 20px;
                padding: 50px;
                text-align: center;
                margin: 50px 0;
                box-shadow: 0 20px 40px rgba(37, 211, 102, 0.3);
            }
            
            .whatsapp-cta h2 {
                font-size: 2.5rem;
                margin-bottom: 20px;
                font-weight: 800;
            }
            
            .phone {
                font-size: 2.2rem;
                font-weight: 800;
                background: rgba(255,255,255,0.2);
                padding: 20px 40px;
                border-radius: 15px;
                margin: 25px 0;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .phone:hover {
                background: rgba(255,255,255,0.3);
                transform: scale(1.05);
            }
            
            .cta-btn {
                display: inline-block;
                background: white;
                color: #25d366;
                padding: 18px 40px;
                border-radius: 50px;
                text-decoration: none;
                font-weight: 700;
                font-size: 1.2rem;
                margin-top: 20px;
                transition: all 0.3s ease;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            }
            
            .cta-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 15px 35px rgba(0,0,0,0.3);
            }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 25px;
                margin: 40px 0;
            }
            
            .stat {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 25px;
                text-align: center;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .stat-number {
                font-size: 2.5rem;
                font-weight: 900;
                color: #00ff88;
                margin-bottom: 10px;
            }
            
            .stat-label {
                opacity: 0.9;
            }
            
            .trading-info {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 30px;
                margin: 30px 0;
                backdrop-filter: blur(10px);
            }
            
            .trading-info h3 {
                font-size: 1.8rem;
                margin-bottom: 20px;
                text-align: center;
            }
            
            .info-list {
                list-style: none;
            }
            
            .info-list li {
                padding: 12px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                font-size: 1.1rem;
            }
            
            .info-list li:last-child {
                border-bottom: none;
            }
            
            .footer {
                text-align: center;
                padding: 30px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 15px;
                margin-top: 40px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            @media (max-width: 768px) {
                .container {
                    padding: 15px;
                }
                
                .title {
                    font-size: 2.5rem;
                }
                
                .phone {
                    font-size: 1.8rem;
                    padding: 15px 25px;
                }
                
                .whatsapp-cta {
                    padding: 30px 20px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">💱</div>
                <h1 class="title">Evocash FX Bot</h1>
                <p class="subtitle">AI-Powered Currency Exchange Assistant</p>
                <div class="status">🟢 ONLINE NOW</div>
            </div>
            
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">🤖</div>
                    <h3>AI Assistant</h3>
                    <p>GPT-4 powered trading advice and instant rate updates</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">💰</div>
                    <h3>Live Rates</h3>
                    <p>Real-time USD, USDT, AED exchange with 9% markup</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">📱</div>
                    <h3>WhatsApp Ready</h3>
                    <p>Trade directly through WhatsApp - no apps needed!</p>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">9%</div>
                    <div class="stat-label">USD/USDT Markup</div>
                </div>
                <div class="stat">
                    <div class="stat-number">8.5%</div>
                    <div class="stat-label">AED Markup</div>
                </div>
                <div class="stat">
                    <div class="stat-number">24/7</div>
                    <div class="stat-label">Available</div>
                </div>
                <div class="stat">
                    <div class="stat-number">3x</div>
                    <div class="stat-label">Daily Updates</div>
                </div>
            </div>
            
            <div class="whatsapp-cta">
                <h2>📲 Start Trading Now!</h2>
                <p>Message our AI assistant on WhatsApp</p>
                <div class="phone" onclick="copyNumber()">+1 (415) 523-8886</div>
                <p><strong>Try saying:</strong> "What's the USD rate?" or "I want to exchange $1000"</p>
                <a href="https://wa.me/14155238886?text=Hi!%20I%27d%20like%20to%20check%20exchange%20rates" 
                   class="cta-btn" target="_blank">
                   💬 Open WhatsApp
                </a>
            </div>
            
            <div class="trading-info">
                <h3>⚡ Trading Features</h3>
                <ul class="info-list">
                    <li>💵 <strong>USD/XAF Exchange</strong> - 9% markup rates</li>
                    <li>🪙 <strong>USDT/XAF Trading</strong> - Crypto to local currency</li>
                    <li>🌍 <strong>AED/USD Conversion</strong> - 8.5% markup</li>
                    <li>🔔 <strong>Rate Alerts</strong> - 9AM, 3PM, 7PM Gulf Time</li>
                    <li>🛡️ <strong>Secure Trading</strong> - AI-powered verification</li>
                </ul>
            </div>
            
            <div class="footer">
                <p><strong>Evocash.org</strong> - Professional Currency Exchange</p>
                <p style="margin-top: 10px; opacity: 0.8;">
                    Powered by OpenAI GPT-4 • Built with Flask & Twilio
                </p>
                <p style="margin-top: 10px; opacity: 0.7; font-size: 0.9rem;">
                    ⚠️ AI trading assistant. Rates for reference only.
                </p>
                <p style="color: #999; font-size: 0.85rem; margin-top: 10px;">
                    Last updated: """ + datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S UTC') + """
                </p>
            </div>
        </div>
        
        <script>
            function copyNumber() {
                const phoneNumber = '+14155238886';
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(phoneNumber).then(() => {
                        const element = document.querySelector('.phone');
                        const original = element.textContent;
                        element.textContent = '📋 Copied!';
                        element.style.background = 'rgba(255,255,255,0.4)';
                        setTimeout(() => {
                            element.textContent = original;
                            element.style.background = 'rgba(255,255,255,0.2)';
                        }, 2000);
                    });
                } else {
                    alert('Phone number: ' + phoneNumber);
                }
            }
        </script>
    </body>
    </html>
    """

@app.route('/ping', methods=['GET'])
@limiter.exempt
def ping():
    """Simple ping endpoint for basic keep-alive"""
    return {"status": "alive", "timestamp": datetime.now(pytz.utc).isoformat()}

@app.route('/keep-alive', methods=['GET', 'POST'])
@limiter.exempt
def keep_alive():
    """Dedicated keep-alive endpoint"""
    return {"message": "Server is alive", "service": "evocash-fx-bot"}

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit errors gracefully"""
    logger.warning(f"Rate limit exceeded: {e}")
    resp = MessagingResponse()
    resp.message("You've sent too many messages in a short period. Please try again later.")
    return str(resp), 429

if __name__ == '__main__':
    # Initialize Redis connection first
    initialize_redis()
    
    # Check for required services before starting
    try:
        # Test Redis connection (only for local development)
        if redis_client and hasattr(redis_client, 'ping'):
            redis_client.ping()
            logger.info("Redis connection verified")
        
        # Initialize enhanced scheduler with keep-alive
        server_url = f"http://localhost:{os.getenv('PORT', 5001)}"
        try:
            initialize_enhanced_scheduler(twilio_client, server_url=server_url)
            logger.info("Enhanced scheduler initialized - Broadcasting at 9AM, 3PM, 7PM Gulf Time + Keep-alive")
        except Exception as e:
            logger.warning(f"Enhanced scheduler initialization failed: {e}")
        
        # Start external keep-alive service
        try:
            external_keep_alive.start()
            logger.info("External keep-alive service started")
        except Exception as e:
            logger.warning(f"External keep-alive service failed to start: {e}")
        
        # Print setup instructions for external monitoring
        try:
            print_setup_instructions()
        except Exception as e:
            logger.warning(f"Failed to print setup instructions: {e}")
        
        # Log startup information
        logger.info(f"Starting WhatsApp AI Assistant on port {os.getenv('PORT', 5001)}")
        logger.info(f"Using OpenAI model: {OPENAI_MODEL}")
        
        # Start the server
        app.run(
            debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
            host=os.getenv('HOST', '0.0.0.0'),
            port=int(os.getenv('PORT', 5001))
        )
    except Exception as e:
        logger.critical(f"Failed to start service: {e}")
        raise

