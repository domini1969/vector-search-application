import re
import argparse

class PartNumberClassifier:
    """Classifier for determining if a query is a part number."""
    
    def __init__(self):
        """Initialize the part number classifier."""
        # Common part number prefixes based on data analysis
        self.common_prefixes = {
            'RAD', 'PIP', 'MIL', 'LIN', 'NOR', 'MSA', 'ESA', 'HYP', 
            'KOI', 'WBU', 'CBR', 'HOU', 'BOS', 'VIC', 'AMS', 'E57',
            'NI'
        }
        # Consumer product terms that might look like part numbers but aren't
        self.consumer_products = {
            'iphone', 'macbook', 'surface', 'galaxy', 'kindle', 'gtx'
        }
        # Search terms that indicate a natural language query
        self.search_terms = {
            'how', 'what', 'where', 'when', 'why', 'find', 'best', 'good',
            'better', 'top', 'review', 'price', 'vs', 'versus', 'buy', 'compare'
        }
        # Common English words that indicate a sentence
        self.sentence_words = {
            'a', 'an', 'the', 'of', 'in', 'for', 'to', 'with', 'by', 
            'is', 'are', 'this', 'that', 'these', 'those'
        }
        # Document reference terms
        self.doc_ref_terms = {
            'page', 'table', 'figure', 'section', 'chapter', 'version'
        }
    
    def is_part_number(self, query: str) -> bool:
        """
        Determine if a query is likely a part number.
        
        Args:
            query: User query string
            
        Returns:
            Boolean indicating if the query is likely a part number
        """
        # If blank query, it's not a part number
        if not query or not query.strip():
            return False
        
        # Clean up the query
        cleaned = query.strip()
        
        # Split into words
        words = cleaned.split()
        
        # EARLY REJECTION RULES
        
        # 1. If there are no digits, it's not a part number
        if not re.search(r'[0-9]', cleaned):
            return False
        
        # 2. If it's too short, it's not a part number
        if len(cleaned) < 4:
            return False
        
        # 3. If it has too many words and contains search terms, it's a search query not a part number
        if len(words) > 2 and any(term in cleaned.lower() for term in self.search_terms):
            return False
        
        # 4. If it starts with common document reference terms
        if re.match(r'^(page|table|figure|section|chapter|room)\s+[0-9]', cleaned, re.IGNORECASE):
            return False
        
        # Calculate score based on various factors
        score = 0
        
        # POSITIVE SCORING FACTORS
        
        # 1. Contains both letters and numbers (strong indicator)
        if re.search(r'[A-Za-z]', cleaned) and re.search(r'[0-9]', cleaned):
            score += 3
        
        # 2. Length is in typical part number range (5-16)
        if 5 <= len(cleaned) <= 16:
            score += 2
        elif 16 < len(cleaned) <= 20:
            score += 1
        
        # 3. Contains a dash, dot or specific separators
        if re.search(r'[\-\./]', cleaned):
            score += 2
        
        # 4. Starts with a common part number prefix from our dataset
        if any(cleaned.upper().startswith(prefix) for prefix in self.common_prefixes):
            score += 3
        
        # 5. Has a typical part number pattern structure
        if re.match(r'^[A-Za-z]{1,3}[0-9]{2,}', cleaned):
            score += 2
        
        # 6. Starts with letters (common for part numbers)
        if re.match(r'^[A-Za-z]', cleaned):
            score += 1
        
        # 7. Begins with specific prefixes followed by numbers
        if re.match(r'^(p/n:|part|model|item|no\.)[\s:]+[a-z0-9]', cleaned, re.IGNORECASE):
            score += 2
        
        # 8. Has repeating alpha-numeric patterns
        if re.search(r'([A-Za-z]+[0-9]+){2,}', cleaned):
            score += 2
        
        # 9. Contains numbers with 3+ digits (common in part numbers)
        if re.search(r'[0-9]{3,}', cleaned):
            score += 1
        
        # 10. Has a specific suffix like XL, AL, etc.
        if re.search(r'[A-Z0-9]+(XL|AL|/[SML]|EU)$', cleaned, re.IGNORECASE):
            score += 1
        
        # NEGATIVE SCORING FACTORS
        
        # 1. Contains typical search terms (negative indicator)
        if any(re.search(rf'\b{term}\b', cleaned.lower()) for term in self.search_terms):
            score -= 4
        
        # 2. Has multiple words separated by spaces (negative indicator)
        if len(words) >= 4:
            score -= 4
        elif len(words) == 3:
            score -= 2
        
        # 3. Contains many words that look like a sentence
        if any(re.search(rf'\b{word}\b', cleaned.lower()) for word in self.sentence_words):
            score -= 3
        
        # 4. Contains a product name that isn't a part number
        if any(re.search(rf'\b{prod}\b', cleaned.lower()) for prod in self.consumer_products):
            score -= 3
        
        # 5. Common document references (negative indicator)
        if any(re.search(rf'\b{term}\b', cleaned.lower()) for term in self.doc_ref_terms):
            score -= 3
        
        # Final threshold for classification
        return score >= 4
    
    def explain_classification(self, query: str) -> dict:
        """
        Explain why a query was classified as a part number or not.
        Useful for debugging and tuning the classifier.
        
        Args:
            query: User query string
            
        Returns:
            Dictionary with classification details and explanation
        """
        # If blank query, it's not a part number
        if not query or not query.strip():
            return {"is_part_number": False, "explanation": "Empty query"}
        
        # Clean up the query
        cleaned = query.strip()
        
        # Split into words
        words = cleaned.split()
        
        # EARLY REJECTION RULES
        
        # 1. If there are no digits, it's not a part number
        if not re.search(r'[0-9]', cleaned):
            return {"is_part_number": False, "explanation": "Rejected: Contains no digits"}
        
        # 2. If it's too short, it's not a part number
        if len(cleaned) < 4:
            return {"is_part_number": False, "explanation": "Rejected: Too short (< 4 characters)"}
        
        # 3. If it has too many words and contains search terms, it's a search query not a part number
        if len(words) > 2 and any(term in cleaned.lower() for term in self.search_terms):
            return {"is_part_number": False, "explanation": "Rejected: Multi-word query with search terms"}
        
        # 4. If it starts with common document reference terms
        if re.match(r'^(page|table|figure|section|chapter|room)\s+[0-9]', cleaned, re.IGNORECASE):
            return {"is_part_number": False, "explanation": "Rejected: Starts with document reference term"}
        
        # Initialize score and explanation
        score = 0
        explanation = []
        
        # POSITIVE SCORING FACTORS
        
        # 1. Contains both letters and numbers (strong indicator)
        if re.search(r'[A-Za-z]', cleaned) and re.search(r'[0-9]', cleaned):
            score += 3
            explanation.append("+3: Contains both letters and numbers")
        
        # 2. Length is in typical part number range (5-16)
        if 5 <= len(cleaned) <= 16:
            score += 2
            explanation.append("+2: Length is in typical part number range (5-16)")
        elif 16 < len(cleaned) <= 20:
            score += 1
            explanation.append("+1: Length is in acceptable part number range (17-20)")
        
        # 3. Contains a dash, dot or specific separators
        if re.search(r'[\-\./]', cleaned):
            score += 2
            explanation.append("+2: Contains a dash, dot or specific separator")
        
        # 4. Starts with a common part number prefix from our dataset
        if any(cleaned.upper().startswith(prefix) for prefix in self.common_prefixes):
            score += 3
            explanation.append("+3: Starts with a common part number prefix")
        
        # 5. Has a typical part number pattern structure
        if re.match(r'^[A-Za-z]{1,3}[0-9]{2,}', cleaned):
            score += 2
            explanation.append("+2: Has a typical part number pattern structure (letters then numbers)")
        
        # 6. Starts with letters (common for part numbers)
        if re.match(r'^[A-Za-z]', cleaned):
            score += 1
            explanation.append("+1: Starts with letters")
        
        # 7. Begins with specific prefixes followed by numbers
        if re.match(r'^(p/n:|part|model|item|no\.)[\s:]+[a-z0-9]', cleaned, re.IGNORECASE):
            score += 2
            explanation.append("+2: Begins with specific part number prefix")
        
        # 8. Has repeating alpha-numeric patterns
        if re.search(r'([A-Za-z]+[0-9]+){2,}', cleaned):
            score += 2
            explanation.append("+2: Has repeating alpha-numeric patterns")
        
        # 9. Contains numbers with 3+ digits (common in part numbers)
        if re.search(r'[0-9]{3,}', cleaned):
            score += 1
            explanation.append("+1: Contains numbers with 3+ digits")
        
        # 10. Has a specific suffix like XL, AL, etc.
        if re.search(r'[A-Z0-9]+(XL|AL|/[SML]|EU)$', cleaned, re.IGNORECASE):
            score += 1
            explanation.append("+1: Has a specific suffix (XL, AL, etc.)")
        
        # NEGATIVE SCORING FACTORS
        
        # 1. Contains typical search terms (negative indicator)
        if any(re.search(rf'\b{term}\b', cleaned.lower()) for term in self.search_terms):
            score -= 4
            explanation.append("-4: Contains typical search terms")
        
        # 2. Has multiple words separated by spaces (negative indicator)
        if len(words) >= 4:
            score -= 4
            explanation.append("-4: Has 4+ words separated by spaces")
        elif len(words) == 3:
            score -= 2
            explanation.append("-2: Has 3 words separated by spaces")
        
        # 3. Contains many words that look like a sentence
        if any(re.search(rf'\b{word}\b', cleaned.lower()) for word in self.sentence_words):
            score -= 3
            explanation.append("-3: Contains words that look like a sentence")
        
        # 4. Contains a product name that isn't a part number
        if any(re.search(rf'\b{prod}\b', cleaned.lower()) for prod in self.consumer_products):
            score -= 3
            explanation.append("-3: Contains a consumer product name")
        
        # 5. Common document references (negative indicator)
        if any(re.search(rf'\b{term}\b', cleaned.lower()) for term in self.doc_ref_terms):
            score -= 3
            explanation.append("-3: Contains common document references")
        
        # Final result
        is_part_number = score >= 4
        return {
            "is_part_number": is_part_number,
            "score": score,
            "explanation": explanation,
            "decision": "IS A PART NUMBER" if is_part_number else "IS NOT A PART NUMBER",
            "threshold": "Threshold: 4"
        }


