import os
import json
import base64
import logging
import hashlib
import math
from datetime import datetime, date
from typing import Any, Optional
from google.oauth2 import service_account
from google.cloud import bigquery, storage, firestore
from fastcore.xtras import timed_cache


# Create API client using base64 encoded service account key
def get_credentials():
    """Get Google Cloud credentials from base64 encoded service account key"""
    service_key_b64 = os.environ.get("GOOGLE_SERVICE_KEY")
    if not service_key_b64:
        raise ValueError("GOOGLE_SERVICE_KEY environment variable is not set")
    
    try:
        # Decode base64 string to get JSON
        service_key_json = base64.b64decode(service_key_b64).decode('utf-8')
        service_account_info = json.loads(service_key_json)
        
        # Create credentials from service account info
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        return credentials
    except Exception as e:
        raise ValueError(f"Failed to decode GOOGLE_SERVICE_KEY: {e}")

credentials = get_credentials()
bq_client = bigquery.Client(credentials=credentials)
storage_client = storage.Client(credentials=credentials)
firestore_client = firestore.Client(credentials=credentials, database="op-leaderboard")

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime.date and datetime.datetime objects."""
    def default(self, obj):
        if isinstance(obj, date):
            return {
                '__type__': 'date',
                '__value__': obj.isoformat()
            }
        elif isinstance(obj, datetime):
            return {
                '__type__': 'datetime',
                '__value__': obj.isoformat()
            }
        return super().default(obj)

def _datetime_object_hook(dct):
    """JSON object hook to deserialize datetime objects."""
    if '__type__' in dct:
        if dct['__type__'] == 'date':
            return datetime.fromisoformat(dct['__value__']).date()
        elif dct['__type__'] == 'datetime':
            return datetime.fromisoformat(dct['__value__'])
    return dct

def _get_cache_key(query: str) -> str:
    """Generate a cache key from query."""
    return hashlib.md5(query.encode()).hexdigest()

def _split_data_into_chunks(data: list[dict[str, Any]], max_chunk_size: int = 800000) -> list[list[dict[str, Any]]]:
    """Split data into chunks that fit within Firestore document size limits."""
    if not data:
        return []
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for item in data:
        item_json = json.dumps(item, cls=DateTimeEncoder, ensure_ascii=False)
        item_size = len(item_json.encode('utf-8'))
        
        # If adding this item would exceed the limit, start a new chunk
        if current_size + item_size > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [item]
            current_size = item_size
        else:
            current_chunk.append(item)
            current_size += item_size
    
    # Add the last chunk if it has data
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def _get_from_firestore_cache(query: str) -> Optional[list[dict[str, Any]]]:
    """Try to get cached result from Firestore using subcollections."""
    if not firestore_client:
        return None
    
    try:
        cache_key = _get_cache_key(query)
        
        # Get the main cache document
        cache_doc_ref = firestore_client.collection('bq_cache').document(cache_key)
        cache_doc = cache_doc_ref.get()
        
        if not cache_doc.exists:
            return None
        
        cache_data = cache_doc.to_dict()
        
        # Check if cache is still valid (2 hours)
        import time
        if time.time() - cache_data.get('timestamp', 0) >= 60 * 60 * 2:
            # Cache expired, delete the entire document (subcollection will be orphaned but that's ok)
            cache_doc_ref.delete()
            logging.info("Firestore cache expired, deleted main document")
            return None
        
        logging.info(f"Cache HIT from Firestore for query: {query[:50]}...")
        
        # Get all chunks from the subcollection
        chunks_collection = cache_doc_ref.collection('chunks')
        chunk_docs = chunks_collection.order_by('chunk_index').stream()
        
        all_data = []
        for chunk_doc in chunk_docs:
            chunk_data = chunk_doc.to_dict()
            chunk_json = chunk_data.get('data', '[]')
            chunk_items = json.loads(chunk_json, object_hook=_datetime_object_hook)
            all_data.extend(chunk_items)
        
        return all_data
        
    except Exception as e:
        logging.warning(f"Firestore cache read failed: {e}")
    
    return None

def _store_in_firestore_cache(query: str, data: list[dict[str, Any]]) -> None:
    """Store result in Firestore cache using subcollections for chunks."""
    if not firestore_client:
        return
    
    try:
        cache_key = _get_cache_key(query)
        
        # Split data into chunks
        chunks = _split_data_into_chunks(data, max_chunk_size=800000)
        
        if not chunks:
            return
        
        import time
        
        # Get reference to main cache document
        cache_doc_ref = firestore_client.collection('bq_cache').document(cache_key)
        
        # Store metadata in the main document
        cache_metadata = {
            'timestamp': time.time(),
            'query_preview': query[:100],
            'result_count': len(data),
            'num_chunks': len(chunks)
        }
        cache_doc_ref.set(cache_metadata)
        
        # Store each chunk in the subcollection
        chunks_collection = cache_doc_ref.collection('chunks')
        
        # Loop over 10 batches of chunks
        for j in range(0, len(chunks), 10):
            chunk_batch = chunks[j:j+10]
            batch = firestore_client.batch()
            
            for i, chunk in enumerate(chunk_batch):
                chunk_doc_ref = chunks_collection.document(str(j+i))
                chunk_json = json.dumps(chunk, cls=DateTimeEncoder, ensure_ascii=False)
                
                chunk_doc = {
                    'data': chunk_json,
                    'chunk_index': j+i,
                    'chunk_size': len(chunk),
                    'timestamp': time.time()
                }
                batch.set(chunk_doc_ref, chunk_doc)
            
            # Commit all chunk documents at once
            batch.commit()
        
        logging.info(f"Stored {len(data)} records in Firestore cache across {len(chunks)} chunks: {query[:50]}...")
        
    except Exception as e:
        logging.warning(f"Firestore cache write failed: {e}")

#@timed_cache(seconds=60 * 60 * 6) # 6 hours
def run_bq_query(query: str) -> list[dict[str, Any]]:
    """Runs a bigquery query with Firestore caching if available, fallback to timed_cache"""
    
    # Try Firestore cache first
    cached_result = _get_from_firestore_cache(query)
    if cached_result is not None and cached_result != []:
        return cached_result
    
    # Execute query
    logging.info(f"Running bq query: {query}")
    query_job = bq_client.query(query, location="europe-west3")
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for caching to hash the return value.
    rows = [dict(row) for row in rows_raw]
    
    # Store in Firestore cache
    _store_in_firestore_cache(query, rows)
    
    return rows