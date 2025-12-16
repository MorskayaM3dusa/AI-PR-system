import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from database import SessionLocal, LLMQuery, LLMResponse
import config
import time
from mistralai import Mistral

def create_prompt_for_query(user_query: str) -> str:
    """Создает оптимизированный промпт для анализатора рынка"""
    prompt_template = """You are a market research analyst specializing in workflow automation tools. 
Please provide a comprehensive analysis based on the following query. 
Your response should be in English and include:

1. Overview of relevant automation tools
2. Key features comparison
3. Pricing information if available
4. Target audience suitability
5. Strengths and weaknesses of each tool
6. Real-world use cases
7. Recommendations based on different scenarios

Focus on these specific tools when relevant: n8n, Zapier, Make (formerly Integromat), Microsoft Power Automate, IFTTT.
If other tools are mentioned, include them as well.

Query: {query}

Provide a detailed, objective analysis:"""
    
    return prompt_template.format(query=user_query)

def query_mistral(prompt: str, model: str = config.MISTRAL_MODEL) -> str:
    """Sends request to Mistral AI (for version 1.x.x)"""
    try:
        client = Mistral(api_key=config.MISTRAL_API_KEY)
        
        chat_response = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
            top_p=0.9
        )
        
        answer = chat_response.choices[0].message.content
        answer = answer.replace("*", "").replace("#", "").strip()

        if hasattr(chat_response, 'usage'):
            print(f"Tokens used: {chat_response.usage.total_tokens}")
            
        return answer
            
    except Exception as e:
        print(f"Error querying Mistral AI: {e}")
        return ""

def process_single_query(query_text: str, query_index: int, total_queries: int) -> bool:
    """Processes a single query and saves results to database"""
    db = SessionLocal()
    success = False
    
    try:
        full_prompt = create_prompt_for_query(query_text)
        
        print(f"[{query_index}/{total_queries}] Processing query: {query_text[:80]}...")

        query_record = LLMQuery(
            query_text=query_text,
            llm_model=config.MISTRAL_MODEL
        )
        db.add(query_record)
        db.commit()
        db.refresh(query_record)

        response_text = query_mistral(full_prompt)
        
        if response_text:
            response_record = LLMResponse(
                query_id=query_record.id,
                response_text=response_text,
                full_raw_response=response_text
            )
            db.add(response_record)
            db.commit()
            
            word_count = len(response_text.split())
            print(f"Response saved ({len(response_text)} chars, {word_count} words)")
            success = True
        else:
            print(f"Empty response from Mistral AI")
            response_record = LLMResponse(
                query_id=query_record.id,
                response_text="",
                full_raw_response=""
            )
            db.add(response_record)
            db.commit()
            
    except Exception as e:
        print(f"Error processing query: {e}")
        db.rollback()
        
    finally:
        db.close()
        
    return success

def run_analysis_queries():
    """Runs all queries from config and saves results to database"""
    total_queries = len(config.SAMPLE_QUERIES)
    successful_queries = 0
    
    print(f"Starting market analysis with {total_queries} queries")
    print(f"Using model: {config.MISTRAL_MODEL}")
    
    for idx, query_text in enumerate(config.SAMPLE_QUERIES, 1):
        try:
            success = process_single_query(query_text, idx, total_queries)
            if success:
                successful_queries += 1

            if idx < total_queries:
                delay_time = 60.0 / config.MISTRAL_RATE_LIMIT
                time.sleep(delay_time)
                
        except KeyboardInterrupt:
            print("Analysis interrupted by user")
            break
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            continue

    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETED")
    print(f"{'='*60}")
    print(f"Total queries: {total_queries}")
    print(f"Successful: {successful_queries}")
    print(f"Success rate: {(successful_queries/total_queries)*100:.1f}%")
    print(f"Results saved to database")
    print(f"{'='*60}")
    
    if successful_queries == 0:
        print("\nAnalysis failed - no successful queries")
        sys.exit(1)

def test_mistral_connection():
    """Tests connection to Mistral AI API"""
    print("Testing Mistral AI connection...")
    
    try:
        client = Mistral(api_key=config.MISTRAL_API_KEY)

        test_prompt = "Hello, please respond with 'Connection successful'."
        response = client.chat.complete(
            model=config.MISTRAL_MODEL,
            messages=[{"role": "user", "content": test_prompt}],
            max_tokens=10
        )
        
        if response.choices[0].message.content:
            print("Mistral AI connection successful")
            return True
        else:
            print("Empty response from Mistral AI")
            return False
            
    except Exception as e:
        print(f"Mistral AI connection failed: {e}")
        return False

if __name__ == "__main__":
    if not config.MISTRAL_API_KEY:
        print("Error: MISTRAL_API_KEY not found in environment variables")
        print("Please set it in your .env file or environment")
        sys.exit(1)
    
    if test_mistral_connection():
        run_analysis_queries()
    else:
        print("Cannot proceed - Mistral AI connection failed")
        sys.exit(1)