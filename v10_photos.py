"""V10 photography catalog: persistent editorial metadata and paged public API.
No changes to existing menu/booking/reward tables, or uploaded Gallery records.
"""
import json,re
from pathlib import Path
from fastapi import HTTPException,Request
from pydantic import BaseModel,Field
from sqlalchemy import Column,String,Boolean,Integer,select,func,or_

CAT={'food','drinks','desserts','interiors','ambience','exterior','branding'}

class PhotoEdit(BaseModel):
    caption:str|None=Field(default=None,max_length=240)
    alt_text:str|None=Field(default=None,max_length=280)
    published:bool|None=None
    featured:bool|None=None
    focal_point:str|None=Field(default=None,max_length=24)
    display_order:int|None=Field(default=None,ge=0,le=999999)


def install_v10(app,Base,engine,Session,Gallery,authenticated,admin_write,audit,root):
    class Photo(Base):
        __tablename__='v10_photo_catalog'
        id=Column(String(16),primary_key=True)
        filename=Column(String(240),nullable=False)
        category=Column(String(40),nullable=False,index=True)
        caption=Column(String(240),nullable=False,default='')
        alt_text=Column(String(280),nullable=False,default='')
        published=Column(Boolean,nullable=False,default=True,index=True)
        featured=Column(Boolean,nullable=False,default=False)
        focal_point=Column(String(24),nullable=False,default='50% 50%')
        display_order=Column(Integer,nullable=False,default=0)
    Base.metadata.create_all(engine,tables=[Photo.__table__])
    manifest_path=Path(root)/'docs/V10_MEDIA_MANIFEST.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    lookup={p['id']:p for p in manifest}
    # Seed only missing images: never overwrite editing or delete existing catalog entries.
    with Session() as db:
        existing=set(db.scalars(select(Photo.id)).all())
        new=[Photo(id=p['id'],filename=p['filename'],category=p['category'],caption=p['visual_subject'],alt_text=p['alt_text'],
                   published=True,featured=p['priority']=='featured',focal_point=p['focal_point'],display_order=i)
             for i,p in enumerate(manifest) if p['id'] not in existing]
        if new:db.add_all(new);db.commit()

    def get_page(category,query,page,page_size,include_hidden=False):
        if category and category not in CAT:raise HTTPException(422,'Unknown category')
        page=min(max(page,1),100000);page_size=min(max(page_size,1),60);query=query.strip()[:100]
        with Session() as db:
            stmt=select(Photo)
            if not include_hidden:stmt=stmt.where(Photo.published.is_(True))
            if category:stmt=stmt.where(Photo.category==category)
            if query:stmt=stmt.where(or_(Photo.caption.ilike('%'+query+'%'),Photo.id.ilike('%'+query+'%'),Photo.filename.ilike('%'+query+'%')))
            total=db.scalar(select(func.count()).select_from(stmt.subquery()))
            rows=db.scalars(stmt.order_by(Photo.featured.desc(),Photo.display_order,Photo.id).offset((page-1)*page_size).limit(page_size)).all()
            counts={k:n for k,n in db.execute(select(Photo.category,func.count(Photo.id)).where(Photo.published.is_(True)).group_by(Photo.category)).all()}
            def item(p):
                source=lookup.get(p.id)
                if not source:return None
                return {'id':p.id,'path':source['optimized_paths']['large'],'thumb':source['optimized_paths']['thumb'],
                    'caption':p.caption,'alt':p.alt_text,'category':p.category,'width':source['width'],'height':source['height'],
                    'focal_point':p.focal_point,'featured':p.featured,'published':p.published,'display_order':p.display_order,
                    'archival_only':source['archival_only'],'verified_menu_item':False}
            return {'items':[x for p in rows if (x:=item(p)) is not None], 'total':total or 0,'page':page,'page_size':page_size,
                    'has_more':page*page_size<(total or 0),'counts':counts}

    @app.get('/api/v10/photos')
    def public_photos(category:str='',q:str='',page:int=1,page_size:int=24):
        return get_page(category,q,page,page_size)

    @app.get('/api/v10/admin/photos')
    def admin_photos(request:Request,category:str='',q:str='',page:int=1,page_size:int=24):
        authenticated(request)
        return get_page(category,q,page,page_size,include_hidden=True)

    @app.patch('/api/v10/admin/photos/{photo_id}')
    def update_photo(photo_id:str,request:Request,payload:PhotoEdit):
        admin_write(request)
        with Session() as db:
            obj=db.get(Photo,photo_id)
            if obj is None:raise HTTPException(404,'Unknown photo')
            changes=payload.model_dump(exclude_unset=True)
            if 'focal_point' in changes and changes['focal_point'] is not None:
                if not re.fullmatch(r'(?:100|\d{1,2})% (?:100|\d{1,2})%',changes['focal_point']):
                    raise HTTPException(422,'Focal point must be two percentages, e.g. 50% 50%')
            for key,value in changes.items():
                if value is not None:setattr(obj,key,value)
            audit(db,'photo.edit',photo_id)
            db.commit()
        return {'saved':True,'id':photo_id}
    return Photo
