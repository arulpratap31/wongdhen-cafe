"""V13 curated public collection endpoints, isolated from V11 & booking APIs.

Publication rights remain controlled by the existing V10 photos table. V13 manifests
contain original source IDs, never create duplicate database rows or dish matches.
"""
import json
from collections import Counter
from pathlib import Path
from fastapi import HTTPException, Query
from sqlalchemy import select


def install_v13(app, Session, Photo, root):
    allocation=json.loads((Path(root)/'docs/V13_PHOTO_ALLOCATION.json').read_text(encoding='utf-8'))
    source=json.loads((Path(root)/'docs/V10_MEDIA_MANIFEST.json').read_text(encoding='utf-8'))
    assets={p['id']:p for p in source}
    asset_sizes=json.loads((Path(root)/'docs/V15_PHOTO_DIMENSIONS.json').read_text(encoding='utf-8'))
    if set(asset_sizes)!=set(assets):
        raise RuntimeError('V15 photographic dimension report does not match the source collection')
    sections=allocation['sections']
    counts={'home':40,'gallery':100,'menu':100,'about':50,'visit':75,'photo-book':75,'journal':100}
    if {key:len(v) for key,v in sections.items()}!=counts:
        raise RuntimeError('Invalid V13 section counts')
    all_ids=[i for ids in sections.values() for i in ids]
    if len(all_ids)!=540 or len(set(all_ids))!=483 or set(all_ids)!=set(assets):
        raise RuntimeError('V13 allocation did not preserve all 483 originals')
    if any(len(set(ids))!=len(ids) for ids in sections.values()):
        raise RuntimeError('V13 allocation contains an in-section duplicate')
    for p in source:
        for image_path in p['optimized_paths'].values():
            if not (Path(root)/image_path.lstrip('/')).is_file():
                raise RuntimeError('Missing photo asset '+image_path)

    def serialize(row,section):
        source_photo=assets[row.id]
        return {
            'id':row.id,'section':section,'category':row.category,
            'caption':row.caption,'alt':row.alt_text,
            'thumb':source_photo['optimized_paths']['thumb'],
            'path':source_photo['optimized_paths']['large'],
            'width':source_photo['width'],'height':source_photo['height'],
            'aspect_ratio':source_photo['aspect_ratio'],
            **asset_sizes[row.id],
            'focal_point':row.focal_point,'has_people':source_photo['has_people'],
            'archival_only':source_photo['archival_only'],
            'verified_menu_item':False,
        }

    @app.get('/api/v13/photos')
    def public_v13_photos(
        section:str=Query('gallery'),category:str=Query(''),q:str=Query('',max_length=100),
        page:int=Query(1,ge=1,le=100000),page_size:int=Query(30,ge=1,le=100)
    ):
        if section not in sections:
            raise HTTPException(422,'Unknown V13 photo collection')
        if category and category not in {'food','drinks','desserts','interiors','ambience','exterior','branding'}:
            raise HTTPException(422,'Invalid photo category')
        ids=sections[section]
        with Session() as db:
            rows=db.scalars(select(Photo).where(Photo.id.in_(ids),Photo.published.is_(True))).all()
            lookup={p.id:p for p in rows}
            ordered=[lookup[id] for id in ids if id in lookup]
            visible_total=len(ordered)
            counts_by_category=dict(Counter(r.category for r in ordered))
            if category:ordered=[r for r in ordered if r.category==category]
            needle=q.strip().casefold()
            if needle:
                ordered=[r for r in ordered if needle in r.id.casefold() or needle in r.caption.casefold() or needle in r.filename.casefold()]
            total=len(ordered)
            page_rows=ordered[(page-1)*page_size:page*page_size]
            return {'section':section,'items':[serialize(p,section) for p in page_rows],
                    'total':total,'section_total':visible_total,'page':page,'page_size':page_size,
                    'pages':max(1,(total+page_size-1)//page_size),'has_more':page*page_size<total,
                    'counts':counts_by_category,'chapters':allocation['chapters'].get(section,[]),
                    'default_section_size':len(ids)}

    @app.get('/api/v13/collections')
    def public_v13_collections():
        with Session() as db:
            visible=set(db.scalars(select(Photo.id).where(Photo.published.is_(True))).all())
        return {'unique_originals':483,'planned_placements':540,
                'published_originals':len(visible & set(assets)),
                'collections':{section:{'planned':len(ids),'published':sum(i in visible for i in ids),
                    'route':'/' if section=='home' else '/'+('journal' if section=='journal' else section)}
                    for section,ids in sections.items()}}
