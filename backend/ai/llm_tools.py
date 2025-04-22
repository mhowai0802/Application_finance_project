from contextlib import nullcontext
from typing import List
import json
import re
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from transactions.routes import get_db_connection

conn = get_db_connection()


@tool
def withdraw_money(user_id: int, source_account: str, amount: int, description: str):
    """Help user to withdraw money from an account

    Args:
        user_id (int): the user ID.
        source_account (str): the source account user want to withdraw from
        amount (int): the amount of money
        description (str): the usage of the withdrawal money
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT account_id FROM accounts
        WHERE user_id = {user_id} and account_name = '{source_account}';
        """
    )
    source_id = cursor.fetchone()
    source_id_number = source_id['account_id']
    output = {
        'source_account_id': source_id_number,
        'destination_account_id': None,
        'transaction_type': "Withdrawal",
        'amount': amount,
        'description': description

    }
    return output


@tool
def transfer_money(user_id: int, source_account: str, target_account: str, amount: int, description: str):
    """Help user to transfer money from source_account to target_account

    Args:
        user_id (int): the user ID.
        amount (int): the amount of money.
        source_account (str): the source account user want to withdraw from
        target_account (str): the target account user want to transfer to
        description (str): the usage of the withdrawal money
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        f"""
        SELECT account_id FROM accounts
        WHERE user_id = {user_id} and account_name LIKE '%{source_account}%';
        """
    )
    source_id = cursor.fetchone()['account_id']
    cursor.execute(
        f"""
        SELECT account_id FROM accounts
        WHERE user_id = {user_id} and account_name LIKE '%{target_account}%';
        """
    )
    target_id = cursor.fetchone()['account_id']
    output = {
        'source_account_id': source_id,
        'destination_account_id': target_id,
        'transaction_type': "Transfer",
        'amount': amount,
        'description': description
    }
    return output


# Define the tools
tools = [transfer_money, withdraw_money]


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
