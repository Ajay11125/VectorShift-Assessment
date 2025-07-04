import os
import redis.asyncio as redis
from kombu.utils.url import safequote

REDIS_CLOUD_HOST = 'redis-12085.crce206.ap-south-1-1.ec2.redns.redis-cloud.com'  
REDIS_CLOUD_PORT = 12085  
REDIS_CLOUD_PASSWORD = 'g9XOHViyabLuyN9mcRY8g0ifkCdPMRhs'  
REDIS_CLOUD_DB = 0 

redis_client = redis.Redis(
    host=REDIS_CLOUD_HOST,
    port=REDIS_CLOUD_PORT,
    password=REDIS_CLOUD_PASSWORD,
    db=REDIS_CLOUD_DB,
    # ssl=True,  
    decode_responses=True
)


async def add_key_value_redis(key, value, expire=None):
    await redis_client.set(key, value)
    if expire:
        await redis_client.expire(key, expire)

async def get_value_redis(key):
    return await redis_client.get(key)

async def delete_key_redis(key):
    await redis_client.delete(key)
