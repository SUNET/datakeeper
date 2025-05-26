import json
import pymongo
import datetime
import numpy as np
from pymongo import MongoClient
from confluent_kafka import Consumer as KafkaConsumer


class DataIngestion:
    def __init__(self, data_source='mongodb', kafka_config=None, mongodb_config=None, update_interval=5):
        self.data_source = data_source
        self.kafka_config = kafka_config or {
            'bootstrap_servers': ['localhost:9092'],
            'topic': 'vessel_tracking'
        }
        self.mongodb_config = mongodb_config or {
            'host': 'localhost',
            'port': 27017,
            'db_name': 'aisdb',
            'collection_name': 'vessels',
            'username': 'mongoadmin',
            'password': 'f48f8'
        }
        self.update_interval = update_interval
        self.vessels = {}
        self.map = None
        self.update_thread = None
        self.running = False
        self._initialize_data_connection()
        
    def _initialize_data_connection(self):
        if self.data_source == 'kafka':
            try:
                self.consumer = KafkaConsumer(
                    self.kafka_config['topic'],
                    bootstrap_servers=self.kafka_config['bootstrap_servers'],
                    auto_offset_reset='latest',
                    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
                )
                print(f"Connected to Kafka topic: {self.kafka_config['topic']}")
            except Exception as e:
                print(f"Error connecting to Kafka: {e}")
                self.data_source = 'simulation'
        elif self.data_source == 'mongodb':
            try:
                self.client = MongoClient(
                    host=self.mongodb_config['host'],
                    port=self.mongodb_config['port'],
                    username=self.mongodb_config['username'],
                    password=self.mongodb_config['password']
                )
                self.db = self.client[self.mongodb_config['db_name']]
                self.collection = self.db[self.mongodb_config['collection_name']]
                print(f"Connected to MongoDB: {self.mongodb_config['db_name']}.{self.mongodb_config['collection_name']}")
            except Exception as e:
                print(f"Error connecting to MongoDB: {e}")
                self.data_source = 'simulation'

    def test_mongo_connectivity(self):
        self.client.admin.command('ping')
        print("✅ MongoDB connected successfully.")

    def convert_vessel_data(self, raw_data):
        return {
            'id': f"vessel_{raw_data['mmsi']}",
            'name': f"{raw_data.get('shipname', raw_data['mmsi'])}",
            'type': raw_data.get('ship_type', ''),
            'lat': np.float64(raw_data['location']['coordinates'][1]),
            'lon': np.float64(raw_data['location']['coordinates'][0]),
            'speed': float(raw_data.get('speed', 0.0)),
            'heading': float(raw_data.get('heading', 0.0)),
            'destination': raw_data.get('destination', ''),
            'turn': raw_data.get('turn', 0.0),
            'timestamp': raw_data['timestamp'].isoformat()
        }
        
    def _get_vessel_data(self):
        if self.data_source == 'mongodb':
            cursor = self.collection.find(
                {
                    'timestamp': {'$gt': datetime.datetime.now() - datetime.timedelta(minutes=10)},
                    'msg_type': 1
                },
                sort=[('timestamp', pymongo.DESCENDING)]
            )
            data = list(cursor)
            return [self.convert_vessel_data(e) for e in data]
        elif self.data_source == 'simulation':
            vessels = []
            for i in range(5):
                angle = np.random.random() * 2 * np.pi
                distance = np.random.random() * 0.5
                lat = 59.612 + distance * np.cos(angle)
                lon = 17.387 + distance * np.sin(angle)
                vessels.append({
                    "id": f"vessel_{i}",
                    "name": f"Ship {i}",
                    "type": np.random.choice(["Cargo", "Tanker", "Passenger", "Fishing"]),
                    "lat": lat,
                    "lon": lon,
                    "speed": round(np.random.random() * 15 + 5, 2),
                    "heading": round(np.random.random() * 360, 2),
                    "timestamp": datetime.datetime.now().isoformat()
                })
            return vessels

            
            