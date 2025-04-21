from typing import List
import json
import re
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from transactions.routes import get_db_connection

conn = get_db_connection()

@tool
def validate_user(user_id: int, addresses: List[str]):
    """Validate user using historical addresses.

    Args:
        user_id (int): the user ID.
        addresses (List[str]): Previous addresses as a list of strings.
    """
    return True

@tool
def withdraw_money(user_id:int, source_account: str, amount: int):
    """Help user to withdraw money from an account

    Args:
        user_id (int): the user ID.
        source_account (str): the source account user want to withdraw from
        amount (int): the amount of money
    """

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT account_id FROM accounts
        WHERE user_id = {user_id} and account_name = '{source_account}';
        """
    )
    source_id = cursor.fetchone()
    print(source_id)
    return source_id

# Define the tools
tools = [validate_user, withdraw_money]

# Create a simple function to parse and execute the tool
def execute_tools_directly(query):
    tool_dict = {tool.name: tool for tool in tools}

    # Initialize the LLM
    llm = ChatOllama(
        model="llama3.2",
        temperature=0,
    )

    # Create a system prompt to encourage direct tool usage
    system_message = """You are an assistant that helps with executing tools. 
    When responding, ALWAYS use the following format:

    Tool: <tool_name>
    Arguments: 
    {
        "arg1": value1,
        "arg2": value2,
        ...
    }

    Use only the tools that are available to you."""

    # Add descriptions of available tools
    for tool in tools:
        system_message += f"\n\nTool: {tool.name}\nDescription: {tool.description}\n"

    # Invoke the LLM
    response = llm.invoke([
        {"role": "system", "content": system_message},
        {"role": "user", "content": query}
    ])

    print(f"LLM Response:\n{response.content}")

    # Extract tool and arguments
    tool_match = re.search(r"Tool: (\w+)", response.content)
    args_match = re.search(r"Arguments:\s*(\{.*?\})", response.content, re.DOTALL)

    if tool_match and args_match:
        tool_name = tool_match.group(1)
        args_str = args_match.group(1)

        try:
            # Parse JSON arguments
            args = json.loads(args_str)

            # Execute the tool if it exists
            if tool_name in tool_dict:
                # Use the invoke method instead of calling directly
                result = tool_dict[tool_name].invoke(args)
                return result
            else:
                return f"Tool '{tool_name}' not found."
        except json.JSONDecodeError:
            return f"Error parsing arguments: {args_str}"
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    return "No tool execution pattern found in the response."




# Execute
queries = [
    "I want to withdraw $500 from my Primary Savings (userid: 3)"

]

for query in queries:
    result = execute_tools_directly(query)
    print(f"\nTool Execution Result: {result}")


# conn = get_db_connection()
# cursor = conn.cursor(dictionary=True)
#
# cursor.execute(
#     """
#     INSERT INTO transactions
#     (source_account_id, destination_account_id, amount, transaction_type, description, status)
#     VALUES (%s, %s, %s, %s, %s, %s)
#     """,
#     (source_account_id, destination_account_id, amount, transaction_type, description, 'pending')
# )
# conn.commit()