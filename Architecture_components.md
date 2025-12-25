Raw Data: 
=======> AWS S3.

Chunks, embeddings: 
=======> Pinecone 

Metadata: 
=======> Production: Postgres, over Render 
=======> Development: Local postgres (docker) 

Frontend: 
=======> Production: Vercal
=======> Development: localhost

Backend API:
=======> Production: FastAPI web server running on Render 
=======> Development: localhost

Handles authentication (Clerk)
Manages documents, insights, training data
Interfaces with Pinecone, S3, PostgreSQL
Provides CORS-enabled API endpoints
