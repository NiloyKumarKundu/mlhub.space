from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import trim_messages
from operator import itemgetter
import streamlit as st
import uuid
from src import logger

class Chatbot:
    def __init__(self):
        # Initialize the store dictionary
        self.store = {}
        
        # Initialize or get session ID from Streamlit's session state
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        self.session_id = st.session_state.session_id

    def get_session_history(self):
        """Retrieve chat history for the current session."""
        if self.session_id not in self.store:
            self.store[self.session_id] = InMemoryChatMessageHistory()
        return self.store[self.session_id]

    def get_prompt(self):
        """Return the chatbot's prompt."""
        
        system_prompt = """
        
        You are an advanced AI assistant on **MLHub.space**, a platform hosting multiple Large Language Models (LLMs) to assist users with interactive problem-solving. Your primary goal is to provide clear, structured, and insightful responses while following these specific guidelines:
        
        # 1️⃣ Owner Information Disclosure:
        
        If a user inquires about the owner of this platform, provide the following details:
        
            👤 Owner: Niloy Kumar Kundu
            
            📧 Email: niloykk.connect@gmail.com
            
            🔗 LinkedIn: https://linkedin.com/in/niloykk
            
            💻 GitHub: https://github.com/NiloyKumarKundu

        # 2️⃣ Math Problem Solving Approach 🧮
        
        When solving a math problem, always:
        
            - ✅ Break it down into multiple logical steps first.
            
            - ✅ Explain each step before proceeding to the next.
            
            - ✅ Ensure clarity by maintaining a structured approach.
            
            - ✅ Provide the final answer with a brief summary.

        For example, if solving an equation:
        
           - 1️⃣ Identify the given information.
            
           - 2️⃣ Define the variables.
            
           - 3️⃣ Apply relevant formulas or rules.
            
           - 4️⃣ Show intermediate calculations.
            
           - 5️⃣ Arrive at the final solution with a concluding remark.

        By following these instructions, you will ensure high-quality responses that are both informative and easy to understand.
        """
        
        prompt_template = ChatPromptTemplate([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name='messages'),
        ])
        return prompt_template

    def get_model(self, model):
        """Load the chatbot model."""
        try:
            llm = ChatOllama(
                model=model,
                convert_system_message_to_human=True
            )
            return llm
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def get_trimmer(self, model):
        """Set up message trimming logic."""
        trimmer = trim_messages(
            max_tokens=1024,
            strategy="last",
            token_counter=self.get_model(model),
            include_system=True,
            allow_partial=False,
            start_on='human'
        )
        return trimmer

    def get_chain(self, model):
        """Build the chain for processing the messages."""
        llm = self.get_model(model)
        output_parser = StrOutputParser()
        prompt = self.get_prompt()
        trimmer = self.get_trimmer(model)
        
        chain = (
            RunnablePassthrough.assign(messages=itemgetter("messages") | trimmer)
            | prompt
            | llm
            | output_parser
        )
        return chain

    def process_input(self, user_input):
        """Process user input through the chain."""
        chain = self.get_chain()
        model_with_history = RunnableWithMessageHistory(
            chain,
            self.get_session_history,
            input_messages_key='messages'
        )
        response = model_with_history.invoke(
            {'messages': user_input},
            config={'configurable': {'session_id': self.session_id}}
        )
        return model_with_history, response

    async def process_input_streaming(self, user_input, model):
        """Process user input and yield streamed chunks."""
        chain = self.get_chain(model)
        model_with_history = RunnableWithMessageHistory(
            chain,
            self.get_session_history,
            input_messages_key='messages'
        )
        async for chunk in model_with_history.astream(
            {'messages': user_input},
            config={'configurable': {'session_id': self.session_id}}
        ):
            yield chunk

    def reset_session(self):
        """Reset the current session's chat history."""
        if self.session_id in self.store:
            del self.store[self.session_id]
            # Generate new session ID
            st.session_state.session_id = str(uuid.uuid4())
            self.session_id = st.session_state.session_id