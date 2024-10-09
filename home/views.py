from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib import messages
import os
from openai import OpenAI, AssistantEventHandler

# Initialize OpenAI client

# Define the event handler for streaming responses
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.answer = None  # Initialize an attribute to store the answer

    def on_text_created(self, text) -> None:
        print(f"\nassistant > {text}", end="", flush=True)
        if self.answer is None:  # Store the first answer received
            self.answer = text  # Assuming text contains the answer

    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > Tool call created: {tool_call.type}\n", flush=True)

    def on_message_done(self, message) -> None:
        print("\nMessage done. Final message received.")
        if message.content:
            # Check if message.content is not empty and extract the answer
            self.answer = message.content[0].text if message.content else "No content available"
            print("Extracted answer:", self.answer)

# Render the upload page with an HTML input field for the file
def upload_pdf_page(request, vector_store_id=None):
    return render(request, 'upload_pdf.html', {'vector_store_id': vector_store_id})

# Handle the file upload and display messages
def upload_pdf(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        file = request.FILES['pdf_file']

        # Save the uploaded file temporarily
        file_name = default_storage.save(file.name, ContentFile(file.read()))
        file_path = default_storage.path(file_name)

        try:
            # Process the PDF with OpenAI
            vector_store_name = "Uploaded_Documents"
            vector_store = upload_file_and_create_vector_store(file_path, vector_store_name)

            # Clean up the temporary file
            os.remove(file_path)

            # Add a success message
            messages.success(request, 'File uploaded and processed successfully.')

            # Redirect to the upload page with the vector_store_id
            return redirect('upload_pdf_page_with_id', vector_store_id=vector_store.id)

        except Exception as e:
            # Add an error message in case of failure
            messages.error(request, f'Error uploading file: {str(e)}')

        return redirect('upload_pdf_page')  # Redirect back to the upload page if there is an error

    # If no file is provided, add an error message
    messages.error(request, 'No file provided.')
    return redirect('upload_pdf_page')

# Function for file processing with OpenAI
def upload_file_and_create_vector_store(file_path: str, vector_store_name: str):
    # Create a vector store for the PDFs
    vector_store = client.beta.vector_stores.create(name=vector_store_name)

    # Open the PDF file in binary mode and upload to OpenAI
    with open(file_path, "rb") as file_stream:
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id, files=[file_stream]
        )

    print("File uploaded and processed.")
    print(f"File Batch Status: {file_batch.status}")
    return vector_store

# Function to ask a question using the vector store with streaming response
def ask_question_with_file_search(question: str, vector_store_id: str):
    try:
        # Create a new thread with the question and reference the vector store
        thread = client.beta.threads.create(
            messages=[{"role": "user", "content": question}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
        )

        # Run the assistant and stream the response using an event handler
        event_handler = EventHandler()

        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions="Please address the user as Jane Doe. The user has a premium account.",
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        # Return the collected answer from the event handler
        return event_handler.answer

    except Exception as e:
        print(f"Error during question processing: {str(e)}")  # Log any error that occurs
        return None  # Return None or an appropriate error message

# Initialize the assistant with file search tool
def initialize_assistant():
    return client.beta.assistants.create(
        name="PDF File QA Assistant",
        instructions="You are an assistant who answers questions based on the content of uploaded PDF files.",
        model="gpt-4o",
        tools=[{"type": "file_search"}]
    )

# Initialize the assistant (do this only once)
assistant = initialize_assistant()

# Handle the question asking
def ask_question(request):
    if request.method == 'POST':
        question = request.POST.get('question')
        vector_store_id = request.POST.get('vector_store_id')

        try:
            answer = ask_question_with_file_search(question, vector_store_id)

            if answer:
                final_answer = getattr(answer, 'value', str(answer))  # Extract 'value' if exists, else fallback to string
                print("Answer:", final_answer)

                # Pass the question and answer to the template
                context = {
                    'answer': final_answer,
                    'question': question,  # Pass the question
                    'vector_store_id': vector_store_id
                }
                messages.success(request, 'Question asked successfully.')
                return render(request, 'upload_pdf.html', context)
            else:
                messages.error(request, 'No answer found for the question.')
        except Exception as e:
            messages.error(request, f'Error asking question: {str(e)}')

        return redirect('upload_pdf_page_with_id', vector_store_id=vector_store_id)

    messages.error(request, 'Invalid request method.')
    return redirect('upload_pdf_page')
