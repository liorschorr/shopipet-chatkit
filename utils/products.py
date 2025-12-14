"""
Product Formatting Utilities
Centralized logic for formatting products for OpenAI and frontend display
"""


def safe_int(val, default=0):
    """Convert to integer safely"""
    try:
        if val is None:
            return default
        return int(float(val))  # Handles "5.0" strings
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0):
    """Convert to float safely"""
    try:
        if not val:
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def get_sales_rank(sales_count):
    """Get sales rank text based on count"""
    count = safe_int(sales_count)
    if count >= 20:
        return "מוביל (רב מכר 🔥)"
    elif count >= 5:
        return "מבוקש"
    return "רגיל"


def get_stock_status_text(stock_quantity, status_tag):
    """
    Get human-readable stock status

    Args:
        stock_quantity: Stock quantity (can be None for unmanaged stock)
        status_tag: WooCommerce stock status ('instock', 'outofstock', etc.)

    Returns:
        Hebrew stock status text
    """
    # Check main status tag first
    if status_tag != 'instock':
        return "אזל מהמלאי"

    # If stock quantity is None (unmanaged) - consider it in stock
    if stock_quantity is None:
        return "במלאי"

    qty = safe_int(stock_quantity)

    if qty > 3:
        return "במלאי"
    elif qty >= 1:
        return f"מלאי נמוך (נותרו רק {qty} יחידות, כדאי להזדרז! 🏃‍♂️)"
    else:
        # Strange case: instock but quantity 0
        return "אזל מהמלאי"


def format_product_for_ai(product: dict) -> str:
    """
    Format a WooCommerce product dictionary into text for OpenAI Vector Store

    This is the single source of truth for product formatting.
    Used by both sync.py and any future catalog generation.

    Args:
        product: WooCommerce product dictionary

    Returns:
        Formatted product text block
    """
    system_id = product.get('id')
    name = product.get('name', 'N/A')

    # Extract identifiers
    identifiers = set()
    if product.get('sku'):
        identifiers.add(str(product.get('sku')))

    for meta in product.get('meta_data', []):
        key = str(meta.get('key', '')).lower()
        if any(k in key for k in ['gtin', 'ean', 'isbn', 'upc', 'barcode']):
            val = meta.get('value')
            if val:
                identifiers.add(str(val))

    codes_display = ", ".join(identifiers) if identifiers else "ללא"

    # Price information
    price_str = f"{product.get('price', '0')} ₪"
    sale_info = ""

    if product.get('on_sale'):
        reg = product.get('regular_price', '')
        sale = product.get('sale_price', '')
        date_to = product.get('date_on_sale_to', '')
        sale_info = f"מבצע: {sale} ₪ (במקום {reg} ₪)"
        if date_to:
            sale_info += f" - בתוקף עד {date_to}"

    # Stock status
    stock_display = get_stock_status_text(
        product.get('stock_quantity'),
        product.get('stock_status')
    )

    # Weight
    w_float = safe_float(product.get('weight'))
    weight_display = ""
    if w_float > 0 and w_float < 1.0:
        weight_display = f"{int(w_float * 1000)} גרם"
    elif w_float >= 1.0:
        weight_display = f"{w_float} ק\"ג"

    # Categories and tags
    categories = ", ".join([c['name'] for c in product.get('categories', [])])
    tags = ", ".join([t['name'] for t in product.get('tags', [])])

    # Brand
    brands_list = [b['name'] for b in product.get('brands', [])]
    if not brands_list:
        for meta in product.get('meta_data', []):
            if 'brand' in str(meta.get('key', '')).lower():
                brands_list.append(str(meta.get('value')))
    brand_display = ", ".join(brands_list)

    # Sales rank
    sales_rank = get_sales_rank(product.get('total_sales'))

    # Attributes
    attributes_list = []
    for attr in product.get('attributes', []):
        opts = ", ".join(attr.get('options', []))
        attributes_list.append(f"{attr.get('name')}: {opts}")
    attributes_str = " | ".join(attributes_list)

    # Description
    raw_desc = str(product.get('short_description', '')) + " " + str(product.get('description', ''))
    clean_desc = (
        raw_desc
        .replace('<p>', '')
        .replace('</p>', '')
        .replace('<br>', '\n')
        .replace('&nbsp;', ' ')
        .strip()
    )
    if len(clean_desc) > 400:
        clean_desc = clean_desc[:400] + "..."

    # Build the formatted block
    lines = ["--- מוצר ---"]
    lines.append(f"System_ID: {system_id} (INTERNAL)")
    lines.append(f"מזהים (מק\"ט/ברקוד): {codes_display}")
    lines.append(f"שם: {name}")

    if brand_display:
        lines.append(f"מותג: {brand_display}")

    lines.append(f"קטגוריות: {categories}")

    if tags:
        lines.append(f"תגיות: {tags}")

    if attributes_str:
        lines.append(f"מאפיינים: {attributes_str}")

    lines.append(f"מחיר: {price_str}")

    if sale_info:
        lines.append(sale_info)

    if weight_display:
        lines.append(f"משקל: {weight_display}")

    lines.append(f"מצב מלאי: {stock_display}")
    lines.append(f"פופולריות: {sales_rank}")
    lines.append(f"תיאור: {clean_desc}")
    lines.append(f"קישור ישיר: /?p={system_id}")
    lines.append("------------\n")

    return "\n".join(lines)
