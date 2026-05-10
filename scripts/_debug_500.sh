#!/usr/bin/env bash
cd /home/jb/dev/hydra
# Run inside container with full traceback
docker compose exec hydra-console python -c "
import sys
sys.path.insert(0, '/app')
import os
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://hydra:hydra@postgres:5432/hydra')

from sqlalchemy import create_engine, desc, select
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)
session = Session()

from db import Product, ProductArtifact, ProductFile, Listing, LlmCall

product_id = 40
product = session.get(Product, product_id)
print('product:', product.title if product else None)

artifacts = session.scalars(select(ProductArtifact).where(ProductArtifact.product_id == product_id).order_by(desc(ProductArtifact.created_at))).all()
print('artifacts:', len(artifacts))

files = session.scalars(select(ProductFile).where(ProductFile.product_id == product_id).order_by(desc(ProductFile.created_at))).all()
print('files:', len(files))

listings = session.scalars(select(Listing).where(Listing.product_id == product_id).order_by(Listing.platform)).all()
print('listings:', len(listings))

recent_llm = session.scalars(select(LlmCall).order_by(desc(LlmCall.created_at)).limit(5)).all()
print('recent_llm_calls:', len(recent_llm))
for c in recent_llm:
    print('  call:', c.purpose, c.status, 'error_type attr:', hasattr(c, 'error_type'), getattr(c, 'error_type', 'MISSING'))

session.close()
print('DB queries OK')
" 2>&1
