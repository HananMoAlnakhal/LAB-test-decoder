"""
RAG Query Engine for Lab Report Decoder
Uses Hugging Face models for embeddings and generation
"""

from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import chromadb
from chromadb.config import Settings
from typing import List, Dict
from pdf_extractor import LabResult
import torch

class LabReportRAG:
    """RAG system for explaining lab results using Hugging Face models"""
    
    def __init__(self, db_path: str = "./chroma_db"):
        """Initialize the RAG system with Hugging Face models"""
        
        print("🔄 Loading Hugging Face models...")
        
        # Use smaller, faster models for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Use a medical-focused or general LLM
        # Options: 
        # - "microsoft/Phi-3-mini-4k-instruct" (good balance)
        # - "google/flan-t5-base" (lighter)
        # - "meta-llama/Llama-2-7b-chat-hf" (requires auth)
        
        model_name = "microsoft/Phi-3-mini-4k-instruct"
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            self.llm = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            print(f"✅ Loaded model: {model_name}")
        except Exception as e:
            print(f"⚠️ Could not load {model_name}, falling back to simpler model")
            # Fallback to lighter model
            self.text_generator = pipeline(
                "text-generation",
                model="google/flan-t5-base",
                max_length=512
            )
            self.llm = None
        
        # Load vector store
        try:
            self.client = chromadb.PersistentClient(path=db_path)
            self.collection = self.client.get_collection("lab_reports")
            print("✅ Vector database loaded")
        except Exception as e:
            print(f"⚠️ No vector database found. Please run build_vector_db.py first.")
            self.collection = None
    
    def _generate_with_phi(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate text using Phi-3 model"""
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        
        if torch.cuda.is_available():
            inputs = {k: v.to('cuda') for k, v in inputs.items()}
        
        outputs = self.llm.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            do_sample=True,
            top_p=0.9
        )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Remove the prompt from response
        response = response.replace(prompt, "").strip()
        return response
    
    def _generate_with_fallback(self, prompt: str) -> str:
        """Generate text using fallback pipeline"""
        result = self.text_generator(prompt, max_length=512, num_return_sequences=1)
        return result[0]['generated_text']
    
    def _generate_text(self, prompt: str) -> str:
        """Generate text using available model"""
        try:
            if self.llm is not None:
                return self._generate_with_phi(prompt)
            else:
                return self._generate_with_fallback(prompt)
        except Exception as e:
            print(f"Generation error: {e}")
            return "Sorry, I encountered an error generating the explanation."
    
    def _retrieve_context(self, query: str, k: int = 3) -> str:
        """Retrieve relevant context from vector database"""
        if self.collection is None:
            return "No medical reference data available."
        
        try:
            # Create query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k
            )
            
            # Combine documents
            if results and results['documents']:
                context = "\n\n".join(results['documents'][0])
                return context
            else:
                return "No relevant information found."
        except Exception as e:
            print(f"Retrieval error: {e}")
            return "Error retrieving medical information."
    
    def explain_result(self, result: LabResult) -> str:
        """Generate explanation for a single lab result"""
        
        # Retrieve relevant context
        query = f"{result.test_name} {result.status} meaning causes treatment"
        context = self._retrieve_context(query, k=3)
        
        # Create prompt
        prompt = f"""You are a helpful medical assistant. Explain this lab result in simple terms.

Medical Information:
{context}

Lab Test: {result.test_name}
Value: {result.value} {result.unit}
Reference Range: {result.reference_range}
Status: {result.status}

Please explain:
1. What this test measures
2. What this result means
3. Possible causes if abnormal
4. Dietary recommendations if applicable

Keep it simple and clear. Answer:"""

        # Generate explanation
        explanation = self._generate_text(prompt)
        
        return explanation
    
    def explain_all_results(self, results: List[LabResult]) -> Dict[str, str]:
        """Generate explanations for all lab results"""
        explanations = {}
        
        for result in results:
            print(f"Explaining {result.test_name}...")
            explanation = self.explain_result(result)
            explanations[result.test_name] = explanation
        
        return explanations
    
    def answer_followup_question(self, question: str, lab_results: List[LabResult]) -> str:
        """Answer follow-up questions about lab results"""
        
        # Create context from lab results
        results_context = "\n".join([
            f"{r.test_name}: {r.value} {r.unit} (Status: {r.status}, Range: {r.reference_range})"
            for r in lab_results
        ])
        
        # Retrieve relevant medical information
        medical_context = self._retrieve_context(question, k=3)
        
        # Create prompt
        prompt = f"""You are a medical assistant. Answer this question based on the patient's lab results and medical information.

Patient's Lab Results:
{results_context}

Medical Information:
{medical_context}

Question: {question}

Provide a clear, helpful answer. Answer:"""
        
        # Generate answer
        answer = self._generate_text(prompt)
        
        return answer
    
    def generate_summary(self, results: List[LabResult]) -> str:
        """Generate overall summary of lab results"""
        
        abnormal = [r for r in results if r.status in ['high', 'low']]
        normal = [r for r in results if r.status == 'normal']
        
        if not abnormal:
            return "✅ Great news! All your lab results are within normal ranges. Keep up the good work with your health!"
        
        # Get context about abnormal results
        queries = [f"{r.test_name} {r.status}" for r in abnormal]
        combined_query = " ".join(queries)
        context = self._retrieve_context(combined_query, k=4)
        
        # Create summary prompt
        abnormal_list = "\n".join([
            f"- {r.test_name}: {r.value} {r.unit} ({r.status})"
            for r in abnormal
        ])
        
        prompt = f"""Provide a brief summary of these lab results.

Normal Results: {len(normal)} tests
Abnormal Results: {len(abnormal)} tests

Abnormal Tests:
{abnormal_list}

Medical Context:
{context}

Write a 2-3 paragraph summary explaining what these results mean overall and general recommendations. Be reassuring but honest. Summary:"""
        
        # Generate summary
        summary = self._generate_text(prompt)
        
        return summary


# Example usage
if __name__ == "__main__":
    from pdf_extractor import LabResult
    
    # Initialize RAG system
    print("Initializing RAG system...")
    rag = LabReportRAG()
    
    # Example result
    test_result = LabResult(
        test_name="Hemoglobin",
        value="10.5",
        unit="g/dL",
        reference_range="12.0-15.5",
        status="low"
    )
    
    # Generate explanation
    print("\nGenerating explanation...")
    explanation = rag.explain_result(test_result)
    print(f"\n{explanation}")