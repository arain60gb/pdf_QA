from django.shortcuts import render, redirect
from .models import UploadedDocument
import openai
import uuid  # To generate a unique vector store ID

# Initialize the OpenAI client with your API key (GPT-4 model used)

def upload_pdf_page(request):
    """Render the PDF upload page and handle uploads and question submissions."""
    uploaded_files = UploadedDocument.objects.all()  # Fetch all uploaded PDFs
    answer = None
    question = None

    if request.method == 'POST':
        if 'pdf_file' in request.FILES:
            # Handle PDF upload
            pdf_file = request.FILES['pdf_file']
            # Generate a unique vector store ID (modify this as needed for your logic)
            vector_store_id = str(uuid.uuid4())  # Use UUID for unique ID

            # Save the uploaded document with the file name and vector store ID
            UploadedDocument.objects.create(file_name=pdf_file.name, vector_store_id=vector_store_id)
            return redirect('upload_pdf_page')  # Redirect to avoid form resubmission

        elif 'uploaded_file' in request.POST and 'question' in request.POST:
            # Handle question submission
            uploaded_file_id = request.POST['uploaded_file']
            question = request.POST['question']
            uploaded_file = UploadedDocument.objects.get(id=uploaded_file_id)

            # Call the function to ask a question using vector store ID
            answer = ask_question_with_vector_id(uploaded_file.vector_store_id, question)

    return render(request, 'upload_pdf.html', {
        'uploaded_files': uploaded_files,
        'answer': answer,
        'question': question
    })

def ask_question_with_vector_id(vector_store_id, question):
    """Generate an answer using the OpenAI API based on the document content tied to the vector store ID."""
    # Retrieve document content associated with the vector store ID
    document_data = get_document_data_by_vector_id(vector_store_id)

    if "Document not found" in document_data:
        return document_data  # Return error if no document is found

    # Generate answer using OpenAI GPT-4 model
    response = openai.ChatCompletion.create(
        model="gpt-4o",  # 
        messages=[
            {
                "role": "user",
                "content": f"The following document is associated with the vector ID {vector_store_id}: {document_data}. "
                           f"Based on this document, the user asks: {question}"
            }
        ],
        max_tokens=150
    )
    return response['choices'][0]['message']['content'].strip()

def get_document_data_by_vector_id(vector_store_id):
    """Retrieve document data associated with the given vector store ID."""
    try:
        # Get the uploaded document by vector store ID
        uploaded_document = UploadedDocument.objects.get(vector_store_id=vector_store_id)
        document_data = f"Title: {uploaded_document.file_name}"  # Return relevant data
        return document_data
    except UploadedDocument.DoesNotExist:
        return "Document not found for the provided vector store ID."
