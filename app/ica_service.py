"""
ICA.se product search and cart integration service.
"""
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# Try to import requests and BeautifulSoup
try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False
    logger.warning("requests or beautifulsoup4 not installed. ICA scraping will be disabled.")


# ICA API endpoints (unofficial, may change)
ICA_SEARCH_API = "https://handla.ica.se/api/search-info/v1/search/skus"
ICA_STORE_API = "https://handla.ica.se/api/store/v1"
ICA_BASE_URL = "https://www.ica.se"
ICA_HANDLA_URL = "https://handla.ica.se"

# Default headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7',
}


def search_ica_products(search_term: str, limit: int = 5) -> List[Dict]:
    """
    Search for products on ICA.se.
    
    Args:
        search_term: Product name to search for
        limit: Maximum number of results
    
    Returns:
        List of product dicts with name, price, url, image_url
    """
    if not SCRAPING_AVAILABLE:
        logger.warning("Scraping libraries not available")
        return []
    
    try:
        # Try the ICA search API
        params = {
            'searchTerm': search_term,
            'limit': limit,
            'includeStoresWithStoreNumbersLike': '',
        }
        
        response = requests.get(
            ICA_SEARCH_API,
            params=params,
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            products = []
            
            # Parse the API response
            items = data.get('searchResultProducts', []) or data.get('products', []) or []
            
            for item in items[:limit]:
                product = {
                    'name': item.get('name', ''),
                    'brand': item.get('brand', ''),
                    'price': item.get('price', {}).get('current', {}).get('amount') if isinstance(item.get('price'), dict) else item.get('price'),
                    'price_unit': item.get('price', {}).get('unit', 'st') if isinstance(item.get('price'), dict) else 'st',
                    'package_size': item.get('packageSize', '') or item.get('packageInformation', ''),
                    'image_url': item.get('imageUrl', ''),
                    'product_id': item.get('sku', '') or item.get('productId', ''),
                    'url': f"{ICA_HANDLA_URL}/produkt/{item.get('sku', '')}" if item.get('sku') else None,
                    'category': item.get('category', ''),
                    'comparison_price': item.get('comparisonPrice', ''),
                }
                products.append(product)
            
            return products
        
        # Fallback: Try web scraping if API fails
        return _scrape_ica_search(search_term, limit)
        
    except requests.RequestException as e:
        logger.error(f"Error searching ICA: {e}")
        return _scrape_ica_search(search_term, limit)
    except Exception as e:
        logger.error(f"Unexpected error searching ICA: {e}")
        return []


def _scrape_ica_search(search_term: str, limit: int = 5) -> List[Dict]:
    """
    Fallback scraping method for ICA product search.
    """
    if not SCRAPING_AVAILABLE:
        return []
    
    try:
        search_url = f"{ICA_BASE_URL}/sok/{quote_plus(search_term)}"
        
        response = requests.get(
            search_url,
            headers={**HEADERS, 'Accept': 'text/html'},
            timeout=10
        )
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        # Try to find product cards (structure may vary)
        product_cards = soup.select('[data-testid="product-card"], .product-card, article.product')
        
        for card in product_cards[:limit]:
            try:
                name_el = card.select_one('[data-testid="product-name"], .product-name, h2, h3')
                price_el = card.select_one('[data-testid="product-price"], .product-price, .price')
                link_el = card.select_one('a[href*="/produkt/"]')
                img_el = card.select_one('img')
                
                product = {
                    'name': name_el.get_text(strip=True) if name_el else 'Okänd produkt',
                    'brand': '',
                    'price': price_el.get_text(strip=True) if price_el else None,
                    'price_unit': 'st',
                    'package_size': '',
                    'image_url': img_el.get('src', '') if img_el else '',
                    'url': ICA_BASE_URL + link_el.get('href', '') if link_el else None,
                    'product_id': '',
                }
                products.append(product)
            except Exception as e:
                logger.debug(f"Error parsing product card: {e}")
                continue
        
        return products
        
    except Exception as e:
        logger.error(f"Error scraping ICA: {e}")
        return []


def get_ica_search_url(search_term: str) -> str:
    """Get URL to search results on ICA Handla."""
    return f"https://handla.ica.se/sok?q={quote_plus(search_term)}"


def generate_ica_cart_links(products: List[Dict]) -> Dict:
    """
    Generate links for adding products to ICA cart.
    
    Note: ICA doesn't have a public API for cart manipulation,
    so this returns search links instead.
    
    Args:
        products: List of products with search terms
    
    Returns:
        Dict with search_links and instructions
    """
    search_links = []
    
    for product in products:
        search_term = product.get('ica_search_term') or product.get('original_name', '')
        if search_term:
            search_links.append({
                'ingredient': product.get('original_name', search_term),
                'amount': product.get('amount', ''),
                'unit': product.get('unit', ''),
                'search_url': get_ica_search_url(search_term),
                'search_term': search_term,
            })
    
    return {
        'search_links': search_links,
        'instructions': 'Klicka på länkarna för att söka efter produkterna på ICA. '
                       'Du kan sedan lägga dem i din varukorg.',
        'handla_url': f"{ICA_BASE_URL}/handla/",
    }


def search_products_batch(ingredients: List[Dict]) -> List[Dict]:
    """
    Search ICA for multiple ingredients at once.
    
    Args:
        ingredients: List of dicts with 'name', 'amount', 'unit'
    
    Returns:
        List of ingredients with 'ica_products' added
    """
    results = []
    
    for ing in ingredients:
        search_term = ing.get('ica_search_term') or ing.get('name', '')
        products = search_ica_products(search_term, limit=3)
        
        result = {
            **ing,
            'ica_products': products,
            'ica_search_url': get_ica_search_url(search_term),
        }
        results.append(result)
    
    return results


def is_ica_available() -> bool:
    """Check if ICA integration is available."""
    return SCRAPING_AVAILABLE
