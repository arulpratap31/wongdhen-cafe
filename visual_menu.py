"""V6: owner-verified photographic menu detail records.

The V4 menu remains authoritative for names/source references. This extension
stores *optional verified claims*, with unknown data explicitly left unknown.
"""
from __future__ import annotations

import csv
import io
import json
import secrets
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile, File, Form, HTTPException, Request
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Column, Integer, String, Boolean, Text, Float, DateTime, ForeignKey, select, func

VALID_DIETARY = {'unconfirmed', 'vegetarian', 'vegan', 'non_vegetarian'}

class DetailIn(BaseModel):
    description:str|None=Field(default=None,max_length=2500)
    description_verified:bool=False
    dietary_class:str='unconfirmed'
    dietary_verified:bool=False
    contains_egg:bool|None=None
    egg_verified:bool=False
    major_ingredients:list[str]=Field(default_factory=list,max_length=40)
    ingredients_verified:bool=False
    protein_sources:list[str]=Field(default_factory=list,max_length=30)
    protein_verified:bool=False
    protein_grams:float|None=Field(default=None,ge=0,le=1000)
    protein_quantity_verified:bool=False
    allergens:list[str]=Field(default_factory=list,max_length=25)
    allergens_verified:bool=False
    cross_contact_notice:str|None=Field(default=None,max_length=350)
    @model_validator(mode='after')
    def consistent(self):
        if self.dietary_class not in VALID_DIETARY:raise ValueError('Invalid dietary category')
        if self.dietary_verified and self.dietary_class=='unconfirmed':raise ValueError('Cannot verify unknown dietary class')
        if self.egg_verified and self.contains_egg is None:raise ValueError('Choose yes/no to verify egg status')
        if self.protein_quantity_verified and (not self.protein_verified or self.protein_grams is None):
            raise ValueError('Verified protein grams require verified protein sources and a value')
        if self.description_verified and not self.description:raise ValueError('Description is empty')
        for field in ('major_ingredients','protein_sources','allergens'):
            items=getattr(self,field)
            if any(not x.strip() or len(x)>100 for x in items):raise ValueError(f'Invalid {field} item')
        return self


