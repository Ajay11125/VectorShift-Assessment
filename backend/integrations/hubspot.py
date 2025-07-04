import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
from datetime import datetime
from typing import Optional, List

from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# HubSpot OAuth Configuration
CLIENT_ID = 'd0e47b08-8208-4f99-83ed-2a253a4d587d'  # Register at developers.hubspot.com
CLIENT_SECRET = 'ac16b72b-2924-4659-ae0a-c836d8537b4a'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
AUTH_URL = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}'
TOKEN_URL = 'https://api.hubapi.com/oauth/v1/token'
SCOPES = 'crm.objects.contacts.read crm.objects.deals.read oauth'

async def authorize_hubspot(user_id, org_id):
    
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)
    
    auth_url = f"{AUTH_URL}&scope={SCOPES}&state={encoded_state}"
    return auth_url

async def oauth2callback_hubspot(request: Request):
    
    if request.query_params.get('error'):
        raise HTTPException(
            status_code=400, 
            detail=f"HubSpot OAuth error: {request.query_params.get('error')}"
        )
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    
    if not code or not encoded_state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    try:
        state_data = json.loads(encoded_state)
        original_state = state_data.get('state')
        user_id = state_data.get('user_id')
        org_id = state_data.get('org_id')

        saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
        
        if not saved_state or original_state != json.loads(saved_state).get('state'):
            raise HTTPException(status_code=400, detail='Invalid state parameter')

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'code': code
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"HubSpot token exchange failed: {response.text}"
                )

            tokens = response.json()
            await asyncio.gather(
                delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
                add_key_value_redis(
                    f'hubspot_credentials:{org_id}:{user_id}',
                    json.dumps(tokens),
                    expire=tokens.get('expires_in', 3600)
                )
            )

        return HTMLResponse(content="""
            <html><script>window.close();</script></html>
        """)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

async def get_hubspot_credentials(user_id, org_id):
    
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No HubSpot credentials found')
    
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
    return credentials

async def get_items_hubspot(credentials) -> List[IntegrationItem]:
    
    credentials = json.loads(credentials)
    access_token = credentials.get('access_token')
    if not access_token:
        raise HTTPException(status_code=400, detail='Missing access token')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    integration_items = []
    
    # Fetch contacts
    async with httpx.AsyncClient() as client:
        # Get contacts
        contacts_response = await client.get(
            'https://api.hubapi.com/crm/v3/objects/contacts',
            headers=headers,
            params={'limit': 100}
        )
        
        # Get companies
        companies_response = await client.get(
            'https://api.hubapi.com/crm/v3/objects/companies',
            headers=headers,
            params={'limit': 100}
        )
        
        # Get deals
        deals_response = await client.get(
            'https://api.hubapi.com/crm/v3/objects/deals',
            headers=headers,
            params={'limit': 100}
        )

        if contacts_response.status_code == 200:
            for contact in contacts_response.json().get('results', []):
                integration_items.append(
                    IntegrationItem(
                        id=contact.get('id'),
                        type='contact',
                        name=contact.get('properties', {}).get('firstname', '') + ' ' + 
                             contact.get('properties', {}).get('lastname', ''),
                        creation_time=datetime.fromisoformat(contact.get('createdAt', '').replace('Z', '+00:00')),
                        last_modified_time=datetime.fromisoformat(contact.get('updatedAt', '').replace('Z', '+00:00')),
                        url=f"https://app.hubspot.com/contacts/{contact.get('id')}"
                    )
                )

        if companies_response.status_code == 200:
            for company in companies_response.json().get('results', []):
                integration_items.append(
                    IntegrationItem(
                        id=company.get('id'),
                        type='company',
                        name=company.get('properties', {}).get('name', ''),
                        creation_time=datetime.fromisoformat(company.get('createdAt', '').replace('Z', '+00:00')),
                        last_modified_time=datetime.fromisoformat(company.get('updatedAt', '').replace('Z', '+00:00')),
                        url=f"https://app.hubspot.com/companies/{company.get('id')}"
                    )
                )

        if deals_response.status_code == 200:
            for deal in deals_response.json().get('results', []):
                integration_items.append(
                    IntegrationItem(
                        id=deal.get('id'),
                        type='deal',
                        name=deal.get('properties', {}).get('dealname', ''),
                        creation_time=datetime.fromisoformat(deal.get('createdAt', '').replace('Z', '+00:00')),
                        last_modified_time=datetime.fromisoformat(deal.get('updatedAt', '').replace('Z', '+00:00')),
                        url=f"https://app.hubspot.com/deals/{deal.get('id')}"
                    )
                )

    return integration_items