def main():
    parser = argparse.ArgumentParser(description='Part Number Classifier')
    parser.add_argument('query', help='The query to classify', nargs='?')
    parser.add_argument('--explain', action='store_true', 
                        help='Show detailed explanation of classification')
    parser.add_argument('--interactive', action='store_true',
                        help='Run in interactive mode')
    
    args = parser.parse_args()
    
    classifier = PartNumberClassifier()
    
    if args.interactive:
        print("Part Number Classifier - Interactive Mode")
        print("Enter 'exit' or 'quit' to end the program")
        print("Enter 'explain' before your query to see detailed classification")
        
        while True:
            user_input = input("\nEnter query: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                break
                
            explain_mode = False
            if user_input.lower().startswith('explain '):
                explain_mode = True
                user_input = user_input[8:].strip()
                
            if not user_input:
                print("Please enter a query")
                continue
                
            if explain_mode:
                result = classifier.explain_classification(user_input)
                print(f"\nQuery: '{user_input}'")
                print(f"Decision: {result['decision']}")
                print(f"Score: {result['score']} (Threshold: 4)")
                print("\nExplanation:")
                for point in result['explanation']:
                    print(f"  {point}")
            else:
                is_part = classifier.is_part_number(user_input)
                print(f"'{user_input}' {'IS' if is_part else 'IS NOT'} a part number")
    
    elif args.query:
        query = args.query
        
        if args.explain:
            result = classifier.explain_classification(query)
            print(f"Query: '{query}'")
            print(f"Decision: {result['decision']}")
            print(f"Score: {result['score']} (Threshold: 4)")
            print("\nExplanation:")
            for point in result['explanation']:
                print(f"  {point}")
        else:
            is_part = classifier.is_part_number(query)
            print(f"'{query}' {'IS' if is_part else 'IS NOT'} a part number")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()