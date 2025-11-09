"""
Vector Database for storing and retrieving conversation history
Uses Pinecone for vector search and sentence-transformers for embeddings
"""
import os
from typing import List, Dict, Optional
from datetime import datetime
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

# Initialize embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
INDEX_NAME = "ai-tutor-conversations"


class ConversationStore:
    """
    Stores and retrieves conversation history using vector embeddings.
    """

    def __init__(self):
        self.pc = None
        self.index = None

        if PINECONE_API_KEY:
            try:
                self.pc = Pinecone(api_key=PINECONE_API_KEY)

                # Create index if it doesn't exist
                if INDEX_NAME not in self.pc.list_indexes().names():
                    print(f"Creating Pinecone index: {INDEX_NAME}")
                    self.pc.create_index(
                        name=INDEX_NAME,
                        dimension=384,  # all-MiniLM-L6-v2 produces 384-dim vectors
                        metric='cosine',
                        spec=ServerlessSpec(
                            cloud='aws',
                            region=PINECONE_ENVIRONMENT
                        )
                    )

                self.index = self.pc.Index(INDEX_NAME)
                print(f"✅ Pinecone initialized: {INDEX_NAME}")

            except Exception as e:
                print(f"⚠️ Pinecone initialization failed: {e}")
                print("Vector search will be disabled.")
        else:
            print("⚠️ PINECONE_API_KEY not set. Vector search disabled.")

    def add_conversation(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a conversation exchange to the vector database.

        Args:
            user_id: The user's ID
            conversation_id: Unique conversation ID
            user_message: What the user said
            assistant_message: How the AI responded
            metadata: Additional metadata (question_id, skill_ids, etc.)

        Returns:
            True if successful, False otherwise
        """
        if not self.index:
            return False

        try:
            # Combine user and assistant messages for better context
            combined_text = f"User: {user_message}\nAssistant: {assistant_message}"

            # Generate embedding
            embedding = embedding_model.encode(combined_text).tolist()

            # Prepare metadata
            meta = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if metadata:
                meta.update(metadata)

            # Upsert to Pinecone
            self.index.upsert(
                vectors=[(
                    f"{user_id}_{conversation_id}_{datetime.utcnow().timestamp()}",
                    embedding,
                    meta
                )]
            )

            return True

        except Exception as e:
            print(f"Error adding conversation to vector DB: {e}")
            return False

    def search_similar_conversations(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar past conversations.

        Args:
            user_id: The user's ID
            query: The search query (e.g., current question or topic)
            top_k: Number of similar conversations to return
            filter_metadata: Additional filters (e.g., skill_id)

        Returns:
            List of similar conversation dictionaries
        """
        if not self.index:
            return []

        try:
            # Generate query embedding
            query_embedding = embedding_model.encode(query).tolist()

            # Build filter
            query_filter = {"user_id": user_id}
            if filter_metadata:
                query_filter.update(filter_metadata)

            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                filter=query_filter,
                include_metadata=True
            )

            # Extract results
            conversations = []
            for match in results['matches']:
                conversations.append({
                    "score": match['score'],
                    "conversation_id": match['metadata'].get('conversation_id'),
                    "user_message": match['metadata'].get('user_message'),
                    "assistant_message": match['metadata'].get('assistant_message'),
                    "timestamp": match['metadata'].get('timestamp'),
                    "metadata": {k: v for k, v in match['metadata'].items()
                               if k not in ['user_id', 'conversation_id', 'user_message',
                                          'assistant_message', 'timestamp']}
                })

            return conversations

        except Exception as e:
            print(f"Error searching conversations: {e}")
            return []

    def get_conversation_context(
        self,
        user_id: str,
        current_question: str,
        skill_id: Optional[str] = None
    ) -> str:
        """
        Get relevant past conversation context for the AI tutor.

        Args:
            user_id: The user's ID
            current_question: The current question being asked
            skill_id: Optional skill filter

        Returns:
            Formatted context string
        """
        filter_meta = {"skill_id": skill_id} if skill_id else None

        similar_convos = self.search_similar_conversations(
            user_id=user_id,
            query=current_question,
            top_k=3,
            filter_metadata=filter_meta
        )

        if not similar_convos:
            return ""

        context = "### Relevant Past Conversations:\n\n"
        for i, convo in enumerate(similar_convos, 1):
            context += f"**Conversation {i}** (similarity: {convo['score']:.2f}):\n"
            context += f"- Student asked: {convo['user_message']}\n"
            context += f"- AI responded: {convo['assistant_message'][:200]}...\n\n"

        return context

    def delete_user_conversations(self, user_id: str) -> bool:
        """
        Delete all conversations for a user (GDPR compliance).

        Args:
            user_id: The user's ID

        Returns:
            True if successful
        """
        if not self.index:
            return False

        try:
            # Pinecone delete by filter
            self.index.delete(filter={"user_id": user_id})
            return True
        except Exception as e:
            print(f"Error deleting user conversations: {e}")
            return False


# Global instance
conversation_store = ConversationStore()
