from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class LLMQuery(Base):
    __tablename__ = 'llm_queries'
    id = Column(Integer, primary_key=True)
    query_text = Column(Text, nullable=False)
    llm_model = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    responses = relationship("LLMResponse", back_populates="query")

class LLMResponse(Base):
    __tablename__ = 'llm_responses'
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey('llm_queries.id'))
    response_text = Column(Text, nullable=False)
    full_raw_response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    query = relationship("LLMQuery", back_populates="responses")
    mentions = relationship("ProductMention", back_populates="response")

class ProductMention(Base):
    __tablename__ = 'product_mentions'
    id = Column(Integer, primary_key=True)
    response_id = Column(Integer, ForeignKey('llm_responses.id'))
    product_name = Column(String(200), nullable=False)
    context = Column(Text)
    sentiment = Column(String(50))
    attributes = Column(Text)
    response = relationship("LLMResponse", back_populates="mentions")

class AuthoritativeSource(Base):
    __tablename__ = 'authoritative_sources'
    id = Column(Integer, primary_key=True)
    source_name = Column(String(500), nullable=False)
    source_url = Column(String(1000))
    mention_count = Column(Integer, default=0)
    example_quote = Column(Text)
    first_detected = Column(DateTime, default=datetime.utcnow)
    
class BlindSpot(Base):
    __tablename__ = 'blind_spots'
    id = Column(Integer, primary_key=True)
    source_name = Column(String(500), nullable=False)
    source_type = Column(String(100))
    competitors = Column(Text)
    context = Column(Text)
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolution_method = Column(String(200)) 

class GeneratedContent(Base):
    __tablename__ = 'generated_content'
    id = Column(Integer, primary_key=True)
    content_type = Column(String(100))
    target_product = Column(String(200))
    content_text = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    based_on_sources = Column(Text)

class ReputationTracking(Base):
    __tablename__ = 'reputation_tracking'
    id = Column(Integer, primary_key=True)
    product_name = Column(String(200), nullable=False)
    mention_count = Column(Integer, default=0)
    avg_sentiment_score = Column(Float)
    date_recorded = Column(DateTime, default=datetime.utcnow)


class AnalysisSession(Base):
    __tablename__ = 'analysis_sessions'
    
    id = Column(Integer, primary_key=True)
    session_type = Column(String(50))
    queries_count = Column(Integer, default=0)
    mentions_found = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20), default='running')
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<AnalysisSession(id={self.id}, type='{self.session_type}', status='{self.status}')>"

engine = create_engine('sqlite:///ai_pr.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)