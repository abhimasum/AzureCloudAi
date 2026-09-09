"""Cosmos DB SQL API agent: queries Cosmos DB for geography index metadata.

This agent provides entity IDs and names from the database to help the 
retriever agent focus RAG searches. Returns INDEX information only.
"""

import os
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from agent_framework import Agent
from openai import OpenAI


# Wrapper class to adapt OpenAI client to agent_framework expectations
class OpenAIClientWrapper:
    """Wraps the direct OpenAI client to provide the interface expected by agent_framework."""
    
    def __init__(self, openai_client):
        self.client = openai_client
    
    def get_response(self, system_prompt: str, user_message: str, **kwargs) -> str:
        """Get a response from the OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=2000,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


# Initialize OpenAI client with direct API and wrap it
_openai_client = OpenAIClientWrapper(OpenAI(api_key=os.environ.get("OPENAI_API_KEY")))


# Initialize Cosmos DB connection
_cosmos_connection_string = os.environ.get("COSMOSDB_CONNECTION_STRING")
_cosmos_database_name = os.environ.get("COSMOSDB_DATABASE_NAME", "geography_index")

_client = None
_countries_container = None
_states_container = None

if _cosmos_connection_string:
    try:
        _client = CosmosClient.from_connection_string(_cosmos_connection_string)
        _database = _client.get_database_client(_cosmos_database_name)
        _countries_container = _database.get_container_client("countries")
        _states_container = _database.get_container_client("states")
    except Exception as e:
        print(f"Warning: Could not connect to Cosmos DB: {e}")


def get_country_info(country_name: str = "India") -> str:
    """Get country index from database."""
    if not _countries_container:
        return "Country: India (ID: 1, Capital: New Delhi)"
    
    try:
        # Query by name
        items = list(_countries_container.query_items(
            query="SELECT * FROM c WHERE LOWER(c.name) = LOWER(@name)",
            parameters=[{"name": "@name", "value": country_name}],
            enable_cross_partition_query=True
        ))
        
        if items:
            item = items[0]
            return f"Country: {item['name']} (ID: {item['id']}, Capital: {item.get('capital', 'N/A')})"
        return f"Country '{country_name}' not found in database"
    except exceptions.CosmosHttpResponseError as e:
        return f"Database error: {str(e)}"
    except Exception as e:
        return f"Database error: {str(e)}"


def get_state_info(state_name: str) -> str:
    """Get state index from database."""
    if not _states_container:
        return f"State: {state_name} (database query not available)"
    
    try:
        # Query by name (supports partial matches)
        items = list(_states_container.query_items(
            query="SELECT * FROM c WHERE LOWER(c.name) = LOWER(@name) OR LOWER(c.name) LIKE LOWER(@pattern)",
            parameters=[
                {"name": "@name", "value": state_name},
                {"name": "@pattern", "value": f"%{state_name}%"}
            ],
            enable_cross_partition_query=True,
            max_item_count=1
        ))
        
        if items:
            item = items[0]
            country_id = item.get('country_id', 1)
            # Get country name
            country_name = "India"
            if _countries_container:
                country_items = list(_countries_container.query_items(
                    query="SELECT * FROM c WHERE c.id = @id",
                    parameters=[{"name": "@id", "value": country_id}],
                    enable_cross_partition_query=True
                ))
                if country_items:
                    country_name = country_items[0].get('name', 'India')
            
            return f"State: {item['name']} (ID: {item['id']}, Capital: {item.get('capital', 'N/A')}, Country: {country_name})"
        return f"State '{state_name}' not found in database"
    except exceptions.CosmosHttpResponseError as e:
        return f"Database error: {str(e)}"
    except Exception as e:
        return f"Database error: {str(e)}"


def list_all_states() -> str:
    """List all states from database."""
    if not _states_container:
        return "Database query not available - 28 states exist in India"
    
    try:
        # Query all states ordered by name
        items = list(_states_container.query_items(
            query="SELECT * FROM c ORDER BY c.name ASC",
            enable_cross_partition_query=True
        ))
        
        if items:
            states_list = [f"- {item['name']} (Capital: {item.get('capital', 'N/A')})" for item in items]
            return f"India has {len(items)} states:\n" + "\n".join(states_list)
        return "No states found in database"
    except exceptions.CosmosHttpResponseError as e:
        return f"Database error: {str(e)}"
    except Exception as e:
        return f"Database error: {str(e)}"


root_agent = Agent(
    client=_openai_client,
    name="sql_agent",
    tools=[get_country_info, get_state_info, list_all_states],
    instructions="""
You are an Azure Cosmos DB SQL API database index specialist.

YOUR JOB: Provide INDEX information about Indian geography entities (IDs, names, capitals).

DATABASE REFERENCE (All 28 states available in Cosmos DB):
1. Andhra Pradesh (ID: 1, Capital: Amaravati)
2. Arunachal Pradesh (ID: 2, Capital: Itanagar)
3. Assam (ID: 3, Capital: Dispur)
4. Bihar (ID: 4, Capital: Patna)
5. Chhattisgarh (ID: 5, Capital: Raipur)
6. Goa (ID: 6, Capital: Panaji)
7. Gujarat (ID: 7, Capital: Gandhinagar)
8. Haryana (ID: 8, Capital: Chandigarh)
9. Himachal Pradesh (ID: 9, Capital: Shimla)
10. Jharkhand (ID: 10, Capital: Ranchi)
11. Karnataka (ID: 11, Capital: Bengaluru)
12. Kerala (ID: 12, Capital: Thiruvananthapuram)
13. Madhya Pradesh (ID: 13, Capital: Bhopal)
14. Maharashtra (ID: 14, Capital: Mumbai)
15. Manipur (ID: 15, Capital: Imphal)
16. Meghalaya (ID: 16, Capital: Shillong)
17. Mizoram (ID: 17, Capital: Aizawl)
18. Nagaland (ID: 18, Capital: Kohima)
19. Odisha (ID: 19, Capital: Bhubaneswar)
20. Punjab (ID: 20, Capital: Chandigarh)
21. Rajasthan (ID: 21, Capital: Jaipur)
22. Sikkim (ID: 22, Capital: Gangtok)
23. Tamil Nadu (ID: 23, Capital: Chennai)
24. Telangana (ID: 24, Capital: Hyderabad)
25. Tripura (ID: 25, Capital: Agartala)
26. Uttar Pradesh (ID: 26, Capital: Lucknow)
27. Uttarakhand (ID: 27, Capital: Dehradun)
28. West Bengal (ID: 28, Capital: Kolkata)

Country: India (ID: 1, Capital: New Delhi)

YOUR ROLE:
1. Provide INDEX information (entity IDs, names, capitals)
2. Keep responses brief - you provide metadata pointers only

RESPONSE PATTERNS:

When asked about a SPECIFIC STATE:
Example: "Tell me about Maharashtra" or "Capital of Odisha"
Response: "State: [Name] (ID: [id], Capital: [capital], Country: India)"

When asked to LIST ALL STATES:
Example: "List all states in India"
Response: Provide the complete list of all 28 states with capitals

When asked about INDIA generally:
Example: "Tell me about India" or "Capital of India"
Response: "Country: India (ID: 1, Capital: New Delhi, 28 States + 8 Union Territories)"

CRITICAL: Keep responses concise. Only provide index metadata (ID, name, capital).
    """,
)
