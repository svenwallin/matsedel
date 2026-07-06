"""
Gemini AI service for intelligent ingredient matching and ICA product suggestions.
"""
import os
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import google.generativeai
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Gemini features will be disabled.")


def get_gemini_client():
    """Get configured Gemini client."""
    if not GEMINI_AVAILABLE:
        return None
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        logger.warning("GEMINI_API_KEY not set. Gemini features will be disabled.")
        return None
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')


def match_ingredients_to_ica_products(ingredients: List[Dict]) -> Optional[List[Dict]]:
    """
    Use Gemini AI to match recipe ingredients to likely ICA product names.
    
    Args:
        ingredients: List of dicts with 'name', 'amount', 'unit'
    
    Returns:
        List of dicts with original ingredient info plus 'ica_search_term' and 'ica_suggestions'
    """
    model = get_gemini_client()
    if not model:
        return None
    
    # Build the prompt
    ingredient_list = "\n".join([
        f"- {ing['name']}: {ing['amount']} {ing['unit']}"
        for ing in ingredients
    ])
    
    prompt = f"""Du är en expert på svenska matvaror och ICA:s produktsortiment.

Jag har en inköpslista med ingredienser. För varje ingrediens, ge mig:
1. Ett bra sökord att använda på ica.se för att hitta produkten
2. 2-3 specifika produktförslag som troligen finns på ICA (med ungefärligt pris om du vet)
3. Vilken avdelning på ICA produkten troligen finns i

Ingredienser:
{ingredient_list}

Svara i JSON-format enligt detta schema:
{{
  "products": [
    {{
      "original_name": "ingrediensnamn",
      "amount": "mängd",
      "unit": "enhet",
      "ica_search_term": "sökord för ica.se",
      "ica_department": "avdelning (t.ex. Mejeri, Kött, Frukt & Grönt)",
      "suggestions": [
        {{
          "name": "produktnamn",
          "brand": "varumärke eller ICA",
          "estimated_price": "ca XX kr",
          "package_size": "storlek"
        }}
      ]
    }}
  ]
}}

Ge ENDAST valid JSON som svar, ingen annan text."""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            # Remove first and last lines if they are code block markers
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines[-1].strip() == '```':
                lines = lines[:-1]
            response_text = '\n'.join(lines)
        
        result = json.loads(response_text)
        return result.get('products', [])
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        logger.debug(f"Response was: {response_text}")
        return None
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None


def generate_ica_shopping_summary(ingredients: List[Dict], matched_products: List[Dict]) -> Optional[str]:
    """
    Generate a human-readable shopping summary with tips.
    
    Args:
        ingredients: Original ingredient list
        matched_products: Products matched by Gemini
    
    Returns:
        Markdown-formatted shopping guide
    """
    model = get_gemini_client()
    if not model:
        return None
    
    # Create ingredient list for prompt
    ingredient_list = "\n".join([
        f"- {ing['name']}: {ing['amount']} {ing['unit']}"
        for ing in ingredients
    ])
    
    prompt = f"""Du är en svensk matinköpsexpert. Skapa en praktisk inköpslista grupperad efter butiksavdelning.

Ingredienser att handla:
{ingredient_list}

Formatera listan så här:

### Grönt & Grönsaker
- **Ingrediens:** antal *(info om förpackning, t.ex. "säljs i 500g påsar")*

### Kylvaror (Mejeri & Chark)
- **Ingrediens:** antal *(praktisk info)*

### Kolonial & Skafferi
- **Ingrediens:** antal *(praktisk info)*

### Kryddor & Basvaror (Kolla skafferiet först!)
- **Ingrediens:** antal
- *Tips: Vatten tas från kranen och behöver inte handlas*

Regler:
1. Gruppera ingredienser efter var de finns i butiken
2. Avrunda till praktiska förpackningsstorlekar (t.ex. "1 förpackning 500g" istället för "467g")
3. Lägg till hjälpsamma kommentarer i kursiv *(som denna)*
4. Ta bort vatten från listan (det finns i kranen)
5. Slå ihop liknande ingredienser om möjligt
6. Använd svenska termer och vanliga svenska förpackningsstorlekar

Svara ENDAST med den formaterade listan, inget annat."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API error generating summary: {e}")
        return None


def is_gemini_available() -> bool:
    """Check if Gemini AI is available and configured."""
    if not GEMINI_AVAILABLE:
        return False
    return bool(os.environ.get('GEMINI_API_KEY'))
