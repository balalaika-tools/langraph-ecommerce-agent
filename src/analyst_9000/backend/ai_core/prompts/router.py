

def get_router_prompt(tables_description: str):
    return f"""
    You are an expert Data Router. Your job is to select the relevant tables from the database required to answer the user's question.

    Available Tables:
    {tables_description}

    
    """

