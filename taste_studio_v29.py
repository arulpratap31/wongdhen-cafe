"""V29 Taste & Visit Studio: public, published-menu-only discovery.

No speculative ingredients/allergens, live stock, discounts or booking confirmations.
A shortlist is an explicitly shareable *plan*, never an order.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException, Query
from sqlalchemy import func, or_, select


TOPICS = {
    'all': ('Everything on the menu', ()),
    'coffee': ('Coffee & sips', ('coffee', 'latte', 'cappuccino', 'espresso', 'mocha', 'tea', 'drink', 'beverage', 'shake', 'lemonade', 'smoothie')),
    'dumplings': ('Dumplings & momos', ('dumpling', 'momo', 'shumai', 'gyoza', 'bao')),
    'mains': ('Meals & comfort plates', ('pasta', 'noodle', 'ramen', 'rice', 'curry', 'sandwich', 'burger', 'hot pot')),
    'sweet': ('Sweets & bakery', ('dessert', 'cake', 'waffle', 'pancake', 'toast', 'brownie', 'cookie', 'bakery', 'tart')),
}


def install_taste_studio_v29(app, Session, MenuItem, Setting):
    def published():
        return select(MenuItem).where(MenuItem.published.is_(True))

    def escaped(term: str) -> str:
        return term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

    def phrase_match(words):
        return or_(*(or_(MenuItem.name.ilike('%' + escaped(word) + '%', escape='\\'),
                         MenuItem.category.ilike('%' + escaped(word) + '%', escape='\\')) for word in words))

    def item_payload(item):
        # Show the original source value rather than pretending variant prices are single totals.
        return {'id': item.id, 'name': item.name, 'category': item.category,
                'price_display': item.price_display, 'source_page': item.source_page,
                'owner_approved': bool(item.approved),
                'single_price_rupees': int(item.price_display.strip()) if re.fullmatch(r'\d{1,5}', item.price_display.strip()) else None}

    @app.get('/api/v29/taste/topics')
    def topic_list():
        with Session() as db:
            response=[]
            for key, (label, words) in TOPICS.items():
                statement=published()
                if words: statement=statement.where(phrase_match(words))
                response.append({'id':key, 'name':label,
                                 'count':int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)})
        return {'topics':response, 'notice':'Categories are keyword matches in the published menu, not verified dietary or allergy classifications.'}

    @app.get('/api/v29/taste/items')
    def browse_taste(topic: str = Query('all', max_length=20),
                     q: str = Query('', max_length=70),
                     limit: int = Query(12, ge=1, le=24),
                     offset: int = Query(0, ge=0, le=5000)):
        if topic not in TOPICS: raise HTTPException(422, 'Unknown menu topic')
        term=q.strip()
        with Session() as db:
            statement=published()
            words=TOPICS[topic][1]
            if words: statement=statement.where(phrase_match(words))
            if term: statement=statement.where(or_(MenuItem.name.ilike('%'+escaped(term)+'%',escape='\\'),
                                                   MenuItem.category.ilike('%'+escaped(term)+'%',escape='\\')))
            total=int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
            items=db.scalars(statement.order_by(MenuItem.category, MenuItem.name, MenuItem.id)
                             .offset(offset).limit(limit)).all()
        return {'items':[item_payload(i) for i in items], 'total':total,
                'offset':offset,'has_more':offset+len(items)<total,
                'notice':'Menu transcription. Prices and availability are not live; confirm with café staff. Nothing here is an order.'}

    @app.get('/api/v29/taste/shortlist')
    def shared_shortlist(ids: str = Query('', max_length=110)):
        if not ids or not re.fullmatch(r'[1-9][0-9]*(,[1-9][0-9]*){0,7}',ids):
            raise HTTPException(422, 'Provide 1–8 comma-separated numeric dish IDs')
        selected=[int(n) for n in ids.split(',')]
        if len(set(selected))!=len(selected) or any(n>2_000_000_000 for n in selected):
            raise HTTPException(422, 'Dish IDs must be unique and valid')
        with Session() as db:
            rows={i.id:i for i in db.scalars(published().where(MenuItem.id.in_(selected))).all()}
        items=[item_payload(rows[i]) for i in selected if i in rows]
        all_single=len(items)==len(selected) and all(item['single_price_rupees'] is not None for item in items)
        return {'items':items,'missing_ids':[i for i in selected if i not in rows],
                'estimated_subtotal_rupees':sum(item['single_price_rupees'] for item in items) if all_single else None,
                'estimate_complete':all_single,
                'notice':'A personal dining shortlist, not an order, booking, invoice, or final bill. Menu prices may have changed; variants, taxes and other charges are not estimated.'}

    @app.get('/api/v29/visit/essentials')
    def visit_essentials():
        with Session() as db:
            values={key: ((db.get(Setting,key).value or '').strip() if db.get(Setting,key) else '')
                    for key in ('address','hours','phone')}
        return {'venue':'Wongdhen Café', 'neighborhood':'Majnu Ka Tila, New Delhi',
                **{k:(v or None) for k,v in values.items()},
                'opening_hours_verified':False,
                'visit_url':'/visit','reservation_url':'/reservations',
                'updated_at_utc':datetime.now(timezone.utc).isoformat(),
                'notice':'Contact the café to confirm opening hours, table arrangements and any special requests.'}
