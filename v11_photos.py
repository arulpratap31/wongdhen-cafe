"""V11 public photographic collections, backed by V10's editable catalog.

Every photograph has a single primary editorial placement. The existing V10
publication settings remain authoritative; no duplicate media records are added.
"""
import json
from collections import Counter
from pathlib import Path
from fastapi import HTTPException, Query
from sqlalchemy import select


def install_v11(app, Session, Photo, root):
    allocation=json.loads((Path(root)/'docs/V11_PHOTO_ALLOCATION.json').read_text(encoding='utf-8'))
    source=json.loads((Path(root)/'docs/V10_MEDIA_MANIFEST.json').read_text(encoding='utf-8'))
    media={p['id']:p for p in source}
    sections=allocation['sections']
    assert len(sections)==7
    assert sum(map(len,sections.values()))==483
    assert len(set(sum(sections.values(),[])))==483
    assert set(sum(sections.values(),[]))==set(media)
    def serialize(row,section):
        original=media[row.id]
        return {
            'id':row.id,'section':section,'category':row.category,
            'caption':row.caption,'alt':row.alt_text,
            'thumb':original['optimized_paths']['thumb'],
            'path':original['optimized_paths']['large'],
            'width':original['width'],'height':original['height'],
            'focal_point':row.focal_point,'archival_only':original['archival_only'],
            'verified_menu_item':False,
        }

    @app.get('/api/v11/photos')
    def public_v11_photos(
        section:str=Query('gallery'),category:str=Query(''),q:str=Query('',max_length=100),
        page:int=Query(1,ge=1,le=100000),page_size:int=Query(30,ge=1,le=60)
    ):
        if section not in sections:
            raise HTTPException(422,'Unknown photographic section')
        if category and category not in {'food','drinks','desserts','interiors','ambience','exterior','branding'}:
            raise HTTPException(422,'Unknown category')
        ids=sections[section]
        with Session() as db:
            # Preserve staff publication edits; unpublishing a photo hides it everywhere.
            rows=db.scalars(select(Photo).where(Photo.id.in_(ids),Photo.published.is_(True))).all()
            mapped={r.id:r for r in rows}
            ordered=[mapped[i] for i in ids if i in mapped]
            counts=dict(Counter(r.category for r in ordered))
            if category:ordered=[r for r in ordered if r.category==category]
            if q.strip():
                needle=q.strip().casefold()
                ordered=[r for r in ordered if needle in r.id.casefold() or needle in r.caption.casefold() or needle in r.filename.casefold()]
            total=len(ordered)
            result=ordered[(page-1)*page_size:page*page_size]
            return {'section':section,'items':[serialize(r,section) for r in result],
                    'total':total,'section_total':len(rows),'page':page,'page_size':page_size,
                    'pages':max(1,(total+page_size-1)//page_size),
                    'has_more':page*page_size<total,'counts':counts}

    @app.get('/api/v11/collections')
    def public_v11_collections():
        with Session() as db:
            published=set(db.scalars(select(Photo.id).where(Photo.published.is_(True))).all())
        return {'total_published':len(published & set(media)),
                'collections':{s:{'total':sum(id in published for id in ids),'route':{
                    'home':'/','gallery':'/gallery','menu':'/menu','about':'/about',
                    'visit':'/visit','photo-book':'/photo-book','journal':'/journal'
                }[s]} for s,ids in sections.items()}}
