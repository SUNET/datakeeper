import json
import time
import asyncio
from typing import Dict, Union, Optional
from confluent_kafka import Producer, KafkaException
from ais_live_router.configuration import AppConfigEnv, AppConfigFile, logger


class KafkaManager:
    """Class for managing Kafka operations"""
    def __init__(self, config: Union[AppConfigEnv, AppConfigFile]):
        self.config = config
        self.producer = None
        self.message_count = 0
        self.last_flush_time = time.time()
        self.pending_messages = 0
        self.delivery_callbacks_received = 0
        self.initialize_producer()
        
    def initialize_producer(self) -> None:
        """Initialize the Kafka producer with configuration"""
        conf = {
            "bootstrap.servers": self.config.bootstrap_servers,
            "client.id": "ais-data-producer",
            # Additional production-ready configuration
            "acks": "all",                 # Wait for all replicas to acknowledge
            "delivery.timeout.ms": 10000,  # 10 seconds delivery timeout
            "request.timeout.ms": 5000,    # 5 seconds request timeout
            "retries": 3,                  # Retry 3 times before failure
            "retry.backoff.ms": 100,       # Wait 100ms between retries
            "linger.ms": 5,                # Wait 5ms to batch messages
            "batch.size": 16384,           # Batch size in bytes
            "compression.type": "snappy"   # Use Snappy compression
        }
        try:
            self.producer = Producer(**conf)
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    def delivery_callback(self, err, msg) -> None:
        """Callback function for Kafka message delivery"""
        self.delivery_callbacks_received += 1
        self.pending_messages -= 1
        
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")

    async def send_data(self, data: Dict, topic: Optional[str] = None) -> bool:
        """Send data to Kafka asynchronously"""
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return False
            
        topic = topic or self.config.kafka_topic
        try:
            json_data = json.dumps(data).encode("utf-8")
            
            # Put in an event loop to not block
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: self.producer.produce(
                    topic=topic, 
                    value=json_data, 
                    callback=self.delivery_callback
                )
            )
            
            self.pending_messages += 1
            self.message_count += 1
            
            # Flush periodically or when batch size is reached
            current_time = time.time()
            if (self.message_count >= self.config.kafka_batch_size or 
                    current_time - self.last_flush_time >= self.config.kafka_flush_timeout):
                await self.flush()
                self.message_count = 0
                self.last_flush_time = current_time
                
            return True
        except KafkaException as e:
            logger.error(f"Kafka error when sending data: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error when sending data to Kafka: {e}")
            return False
    
    async def flush(self) -> None:
        """Flush the producer to ensure all messages are sent"""
        if self.producer:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.producer.flush, 5000)  # 5 second timeout
            logger.debug(f"Flushed Kafka producer, {self.pending_messages} messages pending")
    
    async def close(self) -> None:
        """Flush and close the producer"""
        if self.producer:
            await self.flush()
            logger.info(f"Kafka producer closed, {self.delivery_callbacks_received} callbacks received")
