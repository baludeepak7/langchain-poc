PROMPT_TEMPLATE = """
You are provided with a list of partner profiles.
{http_response}
From this data, fetch me the id corresponding to the name {name} and don't give Python script.
Return the fetched id within | |
"""
