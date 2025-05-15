import os
import sys
import json
import socket
import base64
import asyncio
import hashlib
import traceback
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Union
from pyais import decode as pyais_decode, IterMessages
from ais_live_router.mongo_manager import MongoManager
from ais_live_router.kafka_manager import KafkaManager
from ais_live_router.configuration import AppConfigEnv, AppConfigFile, logger


class AISProcessor:
    """Class for processing AIS data"""
    def __init__(self, config: Union[AppConfigEnv, AppConfigFile], enable_kafka_output: str=None, enable_mongo_output: str=None):
        self.config = config
        self.mongo_manager = MongoManager(config)
        self.kafka_manager = KafkaManager(config)
        self.saved_msg_types = []
        
        if enable_kafka_output:
            self.mongo_manager.config.enable_kafka_output = enable_kafka_output
        if enable_mongo_output:
            self.mongo_manager.config.enable_mongo_output = enable_mongo_output
        
    def logon_msg(self) -> bytearray:
        """Create login message for AIS server"""
        # Build binary message
        # 1. Start with Command ID (1 byte)
        message = bytearray()
        message.append(1)  # Command ID = 1

        # 2. Add username (ASCII bytes)
        message.extend(self.config.ais_user.encode("ascii"))

        # 3. Delimiter (1 byte)
        message.append(0)

        # 4. Add password (ASCII bytes)
        message.extend(self.config.ais_password.encode("ascii"))

        # 5. End mark (1 byte)
        message.append(0)
        return message

    def logon_msg_hashed(self) -> bytearray:
        """Create hashed login message for AIS server"""
        # Step 1: MD5 hash of the password
        md5_hash = hashlib.md5(self.config.ais_password.encode("utf-8")).digest()

        # Step 2: Base64-encode the hash
        password_encoded = base64.b64encode(md5_hash).decode("ascii")

        # Step 3: Build binary message
        message = bytearray()
        message.append(2)  # Command ID = 2
        message.extend(self.config.ais_user.encode("ascii"))  # Username
        message.append(0)  # Delimiter
        message.extend(password_encoded.encode("ascii"))  # Encoded password
        message.append(0)  # End mark
        return message

    @staticmethod
    def filter_valid_ais_lines(lines: List[bytes]) -> List[bytes]:
        """Filter valid AIS lines from raw data"""
        return [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith(b"$ABVSI")
        ]

    @staticmethod
    def is_enum_instance(value: Any) -> bool:
        """Check if a value is an Enum instance"""
        return isinstance(value, Enum)

    def log_to_file(self, data: Dict) -> None:
        """Log AIS data to file"""
        try:
            with open(self.config.log_file, "a") as log_file:
                log_file.write(f"{json.dumps(data)}\n")
        except IOError as e:
            logger.error(f"Failed to write to log file: {e}")

    def normalize_ais_message(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize AIS message format"""
        def decode_bytes(value: Union[bytes, None], key: str) -> Union[str, int, None]:
            if isinstance(value, bytes):
                try:
                    if key == "spare_1" or key == "spare_2":
                        return int.from_bytes(value, "big")
                    return str(value)
                except Exception:
                    return str(value)  # fallback to string representation
            return value

        entry = entry.copy()  # avoid mutating the original

        # Convert enum-like fields to strings
        for key in list(entry.keys()):
            if key in entry and self.is_enum_instance(entry.get(key)):
                entry[key] = entry.get(key).name

        # Convert lat/lon to GeoJSON Point
        if "lat" in entry and "lon" in entry:
            lat, lon = entry["lat"], entry["lon"]
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                entry["location"] = {"type": "Point", "coordinates": [lon, lat]}
                # delete lat & lon
                del entry["lat"]
                del entry["lon"]

        # Decode binary fields
        for bin_key in ["spare_1", "spare_2", "data"]:
            if bin_key in entry:
                entry[bin_key] = decode_bytes(entry[bin_key], bin_key)

        # Add timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()

        return entry


    def is_valid_geo_point(self, lon: float, lat: float) -> bool:
        if lon and lat:
            return -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0
        else:
            return True


    async def process_ais_message(self, decoded_normalized: Dict) -> None:
        """Process normalized AIS message - send to Kafka and MongoDB"""
        
        lon, lat = decoded_normalized.get("location", {}).get("coordinates", [None, None])
        
        if not self.is_valid_geo_point(lon, lat):
            logger.error(f"Invalid geo-coordinates: lng: {lon}, lat: {lat}. Skipping insertion for {decoded_normalized}")
            raise Exception(f"Invalid coordinates [{lon}, {lat}]")
        
        msg_type = int(decoded_normalized.get("msg_type", 0))
        
        # Track unique message types for logging
        if msg_type not in self.saved_msg_types:
            self.saved_msg_types.append(msg_type)
            logger.info(f"New message type encountered: {msg_type}")
        
        # Send data to Kafka and MongoDB asynchronously - with better error handling
        tasks = []
        
        if self.mongo_manager.config.enable_kafka_output:
            # Prepare Kafka task with explicit error catching
            kafka_task = asyncio.create_task(self._safe_send_to_kafka(decoded_normalized))
            tasks.append(kafka_task)
        
        if self.mongo_manager.config.enable_mongo_output:
            # Prepare MongoDB task with explicit error catching
            mongo_task = asyncio.create_task(self._safe_send_to_mongo(decoded_normalized))
            tasks.append(mongo_task)
            
        # Wait for both tasks to complete
        await asyncio.gather(*tasks)
        
        
    async def _safe_send_to_kafka(self, data: Dict) -> None:
        """Safely send data to Kafka with explicit error handling"""
        try:
            logger.debug(f"Starting kafka-sending for MMSI: {data.get('mmsi', 'unknown')}")
            success = await self.kafka_manager.send_data(data)
            if not success:
                logger.warning("Kafka send_data returned False")
        except Exception as e:
            logger.error(f"Failed to send to Kafka: {str(e)}", exc_info=True)
            
    async def _safe_send_to_mongo(self, data: Dict) -> None:
        """Safely send data to MongoDB with explicit error handling"""
        try:
            # Add detailed logging for diagnosis
            logger.debug(f"Starting MongoDB send for MMSI: {data.get('mmsi', 'unknown')}")
            success = await self.mongo_manager.send_data(data)
            if success:
                logger.debug(f"MongoDB send successful for MMSI: {data.get('mmsi', 'unknown')}")
            else:
                logger.warning(f"MongoDB send_data returned False for MMSI: {data.get('mmsi', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to send to MongoDB: {str(e)}", exc_info=True)

    async def connect_and_process(self) -> None:
        """Connect to AIS server and process incoming data"""
        retries = 0
        while retries < self.config.max_retries:
            try:
                logger.info(f"Connecting to {self.config.ais_host}:{self.config.ais_port}")
                login_message = self.logon_msg()
                
                # Create a TCP/IP socket with timeout
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.config.connection_timeout)
                
                # Enable TCP keep-alive
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
                # Additional socket options for production systems
                if hasattr(socket, 'TCP_KEEPIDLE'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                if hasattr(socket, 'TCP_KEEPINTVL'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                if hasattr(socket, 'TCP_KEEPCNT'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
                
                # Connect to the AIS server
                sock.connect((self.config.ais_host, self.config.ais_port))
                logger.info(f"Connected to {self.config.ais_host}:{self.config.ais_port}")
                
                # Send login credentials
                sock.sendall(login_message)
                logger.info("Login message sent")
                
                # Reset retry counter upon successful connection
                retries = 0
                
                # Process incoming data
                try:
                    with sock:
                        # Keep receiving messages until server closes connection
                        while True:
                            data = sock.recv(4096)  # Increased buffer size
                            if not data:
                                logger.warning("Server closed connection.")
                                break

                            data_split = data.split(b'\r\n')
                            data_str_split = self.filter_valid_ais_lines(data_split)
                            
                            try:
                                for msg in IterMessages(data_str_split):
                                    try:
                                        decoded_sentence = msg.decode()
                                        decoded_ais_line = decoded_sentence.asdict()
                                        decoded_normalized = self.normalize_ais_message(decoded_ais_line)
                                        # logger.info(f"data->{decoded_normalized}")
                                        
                                        # Process AIS message asynchronously
                                        await self.process_ais_message(decoded_normalized)
                                    except Exception as e:
                                        logger.error(f"Error processing AIS message: {e}")
                                        continue
                            except Exception as e:
                                logger.error(f"Error iterating messages: {e}")
                                continue
                except Exception as e:
                    logger.error(f"Socket error: {e}")
                finally:
                    if not sock._closed:
                        sock.close()
                        
            except socket.timeout:
                logger.error(f"Connection timeout after {self.config.connection_timeout} seconds")
                retries += 1
            except ConnectionRefusedError:
                logger.error("Connection refused by server")
                retries += 1
            except Exception as e:
                logger.error(f"Connection error: {e}")
                retries += 1
            
            # Wait before retrying
            if retries < self.config.max_retries:
                logger.info(f"Retrying connection in {self.config.retry_interval} seconds... (Attempt {retries+1}/{self.config.max_retries})")
                await asyncio.sleep(self.config.retry_interval)
            else:
                logger.error(f"Failed to connect after {self.config.max_retries} attempts")
                break
    
    async def run(self) -> None:
        """Run the AIS processor"""
        try:
            await self.connect_and_process()
        except KeyboardInterrupt:
            logger.info("Process interrupted by user")
        except Exception as e:
            logger.critical(f"Critical error: {e}", exc_info=True)
        finally:
            # Clean up resources
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shutdown all connections and clean up resources"""
        try:
            logger.info("Shutting down AIS processor...")
            
            # Close Kafka connection
            await self.kafka_manager.close()
            
            # Close MongoDB connection
            await self.mongo_manager.close()
            
            logger.info("AIS processor shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def ais_main(config_file = None, enable_kafka_output: str=None, enable_mongo_output: str=None):
    """Main entry point for the application"""
    try:
        # Load configuration
        config_path = config_file or os.environ.get("CONFIG_FILE")
        config = AppConfigFile(config_path=config_path) if config_path else AppConfigEnv()
        print(f"config={config}")
        # Create and run the AIS processor
        processor = AISProcessor(config=config,
                                 enable_mongo_output=enable_mongo_output,
                                 enable_kafka_output=enable_kafka_output)
        await processor.run()
    except Exception as e:
        logger.critical(f"Application failed: {e}", exc_info=True)
        sys.exit(1)


        
def ais_run():
    try:
        asyncio.run(ais_main())
    except KeyboardInterrupt:
        print("Program interrupted by user")
    except Exception as e:
        print(f"Unhandled exception: {e}")
        traceback.print_exc()
        sys.exit(1)