def install_visual_menu(app, Base, engine, Session, MenuItem, authenticated, admin_write, audit, root:Path):
    class MenuDetail(Base):
        __tablename__='menu_item_details_v6'
        id=Column(Integer,primary_key=True)
        menu_item_id=Column(Integer,ForeignKey('menu_items.id'),nullable=False,unique=True,index=True)
        image_path=Column(String(300),nullable=True)
        thumbnail_path=Column(String(300),nullable=True)
        image_alt=Column(String(240),nullable=True)
        image_credit=Column(String(200),nullable=True)
        image_exact_verified=Column(Boolean,nullable=False,default=False)
        image_rights_confirmed=Column(Boolean,nullable=False,default=False)
        description=Column(Text,nullable=True)
        description_verified=Column(Boolean,nullable=False,default=False)
        dietary_class=Column(String(30),nullable=False,default='unconfirmed')
        dietary_verified=Column(Boolean,nullable=False,default=False)
        contains_egg=Column(Boolean,nullable=True)
        egg_verified=Column(Boolean,nullable=False,default=False)
        major_ingredients=Column(Text,nullable=False,default='[]')
        ingredients_verified=Column(Boolean,nullable=False,default=False)
        protein_sources=Column(Text,nullable=False,default='[]')
        protein_verified=Column(Boolean,nullable=False,default=False)
        protein_grams=Column(Float,nullable=True)
        protein_quantity_verified=Column(Boolean,nullable=False,default=False)
        allergens=Column(Text,nullable=False,default='[]')
        allergens_verified=Column(Boolean,nullable=False,default=False)
        cross_contact_notice=Column(String(350),nullable=True)
        updated_at=Column(DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))

    # Additive separate-table change; avoids mutating existing V4 menu/booking tables.
    Base.metadata.create_all(engine,tables=[MenuDetail.__table__])
    def parsed(value):
        try:
            result=json.loads(value or '[]')
            return result if isinstance(result,list) else []
        except (TypeError,ValueError):return []

    def verified_photo(row):
        return bool(row and row.image_path and row.thumbnail_path and row.image_exact_verified and row.image_rights_confirmed)

    def summary(row):
        return {'has_approved_photo':verified_photo(row),
                'thumbnail_url':row.thumbnail_path if verified_photo(row) else None,
                'dietary_class':row.dietary_class if row and row.dietary_verified else 'unconfirmed',
                'contains_egg':row.contains_egg if row and row.egg_verified else None,
                'ingredients_verified':bool(row and row.ingredients_verified),
                'protein_verified':bool(row and row.protein_verified)}

    def summary_map(db,items):
        ids=[x.id for x in items]
        if not ids:return {}
        details=db.scalars(select(MenuDetail).where(MenuDetail.menu_item_id.in_(ids))).all()
        return {x.menu_item_id:summary(x) for x in details}

    def serialize(row, owner=False):
        if row is None:
            return {'image_url':None,'thumbnail_url':None,'image_alt':None,'image_credit':None,
                'image_exact_verified':False,'image_rights_confirmed':False,'description':None,
                'description_verified':False,'dietary_class':'unconfirmed','dietary_verified':False,
                'contains_egg':None,'egg_verified':False,'major_ingredients':[],
                'ingredients_verified':False,'protein_sources':[],'protein_verified':False,
                'protein_grams':None,'protein_quantity_verified':False,'allergens':[],
                'allergens_verified':False,'cross_contact_notice':None}
        photo=verified_photo(row)
        return {'image_url':row.image_path if (photo or owner) else None,
            'thumbnail_url':row.thumbnail_path if (photo or owner) else None,
            'image_alt':row.image_alt if (photo or owner) else None,
            'image_credit':row.image_credit if (photo or owner) else None,
            'image_exact_verified':row.image_exact_verified,'image_rights_confirmed':row.image_rights_confirmed,
            'description':row.description if (row.description_verified or owner) else None,
            'description_verified':row.description_verified,
            'dietary_class':row.dietary_class if (row.dietary_verified or owner) else 'unconfirmed',
            'dietary_verified':row.dietary_verified,
            'contains_egg':row.contains_egg if (row.egg_verified or owner) else None,'egg_verified':row.egg_verified,
            'major_ingredients':parsed(row.major_ingredients) if (row.ingredients_verified or owner) else [],
            'ingredients_verified':row.ingredients_verified,
            'protein_sources':parsed(row.protein_sources) if (row.protein_verified or owner) else [],
            'protein_verified':row.protein_verified,
            'protein_grams':row.protein_grams if (row.protein_quantity_verified or owner) else None,
            'protein_quantity_verified':row.protein_quantity_verified,
            'allergens':parsed(row.allergens) if (row.allergens_verified or owner) else [],
            'allergens_verified':row.allergens_verified,
            'cross_contact_notice':row.cross_contact_notice}

    @app.get('/api/menu/{item_id}/details')
    def customer_detail(item_id:int):
        with Session() as db:
            item=db.get(MenuItem,item_id)
            if not item or not item.published:raise HTTPException(404,'Menu item unavailable')
            detail=db.scalar(select(MenuDetail).where(MenuDetail.menu_item_id==item.id))
            return {'id':item.id,'name':item.name,'category':item.category,
                    'price_display':item.price_display,'price_owner_approved':item.approved,
                    'source_page':item.source_page,'detail':serialize(detail),
                    'price_disclaimer':'Owner-approved current price' if item.approved else 'From supplied menu PDF; current price not owner-confirmed'}

    @app.get('/api/admin/menu/{item_id}/details')
    def owner_detail(item_id:int,request:Request):
        authenticated(request)
        with Session() as db:
            item=db.get(MenuItem,item_id)
            if not item:raise HTTPException(404,'Item not found')
            detail=db.scalar(select(MenuDetail).where(MenuDetail.menu_item_id==item_id))
            return {'id':item.id,'name':item.name,'category':item.category,'source_page':item.source_page,
                    'detail':serialize(detail,owner=True)}

    @app.put('/api/admin/menu/{item_id}/details')
    def edit_detail(item_id:int,payload:DetailIn,request:Request):
        admin_write(request)
        with Session() as db:
            item=db.get(MenuItem,item_id)
            if item is None:raise HTTPException(404,'Item not found')
            detail=db.scalar(select(MenuDetail).where(MenuDetail.menu_item_id==item_id))
            if detail is None:
                detail=MenuDetail(menu_item_id=item_id);db.add(detail)
            for key,value in payload.model_dump().items():
                if key in {'major_ingredients','protein_sources','allergens'}:
                    value=json.dumps([v.strip() for v in value],ensure_ascii=False)
                elif isinstance(value,str):value=value.strip() or None
                setattr(detail,key,value)
            detail.updated_at=datetime.now(timezone.utc)
            audit(db,'menu_v6.details',f'Item {item_id}: owner verification data updated')
            db.commit()
            return {'saved':True,'detail':serialize(detail,owner=True)}

    @app.post('/api/admin/menu/{item_id}/photo')
    async def upload_menu_photo(item_id:int, request:Request, file:UploadFile=File(...),
                                rights_confirmed:bool=Form(False),exact_item_confirmed:bool=Form(False),
                                credit:str=Form('')):
        admin_write(request)
        if not rights_confirmed or not exact_item_confirmed:
            raise HTTPException(422,'Both commercial rights and exact dish match must be confirmed')
        if len(credit)>200:raise HTTPException(422,'Photo credit too long')
        with Session() as db:
            item=db.get(MenuItem,item_id)
            if item is None:raise HTTPException(404,'Item not found')
            name=item.name
        if file.content_type not in {'image/jpeg','image/png','image/webp'}:
            raise HTTPException(422,'Use a JPEG, PNG or WebP photograph')
        data=await file.read(8_000_001)
        if len(data)>8_000_000:raise HTTPException(413,'Maximum image file size is 8 MB')
        try:
            im=Image.open(BytesIO(data));im.verify()
            im=Image.open(BytesIO(data))
            if im.width*im.height>25_000_000:raise ValueError('too many pixels')
            im=ImageOps.exif_transpose(im).convert('RGB')
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise HTTPException(422,'Invalid or oversized photograph')
        folder=root/'static'/'images'/'menu'
        folder.mkdir(parents=True,exist_ok=True)
        token=secrets.token_hex(16)
        full=folder/(token+'.webp'); thumb=folder/(token+'-thumb.webp')
        try:
            large=im.copy(); large.thumbnail((1800,1800)); large.save(full,format='WEBP',quality=83,method=4)
            small=im.copy(); small.thumbnail((480,480)); small.save(thumb,format='WEBP',quality=78,method=4)
            with Session() as db:
                detail=db.scalar(select(MenuDetail).where(MenuDetail.menu_item_id==item_id))
                if detail is None:
                    detail=MenuDetail(menu_item_id=item_id);db.add(detail)
                old=(detail.image_path,detail.thumbnail_path)
                detail.image_path='/static/images/menu/'+full.name
                detail.thumbnail_path='/static/images/menu/'+thumb.name
                detail.image_alt=f'{name} photographed at Wongdhen Cafe'
                detail.image_credit=credit.strip() or None
                detail.image_exact_verified=True
                detail.image_rights_confirmed=True
                detail.updated_at=datetime.now(timezone.utc)
                audit(db,'menu_v6.photo',f'Verified image uploaded for item {item_id}')
                db.commit()
        except Exception:
            # No orphan files if conversion or database commit failed.
            full.unlink(missing_ok=True);thumb.unlink(missing_ok=True)
            raise
        for p in old:
            # Best-effort cleanup after the successful commit, without compromising it.
            if p and p.startswith('/static/images/menu/'):
                try:(folder/Path(p).name).unlink(missing_ok=True)
                except OSError:pass
        return {'saved':True,'image_url':'/static/images/menu/'+full.name,
                'thumbnail_url':'/static/images/menu/'+thumb.name}

    def coverage(db):
        items=db.scalars(select(MenuItem).order_by(MenuItem.category,MenuItem.name)).all()
        details={x.menu_item_id:x for x in db.scalars(select(MenuDetail)).all()}
        public=[i for i in items if i.published]
        result=[]
        for item in public:
            row=details.get(item.id)
            photo=verified_photo(row)
            record={'id':item.id,'name':item.name,'category':item.category,'source_page':item.source_page,
                    'photo_verified':photo,'ingredients_verified':bool(row and row.ingredients_verified),
                    'dietary_verified':bool(row and row.dietary_verified and row.dietary_class!='unconfirmed'),
                    'egg_verified':bool(row and row.egg_verified and row.contains_egg is not None),
                    'protein_verified':bool(row and row.protein_verified),
                    'allergens_verified':bool(row and row.allergens_verified),
                    'price_owner_approved':bool(item.approved)}
            record['missing']=[name for field,name in [('photo_verified','Exact-match photograph'),
                     ('ingredients_verified','Major ingredients'),('dietary_verified','Dietary classification'),
                     ('egg_verified','Egg status'),('protein_verified','Protein sources'),
                     ('allergens_verified','Allergen data'),('price_owner_approved','Current price approval')]
                     if not record[field]]
            result.append(record)
        counts={field:sum(bool(i[field]) for i in result) for field in (
            'photo_verified','ingredients_verified','dietary_verified','egg_verified','protein_verified',
            'allergens_verified','price_owner_approved')}
        return {'total_public_digital_items':len(public),'total_all_digital_items':len(items),
           'categories':len({i.category for i in public}),
           'interactive_public_items':len(public),
           'interactive_coverage_percent':100 if public else 0,
           'known_source_pages':16,'pdf_fully_digitized':False,
           'note':'All current public database items are interactive. The original 16-page PDF is NOT fully digitized; its remaining items must be inventoried before claiming complete printed-menu coverage.',
           'verified_counts':counts,'missing_by_item':result}

    @app.get('/api/admin/menu-v6/coverage')
    def owner_coverage(request:Request):
        authenticated(request)
        with Session() as db:return coverage(db)

    @app.get('/api/admin/menu-v6/coverage.csv')
    def owner_coverage_csv(request:Request):
        authenticated(request)
        with Session() as db:rows=coverage(db)['missing_by_item']
        buffer=io.StringIO();writer=csv.writer(buffer)
        writer.writerow(['id','category','name','source_page','missing_verifications'])
        for row in rows:writer.writerow([row['id'],row['category'],row['name'],row['source_page'],'; '.join(row['missing'])])
        return Response(content='\ufeff'+buffer.getvalue(),media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition':'attachment; filename="wongdhen-v6-coverage.csv"',
                             'Cache-Control':'no-store'})

    return {'summary_map':summary_map,'serialize':serialize,'model':MenuDetail}
