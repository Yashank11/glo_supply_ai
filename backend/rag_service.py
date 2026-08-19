import os
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

class VectorRAGService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.embedding_model = "models/text-embedding-004"
        self.generation_model = "gemini-3.1-flash-lite"
        
        # In-memory document storage: list of dicts {"id", "text", "metadata", "embedding"}
        self.documents = []
        self.seed_knowledge_base()

    def get_embedding(self, text: str) -> np.ndarray:
        """
        Calls Gemini API to generate a vector embedding.
        """
        if not self.api_key:
            # Fallback random vector if no key is configured
            return np.random.rand(768)
            
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return np.array(result["embedding"])
        except Exception as e:
            print(f"Error fetching embedding: {e}")
            return np.random.rand(768) # fallback placeholder

    def index_document(self, doc_id: str, text: str, metadata: dict = None):
        """
        Generates vector and indexes document.
        """
        emb = self.get_embedding(text)
        self.documents.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
            "embedding": emb
        })

    def search(self, query: str, top_k: int = 2) -> list:
        """
        Executes semantic search using Cosine Similarity on embeddings.
        """
        if not self.documents:
            return []
            
        query_emb = self.get_embedding(query)
        results = []
        
        for doc in self.documents:
            # Calculate Cosine Similarity: dot(a, b) / (norm(a) * norm(b))
            dot_product = np.dot(query_emb, doc["embedding"])
            norm_q = np.linalg.norm(query_emb)
            norm_d = np.linalg.norm(doc["embedding"])
            
            similarity = dot_product / (norm_q * norm_d) if norm_q > 0 and norm_d > 0 else 0.0
            
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "metadata": doc["metadata"],
                "similarity_score": float(similarity)
            })
            
        # Sort by similarity descending
        results = sorted(results, key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

    def generate_rag_answer(self, query: str) -> str:
        """
        Searches semantic database, appends matches as context, and runs LLM question-answering.
        """
        matches = self.search(query, top_k=2)
        
        # Build context string
        context_str = ""
        for i, match in enumerate(matches):
            context_str += f"[Source {i+1}: doc_id={match['id']}, score={match['similarity_score']:.3f}]\n{match['text']}\n\n"
            
        prompt = f"""
        You are a Supply Chain Consultant. Answer the user query using only the provided contract and policy context below.
        If the answer cannot be found in the context, use your general knowledge but clearly state that it is outside the formal contract records.
        
        ---
        CONTEXT RECORDS:
        {context_str}
        ---
        
        USER QUERY: "{query}"
        
        ANSWER (Structured, fact-based):
        """
        try:
            model = genai.GenerativeModel(model_name=self.generation_model)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error executing RAG: {e}"

    def seed_knowledge_base(self):
        """
        Seeds vector database with realistic vendor agreements and compliance policies.
        """
        contracts = [
            (
                "contract_tsmc_2026",
                "Master Semiconductor Foundry Agreement between Apple Inc. and TSMC (2026). "
                "Section 8.2 (Force Majeure): Neither party shall be liable for failures due to earthquakes, "
                "typhoons, military conflicts in the Taiwan Strait, or export blocks. In the event of a force majeure "
                "exceeding 14 consecutive days, Apple retains the right to reroute wafer fabrication allocation to alternate foundries "
                "without penalty, provided 48 hours notice is given. Payment terms: Net 60 days.",
                {"vendor": "TSMC", "type": "Foundry Contract"}
            ),
            (
                "policy_lithium_compliance",
                "Global Minerals & Battery Cell Compliance Guidelines (2025). "
                "All battery component sourcing must pass ESG audits. CATL supply chains in Ningde are rated Class-A for "
                "carbon offset and environmental compliance. Backup suppliers in Korea (LG Energy Solution) are audited "
                "and pre-approved for secondary raw mineral sourcing in South America (Chile, Argentina) for Lithium Carbonate. "
                "Standard Lead times: Ocean transport is 22 days, Air freight is 3 days.",
                {"type": "Compliance Policy"}
            ),
            (
                "contract_asml_litho",
                "Lithography Equipment Procurement Agreement with ASML Netherlands. "
                "ASML warrants regular software patches and operational engineering support on-site at TSMC Fab 18. "
                "Delivery lead times for Extreme Ultraviolet (EUV) systems: 18 months from purchase order confirmation. "
                "Late delivery penalties: 0.5% of purchase value per week of delay, capped at 10% total.",
                {"vendor": "ASML", "type": "Procurement Contract"}
            )
        ]
        
        for doc_id, text, meta in contracts:
            self.index_document(doc_id, text, meta)
