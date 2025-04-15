def analyze_spending_patterns(transactions):
    """
    Analyze user spending patterns from transaction history.

    Args:
        transactions (list): List of transaction dictionaries

    Returns:
        dict: Analysis results with categories and trends
    """
    if not transactions:
        return {
            "categories": {},
            "trends": {
                "increasing": [],
                "decreasing": []
            },
            "summary": "Not enough transaction data for analysis."
        }

    # Extract categories from transaction descriptions
    categories = {}

    # Simple category detection from keywords
    category_keywords = {
        "food": ["restaurant", "cafe", "grocery", "food", "meal", "dining"],
        "transport": ["transport", "uber", "taxi", "bus", "mtr", "train", "fare"],
        "shopping": ["shop", "store", "mall", "purchase", "buy"],
        "entertainment": ["movie", "cinema", "theater", "game", "entertainment"],
        "utilities": ["bill", "utility", "electric", "water", "gas", "internet"],
        "housing": ["rent", "mortgage", "housing", "maintenance"],
        "healthcare": ["doctor", "hospital", "medicine", "healthcare", "medical"],
        "education": ["tuition", "school", "course", "book", "education"],
    }

    # Categorize transactions
    for transaction in transactions:
        if transaction['transaction_type'] != 'Withdrawal':
            continue

        description = transaction['description'].lower() if transaction['description'] else ""
        amount = float(transaction['amount'])

        # Determine category
        category = "other"
        for cat, keywords in category_keywords.items():
            if any(keyword in description for keyword in keywords):
                category = cat
                break

        # Add to categories
        if category not in categories:
            categories[category] = 0
        categories[category] += amount

    # Sort categories by total amount
    sorted_categories = {k: v for k, v in sorted(categories.items(), key=lambda item: item[1], reverse=True)}

    # Identify trends (would need more data for real analysis)
    trends = {
        "increasing": list(sorted_categories.keys())[:2] if len(sorted_categories) >= 2 else [],
        "decreasing": []
    }

    # Generate summary
    if sorted_categories:
        top_category = next(iter(sorted_categories))
        top_amount = sorted_categories[top_category]
        summary = f"Your highest spending category is {top_category} at HK${top_amount:.2f}."
    else:
        summary = "No spending transactions found to analyze."

    return {
        "categories": sorted_categories,
        "trends": trends,
        "summary": summary
    }


def extract_transaction_intent(message):
    """
    Extract transaction intent from a natural language message.

    Args:
        message (str): The user's message

    Returns:
        dict: Transaction details if a transaction intent is detected, None otherwise
    """
    message = message.lower()

    # Simple keyword detection for transfer intent
    transfer_keywords = ["transfer", "send", "pay", "give"]

    if any(keyword in message for keyword in transfer_keywords):
        # Try to extract amount
        import re
        amount_pattern = r"(\$|hk\$|\bhk\s*\$)?\s*(\d+(?:\.\d+)?)"
        amount_match = re.search(amount_pattern, message)

        amount = None
        if amount_match:
            amount = float(amount_match.group(2))

        # Extract potential recipient (very basic implementation)
        recipient = None
        to_pattern = r"to\s+(\w+)"
        to_match = re.search(to_pattern, message)

        if to_match:
            recipient = to_match.group(1)

        if amount:
            return {
                "type": "transfer",
                "amount": amount,
                "recipient": recipient,
                "detected": True
            }

    return {"detected": False}