import asyncio
from typing import Dict, Union
from datetime import datetime
from pymongo.errors import PyMongoError
from pymongo import MongoClient, GEOSPHERE
from ais_live_router.configuration import AppConfigEnv, AppConfigFile, logger


class MongoManager:
    """Class for managing MongoDB operations"""
    
    def __init__(self, config: Union[AppConfigEnv, AppConfigFile]):
        self.config = config
        self.client = None
        self.db = None
        self.collection = None
        self.bulk_operations = []
        self.bulk_counter = 0
        self.bulk_limit = 500  # Adjust based on your needs
        

        print("MongoManager.init")
        print("enable_mongo_output=", self.config.enable_mongo_output, "enable_mongo_output.boolean=", type(self.config.enable_mongo_output))

        self.initialize_connection()
        
    def initialize_connection(self) -> None:
        """Initialize MongoDB connection and collection"""
        try:
            # Production-ready MongoDB client settings with connection pooling
            self.client = MongoClient(
                self.config.mongo_url,
                retryWrites=True,
                connectTimeoutMS=5000,
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection - wrap this in a try/except to catch connection issues
            try:
                self.client.admin.command('ping')
                logger.info("MongoDB server ping successful")
            except Exception as ping_error:
                logger.error(f"MongoDB ping failed: {ping_error}")
                raise
            
            self.db = self.client[self.config.mongo_db]
            self.collection = self.db[self.config.mongo_collection]
            logger.info(f"Using MongoDB database '{self.config.mongo_db}' and collection '{self.config.mongo_collection}'")
            
            # Create indexes in a separate try block
            try:
                # Ensure 2dsphere index on 'location' for geospatial queries
                self.collection.create_index([("location", GEOSPHERE)])
                # Create index for common query fields
                self.collection.create_index([("mmsi", 1)])
                self.collection.create_index([("timestamp", -1)])
                self.collection.create_index([("msg_type", 1)])
                logger.info("MongoDB indexes created successfully")
            except Exception as index_error:
                logger.warning(f"Could not create MongoDB indexes: {index_error}")

            # Test collection access
            try:
                doc_count = self.collection.count_documents({}, limit=1)
                logger.info(f"MongoDB collection access successful, found documents: {doc_count > 0}")
                self.connection_established = True
            except Exception as coll_error:
                logger.error(f"MongoDB collection access failed: {coll_error}")
                raise

            logger.info("MongoDB connection fully initialized")
        except PyMongoError as e:
            logger.error(f"Failed to initialize MongoDB connection: {str(e)}")
            # Don't raise here, try to reconnect later
            self.connection_established = False
        except Exception as e:
            logger.error(f"Unexpected error initializing MongoDB: {str(e)}", exc_info=True)
            self.connection_established = False
            
    def ensure_connection(self) -> bool:
        """Ensure we have a valid MongoDB connection, reconnect if needed"""
        if self.connection_established and self.collection is not None:
            return True
            
        logger.info("MongoDB connection not established, attempting to reconnect...")
        try:
            self.initialize_connection()
            return self.connection_established
        except Exception as e:
            logger.error(f"Failed to reconnect to MongoDB: {str(e)}")
            return False
        
        
    async def send_data(self, data: Dict) -> bool:
        """Send data to MongoDB asynchronously"""
        logger.debug(f"MongoDB send_data called with data: {data.get('mmsi', 'no-mmsi')}")
        
        # Ensure connection is established
        if not self.ensure_connection():
            logger.error("MongoDB connection not available - data will be lost")
            return False
            
        # Safeguard against None or empty data
        if not data:
            logger.warning("Attempted to send empty data to MongoDB")
            return False
            
        try:
            # Deep copy the data to prevent modification issues
            safe_data = data.copy()
            
            # Add timestamp if not present
            if "timestamp" not in safe_data:
                safe_data["timestamp"] = datetime.now()
            
            # Validate timestamp format - convert string to datetime if needed
            if isinstance(safe_data["timestamp"], str):
                try:
                    safe_data["timestamp"] = datetime.fromisoformat(safe_data["timestamp"])
                except ValueError:
                    logger.warning(f"Invalid timestamp format: {safe_data['timestamp']}, using current time")
                    safe_data["timestamp"] = datetime.utcnow()

            # Ensure we have a document_id for upsert operations
            document_id = None
            if "mmsi" in safe_data:
                document_id = safe_data["mmsi"]
                logger.debug(f"Using MMSI {document_id} as document ID")
            
            # Handle non-serializable objects
            for key, value in list(safe_data.items()):
                if isinstance(value, (set, complex)):
                    safe_data[key] = str(value)
                
            # Get event loop - handle cases where no loop exists
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # If no event loop exists in this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Execute MongoDB operation in executor
            if document_id:
                logger.debug(f"Checking if MMSI {document_id} exists in the database")
                try:
                    # Check if a document with this MMSI exists
                    exists = await loop.run_in_executor(
                        None,
                        lambda: self.collection.find_one({"mmsi": document_id}, {"_id": 1}) is not None
                    )
                except Exception as check_error:
                    logger.error(f"Error checking existing MMSI: {str(check_error)}", exc_info=True)
                    return False

                if exists:
                    logger.debug(f"MMSI {document_id} found — updating document")
                    try:
                        result = await loop.run_in_executor(
                            None,
                            lambda: self.collection.update_one(
                                {"mmsi": document_id},
                                {"$set": safe_data},
                                upsert=True  # Upsert true is safe if the document exists
                            )
                        )
                        logger.debug(f"MongoDB update result: matched={result.matched_count}, modified={result.modified_count}, upserted_id={result.upserted_id}")
                        return True
                    except Exception as update_error:
                        logger.error(f"MongoDB update_one error: {str(update_error)}", exc_info=True)
                        return False
                else:
                    logger.debug(f"MMSI {document_id} not found — inserting as new document")
                    try:
                        result = await loop.run_in_executor(
                            None,
                            lambda: self.collection.insert_one(safe_data)
                        )
                        logger.debug(f"MongoDB insert result: inserted_id={result.inserted_id}")
                        return True
                    except Exception as insert_error:
                        logger.error(f"MongoDB insert_one error: {str(insert_error)}", exc_info=True)
                        return False
            else:
                logger.warning("Inserting new document (no MMSI) !!!")
                try:
                    # Insert new document if no mmsi
                    result = await loop.run_in_executor(
                        None, 
                        lambda: self.collection.insert_one(safe_data)
                    )
                    logger.warning(f"MongoDB insert result: inserted_id={result.inserted_id}")
                    return True
                except Exception as insert_error:
                    logger.error(f"MongoDB insert_one error: {str(insert_error)}", exc_info=True)
                    return False
                
        except PyMongoError as e:
            logger.error(f"MongoDB error when sending data: {str(e)}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error when sending data to MongoDB: {str(e)}", exc_info=True)
            return False
    
    async def close(self) -> None:
        """Close the MongoDB connection"""
        if self.client:
            try:
                self.client.close()
                logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {str(e)}")
        else:
            logger.warning("Attempted to close non-existent MongoDB connection")
        
        self.connection_established = False
